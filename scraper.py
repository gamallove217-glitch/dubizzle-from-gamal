import json
import time
import re
import os
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

API_KEY = "1fbcb4ca0bad271b0780c0a848e8c05b"

LIVE_CATEGORY_URLS = [
    {"url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/", "deal": "إيجار", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/", "deal": "بيع", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/rooms-for-rent/new-cairo/", "deal": "إيجار", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/", "deal": "إيجار", "category": "فيلا"},
    {"url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/", "deal": "بيع", "category": "فيلا"},
    {"url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/", "deal": "إيجار", "category": "تجاري وإداري"},
    {"url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/", "deal": "بيع", "category": "تجاري وإداري"}
]

SEARCH_QUERIES = [
    {"q": "site:dubizzle.com.eg/properties/ شقة للايجار التجمع الخامس القاهرة الجديدة", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/properties/ شقة للبيع التجمع الخامس القاهرة الجديدة", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار التجمع الخامس ج.م", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع التجمع الخامس ج.م", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ دوبلكس او بنتهاوس او استوديو التجمع ج.م", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ فيلا التجمع الخامس القاهرة الجديدة ج.م", "deal": "بيع", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ مكتب او محل او اداري التجمع الخامس ج.م", "deal": "إيجار", "category": "تجاري وإداري"}
]

BROKER_KEYWORDS = [
    "شركة", "للعقارات", "التسويق العقاري", "بروكر", "سمسار", "عمولة", "مكتب عقارات",
    "real estate", "property", "properties", "agency", "broker", "consultancy", "investment",
    "verified business", "featured business"
]

DELETED_PHRASES = [
    "لم يتم العثور على تطابقات",
    "قد تم بيعه أو إزالته",
    "تم بيعه أو إزالته",
    "nolongeravailable",
    "page not found"
]

SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

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

def extract_specs(text):
    price_text = ""
    price_num = 0
    patterns = [
        r"([\d,]{4,12})\s*(?:ج\.م|جنيه|جنية|EGP)",
        r"(?:ج\.م|ج\.م\.|EGP)\s*([\d,]{4,12})",
        r"السعر\s*[:：]?\s*([\d,]{4,12})"
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            raw_p = m.group(1).replace(",", "")
            if raw_p.isdigit() and int(raw_p) >= 1000:
                price_num = int(raw_p)
                price_text = f"{price_num:,} ج.م"
                break

    area_match = re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢|م\b)", text, re.I)
    beds_match = re.search(r"(\d)\s*(?:غرف|غرفة|نوم|beds|bed)", text, re.I)
    baths_match = re.search(r"(\d)\s*(?:حمام|حمامات|baths|bath)", text, re.I)

    area = area_match.group(1) + " م²" if area_match else "مدرج بالإعلان"
    beds = beds_match.group(1) + " غرف" if beds_match else ""
    baths = baths_match.group(1) + " حمام" if baths_match else ""
    return price_text, price_num, area, beds, baths

def fetch_dubizzle_html(url):
    for mode in [{"premium": "true"}, {"render": "true"}, {}]:
        try:
            params = {"api_key": API_KEY, "url": url}
            params.update(mode)
            res = requests.get("http://api.scraperapi.com", params=params, timeout=40)
            if res.status_code == 200 and len(res.text) > 1500:
                low = res.text.lower()
                if any(dp in low for dp in DELETED_PHRASES):
                    return "DELETED"
                if "/ad/" in res.text or "<article" in res.text or "dubizzle" in low:
                    return res.text
        except Exception:
            pass
    return ""

def scrape_live_categories(seen_urls, blocked_users, seller_counts, now_ts, now_cairo):
    collected = []
    for cat in LIVE_CATEGORY_URLS:
        html = fetch_dubizzle_html(cat["url"])
        if not html or html == "DELETED":
            continue
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("article")
        if not cards:
            cards = [a.find_parent("div") or a for a in soup.find_all("a", href=re.compile(r"/ad/"))]

        for card in cards:
            card_html = str(card)
            if "/companies/" in card_html or "/agencies/" in card_html:
                blocked_users.add(cat["url"] + "#broker")
                continue

            link_el = card.find("a", href=re.compile(r"/ad/")) if card.name != "a" else card
            if not link_el or not link_el.get("href"):
                continue

            href = link_el["href"].split("?")[0]
            ad_url = "https://www.dubizzle.com.eg" + href if href.startswith("/") else href
            if "/ad/" not in ad_url or ad_url in seen_urls:
                continue

            card_text = card.get_text(" | ", strip=True)
            if is_broker_text(card_text):
                blocked_users.add(ad_url)
                continue

            price_el = card.find("span", {"aria-label": "Price"})
            price_text, price_num, area, beds, baths = extract_specs(card_text)
            if price_el and price_num == 0:
                p_str = price_el.get_text(strip=True)
                nums = re.findall(r"\d+", p_str.replace(",", ""))
                if nums and int(nums[0]) >= 1000:
                    price_num = int(nums[0])
                    price_text = f"{price_num:,} ج.م"

            if price_num == 0:
                continue

            title_el = card.find("h2") or link_el
            title = title_el.get_text(strip=True) if title_el else ""
            if len(title) < 5:
                parts = [p.strip() for p in card_text.split("|") if len(p.strip()) > 8]
                title = parts[0] if parts else "عقار بالقاهرة الجديدة"

            seller_name = "مالك مباشر"
            seller_key = title[:25]
            for a in card.find_all("a", href=True):
                if "/profile/" in a["href"]:
                    seller_key = a["href"]
                    seller_name = a.get_text(strip=True) or "مالك مباشر"
                    break

            seller_counts[seller_key] = seller_counts.get(seller_key, 0) + 1
            if seller_counts[seller_key] > 7:
                blocked_users.add(seller_key)
                continue

            clean_desc = "\n".join([p.strip() for p in card_text.split("|") if len(p.strip()) > 3])
            subtype = detect_subtype(title, clean_desc, cat["category"])

            seen_urls.add(ad_url)
            collected.append({
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
                "seller_ads_count": seller_counts[seller_key],
                "scraped_timestamp": now_ts,
                "scraped_date": now_cairo
            })
    return collected

def verify_and_get_live_ad(ad_url, fallback_title, fallback_snippet):
    html = fetch_dubizzle_html(ad_url)
    if html == "DELETED":
        return None
    if not html:
        price_text, price_num, area, beds, baths = extract_specs(fallback_title + " " + fallback_snippet)
        if price_num == 0:
            return None
        return {
            "title": fallback_title,
            "price_text": price_text,
            "price_num": price_num,
            "area": area,
            "beds": beds,
            "baths": baths,
            "description": fallback_snippet,
            "seller_name": "مالك مباشر",
            "seller_key": fallback_title[:25]
        }

    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" | ", strip=True)
    if any(dp in page_text.lower() for dp in DELETED_PHRASES):
        return None

    for a in soup.find_all("a", href=True):
        if "/companies/" in a["href"] or "/agencies/" in a["href"]:
            return None

    price_text, price_num, area, beds, baths = extract_specs(page_text + " " + fallback_title + " " + fallback_snippet)
    if price_num == 0:
        return None

    desc_el = soup.find("div", {"aria-label": "Description"}) or soup.find("div", class_=re.compile(r"description", re.I))
    description = desc_el.get_text("\n", strip=True) if desc_el else fallback_snippet

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 and h1.get_text(strip=True) else fallback_title

    seller_name = "مالك مباشر"
    seller_key = title[:25]
    for a in soup.find_all("a", href=True):
        if "/profile/" in a["href"]:
            seller_key = a["href"]
            seller_name = a.get_text(strip=True) or "مالك مباشر"
            break

    if is_broker_text(seller_name + " " + title + " " + description[:200]):
        return None

    return {
        "title": title,
        "price_text": price_text,
        "price_num": price_num,
        "area": area,
        "beds": beds,
        "baths": baths,
        "description": description,
        "seller_name": seller_name,
        "seller_key": seller_key
    }

def scrape_structured_google(seen_urls, blocked_users, seller_counts, now_ts, now_cairo):
    collected = []
    for item in SEARCH_QUERIES:
        try:
            params = {
                "api_key": API_KEY,
                "query": item["q"],
                "hl": "ar",
                "gl": "eg",
                "tbs": "qdr:w",
                "num": "15"
            }
            res = requests.get("https://api.scraperapi.com/structured/google/search", params=params, timeout=35)
            if res.status_code != 200:
                continue

            data = res.json()
            for r in data.get("organic_results", []):
                ad_url = r.get("link", "").split("?")[0]
                if "dubizzle.com.eg" not in ad_url or "/ad/" not in ad_url:
                    continue
                if ad_url in seen_urls:
                    continue

                title = re.sub(r"\s*[-|]\s*(?:دوبيزل|dubizzle).*$", "", r.get("title", ""), flags=re.I).strip()
                snippet = r.get("snippet", "").strip()
                full_text = f"{title} | {snippet}"

                if is_broker_text(full_text):
                    blocked_users.add(ad_url)
                    continue

                verified = verify_and_get_live_ad(ad_url, title, snippet)
                seen_urls.add(ad_url)
                if not verified:
                    continue

                sk = verified["seller_key"]
                seller_counts[sk] = seller_counts.get(sk, 0) + 1
                if seller_counts[sk] > 7:
                    blocked_users.add(sk)
                    continue

                deal = "إيجار" if any(w in full_text for w in ["ايجار", "إيجار", "للايجار", "للإيجار", "rent"]) else item["deal"]
                subtype = detect_subtype(verified["title"], verified["description"], item["category"])

                collected.append({
                    "title": verified["title"],
                    "url": ad_url,
                    "price_text": verified["price_text"],
                    "price_num": verified["price_num"],
                    "deal": deal,
                    "category": item["category"],
                    "subtype": subtype,
                    "location": "القاهرة الجديدة",
                    "area": verified["area"],
                    "beds": verified["beds"],
                    "baths": verified["baths"],
                    "description": verified["description"],
                    "seller_name": verified["seller_name"],
                    "seller_profile": sk,
                    "seller_ads_count": seller_counts[sk],
                    "scraped_timestamp": now_ts,
                    "scraped_date": now_cairo
                })
        except Exception as e:
            print(f"Google structured error: {e}")
    return collected

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
        has_valid_price = ad.get("price_num", 0) > 0
        if has_valid_price and (now_ts - ad_ts) < SEVEN_DAYS_SECONDS and (not seller_prof or seller_prof not in blocked_users):
            valid_existing_ads.append(ad)

    seen_urls = {ad.get("url") for ad in valid_existing_ads if ad.get("url")}
    seller_counts = {}

    live_cat_ads = scrape_live_categories(seen_urls, blocked_users, seller_counts, now_ts, now_cairo)
    google_verified_ads = scrape_structured_google(seen_urls, blocked_users, seller_counts, now_ts, now_cairo)

    all_new = live_cat_ads + google_verified_ads
    filtered_new = [
        ad for ad in all_new
        if ad["seller_profile"] not in blocked_users and 1 <= ad["seller_ads_count"] <= 4 and ad["price_num"] > 0
    ]

    final_ads = filtered_new + valid_existing_ads
    unique_owners = len({ad.get("seller_profile") or ad.get("seller_name") or ad.get("url") for ad in final_ads})

    payload = {
        "last_scrape": now_cairo,
        "total": len(final_ads),
        "owners_count": unique_owners,
        "blocked_count": len(blocked_users),
        "blocked_users": list(blocked_users),
        "ads": final_ads
    }

    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(final_ads)} verified active ads with prices from {unique_owners} owners.")

if __name__ == "__main__":
    scrape_all()
