import json
import time
import re
import os
from datetime import datetime, timedelta, timezone
import requests

API_KEY = "1fbcb4ca0bad271b0780c0a848e8c05b"
SCHEMA_VERSION = 13
SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

SEARCH_QUERIES = [
    {"q": 'site:dubizzle.com.eg/ad/ "الإعلانات النشطة 1" "المساحة" شقة للايجار التجمع', "deal": "إيجار", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ "الإعلانات النشطة 1" "المساحة" شقة للايجار القاهرة الجديدة', "deal": "إيجار", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ "الإعلانات النشطة 1" "المساحة" شقة للبيع التجمع', "deal": "بيع", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ "الإعلانات النشطة 1" "المساحة" شقة للبيع القاهرة الجديدة', "deal": "بيع", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ "الإعلانات النشطة 1" "المساحة" شقة الرحاب', "deal": "بيع", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ "الإعلانات النشطة 1" "المساحة" شقة مدينتي', "deal": "بيع", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ "الإعلانات النشطة 1" "المساحة" دوبلكس التجمع OR القاهرة الجديدة', "deal": "بيع", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ "الإعلانات النشطة 1" "المساحة" بنتهاوس OR روف التجمع OR القاهرة الجديدة', "deal": "بيع", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ "الإعلانات النشطة 1" "المساحة" استوديو OR غرفة التجمع OR القاهرة الجديدة', "deal": "إيجار", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ "الإعلانات النشطة 1" "المساحة" فيلا OR تاون هاوس التجمع OR القاهرة الجديدة', "deal": "بيع", "category": "فيلا"},
    {"q": 'site:dubizzle.com.eg/ad/ "الإعلانات النشطة 1" "المساحة" مكتب OR محل OR عيادة التجمع OR مدينتي', "deal": "إيجار", "category": "تجاري وإداري"},
    {"q": 'site:dubizzle.com.eg/ad/ ("الإعلانات النشطة 2" OR "الإعلانات النشطة 3" OR "الإعلانات النشطة 4") "المساحة" شقة للايجار التجمع', "deal": "إيجار", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ ("الإعلانات النشطة 2" OR "الإعلانات النشطة 3" OR "الإعلانات النشطة 4") "المساحة" شقة للبيع التجمع', "deal": "بيع", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ ("الإعلانات النشطة 2" OR "الإعلانات النشطة 3" OR "الإعلانات النشطة 4") "المساحة" شقة الرحاب OR مدينتي', "deal": "بيع", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ ("الإعلانات النشطة 2" OR "الإعلانات النشطة 3" OR "الإعلانات النشطة 4") "المساحة" دوبلكس OR بنتهاوس OR فيلا التجمع', "deal": "بيع", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ ("الإعلانات النشطة 2" OR "الإعلانات النشطة 3" OR "الإعلانات النشطة 4") "المساحة" مكتب OR محل التجمع OR القاهرة الجديدة', "deal": "إيجار", "category": "تجاري وإداري"}
]

NEW_CAIRO_PLACES = [
    "التجمع", "القاهرة الجديدة", "القاهره الجديده", "الرحاب", "مدينتي", "مدينتى",
    "النرجس", "اللوتس", "الياسمين", "البنفسج", "الشويفات", "الأندلس", "الاندلس",
    "بيت الوطن", "الأكاديمية", "الاكاديمية", "المستثمرين", "القطامية", "ميفيدا",
    "هايد بارك", "ماونتن فيو", "بالم هيلز", "سراي", "التسعين", "القرنفل",
    "تاج سيتي", "ابو الهول", "جاردينيا", "جاردنيا", "دار مصر", "سكن مصر", "جنة",
    "الباتيو", "المراسم", "فيفث سكوير", "ستون ريزيدنس", "بيلاجيو", "لاڤي",
    "new cairo", "5th settlement", "rehab", "madinaty", "mivida", "hyde park", "marasem"
]

EXCLUDED_CITIES = [
    "العبور", "لوران", "سموحة", "سموحه", "الإسكندرية", "الاسكندرية", "اسكندرية",
    "أكتوبر", "اكتوبر", "زايد", "الشيخ زايد", "الشروق", "بدر", "المعادي", "المعادى",
    "زهراء المعادي", "زهراء المعادى", "مدينة المعراج", "مدينة نصر", "مدينه نصر",
    "مصر الجديدة", "مصر الجديده", "النزهة", "النزهه", "شيراتون", "العباسية",
    "السيدة زينب", "المقطم", "الهرم", "فيصل", "الدقي", "المهندسين", "حلوان",
    "شبرا", "عين شمس", "المطرية", "البساتين", "الساحل", "راس الحكمة", "السخنة",
    "الغردقة", "ميامي", "سيدي بشر", "المنتزه", "العجمي", "طنطا", "المنصورة",
    "الزقازيق", "العاصمة الإدارية", "العاصمه الاداريه"
]

NON_REAL_ESTATE_WORDS = [
    "سائق", "سواق", "محاسب", "كاشير", "سكرتيرة", "سكرتيره", "جليسة", "جليسه",
    "وظائف", "وظيفة", "تعيين", "مطلوب للعمل", "برخصة", "سيارات للبيع", "كيلومترات",
    "ناقل الحركة", "فني دش", "نجار", "دهانات", "صيانة", "حفلات", "مناسبات", "روبوت"
]

COMPANY_SELLER_WORDS = [
    "real estate", "realestate", "properties", "property", "investment",
    "developments", "development", "consultancy", "agency", "broker", "group",
    "homes", "home", "aqar", "عقارات", "للتسويق", "للاستثمار", "للتنمية",
    "للتطوير", "شركة", "مكتب", "الوكيل"
]

DELETED_PHRASES = [
    "لم يتم العثور على تطابقات",
    "قد تم بيعه أو إزالته",
    "تم بيعه أو إزالته",
    "حاول البحث عن إعلانات مشابهة",
    "هذا الإعلان غير متاح",
    "we couldn't find any matches",
    "no longer available"
]

def is_strictly_new_cairo(title, main_text):
    t_low = title.lower()
    m_low = main_text.lower()

    if any(nw in (t_low + " " + m_low) for nw in NON_REAL_ESTATE_WORDS):
        return False

    loc_match = re.search(r"الموقع\.\s*([^\.]+?)\.\s*Map placeholder", main_text)
    loc_str = loc_match.group(1).lower() if loc_match else ""

    if any(ex in t_low for ex in EXCLUDED_CITIES):
        return False
    if loc_str and any(ex in loc_str for ex in EXCLUDED_CITIES):
        return False

    if any(nc in t_low for nc in NEW_CAIRO_PLACES):
        return True
    if loc_str and any(nc in loc_str for nc in NEW_CAIRO_PLACES):
        return True
    if any(nc in m_low for nc in NEW_CAIRO_PLACES) and not any(ex in m_low for ex in EXCLUDED_CITIES):
        return True

    return False

def detect_category_and_subtype(title, main_text, default_cat):
    t_low = title.lower()
    m_low = main_text.lower()
    for src in [t_low, m_low]:
        if any(w in src for w in ["مكتب", "محل", "عيادة", "عياده", "إداري", "اداري", "تجاري", "مول", "مقر", "مخزن", "office", "clinic", "retail"]):
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
        if any(w in src for w in ["فيلا", "تاون هاوس", "توين هاوس", "ستاند الون", "town house", "villa", "townhouse", "twinhouse", "standalone"]):
            return "فيلا", "فيلا"
    return default_cat, ("شقة" if default_cat == "شقق" else default_cat)

def detect_deal(title, main_text, default_deal):
    t_low = title.lower()
    m_low = main_text.lower()
    if "غرض العقارللإيجار" in m_low or any(w in t_low for w in ["للايجار", "للإيجار", "ايجار", "إيجار", "for rent", "rent", "مفروش", "مفروشة"]):
        return "إيجار"
    if "غرض العقارللبيع" in m_low or any(w in t_low for w in ["للبيع", "بيع", "for sale", "sale", "تمليك"]):
        return "بيع"
    if any(w in m_low for w in ["للايجار", "للإيجار", "شهرياً", "شهريا", "سنوياً"]):
        return "إيجار"
    if any(w in m_low for w in ["للبيع", "تمليك"]):
        return "بيع"
    return default_deal

def extract_main_part(raw_snippet):
    main_part = raw_snippet.split("الإبلاغ عن هذا الإعلان")[0].split("قم بالإبلاغ عن هذا الإعلان")[0]
    main_part = re.sub(r"^.*?الإعلانات ذات الصلة\.\s*", "", main_part)
    return main_part.strip()

def extract_ad_id_and_seller(title, main_part, ad_url):
    ad_id = 0
    m_id = re.search(r"رقم الإعلان\s*(\d+)", main_part) or re.search(r"-ID(\d+)", ad_url, re.I) or re.search(r"(\d{9})", title)
    if m_id and m_id.group(1).isdigit():
        ad_id = int(m_id.group(1))

    ads_count = None
    m_count = (
        re.search(r"(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]\s*[:：]?\s*(\d+)", main_part)
        or re.search(r"(\d+)\s*(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]", main_part)
    )
    if m_count:
        ads_count = int(m_count.group(1))

    seller_name = "مالك مباشر"
    m_name = re.search(r"تم النشر بواسطة\s*([^\.\|\n]+?)(?:\.\s*عضو منذ|\s+عضو منذ|\.\s*الإعلانات|$)", main_part)
    if m_name:
        cand = m_name.group(1).strip()
        if 1 < len(cand) <= 35:
            seller_name = cand

    return ad_id, ads_count, seller_name

def extract_specs_and_desc(title, main_part):
    full = f"{title} . {main_part}"
    price_text = "موضح داخل الإعلان"
    price_num = 1

    patterns = [
        r"([\d,]{4,12})\s*(?:ج\.م|جنيه|جنية|EGP)",
        r"(?:ج\.م|ج\.م\.|EGP)\s*([\d,]{4,12})",
        r"(?:السعر|بسعر|مطلوب|الايجار|الإيجار|إجمالي السعر)\s*[:：]?\s*([\d,]{4,12})"
    ]
    for pat in patterns:
        m = re.search(pat, full, re.I)
        if m:
            raw_p = m.group(1).replace(",", "")
            if raw_p.isdigit() and int(raw_p) >= 2000:
                price_num = int(raw_p)
                price_text = f"{price_num:,} ج.م"
                break

    if price_num == 1:
        m_mil = re.search(r"(\d+(?:\.\d+)?)\s*(?:مليون|ملايين|million)", full, re.I)
        if m_mil:
            price_num = int(float(m_mil.group(1)) * 1000000)
            price_text = f"{price_num:,} ج.م"
        else:
            m_k = re.search(r"(\d{1,3})\s*(?:الف|ألف|آلاف)\b", full, re.I)
            if m_k and int(m_k.group(1)) >= 3:
                price_num = int(m_k.group(1)) * 1000
                price_text = f"{price_num:,} ج.م"

    area_match = (
        re.search(r"المساحة\s*\(?م[٢2²]?\)?\s*[:：]?\s*(\d{2,4})", full, re.I)
        or re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢|م\b)", full, re.I)
    )
    beds_match = (
        re.search(r"(?:غرف نوم|غرف|غرفة)\s*[:：]?\s*(\d+)", full, re.I)
        or re.search(r"(\d+)\s*(?:غرف|غرفة|نوم|bedroom|bedrooms|beds)", full, re.I)
    )
    baths_match = (
        re.search(r"(?:الحمامات|حمامات|حمام)\s*[:：]?\s*(\d+)", full, re.I)
        or re.search(r"(\d+)\s*(?:حمام|حمامات|bathroom|bathrooms|toilets)", full, re.I)
    )

    area = area_match.group(1) + " م²" if area_match else "مدرج بالإعلان"
    beds = beds_match.group(1) + " غرف" if beds_match else ""
    baths = baths_match.group(1) + " حمام" if baths_match else ""

    m_desc = re.search(r"الوصف\.\s*(.+?)(?:اقرأ المزيد|الكماليات\.|تم النشر بواسطة|$)", main_part)
    clean_desc = m_desc.group(1).strip() if m_desc else main_part.split("تم النشر بواسطة")[0].strip()
    if len(clean_desc) < 15:
        clean_desc = title

    return price_text, price_num, area, beds, baths, clean_desc

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
        if ad.get("schema_version") != SCHEMA_VERSION:
            continue
        if (now_ts - ad.get("scraped_timestamp", now_ts)) >= SEVEN_DAYS_SECONDS:
            continue
        if ad.get("ad_id", 0) >= 500000000:
            continue
        sk = ad.get("seller_profile", "")
        if sk and sk in blocked_users:
            continue
        if ad.get("seller_ads_count", 1) > 4:
            continue
        valid_existing_ads.append(ad)

    seen_urls = {ad.get("url") for ad in valid_existing_ads if ad.get("url")}
    seen_ids = {ad.get("ad_id") for ad in valid_existing_ads if ad.get("ad_id")}
    new_ads = []

    for idx, item in enumerate(SEARCH_QUERIES):
        if idx > 0:
            time.sleep(4)

        try:
            params = {
                "api_key": API_KEY,
                "query": item["q"],
                "hl": "ar",
                "gl": "eg"
            }
            res = requests.get("https://api.scraperapi.com/structured/google/search", params=params, timeout=30)
            print(f"[{idx+1}/{len(SEARCH_QUERIES)}] Status {res.status_code} | {item['q']}")
            if res.status_code != 200:
                continue

            results = res.json().get("organic_results", [])
            for r in results:
                ad_url = r.get("link", "").split("?")[0]
                if "dubizzle.com.eg" not in ad_url or "/ad/" not in ad_url or ad_url in seen_urls:
                    continue

                raw_title = r.get("title", "")
                raw_snippet = r.get("snippet", "")

                if any(dp in (raw_title + " " + raw_snippet).lower() for dp in DELETED_PHRASES):
                    continue

                main_part = extract_main_part(raw_snippet)
                ad_id, ads_count, seller_name = extract_ad_id_and_seller(raw_title, main_part, ad_url)

                if ad_id >= 500000000:
                    blocked_users.add(seller_name if seller_name != "مالك مباشر" else ad_url)
                    continue

                if ad_id > 0 and ad_id in seen_ids:
                    continue

                if ads_count is None or ads_count < 1 or ads_count > 4:
                    if ads_count is not None and ads_count > 7:
                        blocked_users.add(seller_name)
                    continue

                if any(cw in (seller_name + " " + main_part).lower() for cw in COMPANY_SELLER_WORDS):
                    blocked_users.add(seller_name)
                    continue

                clean_title = re.sub(r"\s*[-|]\s*(?:شقق|فلل|عقار|مبانى).*$", "", raw_title, flags=re.I)
                clean_title = re.sub(r"\s*[-|]\s*(?:دوبيزل|dubizzle).*$", "", clean_title, flags=re.I).strip()

                if not is_strictly_new_cairo(clean_title, main_part):
                    continue

                price_text, price_num, area, beds, baths, clean_desc = extract_specs_and_desc(clean_title, main_part)
                cat_name, subtype = detect_category_and_subtype(clean_title, main_part, item["category"])
                deal_name = detect_deal(clean_title, main_part, item["deal"])

                seller_key = seller_name if seller_name != "مالك مباشر" else ad_url
                if seller_key in blocked_users:
                    continue

                seen_urls.add(ad_url)
                if ad_id > 0:
                    seen_ids.add(ad_id)

                new_ads.append({
                    "schema_version": SCHEMA_VERSION,
                    "ad_id": ad_id,
                    "title": clean_title,
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
                    "description": clean_desc,
                    "seller_name": seller_name,
                    "seller_profile": seller_key,
                    "seller_ads_count": ads_count,
                    "scraped_timestamp": now_ts,
                    "scraped_date": now_cairo
                })
        except Exception as e:
            print(f"Error: {e}")

    final_ads = new_ads + valid_existing_ads
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
    print(f"Saved {len(final_ads)} verified private owner ads (IDs 20x, 1-4 active ads).")

if __name__ == "__main__":
    scrape_all()
