import json
import time
import re
import os
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

API_KEY = "1fbcb4ca0bad271b0780c0a848e8c05b"

URLS = [
    {"url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/", "deal": "بيع", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/", "deal": "إيجار", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/rooms-for-rent/new-cairo/", "deal": "إيجار", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/", "deal": "بيع", "category": "فيلا"},
    {"url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/", "deal": "إيجار", "category": "فيلا"},
    {"url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/", "deal": "بيع", "category": "تجاري وإداري"},
    {"url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/", "deal": "إيجار", "category": "تجاري وإداري"}
]

BROKER_KEYWORDS = [
    "شركة", "للعقارات", "التسويق العقاري", "بروكر", "سمسار", "عمولة", "مكتب عقارات",
    "real estate", "property", "properties", "agency", "broker", "consultancy", "investment",
    "verified business", "featured business"
]

SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

def fetch_via_api(target_url):
    for extra in [{"render": "false"}, {"premium": "true"}, {"render": "true"}]:
        try:
            params = {"api_key": API_KEY, "url": target_url}
            params.update(extra)
            res = requests.get("http://api.scraperapi.com", params=params, timeout=35)
            if res.status_code == 200 and ("/ad/" in res.text or "<article" in res.text):
                return res.text
        except Exception as e:
            print(f"Fetch error: {e}")
    return ""

def detect_subtype(title, description, category):
    if category != "شقق":
        return category
    text = (title + " " + description).lower()
    if any(w in text for w in ["بنتهاوس", "بنت هاوس", "penthouse"]):
        return "بنتهاوس"
    if any(w in text for w in ["دوبلكس", "دوبليكس", "duplex"]):
        return "دوبلكس"
    if any(w in text for w in ["استوديو", "ستوديو", "studio"]):
        return "استوديو"
    if any(w in text for w in ["روف", "رووف", "roof"]):
        return "روف"
    if any(w in text for w in ["غرفة", "غرفه", "room"]):
        return "غرفة"
    return "شقة"

def is_broker_text(text):
    low = text.lower()
    return any(kw in low for kw in BROKER_KEYWORDS)

def scrape_all():
    now_ts = int(time.time())
    cairo_tz = timezone(timedelta(hours=2))
    now_cairo = datetime.now(cairo_tz).strftime("%Y/%m/%d، %I:%M %p")

    existing_ads = []
    blocked_users = set()

    if os.path.exists("ads.json"):
        try:
            with open("ads.json", "r", encoding="utf-8") as f:
                old_data = json.load(f)
                existing_ads = old_data.get("ads", [])
                blocked_users = set(old_data.get("blocked_users", []))
        except Exception:
            pass

    valid_existing_ads = []
    for ad in existing_ads:
        ad_ts = ad.get("scraped_timestamp", now_ts)
        seller_prof = ad.get("seller_profile", "")
        if (now_ts - ad_ts) < SEVEN_DAYS_SECONDS and (not seller_prof or seller_prof not in blocked_users):
            valid_existing_ads.append(ad)

    seen_urls = {ad.get("url") for ad in valid_existing_ads if ad.get("url")}
    candidate_ads = []
    seller_ad_counts = {}

    for cat in URLS:
        print(f"Scraping: {cat['url']}")
        html = fetch_via_api(cat["url"])
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("article")
        if not cards:
            cards = [a.find_parent("div") or a for a in soup.find_all("a", href=re.compile(r"/ad/"))]

        for card in cards:
            card_html = str(card)
            if "/companies/" in card_html or "/agencies/" in card_html:
                for a in card.find_all("a", href=True):
                    if "/companies/" in a["href"] or "/agencies/" in a["href"]:
                        blocked_users.add(a["href"])
                continue

            link_el = card.find("a", href=re.compile(r"/ad/")) if card.name != "a" else card
            if not link_el or not link_el.get("href"):
                continue

            href = link_el["href"]
            ad_url = "https://www.dubizzle.com.eg" + href if href.startswith("/") else href
            if ad_url in seen_urls:
                continue

            card_text = card.get_text(" | ", strip=True)
            if is_broker_text(card_text):
                blocked_users.add(ad_url)
                continue

            seller_name = "مالك"
            seller_key = ad_url
            for a in card.find_all("a", href=True):
                if "/profile/" in a["href"]:
                    seller_key = a["href"]
                    seller_name = a.get_text(strip=True) or "مالك"
                    break

            if seller_key in blocked_users:
                continue

            seller_ad_counts[seller_key] = seller_ad_counts.get(seller_key, 0) + 1
            if seller_ad_counts[seller_key] > 7:
                blocked_users.add(seller_key)
                continue

            title_el = card.find("h2") or link_el
            title = title_el.get_text(strip=True) if title_el else ""
            if len(title) < 5:
                parts = [p.strip() for p in card_text.split("|") if len(p.strip()) > 10]
                title = parts[0] if parts else "عقار من المالك بالقاهرة الجديدة"

            price_text = "غير محدد"
            price_num = 0
            price_match = re.search(r"([\d,]+)\s*(?:ج\.م|جنيه|EGP)", card_text) or re.search(r"(?:ج\.م|EGP)\s*([\d,]+)", card_text)
            if price_match:
                price_num = int(price_match.group(1).replace(",", ""))
                price_text = f"{price_num:,} ج.م"

            area_match = re.search(r"(\d+)\s*(?:م²|متر|sqm|m²|م٢)", card_text, re.I)
            beds_match = re.search(r"(\d+)\s*(?:غرف|غرفة|beds|bed)", card_text, re.I)
            baths_match = re.search(r"(\d+)\s*(?:حمام|حمامات|baths|bath)", card_text, re.I)

            area = area_match.group(1) + " م²" if area_match else "غير محدد"
            beds = beds_match.group(1) + " غرف" if beds_match else ""
            baths = baths_match.group(1) + " حمام" if baths_match else ""

            clean_desc = "\n".join([p.strip() for p in card_text.split("|") if len(p.strip()) > 3])
            subtype = detect_subtype(title, clean_desc, cat["category"])

            seen_urls.add(ad_url)
            candidate_ads.append({
                "title": title,
                "url": ad_url,
                "price_text": price_text,
                "price_num": price_num,
                "deal": cat["deal"],
                "category": cat["category"],
                "subtype": subtype,
                "location": "القاهرة الجديدة",
                "area": area,
                "beds": beds,
                "baths": baths,
                "description": clean_desc,
                "seller_name": seller_name,
                "seller_profile": seller_key,
                "seller_ads_count": 1,
                "scraped_timestamp": now_ts,
                "scraped_date": now_cairo
            })

    new_ads = []
    for ad in candidate_ads:
        sk = ad["seller_profile"]
        count = seller_ad_counts.get(sk, 1)
        if sk in blocked_users or count > 4:
            continue
        ad["seller_ads_count"] = count
        new_ads.append(ad)

    final_ads = new_ads + valid_existing_ads

    payload = {
        "last_scrape": now_cairo,
        "total": len(final_ads),
        "blocked_count": len(blocked_users),
        "blocked_users": list(blocked_users),
        "ads": final_ads
    }

    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Done. Saved {len(final_ads)} owner ads, blocked {len(blocked_users)} brokers.")

if __name__ == "__main__":
    scrape_all()
