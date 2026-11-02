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
    "real estate", "property", "properties", "agency", "broker", "consultancy", "investment", "group"
]

SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

def fetch_via_api(target_url):
    modes = [
        {"api_key": API_KEY, "url": target_url},
        {"api_key": API_KEY, "url": target_url, "premium": "true"},
        {"api_key": API_KEY, "url": target_url, "render": "true"}
    ]
    for params in modes:
        try:
            res = requests.get("http://api.scraperapi.com", params=params, timeout=60)
            if res.status_code == 200 and ("/ad/" in res.text or "<article" in res.text or "h1" in res.text):
                return res.text
        except Exception as e:
            print(f"Attempt error: {e}")
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

def get_user_ads_count(profile_url):
    if not profile_url:
        return 1
    try:
        html = fetch_via_api(profile_url)
        if not html:
            return 1
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        match = re.search(r"(\d+)\s*(?:إعلان|إعلانات|اعلان|Ads|ad)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        ad_links = {a["href"] for a in soup.find_all("a", href=True) if "/ad/" in a["href"]}
        if ad_links:
            return len(ad_links)
        return 1
    except Exception:
        return 1

def enrich_ad_details(ad_url, fallback_title, fallback_price_text, fallback_price_num, fallback_area, fallback_beds, fallback_baths, fallback_desc, blocked_users):
    try:
        html = fetch_via_api(ad_url)
        if not html:
            return {
                "title": fallback_title,
                "price_text": fallback_price_text,
                "price_num": fallback_price_num,
                "area": fallback_area,
                "beds": fallback_beds,
                "baths": fallback_baths,
                "description": fallback_desc,
                "seller_name": "مالك",
                "seller_profile": "",
                "seller_ads_count": 1
            }

        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            if "/companies/" in a["href"] or "/agencies/" in a["href"]:
                blocked_users.add(a["href"])
                return None

        seller_name = "مالك"
        profile_url = ""
        for a in soup.find_all("a", href=True):
            if "/profile/" in a["href"]:
                profile_url = "https://www.dubizzle.com.eg" + a["href"] if a["href"].startswith("/") else a["href"]
                seller_name = a.get_text(strip=True) or "مالك"
                break

        if profile_url and profile_url in blocked_users:
            return None

        description = ""
        desc_el = soup.find("div", {"aria-label": "Description"}) or soup.find("div", class_=re.compile(r"description", re.I))
        if desc_el:
            description = desc_el.get_text("\n", strip=True)
        if not description:
            meta_desc = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
            if meta_desc and meta_desc.get("content"):
                description = meta_desc["content"].strip()
        if not description:
            description = fallback_desc

        title = fallback_title
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            title = h1.get_text(strip=True)

        if is_broker_text(seller_name + " " + title + " " + description[:200]):
            if profile_url:
                blocked_users.add(profile_url)
            return None

        ads_count = 1
        if profile_url:
            ads_count = get_user_ads_count(profile_url)
            if ads_count > 7:
                blocked_users.add(profile_url)
                return None
            if ads_count > 4:
                return None

        return {
            "title": title,
            "price_text": fallback_price_text,
            "price_num": fallback_price_num,
            "area": fallback_area,
            "beds": fallback_beds,
            "baths": fallback_baths,
            "description": description,
            "seller_name": seller_name,
            "seller_profile": profile_url,
            "seller_ads_count": ads_count
        }
    except Exception:
        return None

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
    new_ads = []

    for cat in URLS:
        print(f"Fetching category: {cat['url']}")
        html = fetch_via_api(cat["url"])
        if not html:
            print("Failed to fetch category html")
            continue

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("article")
        if not cards:
            cards = [a.find_parent("div") or a for a in soup.find_all("a", href=re.compile(r"/ad/"))]

        print(f"Found {len(cards)} cards in category")
        checked_in_cat = 0

        for card in cards:
            if checked_in_cat >= 5:
                break

            card_html = str(card)
            if "/companies/" in card_html or "/agencies/" in card_html:
                comp_links = [a["href"] for a in card.find_all("a", href=True) if "/companies/" in a["href"] or "/agencies/" in a["href"]]
                for cl in comp_links:
                    blocked_users.add(cl)
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

            title_el = card.find("h2") or link_el
            fallback_title = title_el.get_text(strip=True) if title_el else "عقار بالقاهرة الجديدة"
            if len(fallback_title) < 5:
                fallback_title = card_text.split("|")[0].strip() or "عقار بالقاهرة الجديدة"

            price_text = "غير محدد"
            price_num = 0
            price_match = re.search(r"([\d,]+)\s*(?:ج\.م|جنيه|EGP)", card_text)
            if price_match:
                price_text = price_match.group(1) + " ج.م"
                price_num = int(price_match.group(1).replace(",", ""))

            area_match = re.search(r"(\d+)\s*(?:م²|متر|sqm|m²)", card_text, re.I)
            beds_match = re.search(r"(\d+)\s*(?:غرف|غرفة|beds|bed)", card_text, re.I)
            baths_match = re.search(r"(\d+)\s*(?:حمام|حمامات|baths|bath)", card_text, re.I)

            fallback_area = area_match.group(1) + " م²" if area_match else "غير محدد"
            fallback_beds = beds_match.group(1) + " غرف" if beds_match else ""
            fallback_baths = baths_match.group(1) + " حمام" if baths_match else ""

            seen_urls.add(ad_url)
            checked_in_cat += 1

            details = enrich_ad_details(
                ad_url,
                fallback_title,
                price_text,
                price_num,
                fallback_area,
                fallback_beds,
                fallback_baths,
                card_text,
                blocked_users
            )
            if not details:
                continue

            subtype = detect_subtype(details["title"], details["description"], cat["category"])
            new_ads.append({
                "title": details["title"],
                "url": ad_url,
                "price_text": details["price_text"],
                "price_num": details["price_num"],
                "deal": cat["deal"],
                "category": cat["category"],
                "subtype": subtype,
                "location": "القاهرة الجديدة",
                "area": details["area"],
                "beds": details["beds"],
                "baths": details["baths"],
                "description": details["description"],
                "seller_name": details["seller_name"],
                "seller_profile": details["seller_profile"],
                "seller_ads_count": details["seller_ads_count"],
                "scraped_timestamp": now_ts,
                "scraped_date": now_cairo
            })

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
    print(f"Saved {len(final_ads)} owner ads and {len(blocked_users)} blocked brokers.")

if __name__ == "__main__":
    scrape_all()
