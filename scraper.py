import json
import time
import re
import os
from datetime import datetime, timedelta, timezone
import requests

API_KEY = "1fbcb4ca0bad271b0780c0a848e8c05b"
SCHEMA_VERSION = 7
MIN_ACTIVE_AD_ID = 204600000
SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

SEARCH_QUERIES = [
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار التجمع", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع التجمع", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار القاهرة الجديدة", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع القاهرة الجديدة", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ دوبلكس التجمع", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ بنتهاوس التجمع", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ استوديو التجمع", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة الرحاب", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة مدينتي", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ فيلا التجمع", "deal": "بيع", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ تاون هاوس التجمع", "deal": "بيع", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ مكتب للايجار التجمع", "deal": "إيجار", "category": "تجاري وإداري"},
    {"q": "site:dubizzle.com.eg/ad/ محل التجمع", "deal": "إيجار", "category": "تجاري وإداري"}
]

DELETED_PHRASES = [
    "لم يتم العثور على تطابقات",
    "قد تم بيعه أو إزالته",
    "تم بيعه أو إزالته",
    "حاول البحث عن إعلانات مشابهة",
    "we couldn't find any matches",
    "no longer available"
]

def detect_category_and_subtype(title, description, default_cat):
    text = (title + " " + description).lower()
    if any(w in text for w in ["مكتب", "محل", "عيادة", "عياده", "إداري", "اداري", "تجاري", "مول", "مقر", "office", "clinic", "retail", "commercial"]):
        return "تجاري وإداري", "تجاري وإداري"
    if any(w in text for w in ["فيلا", "تاون هاوس", "توين هاوس", "ستاند الون", "villa", "townhouse", "twinhouse", "standalone"]):
        return "فيلا", "فيلا"
    if any(w in text for w in ["بنتهاوس", "بنت هاوس", "penthouse"]):
        return "شقق", "بنتهاوس"
    if any(w in text for w in ["دوبلكس", "دوبليكس", "duplex"]):
        return "شقق", "دوبلكس"
    if any(w in text for w in ["استوديو", "ستوديو", "studio"]):
        return "شقق", "استوديو"
    if any(w in text for w in ["روف", "رووف", "roof"]):
        return "شقق", "روف"
    if any(w in text for w in ["غرفة", "غرفه", "room"]):
        return "شقق", "غرفة"
    return default_cat, ("شقة" if default_cat == "شقق" else default_cat)

def detect_deal(title, description, default_deal):
    text = (title + " " + description).lower()
    if any(w in text for w in ["للايجار", "للإيجار", "ايجار", "إيجار", "for rent", "rent", "monthly", "شهري"]):
        return "إيجار"
    if any(w in text for w in ["للبيع", "بيع", "for sale", "sale"]):
        return "بيع"
    return default_deal

def extract_ad_id(ad_url):
    m = re.search(r"-ID(\d+)", ad_url, re.I)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return 0
    return 0

def extract_specs(text):
    price_text = "موضح داخل الإعلان"
    price_num = 0

    patterns = [
        r"([\d,]{4,12})\s*(?:ج\.م|جنيه|جنية|EGP|ج\b)",
        r"(?:ج\.م|ج\.م\.|EGP)\s*([\d,]{4,12})",
        r"(?:السعر|بسعر|مطلوب|الايجار|الإيجار|price)\s*[:：]?\s*([\d,]{4,12})"
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            raw_p = m.group(1).replace(",", "")
            if raw_p.isdigit() and int(raw_p) >= 1000:
                price_num = int(raw_p)
                price_text = f"{price_num:,} ج.م"
                break

    if price_num == 0:
        m_mil = re.search(r"(\d+(?:\.\d+)?)\s*(?:مليون|million)", text, re.I)
        if m_mil:
            price_num = int(float(m_mil.group(1)) * 1000000)
            price_text = f"{price_num:,} ج.م"
        else:
            m_k = re.search(r"(\d{1,3})\s*(?:الف|ألف|آلاف)\b", text, re.I)
            if m_k:
                price_num = int(m_k.group(1)) * 1000
                price_text = f"{price_num:,} ج.م"

    area_match = re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢|م\b)", text, re.I)
    beds_match = re.search(r"(\d)\s*(?:غرف|غرفة|نوم|beds|bed|bedrooms)", text, re.I)
    baths_match = re.search(r"(\d)\s*(?:حمام|حمامات|baths|bath|bathrooms)", text, re.I)

    area = area_match.group(1) + " م²" if area_match else "مدرج بالإعلان"
    beds = beds_match.group(1) + " غرف" if beds_match else ""
    baths = baths_match.group(1) + " حمام" if baths_match else ""
    return price_text, price_num, area, beds, baths

def extract_seller_key(title, snippet, ad_url):
    full = title + " " + snippet
    m = re.search(r"(?:المعلن|بواسطة|للتواصل)\s*[:：]?\s*([\w\s]{3,20})", full)
    if m:
        return m.group(1).strip()
    words = [w for w in re.split(r"\s+", title) if len(w) > 2]
    if len(words) >= 4:
        return " ".join(words[:4])
    return ad_url

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
    seller_counts = {}

    for ad in existing_ads:
        if ad.get("schema_version") != SCHEMA_VERSION:
            continue
        ad_stored_ts = ad.get("scraped_timestamp", now_ts)
        if (now_ts - ad_stored_ts) >= SEVEN_DAYS_SECONDS:
            continue
        sk = ad.get("seller_profile", "")
        if sk and sk in blocked_users:
            continue
        valid_existing_ads.append(ad)
        if sk:
            seller_counts[sk] = seller_counts.get(sk, 0) + 1

    seen_urls = {ad.get("url") for ad in valid_existing_ads if ad.get("url")}
    candidates = []

    for idx, item in enumerate(SEARCH_QUERIES):
        if idx > 0:
            time.sleep(24)

        try:
            params = {
                "api_key": API_KEY,
                "query": item["q"],
                "hl": "ar",
                "gl": "eg",
                "num": "20"
            }
            res = requests.get("https://api.scraperapi.com/structured/google/search", params=params, timeout=45)
            print(f"[{idx+1}/{len(SEARCH_QUERIES)}] {item['q']} -> Status {res.status_code}")
            if res.status_code != 200:
                continue

            data = res.json()
            results = data.get("organic_results", [])
            print(f"Results found: {len(results)}")

            for r in results:
                ad_url = r.get("link", "").split("?")[0]
                if "dubizzle.com.eg" not in ad_url or "/ad/" not in ad_url:
                    continue
                if "/companies/" in ad_url or "/agencies/" in ad_url:
                    blocked_users.add(ad_url)
                    continue
                if ad_url in seen_urls:
                    continue

                ad_id = extract_ad_id(ad_url)
                if ad_id > 0 and ad_id < MIN_ACTIVE_AD_ID:
                    continue

                title = re.sub(r"\s*[-|]\s*(?:دوبيزل|dubizzle).*$", "", r.get("title", ""), flags=re.I).strip()
                snippet = r.get("snippet", "").strip()
                full_text = f"{title} | {snippet}"

                if any(dp in full_text.lower() for dp in DELETED_PHRASES):
                    continue

                seller_key = extract_seller_key(title, snippet, ad_url)
                if seller_key in blocked_users:
                    continue

                seller_counts[seller_key] = seller_counts.get(seller_key, 0) + 1
                if seller_counts[seller_key] > 7:
                    blocked_users.add(seller_key)
                    continue

                price_text, price_num, area, beds, baths = extract_specs(full_text)
                cat_name, subtype = detect_category_and_subtype(title, snippet, item["category"])
                deal_name = detect_deal(title, snippet, item["deal"])

                seen_urls.add(ad_url)
                candidates.append({
                    "schema_version": SCHEMA_VERSION,
                    "ad_id": ad_id,
                    "title": title or "عقار بالقاهرة الجديدة",
                    "url": ad_url,
                    "price_text": price_text,
                    "price_num": price_num,
                    "deal": deal_name,
                    "category": cat_name,
                    "subtype": subtype,
                    "location": "القاهرة الجديدة",
                    "area": area,
                    "beds": beds,
                    "baths": baths,
                    "description": snippet if snippet else title,
                    "seller_name": "مالك",
                    "seller_profile": seller_key,
                    "seller_ads_count": 1,
                    "scraped_timestamp": now_ts,
                    "scraped_date": now_cairo
                })
        except Exception as e:
            print(f"Error: {e}")

    all_combined = candidates + valid_existing_ads
    final_ads = []

    for ad in all_combined:
        sk = ad.get("seller_profile", "")
        count = seller_counts.get(sk, 1)
        if count > 7:
            blocked_users.add(sk)
            continue
        if sk in blocked_users or count < 1 or count > 4:
            continue
        ad["seller_ads_count"] = count
        final_ads.append(ad)

    final_ads.sort(key=lambda x: x.get("ad_id", 0), reverse=True)
    unique_owners = len({ad.get("seller_profile") or ad.get("url") for ad in final_ads})

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
    print(f"Done: {len(final_ads)} active owner ads from {unique_owners} owners.")

if __name__ == "__main__":
    scrape_all()
