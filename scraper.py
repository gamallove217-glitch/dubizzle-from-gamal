import json
import time
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

API_KEY = "1fbcb4ca0bad271b0780c0a848e8c05b"
SCHEMA_VERSION = 9
SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

SEARCH_QUERIES = [
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار التجمع الخامس", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار القاهرة الجديدة", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع التجمع الخامس", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع القاهرة الجديدة", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار الرحاب", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار مدينتي", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع الرحاب او مدينتي", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ دوبلكس التجمع الخامس", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ بنتهاوس التجمع الخامس", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ استوديو او غرفة للايجار التجمع", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ فيلا للايجار التجمع الخامس", "deal": "إيجار", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ فيلا للبيع التجمع الخامس", "deal": "بيع", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ تاون هاوس التجمع الخامس", "deal": "بيع", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ مكتب اداري للايجار التجمع الخامس", "deal": "إيجار", "category": "تجاري وإداري"},
    {"q": "site:dubizzle.com.eg/ad/ محل او عيادة التجمع الخامس", "deal": "إيجار", "category": "تجاري وإداري"}
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
    t_low = title.lower()
    if any(w in t_low for w in ["للايجار", "للإيجار", "ايجار", "إيجار", "for rent", "rent", "مفروش"]):
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
    m = re.search(r"-ID(\d+)", ad_url, re.I)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return 0
    return 0

def extract_specs(text):
    price_text = ""
    price_num = 0

    patterns = [
        r"(?:ج\.م|ج\.م\.|EGP)\s*([\d,]{4,12})",
        r"([\d,]{4,12})\s*(?:ج\.م|جنيه|جنية|EGP)",
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

def inspect_live_ad(cand, blocked_users):
    ad_url = cand["url"]
    html = ""
    for mode in [{"premium": "true"}, {}]:
        try:
            params = {"api_key": API_KEY, "url": ad_url}
            params.update(mode)
            res = requests.get("http://api.scraperapi.com", params=params, timeout=35)
            if res.status_code in [404, 410]:
                return None
            if res.status_code == 200 and len(res.text) > 1500:
                html = res.text
                break
        except Exception:
            pass

    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    for s in soup(["script", "style", "noscript"]):
        s.decompose()

    vis_text = soup.get_text(" | ", strip=True)
    if any(dp in vis_text.lower() for dp in DELETED_PHRASES):
        return None

    for a in soup.find_all("a", href=True):
        if "/companies/" in a["href"] or "/agencies/" in a["href"]:
            blocked_users.add(a["href"])
            return None

    h1 = soup.find("h1")
    live_title = h1.get_text(strip=True) if h1 and h1.get_text(strip=True) else cand["title"]
    if not is_strictly_new_cairo(live_title):
        return None

    main_content = vis_text.split("الاتجاهات والمؤشرات")[0].split("إعلانات ذات صلة")[0]

    m_count = (
        re.search(r"(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]\s*[:：]?\s*(\d+)", vis_text, re.I)
        or re.search(r"(\d+)\s*(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]", vis_text, re.I)
        or re.search(r"active\s*ads\s*[:：]?\s*(\d+)", vis_text, re.I)
    )
    if not m_count:
        return None

    ads_count = int(m_count.group(1))

    seller_name = "مالك مباشر"
    m_name = re.search(r"تم النشر بواسطة\s*\|?\s*([^\|\n\.]{2,35})", vis_text)
    if m_name:
        seller_name = m_name.group(1).strip()

    seller_key = seller_name if seller_name != "مالك مباشر" else ad_url
    for a in soup.find_all("a", href=True):
        if "/profile/" in a["href"]:
            seller_key = a["href"]
            if seller_name == "مالك مباشر":
                seller_name = a.get_text(strip=True) or "مالك مباشر"
            break

    if ads_count > 7:
        blocked_users.add(seller_key)
        return None

    if seller_key in blocked_users or ads_count < 1 or ads_count > 4:
        return None

    price_text, price_num, area, beds, baths = extract_specs(main_content)
    if price_num <= 0:
        return None

    desc_el = soup.find("div", {"aria-label": "Description"}) or soup.find("div", class_=re.compile(r"description", re.I))
    if desc_el:
        clean_desc = desc_el.get_text("\n", strip=True)
    else:
        m_desc = re.search(r"وصف\s*\|?\s*(.+?)(?:المرافق|الاتجاهات والمؤشرات|تم النشر بواسطة|$)", main_content)
        clean_desc = m_desc.group(1).replace(" | ", "\n").strip() if m_desc else cand["snippet"]

    cat_name, subtype = detect_category_and_subtype(live_title, clean_desc, cand["default_cat"])
    deal_name = detect_deal(live_title, clean_desc, cand["default_deal"])

    return {
        "schema_version": SCHEMA_VERSION,
        "ad_id": extract_ad_id(ad_url),
        "title": live_title,
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
        "seller_ads_count": ads_count
    }

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
        ad_stored_ts = ad.get("scraped_timestamp", now_ts)
        if (now_ts - ad_stored_ts) >= SEVEN_DAYS_SECONDS:
            continue
        sk = ad.get("seller_profile", "")
        if sk and sk in blocked_users:
            continue
        if not is_strictly_new_cairo(ad.get("title", "")):
            continue
        if ad.get("seller_ads_count", 1) > 4 or ad.get("price_num", 0) <= 0:
            continue
        valid_existing_ads.append(ad)

    seen_urls = {ad.get("url") for ad in valid_existing_ads if ad.get("url")}
    candidates = []

    for idx, item in enumerate(SEARCH_QUERIES):
        if idx > 0:
            time.sleep(3)
        try:
            params = {
                "api_key": API_KEY,
                "query": item["q"],
                "hl": "ar",
                "gl": "eg",
                "num": "20"
            }
            res = requests.get("https://api.scraperapi.com/structured/google/search", params=params, timeout=40)
            if res.status_code != 200:
                continue
            results = res.json().get("organic_results", [])
            for r in results:
                ad_url = r.get("link", "").split("?")[0]
                if "dubizzle.com.eg" not in ad_url or "/ad/" not in ad_url:
                    continue
                if "/companies/" in ad_url or "/agencies/" in ad_url or ad_url in seen_urls:
                    continue

                title = re.sub(r"\s*[-|]\s*(?:دوبيزل|dubizzle).*$", "", r.get("title", ""), flags=re.I).strip()
                snippet = r.get("snippet", "").strip()

                if not is_strictly_new_cairo(title):
                    continue
                if any(dp in (title + " " + snippet).lower() for dp in DELETED_PHRASES):
                    continue

                seen_urls.add(ad_url)
                candidates.append({
                    "title": title,
                    "snippet": snippet,
                    "url": ad_url,
                    "default_deal": item["deal"],
                    "default_cat": item["category"]
                })
        except Exception as e:
            print(f"Query error: {e}")

    print(f"Collected {len(candidates)} New Cairo candidates. Inspecting live pages...")

    verified_new = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(inspect_live_ad, cand, blocked_users) for cand in candidates[:55]]
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                res["scraped_timestamp"] = now_ts
                res["scraped_date"] = now_cairo
                verified_new.append(res)

    final_ads = verified_new + valid_existing_ads
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
    print(f"Saved {len(final_ads)} verified New Cairo owner ads (1-4 ads only).")

if __name__ == "__main__":
    scrape_all()
