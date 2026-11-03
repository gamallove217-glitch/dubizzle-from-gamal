import json
import time
import re
import os
from datetime import datetime, timedelta, timezone
import requests

API_KEY = "1fbcb4ca0bad271b0780c0a848e8c05b"
SCHEMA_VERSION = 12
SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

SEARCH_QUERIES = [
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار التجمع الخامس", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار القاهرة الجديدة", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة مفروشة للايجار التجمع", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع التجمع الخامس", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع القاهرة الجديدة", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار الرحاب", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار مدينتي", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع الرحاب او مدينتي", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ دوبلكس للايجار او للبيع التجمع الخامس", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ بنتهاوس للايجار او للبيع التجمع الخامس", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ استوديو للايجار التجمع الخامس", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ غرفة او روف للايجار التجمع", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ فيلا للايجار التجمع الخامس", "deal": "إيجار", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ فيلا للبيع التجمع الخامس", "deal": "بيع", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ تاون هاوس او توين هاوس التجمع", "deal": "بيع", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ مكتب اداري للايجار التجمع الخامس", "deal": "إيجار", "category": "تجاري وإداري"},
    {"q": "site:dubizzle.com.eg/ad/ محل تجاري او عيادة التجمع الخامس", "deal": "إيجار", "category": "تجاري وإداري"}
]

NEW_CAIRO_PLACES = [
    "التجمع", "القاهرة الجديدة", "القاهره الجديده", "الرحاب", "مدينتي", "مدينتى",
    "النرجس", "اللوتس", "الياسمين", "البنفسج", "الشويفات", "الأندلس", "الاندلس",
    "بيت الوطن", "الأكاديمية", "الاكاديمية", "المستثمرين", "القطامية", "ميفيدا",
    "هايد بارك", "ماونتن فيو", "بالم هيلز", "سراي", "التسعين", "القرنفل",
    "تاج سيتي", "ابو الهول", "جاردينيا", "دار مصر", "سكن مصر", "جنة", "الباتيو",
    "new cairo", "5th settlement", "rehab", "madinaty", "mivida", "hyde park"
]

EXCLUDED_CITIES = [
    "العبور", "لوران", "سموحة", "سموحه", "الإسكندرية", "الاسكندرية", "اسكندرية",
    "أكتوبر", "اكتوبر", "زايد", "الشيخ زايد", "الشروق", "بدر", "المعادي", "المعادى",
    "مدينة نصر", "مدينه نصر", "مصر الجديدة", "مصر الجديده", "المقطم", "الهرم",
    "فيصل", "الدقي", "المهندسين", "حلوان", "شبرا", "عين شمس", "الساحل", "السخنة",
    "الغردقة", "ميامي", "سيدي بشر", "المنتزه", "العجمي", "طنطا", "المنصورة", "الزقازيق"
]

BROKER_PATTERNS = [
    "للتنمية العقارية", "للتنميه العقاريه", "للعقارات", "للتسويق العقاري",
    "للاستثمار العقاري", "مكتب عقارات", "شركة عقارات", "real estate",
    "properties", "property", "agency", "consultancy", "brokerage",
    "go homes", "quality square", "بانوراما", "دفعة الأولى", "دفعه اولى",
    "بمقدم", "وتقسيط حتى", "أقساط على", "اقساط على", "كود الوحدة", "كود الاعلان", "**"
]

DELETED_PHRASES = [
    "لم يتم العثور على تطابقات",
    "قد تم بيعه أو إزالته",
    "تم بيعه أو إزالته",
    "حاول البحث عن إعلانات مشابهة",
    "we couldn't find any matches",
    "no longer available"
]

def is_strictly_new_cairo(title):
    t_low = title.lower()
    if any(ex in t_low for ex in EXCLUDED_CITIES):
        return False
    return any(nc in t_low for nc in NEW_CAIRO_PLACES)

def is_broker_ad(title, snippet):
    combined = (title + " " + snippet).lower()
    return any(bp in combined for bp in BROKER_PATTERNS)

def detect_category_and_subtype(title, description, default_cat):
    t_low = title.lower()
    d_low = description.lower()
    for src in [t_low, d_low]:
        if any(w in src for w in ["مكتب", "محل", "عيادة", "عياده", "إداري", "اداري", "تجاري", "مول", "مقر", "office", "clinic", "retail"]):
            return "تجاري وإداري", "تجاري وإداري"
        if any(w in src for w in ["بنتهاوس", "بنت هاوس", "penthouse"]):
            return "شقق", "بنتهاوس"
        if any(w in src for w in ["دوبلكس", "دوبليكس", "duplex"]):
            return "شقق", "دوبلكس"
        if any(w in src for w in ["استوديو", "ستوديو", "studio"]):
            return "شقق", "استوديو"
        if any(w in src for w in ["روف", "رووف", "roof"]):
            return "شقق", "روف"
        if any(w in src for w in ["غرفة", "غرفه", "room"]):
            return "شقق", "غرفة"
        if any(w in src for w in ["شقة", "شقه", "apartment", "flat"]):
            return "شقق", "شقة"
        if any(w in src for w in ["فيلا", "تاون هاوس", "توين هاوس", "ستاند الون", "villa", "townhouse", "twinhouse", "standalone"]):
            return "فيلا", "فيلا"
    return default_cat, ("شقة" if default_cat == "شقق" else default_cat)

def detect_deal(title, description, default_deal):
    t_low = title.lower()
    if any(w in t_low for w in ["للايجار", "للإيجار", "ايجار", "إيجار", "for rent", "rent", "مفروش", "مفروشة"]):
        return "إيجار"
    if any(w in t_low for w in ["للبيع", "بيع", "for sale", "sale", "تمليك"]):
        return "بيع"
    d_low = description.lower()
    if any(w in d_low for w in ["للايجار", "للإيجار", "ايجار", "إيجار", "شهري", "شهريا"]):
        return "إيجار"
    if any(w in d_low for w in ["للبيع", "بيع", "تمليك"]):
        return "بيع"
    return default_deal

def extract_ad_id(ad_url):
    m = re.search(r"-ID(\d+)", ad_url, re.I) or re.search(r"(\d{8,10})", ad_url)
    return int(m.group(1)) if m and m.group(1).isdigit() else 0

def clean_related_ads_noise(snippet):
    cleaned = snippet
    for marker in ["الإبلاغ عن هذا الإعلان", "قم بالإبلاغ عن هذا الإعلان", "الاتجاهات والمؤشرات", "إعلانات ذات صلة", "إعلانات مشابهة"]:
        if marker in cleaned:
            cleaned = cleaned.split(marker)[0]
    if cleaned.count(";") >= 2 and ("ج.م" in cleaned):
        parts = [p.strip() for p in cleaned.split(";") if "ج.م" not in p]
        cleaned = " ".join(parts)
    return cleaned.strip()

def extract_specs(text):
    price_text = "موضح داخل الإعلان"
    price_num = 1

    patterns = [
        r"(?:السعر|بسعر|مطلوب|الايجار|الإيجار|price)\s*[:：]?\s*([\d,]{4,12})",
        r"([\d,]{4,12})\s*(?:ج\.م|جنيه|جنية|EGP)",
        r"(?:ج\.م|ج\.م\.|EGP)\s*([\d,]{4,12})"
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            raw_p = m.group(1).replace(",", "")
            if raw_p.isdigit() and int(raw_p) >= 2000:
                price_num = int(raw_p)
                price_text = f"{price_num:,} ج.م"
                break

    if price_num == 1:
        m_mil = re.search(r"(\d+(?:\.\d+)?)\s*(?:مليون|million)", text, re.I)
        if m_mil:
            price_num = int(float(m_mil.group(1)) * 1000000)
            price_text = f"{price_num:,} ج.م"
        else:
            m_k = re.search(r"(\d{1,3})\s*(?:الف|ألف|آلاف)\b", text, re.I)
            if m_k and int(m_k.group(1)) >= 3:
                price_num = int(m_k.group(1)) * 1000
                price_text = f"{price_num:,} ج.م"

    area_match = (
        re.search(r"المساحة\s*\(?م[٢2²]?\)?\s*[:：]?\s*(\d{2,4})", text, re.I)
        or re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢|م\b)", text, re.I)
    )
    beds_match = (
        re.search(r"(?:غرف نوم|غرف|غرفة)\s*[:：]?\s*(\d+)", text, re.I)
        or re.search(r"(\d+)\s*(?:غرف|غرفة|نوم|beds|bed|bedrooms)", text, re.I)
    )
    baths_match = (
        re.search(r"(?:الحمامات|حمامات|حمام)\s*[:：]?\s*(\d+)", text, re.I)
        or re.search(r"(\d+)\s*(?:حمام|حمامات|baths|bath|bathrooms)", text, re.I)
    )

    area = area_match.group(1) + " م²" if area_match else "مدرج بالإعلان"
    beds = beds_match.group(1) + " غرف" if beds_match else ""
    baths = baths_match.group(1) + " حمام" if baths_match else ""
    return price_text, price_num, area, beds, baths

def extract_seller_info(title, snippet, ad_url):
    full = f"{title} | {snippet}"
    seller_name = "مالك مباشر"
    m_name = re.search(r"تم النشر بواسطة\s*[:：]?\s*([^\.\|\n]+?)(?:\s+عضو منذ|\s+(?:ال)?[إأآا]علانات|\s+نشطة|\.|\||$)", full)
    if m_name:
        cand_name = m_name.group(1).strip()
        if 1 < len(cand_name) <= 35:
            seller_name = cand_name

    explicit_count = None
    m_count = (
        re.search(r"(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]\s*[:：]?\s*(\d+)", full, re.I)
        or re.search(r"(\d+)\s*(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]", full, re.I)
    )
    if m_count:
        explicit_count = int(m_count.group(1))

    if seller_name != "مالك مباشر":
        seller_key = seller_name
    else:
        words = [w for w in re.split(r"\s+", title) if len(w) > 2]
        seller_key = " ".join(words[:4]) if len(words) >= 4 else ad_url

    return seller_name, seller_key, explicit_count

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
        if (now_ts - ad.get("scraped_timestamp", now_ts)) >= SEVEN_DAYS_SECONDS:
            continue
        sk = ad.get("seller_profile", "")
        if sk and sk in blocked_users:
            continue
        if not is_strictly_new_cairo(ad.get("title", "")):
            continue
        if ad.get("seller_ads_count", 1) > 4:
            continue
        valid_existing_ads.append(ad)
        if sk:
            seller_counts[sk] = max(seller_counts.get(sk, 0), ad.get("seller_ads_count", 1))

    seen_urls = {ad.get("url") for ad in valid_existing_ads if ad.get("url")}
    candidates = []

    for idx, item in enumerate(SEARCH_QUERIES):
        if idx > 0:
            time.sleep(10)

        try:
            params = {
                "api_key": API_KEY,
                "query": item["q"],
                "hl": "ar",
                "gl": "eg",
                "num": "25"
            }
            res = requests.get("https://api.scraperapi.com/structured/google/search", params=params, timeout=45)
            print(f"[{idx+1}/{len(SEARCH_QUERIES)}] {item['q']} -> Status {res.status_code}")
            if res.status_code != 200:
                continue

            results = res.json().get("organic_results", [])
            print(f"Found {len(results)} results")

            for r in results:
                ad_url = r.get("link", "").split("?")[0]
                if "dubizzle.com.eg" not in ad_url or "/ad/" not in ad_url:
                    continue
                if "/companies/" in ad_url or "/agencies/" in ad_url or ad_url in seen_urls:
                    continue

                title = re.sub(r"\s*[-|]\s*(?:دوبيزل|dubizzle).*$", "", r.get("title", ""), flags=re.I).strip()
                raw_snippet = r.get("snippet", "").strip()

                if any(dp in (title + " " + raw_snippet).lower() for dp in DELETED_PHRASES):
                    continue

                if not is_strictly_new_cairo(title):
                    continue

                if is_broker_ad(title, raw_snippet):
                    blocked_users.add(ad_url)
                    continue

                seller_name, seller_key, explicit_count = extract_seller_info(title, raw_snippet, ad_url)
                if seller_key in blocked_users:
                    continue

                if explicit_count is not None:
                    if explicit_count > 7:
                        blocked_users.add(seller_key)
                        continue
                    if explicit_count < 1 or explicit_count > 4:
                        continue

                current_count = seller_counts.get(seller_key, 0) + 1
                if explicit_count is not None:
                    current_count = max(current_count, explicit_count)
                seller_counts[seller_key] = current_count

                if current_count > 7:
                    blocked_users.add(seller_key)
                    continue

                clean_snippet = clean_related_ads_noise(raw_snippet)
                full_clean = f"{title} | {clean_snippet}"

                price_text, price_num, area, beds, baths = extract_specs(full_clean)
                cat_name, subtype = detect_category_and_subtype(title, clean_snippet, item["category"])
                deal_name = detect_deal(title, clean_snippet, item["deal"])
                ad_id = extract_ad_id(ad_url)

                seen_urls.add(ad_url)
                candidates.append({
                    "schema_version": SCHEMA_VERSION,
                    "ad_id": ad_id,
                    "title": title,
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
                    "description": clean_snippet if clean_snippet else title,
                    "seller_name": seller_name,
                    "seller_profile": seller_key,
                    "seller_ads_count": current_count,
                    "scraped_timestamp": now_ts,
                    "scraped_date": now_cairo
                })
        except Exception as e:
            print(f"Error: {e}")

    all_combined = candidates + valid_existing_ads
    final_ads = []

    for ad in all_combined:
        sk = ad.get("seller_profile", "")
        count = max(seller_counts.get(sk, 1), ad.get("seller_ads_count", 1))
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
    print(f"Saved {len(final_ads)} verified New Cairo ads from {unique_owners} owners.")

if __name__ == "__main__":
    scrape_all()
