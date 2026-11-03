import json
import time
import re
import os
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

API_KEY = "1fbcb4ca0bad271b0780c0a848e8c05b"

SEARCH_QUERIES = [
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار التجمع الخامس القاهرة الجديدة", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار الرحاب او مدينتي القاهرة الجديدة", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع التجمع الخامس القاهرة الجديدة", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ دوبلكس او بنتهاوس او استوديو او روف للايجار التجمع القاهرة الجديدة", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ دوبلكس او بنتهاوس او استوديو للبيع التجمع القاهرة الجديدة", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ غرفة للايجار التجمع القاهرة الجديدة", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ فيلا او تاون هاوس للايجار التجمع القاهرة الجديدة", "deal": "إيجار", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ فيلا او تاون هاوس للبيع التجمع القاهرة الجديدة", "deal": "بيع", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ مكتب او محل او اداري او تجاري للايجار التجمع القاهرة الجديدة", "deal": "إيجار", "category": "تجاري وإداري"},
    {"q": "site:dubizzle.com.eg/ad/ مكتب او محل او اداري او تجاري للبيع التجمع القاهرة الجديدة", "deal": "بيع", "category": "تجاري وإداري"}
]

BROKER_KEYWORDS = [
    "شركة", "للعقارات", "التسويق العقاري", "بروكر", "سمسار", "عمولة", "مكتب عقارات",
    "real estate", "property", "properties", "agency", "broker", "consultancy", "investment",
    "verified business", "featured business"
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
    price_text = "السعر داخل الإعلان"
    price_num = 0
    p_match = (
        re.search(r"([\d,]{4,12})\s*(?:ج\.م|جنيه|EGP)", text, re.I)
        or re.search(r"(?:ج\.م|EGP)\s*([\d,]{4,12})", text, re.I)
    )
    if p_match:
        raw_p = p_match.group(1).replace(",", "")
        if raw_p.isdigit():
            price_num = int(raw_p)
            price_text = f"{price_num:,} ج.م"

    area_match = re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢|م\b)", text, re.I)
    beds_match = re.search(r"(\d)\s*(?:غرف|غرفة|نوم|beds|bed)", text, re.I)
    baths_match = re.search(r"(\d)\s*(?:حمام|حمامات|baths|bath)", text, re.I)

    area = area_match.group(1) + " م²" if area_match else "مدرج بالإعلان"
    beds = beds_match.group(1) + " غرف" if beds_match else ""
    baths = baths_match.group(1) + " حمام" if baths_match else ""
    return price_text, price_num, area, beds, baths

def scrape_structured_google(seen_urls, blocked_users, seller_counts, now_ts, now_cairo):
    collected = []
    for item in SEARCH_QUERIES:
        try:
            params = {
                "api_key": API_KEY,
                "query": item["q"],
                "hl": "ar",
                "gl": "eg",
                "num": "20"
            }
            res = requests.get("https://api.scraperapi.com/structured/google/search", params=params, timeout=40)
            print(f"Query: {item['q']} -> Status: {res.status_code}")
            if res.status_code != 200:
                continue

            data = res.json()
            results = data.get("organic_results", [])
            print(f"Found {len(results)} organic results")

            for r in results:
                ad_url = r.get("link", "").split("?")[0]
                if "dubizzle.com.eg" not in ad_url or "/ad/" not in ad_url:
                    continue
                if ad_url in seen_urls:
                    continue

                title = r.get("title", "").strip()
                title = re.sub(r"\s*[-|]\s*(?:دوبيزل|dubizzle).*$", "", title, flags=re.I).strip()
                snippet = r.get("snippet", "").strip()
                full_text = f"{title} | {snippet}"

                if is_broker_text(full_text):
                    blocked_users.add(ad_url)
                    continue

                seller_key = title[:30] if title else ad_url
                seller_counts[seller_key] = seller_counts.get(seller_key, 0) + 1
                if seller_counts[seller_key] > 7:
                    blocked_users.add(seller_key)
                    continue

                price_text, price_num, area, beds, baths = extract_specs(full_text)
                subtype = detect_subtype(title, snippet, item["category"])

                seen_urls.add(ad_url)
                collected.append({
                    "title": title or "عقار بالقاهرة الجديدة",
                    "url": ad_url,
                    "price_text": price_text,
                    "price_num": price_num,
                    "deal": item["deal"],
                    "category": item["category"],
                    "subtype": subtype,
                    "location": "القاهرة الجديدة",
                    "area": area,
                    "beds": beds,
                    "baths": baths,
                    "description": snippet if snippet else title,
                    "seller_name": "مالك مباشر",
                    "seller_profile": seller_key,
                    "seller_ads_count": seller_counts[seller_key],
                    "scraped_timestamp": now_ts,
                    "scraped_date": now_cairo
                })
        except Exception as e:
            print(f"Structured search error: {e}")
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
        if (now_ts - ad_ts) < SEVEN_DAYS_SECONDS and (not seller_prof or seller_prof not in blocked_users):
            valid_existing_ads.append(ad)

    seen_urls = {ad.get("url") for ad in valid_existing_ads if ad.get("url")}
    seller_counts = {}

    new_candidates = scrape_structured_google(seen_urls, blocked_users, seller_counts, now_ts, now_cairo)

    filtered_new = [
        ad for ad in new_candidates
        if ad["seller_profile"] not in blocked_users and 1 <= ad["seller_ads_count"] <= 4
    ]

    final_ads = filtered_new + valid_existing_ads

    payload = {
        "last_scrape": now_cairo,
        "total": len(final_ads),
        "blocked_count": len(blocked_users),
        "blocked_users": list(blocked_users),
        "ads": final_ads
    }

    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Total saved: {len(final_ads)} owner ads, {len(blocked_users)} blocked.")

if __name__ == "__main__":
    scrape_all()
