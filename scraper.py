import json
import random
import re
import time
import urllib.parse
import requests as std_requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

CAIRO_TZ = timezone(timedelta(hours=2))
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
MAX_RUNTIME_SECONDS = 22 * 60

STRICT_NEW_CAIRO_HEADER = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "القطامية", "القطاميه"
]

NEW_CAIRO_WORDS = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "التجمع", "النرجس", "اللوتس", "الأندلس", "الاندلس",
    "الياسمين", "البنفسج", "جنوب الأكاديمية", "الاكاديمية", "شرق الأكاديمية", "المستثمرين",
    "بيت الوطن", "القرنفل", "تمر حنة", "ابو الهول", "أبو الهول",
    "الشويفات", "الداون تاون", "التسعين", "القطامية", "القطاميه",
    "كايرو فيستيفال", "كايرو فستيفال", "ميفيدا", "ماونتن فيو", "هايد بارك", "بالم هيلز",
    "سوديك", "فيليت", "ايست تاون", "ايستاون", "زيد ايست", "تريو", "ازار", "دار مصر",
    "سكن مصر", "الجامعة الأمريكية", "الجامعه الامريكيه", "الجولدن سكوير",
    "فيلدج جيت", "سيتي جيت", "ليك فيو", "مكسيم", "الحي التكميلي",
    "الدبلوماسيين", "ارابيلا", "لافيستا", "الباتيو", "مون فالي", "ذا سكوير", "فيفث سكوير", "سراي"
]

STRICT_FORBIDDEN_EVERYWHERE = [
    "مصر الجديدة", "مصر الجديده", "مدينة نصر", "مدينه نصر", "زهراء مدينة نصر",
    "الكوربة", "أرض الجولف", "ارض الجولف", "ميدان الحجاز", "روكسي", "الميريلاند",
    "الماظة", "ألماظة", "شيراتون", "النزهة", "النزهه", "عباس العقاد", "مكرم عبيد",
    "مصطفى النحاس", "الحي السابع", "الحي الثامن", "الحي العاشر", "الحي السادس",
    "جاردينيا سيتي", "جسر السويس", "عين شمس", "حدائق القبة", "شبرا",
    "حلوان", "الزمالك", "وسط البلد", "رمسيس", "العباسية",
    "الإسكندرية", "الاسكندرية", "سموحة", "العجمي", "برج العرب", "الساحل الشمالي",
    "العين السخنة", "الغردقة", "شرم الشيخ", "المنصورة", "طنطا", "أسيوط",
    "الشيخ زايد", "6 أكتوبر", "٦ أكتوبر", "حدائق أكتوبر", "الهرم", "حدائق الأهرام",
    "فيصل", "المهندسين", "الدقي", "العجوزة", "المعادي", "زهراء المعادي",
    "العاشر من رمضان", "المقطم", "الهضبة الوسطى"
]

EXCLUDE_CITIES = STRICT_FORBIDDEN_EVERYWHERE + [
    "الرحاب", "مدينة الرحاب", "مدينتي", "مدينتى", "الشروق", "مدينة الشروق",
    "مدينة المستقبل", "المستقبل سيتي", "بدر", "مدينة بدر", "العبور", "العاصمة الإدارية",
    "تاج سيتي"
]

LIVE_DUBIZZLE_URLS = [
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/q-%D8%A8%D8%AF%D9%88%D9%86-%D9%88%D8%B3%D9%8A%D8%B7/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/q-%D8%A8%D8%AF%D9%88%D9%86-%D9%88%D8%B3%D9%8A%D8%B7/",
    "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/villas-for-sale/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/villas-for-rent/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/commercial-for-sale/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/commercial-for-rent/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/"
]

QUERIES = [
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "من المالك" -الرحاب -مدينتي -الشروق -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "من المالك" -الرحاب -مدينتي -الشروق -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "بدون وسيط" -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "بدون وسيط" -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "النرجس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "النرجس الجديدة" "التجمع"',
    'site:dubizzle.com.eg/ad/ "النرجس عمارات" "التجمع"',
    'site:dubizzle.com.eg/ad/ "النرجس فيلات" "التجمع"',
    'site:dubizzle.com.eg/ad/ "اللوتس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "اللوتس الشمالية" "التجمع"',
    'site:dubizzle.com.eg/ad/ "اللوتس الجنوبية" "التجمع"',
    'site:dubizzle.com.eg/ad/ "اللوتس الجديدة" "التجمع"',
    'site:dubizzle.com.eg/ad/ "الياسمين" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "البنفسج" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "البنفسج عمارات" "التجمع"',
    'site:dubizzle.com.eg/ad/ "بيت الوطن" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "الأندلس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "جنوب الأكاديمية" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "شرق الأكاديمية" "التجمع"',
    'site:dubizzle.com.eg/ad/ "المستثمرين" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "القرنفل" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "تمر حنة" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "أبو الهول" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "الشويفات" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "الدبلوماسيين" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "التجمع الأول" "القاهرة الجديدة"',
    'site:dubizzle.com.eg/ad/ "التجمع الثالث" "القاهرة الجديدة"',
    'site:dubizzle.com.eg/ad/ "القطامية" "القاهرة الجديدة"',
    'site:dubizzle.com.eg/ad/ "دار مصر" "التجمع"',
    'site:dubizzle.com.eg/ad/ "سكن مصر" "التجمع"',
    'site:dubizzle.com.eg/ad/ "جنة" "التجمع"',
    'site:dubizzle.com.eg/ad/ "ميفيدا" "التجمع"',
    'site:dubizzle.com.eg/ad/ "ماونتن فيو" "التجمع"',
    'site:dubizzle.com.eg/ad/ "هايد بارك" "التجمع"',
    'site:dubizzle.com.eg/ad/ "فيلدج جيت" "التجمع"',
    'site:dubizzle.com.eg/ad/ "سوديك" "التجمع"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "فيلا" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "دوبلكس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "بنتهاوس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "ستوديو" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "مكتب" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "عيادة" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "محل" "التجمع الخامس"'
]


def classify_deal_category_subtype(url, title_clean, desc_clean, details_sec, price_num):
    u_dec = urllib.parse.unquote(url).lower()
    t_and_d = f"{title_clean} {desc_clean[:180]}"

    deal = "بيع"
    if any(w in u_dec for w in ["rent", "إيجار", "ايجار", "للايجار", "للإيجار"]) or any(
        w in t_and_d for w in ["للإيجار", "للايجار", "إيجار", "ايجار", "مفروش", "شهري", "شهريا"]
    ):
        deal = "إيجار"
    elif 0 < price_num < 150000:
        deal = "إيجار"

    check_str = f"{title_clean} {u_dec} {details_sec} {desc_clean[:160]}"
    subtype = "شقة"

    if any(w in check_str for w in ["دوبلكس", "دوبليكس", "duplex"]):
        subtype = "دوبلكس"
    elif any(w in check_str for w in ["بنتهاوس", "penthouse"]):
        subtype = "بنتهاوس"
    elif any(w in check_str for w in ["تاون هاوس", "توين هاوس", "فيلا", "ڤيلا", "ستاند الون", "villa", "townhouse", "twin"]):
        subtype = "فيلا"
    elif any(w in check_str for w in ["سطح", "رووف", "روف", "roof"]):
        subtype = "سطح"
    elif any(w in check_str for w in ["شقة فندقية", "شقه فندقيه", "فندقية", "فندقيه", "serviced"]):
        subtype = "شقة فندقية"
    elif any(w in check_str for w in ["ستوديو", "استوديو", "studio"]):
        subtype = "ستوديو"
    elif any(w in check_str for w in ["غرفة للإيجار", "غرفه للايجار", "غرفة مفروشة", "غرفة مشتركة", "سكن طلاب"]):
        subtype = "غرفة"
    elif any(w in f"{title_clean} {u_dec}" for w in ["مكتب", "إداري", "اداري", "عيادة", "عياده", "محل", "تجاري", "تجارى", "معرض", "صيدلية", "مقر اداري", "مبنى تجاري", "commercial", "office", "clinic", "shop"]):
        subtype = "عقار تجاري"

    if subtype == "فيلا":
        category = "فلل للإيجار" if deal == "إيجار" else "فلل للبيع"
    elif subtype == "عقار تجاري":
        category = "عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"
    else:
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"

    return deal, category, subtype


def load_existing():
    kept = []
    checked = {504371289, 504371232, 504371218, 504371178, 209365202}
    banned_accounts = set()

    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for a in data.get("ads", []):
                aid = int(a.get("ad_id", 0))
                if aid in checked:
                    continue
                if a.get("verified_v11") is True or a.get("verified_v12") is True:
                    kept.append(a)
            checked |= set(data.get("checked_ids_v6", []))
            banned_accounts |= set(data.get("banned_accounts_v6", []))
    except Exception:
        pass

    return kept, checked, banned_accounts


def normalize_dubizzle_url(raw_u):
    if not raw_u:
        return None, None
    u = urllib.parse.unquote(urllib.parse.unquote(str(raw_u))).strip()
    u = re.sub(r"^https?://(?:www\.)?dubizzle\.com\.eg/+en/ad/", "https://www.dubizzle.com.eg/ad/", u)
    u = re.sub(r"^/+en/ad/", "/ad/", u)
    if u.startswith("/ad/"):
        u = "https://www.dubizzle.com.eg" + u
    m = re.search(r"(https?://(?:www\.)?dubizzle\.com\.eg/ad/[^\s\"'<>)\]]+?-ID(\d+)\.html)", u)
    if not m:
        return None, None
    full_u = m.group(1)
    ad_id = int(m.group(2))
    if ad_id < 208500000:
        return None, None
    p = urllib.parse.urlsplit(full_u)
    clean_path = urllib.parse.quote(p.path, safe="/-._~")
    return f"https://www.dubizzle.com.eg{clean_path}", ad_id


def is_recent_id_for_search(ad_id):
    if 200000000 <= ad_id < 300000000:
        return ad_id >= 209000000
    if ad_id >= 500000000:
        return ad_id >= 503900000
    return False


def clean_markdown_to_text(md):
    txt = (md or "").translate(AR_DIGITS)
    txt = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"\bImage\s*\d+:?\b", " ", txt, flags=re.I)
    txt = re.sub(r"[*#_`~>|]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def get_card_tier(card_text):
    t = card_text.translate(AR_DIGITS)
    if re.search(r"منذ\s*(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)", t):
        return 3
    m_d = re.search(r"منذ\s*(\d+)\s*(?:أيام|ايام|يوم)", t)
    if m_d:
        d = int(m_d.group(1))
        if d == 1:
            return 2
        if d <= 5:
            return 1
        return 0
    if re.search(r"منذ\s*(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة)", t):
        return 0
    return 1


def extract_links_from_text_or_html(raw_content):
    links = {}
    if not raw_content:
        return links
    for m in re.finditer(r"(?:https?://(?:www\.)?dubizzle\.com\.eg)?/+(?:en/)?ad/[^\s\"'<>)\]]+?-ID(\d+)\.html", raw_content):
        clean_u, ad_id = normalize_dubizzle_url(m.group(0))
        if not clean_u or not ad_id:
            continue
        window = raw_content[max(0, m.start() - 320):min(len(raw_content), m.end() + 320)]
        card_snip = clean_markdown_to_text(window)
        if ad_id not in links or len(card_snip) > len(links[ad_id][1]):
            links[ad_id] = (clean_u, card_snip)
    return links


def jina_get(req_sess, cffi_sess, url, timeout_sec=26):
    j_url = "https://r.jina.ai/" + url
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    for sess in (cffi_sess, req_sess):
        try:
            r = sess.get(j_url, headers=headers, timeout=timeout_sec)
            if r.status_code == 429 or "Too Many Requests" in r.text or "RateLimitExceeded" in r.text:
                time.sleep(10.0)
                continue
            if r.status_code == 200 and len(r.text) > 500:
                if "تم النشر بواسطة" in r.text or "/ad/" in r.text or "لم يعد هذا الإعلان متاح" in r.text:
                    return r.text
        except Exception:
            pass
    return ""


def fetch_live_dubizzle_categories(req_sess, cffi_sess):
    live_found = {}
    urls_to_check = list(LIVE_DUBIZZLE_URLS)
    random.shuffle(urls_to_check)
    for cat_url in urls_to_check[:6]:
        raw_txt = jina_get(req_sess, cffi_sess, cat_url, timeout_sec=24)
        if raw_txt:
            extracted = extract_links_from_text_or_html(raw_txt)
            for ad_id, (u, card_snip) in extracted.items():
                if any(bad in card_snip for bad in STRICT_FORBIDDEN_EVERYWHERE):
                    continue
                tier = get_card_tier(card_snip)
                if tier == 0:
                    continue
                if ad_id not in live_found or tier > live_found[ad_id][2]:
                    live_found[ad_id] = (u, card_snip, tier)
        time.sleep(1.2)
    return live_found


def search_engines(session):
    found = {}
    q_list = list(QUERIES)
    random.shuffle(q_list)
    for q in q_list[:22]:
        encoded = urllib.parse.quote(q)
        for y_url in [
            f"https://search.yahoo.com/search?p={encoded}&b=1",
            f"https://search.yahoo.com/search?p={encoded}&b=11"
        ]:
            try:
                r = session.get(y_url, timeout=9)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "lxml")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        target = href.split("RU=")[1].split("/RK=")[0] if "RU=" in href else href
                        clean_u, ad_id = normalize_dubizzle_url(target)
                        if clean_u and ad_id and is_recent_id_for_search(ad_id) and ad_id not in found:
                            parent = a.find_parent(["div", "li"])
                            snip = parent.get_text(" ", strip=True) if parent else a.get_text(" ", strip=True)
                            if not any(bad in snip for bad in STRICT_FORBIDDEN_EVERYWHERE):
                                found[ad_id] = (clean_u, snip, 1)
            except Exception:
                pass
            time.sleep(0.1)

        for b_url in [
            f"https://www.bing.com/search?q={encoded}&first=1",
            f"https://search.brave.com/search?q={encoded}"
        ]:
            try:
                r = session.get(b_url, timeout=9)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "lxml")
                    for a in soup.find_all("a", href=True):
                        clean_u, ad_id = normalize_dubizzle_url(a["href"])
                        if clean_u and ad_id and is_recent_id_for_search(ad_id) and ad_id not in found:
                            parent = a.find_parent(["li", "div"])
                            snip = parent.get_text(" ", strip=True) if parent else a.get_text(" ", strip=True)
                            if not any(bad in snip for bad in STRICT_FORBIDDEN_EVERYWHERE):
                                found[ad_id] = (clean_u, snip, 1)
            except Exception:
                pass
            time.sleep(0.1)
    return found


def check_ad_freshness(raw_text):
    before_desc = raw_text.split("الوصف")[0] if "الوصف" in raw_text else raw_text[:2200]
    header_txt = clean_markdown_to_text(before_desc)

    m_old = re.search(
        r"منذ\s*(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة|سنه|سنوات)",
        header_txt
    )
    if m_old:
        return 0, m_old.group(0)

    m_old2 = re.search(
        r"(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة|سنه|سنوات)\s*(?:مضى|مضت)",
        header_txt
    )
    if m_old2:
        return 0, m_old2.group(0)

    m_days = re.search(r"منذ\s*(\d+)\s*(?:أيام|ايام|يومًا|يوما|يوم)", header_txt)
    if m_days:
        d = int(m_days.group(1))
        if d > 5:
            return 0, m_days.group(0)
        if d == 1:
            return 2, m_days.group(0)
        return 1, m_days.group(0)

    m_days2 = re.search(r"(\d+)\s*(?:أيام|ايام|يومًا|يوما|يوم)\s*(?:مضى|مضت)", header_txt)
    if m_days2:
        d = int(m_days2.group(1))
        if d > 5:
            return 0, m_days2.group(0)
        if d == 1:
            return 2, m_days2.group(0)
        return 1, m_days2.group(0)

    m_hours = re.search(
        r"منذ\s*(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)",
        header_txt
    )
    if m_hours:
        return 3, m_hours.group(0)

    m_hours2 = re.search(
        r"(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)\s*(?:مضى|مضت)",
        header_txt
    )
    if m_hours2:
        return 3, m_hours2.group(0)

    return 0, "OLD_OR_UNKNOWN_DATE"


def extract_seller_account_and_active_ads(text_src):
    if not text_src:
        return 0, "", ""

    account_id = ""
    m_prof = re.search(r"dubizzle\.com\.eg/(?:en/)?(?:profile|companies)/([^\s\"'/?#)\]]+)", text_src)
    if m_prof:
        account_id = m_prof.group(1).strip().lower()

    clean_all = clean_markdown_to_text(text_src)

    seller = "مالك"
    if "عضو منذ" in clean_all:
        before_member = clean_all.split("عضو منذ")[0]
        if "تم النشر بواسطة" in before_member:
            cand = before_member.split("تم النشر بواسطة")[-1].strip(" .-:|")
            if 1 <= len(cand) <= 55:
                seller = cand

    if not account_id and seller and seller != "مالك":
        account_id = f"name:{seller.lower()}"

    seller_window = clean_all
    if "تم النشر بواسطة" in clean_all:
        idx = clean_all.find("تم النشر بواسطة")
        seller_window = clean_all[max(0, idx - 50):min(len(clean_all), idx + 450)]

    clean_no_year = re.sub(r"عضو\s*منذ\s*\d{4}", " ", seller_window)
    clean_no_year = re.sub(r"\b20[0-2]\d\b", " ", clean_no_year)

    counts = []
    for m in re.finditer(r"\b(\d{1,4})[\s:|\-•.]{0,15}(?:ال)?(?:إ|ا|أ)علان(?:ات)?\s*(?:ال)?نشط", clean_no_year):
        val = int(m.group(1))
        if 1 <= val <= 3000:
            counts.append(val)
    for m in re.finditer(r"(?:ال)?(?:إ|ا|أ)علان(?:ات)?\s*(?:ال)?نشط(?:ة|ه)?[^\d]{0,20}(\d{1,4})\b", clean_no_year):
        val = int(m.group(1))
        if 1 <= val <= 3000:
            counts.append(val)

    cnt = max(counts) if counts else 0
    return cnt, seller, account_id


def extract_same_seller_ads_to_ban(raw_text):
    banned_ad_ids = set()
    if not raw_text or "شاهد المزيد من إعلانات" not in raw_text:
        return banned_ad_ids
    after_more = raw_text.split("شاهد المزيد من إعلانات", 1)[1][:4000]
    for m in re.finditer(r"-ID(\d+)\.html", after_more):
        banned_ad_ids.add(int(m.group(1)))
    return banned_ad_ids


def extract_related_fresh(raw_text, exclude_ids=None):
    related = {}
    if not raw_text:
        return related
    exclude_ids = exclude_ids or set()

    for rid, (ru, rcard) in extract_links_from_text_or_html(raw_text).items():
        if rid in exclude_ids:
            continue
        if any(bad in rcard for bad in STRICT_FORBIDDEN_EVERYWHERE):
            continue
        tier = get_card_tier(rcard)
        if tier == 0:
            continue
        if any(w in rcard for w in NEW_CAIRO_WORDS):
            related[rid] = (ru, rcard, tier)
    return related


def inspect_and_parse(req_sess, cffi_sess, ad_id, url, snippet, banned_accounts, checked_ids):
    raw_s = jina_get(req_sess, cffi_sess, url)
    if not raw_s:
        return None, False, "NO_PAGE", {}

    if "لم يعد هذا الإعلان متاح" in raw_s or "هذا الإعلان لم يعد متاح" in raw_s or "هذا الإعلان غير متاح" in raw_s:
        return None, True, "EXPIRED", {}

    tier, age_label = check_ad_freshness(raw_s)
    if tier == 0 and age_label != "OLD_OR_UNKNOWN_DATE":
        print(f"Skipped Old Ad {ad_id}: Age={age_label}")
        return None, True, "OLD_AD", {}

    cnt, seller, account_id = extract_seller_account_and_active_ads(raw_s)

    if account_id and account_id in banned_accounts:
        same_broker_ids = extract_same_seller_ads_to_ban(raw_s)
        checked_ids.update(same_broker_ids)
        print(f"Skipped Banned Account ({seller}) on Ad {ad_id}")
        return None, True, "BANNED_ACCOUNT", {}

    fallback_s = ""
    if cnt == 0:
        fallback_s = jina_get(req_sess, cffi_sess, url + "?abs=1")
        if fallback_s:
            if "لم يعد هذا الإعلان متاح" in fallback_s or "هذا الإعلان لم يعد متاح" in fallback_s:
                return None, True, "EXPIRED", {}
            if tier == 0:
                tier, age_label = check_ad_freshness(fallback_s)
            cnt2, seller2, acc2 = extract_seller_account_and_active_ads(fallback_s)
            if cnt2 > cnt:
                cnt = cnt2
            if seller == "مالك" and seller2 != "مالك":
                seller = seller2
            if not account_id and acc2:
                account_id = acc2

    if tier == 0:
        print(f"Skipped Old Ad {ad_id}: Age={age_label}")
        return None, True, "OLD_AD", {}

    if cnt == 0:
        return None, False, "NO_CNT", {}

    print(f"Checked Ad {ad_id} ({age_label}): Active_Ads={cnt} | Seller={seller}")

    if cnt not in (1, 2, 3, 4):
        if account_id:
            banned_accounts.add(account_id)
        if seller and seller != "مالك":
            banned_accounts.add(f"name:{seller.lower()}")
        same_broker_ids = extract_same_seller_ads_to_ban(raw_s)
        if fallback_s:
            same_broker_ids |= extract_same_seller_ads_to_ban(fallback_s)
        checked_ids.update(same_broker_ids)
        return None, True, f"BANNED_BROKER_{cnt}_ADS", {}

    related_today = extract_related_fresh(raw_s)
    if fallback_s:
        related_today.update(extract_related_fresh(fallback_s))

    combined_raw = raw_s + "\n" + fallback_s
    desc_clean = ""
    for src in [raw_s, fallback_s]:
        if src and "الوصف" in src:
            after_desc = src.split("الوصف")[-1]
            for stop_w in ["تم النشر بواسطة", "الموقع", "معرّف الإعلان", "معرف الإعلان", "رقم الإعلان", "اقرأ المزيد في التطبيق", "الكماليات"]:
                if stop_w in after_desc:
                    after_desc = after_desc.split(stop_w)[0]
            cand = clean_markdown_to_text(after_desc)
            if len(cand) > len(desc_clean):
                desc_clean = cand

    title_clean = ""
    m_h1 = re.search(r"^#\s+(.+)$", raw_s, flags=re.M)
    if m_h1:
        title_clean = clean_markdown_to_text(m_h1.group(1))
    if not title_clean:
        m_t = re.search(r"Title:\s*(.+?)(?:\n|\|)", combined_raw)
        if m_t:
            title_clean = clean_markdown_to_text(m_t.group(1))

    top_sec = clean_markdown_to_text(raw_s.split("تم النشر بواسطة")[0] if "تم النشر بواسطة" in raw_s else raw_s[:3000])
    before_desc_clean = clean_markdown_to_text(raw_s.split("الوصف")[0] if "الوصف" in raw_s else raw_s[:1800])
    loc_box_clean = clean_markdown_to_text(combined_raw.split("الموقع")[-1][:220]) if "الموقع" in combined_raw else ""
    details_sec = top_sec.split("تفاصيل")[-1][:250] if "تفاصيل" in top_sec else ""

    official_loc_and_title = f"{title_clean} {before_desc_clean} {loc_box_clean}"
    entire_ad_text = f"{official_loc_and_title} {desc_clean}"

    for bad_city in STRICT_FORBIDDEN_EVERYWHERE:
        if bad_city in entire_ad_text:
            print(f"Skipped Excluded Area ({bad_city}) in Ad {ad_id}")
            return None, True, "EXCLUDED_AREA", {}

    for bad_sat in EXCLUDE_CITIES:
        if bad_sat in official_loc_and_title:
            print(f"Skipped Excluded Location ({bad_sat}) in Ad {ad_id}")
            return None, True, "EXCLUDED_AREA", {}

    if not any(w in official_loc_and_title for w in STRICT_NEW_CAIRO_HEADER):
        print(f"Skipped Non-New-Cairo Location in Ad {ad_id}")
        return None, True, "NOT_NEW_CAIRO", {}

    if not any(w in entire_ad_text for w in NEW_CAIRO_WORDS):
        return None, True, "NOT_NEW_CAIRO", {}

    all_price_text = f"{top_sec} {desc_clean} {clean_markdown_to_text(snippet)}"
    price_num = 0
    for pm in re.finditer(r"(\d[\d,]{3,11})\s*(?:ج\.م|جنيه|جم|EGP)", all_price_text):
        val = int(pm.group(1).replace(",", ""))
        if val >= 2000:
            price_num = val
            break
    if price_num == 0:
        m_mil = re.search(r"(\d+(?:\.\d+)?)\s*مليون", all_price_text)
        if m_mil:
            price_num = int(float(m_mil.group(1)) * 1000000)

    price_text = f"{price_num:,} ج.م" if price_num > 0 else "مدرج بالإعلان"

    area = "مدرج بالإعلان"
    m_area = re.search(r"(?:المساحة|مساحة|المساحه)[^\d]{0,12}(\d{2,4})", top_sec + " " + desc_clean)
    if not m_area:
        m_area = re.search(r"\b(\d{2,4})\s*(?:متر|م2|م²|sqm)\b", top_sec + " " + desc_clean, re.I)
    if m_area:
        area = f"{m_area.group(1)} م²"

    beds = ""
    m_beds = re.search(r"(?:غرف نوم|غرف|غرفة)[^\d]{0,8}(\d{1,2})", top_sec + " " + desc_clean)
    if m_beds and 1 <= int(m_beds.group(1)) <= 12:
        beds = f"{m_beds.group(1)} غرف"

    baths = ""
    m_baths = re.search(r"(?:الحمامات|حمامات|حمام)[^\d]{0,8}(\d{1,2})", top_sec + " " + desc_clean)
    if m_baths and 1 <= int(m_baths.group(1)) <= 10:
        baths = f"{m_baths.group(1)} حمام"

    deal, category, subtype = classify_deal_category_subtype(url, title_clean, desc_clean, details_sec, price_num)
    now_iso = datetime.now(CAIRO_TZ).isoformat()

    return {
        "ad_id": ad_id,
        "title": title_clean[:130] if title_clean else "وحدة بالقاهرة الجديدة",
        "price_num": price_num,
        "price_text": price_text,
        "area": area,
        "beds": beds,
        "baths": baths,
        "deal": deal,
        "category": category,
        "subtype": subtype,
        "seller_name": seller,
        "seller_ads_count": cnt,
        "fresh_tier": tier,
        "description": f"[{age_label}] " + (desc_clean[:680] if desc_clean else title_clean),
        "url": url,
        "today_verified": True,
        "verified_v12": True,
        "scraped_at": now_iso
    }, True, f"ADDED_OWNER_{cnt}_ADS", related_today


def priority_score(item_tuple):
    uid, u, snip, tier = item_tuple
    u_dec = urllib.parse.unquote(u)
    score = tier * 30000000000
    if 209000000 <= uid < 300000000:
        score += 15000000000
    if any(w in (snip + " " + u_dec) for w in ["من المالك", "بدون وسيط", "المالك مباشر", "من-المالك", "بدون-وسيط"]):
        score += 8000000000
    score += uid
    return score


def scrape_all():
    run_start = time.time()
    existing_ads, checked_ids, banned_accounts = load_existing()
    now_dt = datetime.now(CAIRO_TZ)
    kept_ads = {int(a["ad_id"]): a for a in existing_ads if "ad_id" in a}

    req_sess = std_requests.Session()
    cffi_sess = cffi_requests.Session(impersonate="chrome120")

    live_candidates = fetch_live_dubizzle_categories(req_sess, cffi_sess)
    search_candidates = search_engines(cffi_sess)

    candidates = dict(search_candidates)
    for lid, lval in live_candidates.items():
        if lid not in candidates or lval[2] > candidates[lid][2]:
            candidates[lid] = lval

    for a in existing_ads:
        try:
            raw_seed = jina_get(req_sess, cffi_sess, a["url"], timeout_sec=22)
            for rid, rval in extract_related_fresh(raw_seed, exclude_ids=checked_ids).items():
                if rid not in candidates or rval[2] > candidates[rid][2]:
                    candidates[rid] = rval
            time.sleep(0.9)
        except Exception:
            pass

    unchecked = [
        (uid, u, snip, tier)
        for uid, (u, snip, tier) in candidates.items()
        if uid not in kept_ads and uid not in checked_ids
    ]
    unchecked.sort(key=priority_score, reverse=True)

    queue = list(unchecked)
    queued_ids = {x[0] for x in queue}

    print(f"Kept existing owners: {len(kept_ads)} | Fresh unchecked candidates: {len(queue)} | Banned accounts: {len(banned_accounts)}")

    stats = {}
    inspected = 0

    while queue and (time.time() - run_start) < MAX_RUNTIME_SECONDS:
        uid, u, snip, tier = queue.pop(0)
        if uid in kept_ads or uid in checked_ids:
            continue
        inspected += 1
        try:
            item, mark_checked, reason, discovered_today = inspect_and_parse(
                req_sess, cffi_sess, uid, u, snip, banned_accounts, checked_ids
            )
            stats[reason] = stats.get(reason, 0) + 1
            if mark_checked:
                checked_ids.add(uid)
            if item:
                kept_ads[uid] = item
                print(
                    f"[{inspected}] ADDED: {uid} | {item['category']} ({item['subtype']}) | "
                    f"{item['price_text']} | {item['seller_name']} (Active Ads: {item['seller_ads_count']})"
                )
            added_new_to_q = False
            for rid, (ru, rsnip, rtier) in discovered_today.items():
                if rid not in kept_ads and rid not in checked_ids and rid not in queued_ids:
                    queue.append((rid, ru, rsnip, rtier))
                    queued_ids.add(rid)
                    added_new_to_q = True
            if added_new_to_q:
                queue.sort(key=priority_score, reverse=True)
        except Exception as e:
            print(f"[{inspected}] Error {uid}: {e}")

        time.sleep(1.2)

    print(f"Total inspected this run: {inspected} | Queue remaining: {len(queue)} | Total banned accounts: {len(banned_accounts)}")
    print(f"Inspection Summary: {stats}")

    final_ads = list(kept_ads.values())
    final_ads.sort(key=lambda x: (x.get("fresh_tier", 2), x.get("ad_id", 0)), reverse=True)

    out = {
        "last_scrape": now_dt.strftime("%Y/%m/%d, %I:%M %p"),
        "total_ads": len(final_ads),
        "checked_ids_v6": sorted(list(checked_ids))[-5000:],
        "banned_accounts_v6": sorted(list(banned_accounts))[-2000:],
        "ads": final_ads
    }
    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(final_ads)} verified fresh New Cairo owner ads.")


if __name__ == "__main__":
    scrape_all()
