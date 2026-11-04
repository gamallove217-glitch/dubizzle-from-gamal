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

NEW_CAIRO_WORDS = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "التجمع", "النرجس", "اللوتس", "الأندلس", "الاندلس",
    "الياسمين", "البنفسج", "جنوب الأكاديمية", "الاكاديمية", "شرق الأكاديمية", "المستثمرين",
    "بيت الوطن", "القرنفل", "تمر حنة", "جاردينيا", "ابو الهول", "أبو الهول",
    "النخيل", "الشويفات", "الداون تاون", "التسعين", "القطامية", "القطاميه",
    "كايرو فيستيفال", "كايرو فستيفال", "ميفيدا", "ماونتن فيو", "هايد بارك", "بالم هيلز",
    "سوديك", "فيليت", "ايست تاون", "ايستاون", "زيد ايست", "تريو", "ازار", "دار مصر",
    "سكن مصر", "جنة", "الجامعة الأمريكية", "الجامعه الامريكيه", "الجولدن سكوير",
    "فيلدج جيت", "سيتي جيت", "تاج سيتي", "ليك فيو", "مكسيم", "الحي التكميلي", "الحي الخامس",
    "الحي الثالث", "الحي الرابع", "الحي الأول", "الحي الثاني", "الدبلوماسيين", "ارابيلا",
    "لافيستا", "الباتيو", "مون فالي", "ذا سكوير", "فيفث سكوير", "سراي"
]

EXCLUDE_CITIES = [
    "الرحاب", "مدينة الرحاب", "مدينتي", "مدينتى", "الشروق", "مدينة الشروق",
    "مدينة المستقبل", "المستقبل سيتي", "بدر", "مدينة بدر", "العبور", "العاصمة الإدارية",
    "الإسكندرية", "الاسكندرية", "سموحة", "العجمي", "برج العرب", "الساحل الشمالي",
    "العين السخنة", "الغردقة", "شرم الشيخ", "المنصورة", "طنطا", "أسيوط",
    "الشيخ زايد", "6 أكتوبر", "٦ أكتوبر", "حدائق أكتوبر", "الهرم", "فيصل",
    "المهندسين", "المعادي", "زهراء المعادي", "مدينة نصر", "مصر الجديدة", "العاشر من رمضان",
    "المقطم", "الهضبة الوسطى", "شيراتون"
]

BROKER_SNIPPET_WORDS = [
    "real estate", "realestate", "properties", "property", "investment", "investments",
    "development", "developments", "group", "agency", "consultancy", "consulting",
    "broker", "brokers", "marketing", "hospitality", "capital", "avenue", "hills",
    "lounge", "hub", "insider", "middlemen", "coldwell", "remax", "houseology",
    "westfield", "conquer", "sadan", "retaj", "colombus", "aspire", "privilege",
    "signature", "imkan", "closer", "el rabeh", "green home", "home group", "4 c",
    "egy property", "gate real estate", "al hayah", "elnemr", "el boushi", "scouts",
    "falcon", "gravity", "ninety two", "mynt", "redefine", "elviro", "novo", "apeiron",
    "allocate", "orb", "hause", "start homes", "light gate", "wall street", "urz",
    "catchers", "home locator", "imic", "elaph", "msk", "the best", "deal", "proxy",
    "urban leo", "future square", "core living", "prime location", "ericson", "la costa",
    "choice", "cashpeak", "capital lords", "esmail ali", "hype set", "sfr", "damas",
    "kemet", "brookfield", "sky prime", "modern cairo", "modern home", "home approach",
    "better estate", "al fanar", "egypt land", "ahmed essam ahmed", "tarek mamdouh",
    "mustafa ghanima", "hm group", "ahmed hamza", "mostafa hamdon", "moamen farouk",
    "تريجير", "للتسويق", "للاستثمار", "للتطوير", "للمقاولات", "للعقارات", "التسويق العقاري",
    "الاستثمار العقاري", "التطوير العقاري", "شركة موثقة", "الالمانية للتنمية", "وايت هوم",
    "بيتي للمقاولات", "بانوراما للتنميه", "النمر للتطوير", "شركة السويدي", "شركه نزل",
    "ثقة العقارية", "بلوتو للوساطة"
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
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/",
    "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/"
]

QUERIES = [
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "من المالك" -الرحاب -مدينتي -الشروق',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "من المالك" -الرحاب -مدينتي -الشروق',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "بدون وسيط"',
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "بدون وسيط"',
    'site:dubizzle.com.eg/ad/ "النرجس" "من المالك"',
    'site:dubizzle.com.eg/ad/ "اللوتس" "من المالك"',
    'site:dubizzle.com.eg/ad/ "الياسمين" "من المالك"',
    'site:dubizzle.com.eg/ad/ "البنفسج" "من المالك"',
    'site:dubizzle.com.eg/ad/ "بيت الوطن" "من المالك"',
    'site:dubizzle.com.eg/ad/ "الأندلس" "من المالك"',
    'site:dubizzle.com.eg/ad/ "جنوب الأكاديمية" "من المالك"',
    'site:dubizzle.com.eg/ad/ "المستثمرين" "من المالك"',
    'site:dubizzle.com.eg/ad/ "التجمع الأول" "من المالك"',
    'site:dubizzle.com.eg/ad/ "التجمع الثالث" "من المالك"',
    'site:dubizzle.com.eg/ad/ "جاردينيا" "التجمع"',
    'site:dubizzle.com.eg/ad/ "دار مصر" "القرنفل"',
    'site:dubizzle.com.eg/ad/ "دار مصر" "الأندلس"',
    'site:dubizzle.com.eg/ad/ "سكن مصر" "التجمع"',
    'site:dubizzle.com.eg/ad/ "جنة" "التجمع"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "دوبلكس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "بنتهاوس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "فيلا" "التجمع الخامس"'
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
    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            kept = []
            for a in data.get("ads", []):
                if a.get("today_verified") is True:
                    deal, cat, sub = classify_deal_category_subtype(
                        a.get("url", ""),
                        a.get("title", ""),
                        a.get("description", ""),
                        "",
                        a.get("price_num", 0)
                    )
                    a["deal"] = deal
                    a["category"] = cat
                    a["subtype"] = sub
                    kept.append(a)
            checked = (
                set(data.get("checked_ids_today_v7", []))
                | set(data.get("checked_ids_today_v6", []))
                | set(data.get("checked_ids_today_v5", []))
            )
            brokers = set(data.get("known_brokers", []))
            return kept, checked, brokers
    except Exception:
        return [], set(), set()


def normalize_dubizzle_url(raw_u):
    u = urllib.parse.unquote(urllib.parse.unquote(raw_u)).strip()
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


def clean_markdown_to_text(md):
    txt = (md or "").translate(AR_DIGITS)
    txt = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"[*#_`~>|]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def is_likely_broker_card(card_text, known_brokers):
    low = card_text.lower()
    for w in BROKER_SNIPPET_WORDS:
        if w in low:
            return True
    for b in known_brokers:
        if len(b) >= 4 and b.lower() in low:
            return True
    return False


def get_card_tier(card_text):
    if re.search(r"منذ\s*(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة)", card_text):
        return 0
    m_d = re.search(r"منذ\s*(\d+)\s*(?:أيام|ايام|يوم)", card_text)
    if m_d and int(m_d.group(1)) >= 4:
        return 0
    if re.search(r"منذ\s*(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)", card_text):
        return 2
    if re.search(r"منذ\s*[123]\s*(?:أيام|ايام|يوم)", card_text):
        return 1
    return 1


def extract_links_from_text_or_html(raw_content):
    links = {}
    blocked_logo_ids = set()
    if not raw_content:
        return links
    for m in re.finditer(r"(?:https?://(?:www\.)?dubizzle\.com\.eg)?/ad/[^\s\"'<>)\]]+?-ID(\d+)\.html", raw_content):
        clean_u, ad_id = normalize_dubizzle_url(m.group(0))
        if not clean_u or not ad_id:
            continue
        before_220 = raw_content[max(0, m.start() - 220):m.start()]
        if "-200x150." in before_220:
            blocked_logo_ids.add(ad_id)
            links.pop(ad_id, None)
            continue
        if ad_id in blocked_logo_ids:
            continue
        window = raw_content[max(0, m.start() - 480):min(len(raw_content), m.end() + 340)]
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
            if r.status_code == 200 and len(r.text) > 500:
                if "Too Many Requests" not in r.text and "RateLimitExceeded" not in r.text:
                    if "تم النشر بواسطة" in r.text or "/ad/" in r.text or "لم يعد هذا الإعلان متاح" in r.text:
                        return r.text
        except Exception:
            pass
    return ""


def fetch_live_dubizzle_categories(req_sess, cffi_sess, known_brokers):
    live_found = {}
    for cat_url in LIVE_DUBIZZLE_URLS:
        raw_txt = jina_get(req_sess, cffi_sess, cat_url, timeout_sec=25)
        if raw_txt:
            extracted = extract_links_from_text_or_html(raw_txt)
            for ad_id, (u, card_snip) in extracted.items():
                if any(bad in card_snip for bad in EXCLUDE_CITIES):
                    continue
                tier = get_card_tier(card_snip)
                if tier == 0:
                    continue
                if is_likely_broker_card(card_snip, known_brokers):
                    continue
                if ad_id not in live_found or tier > live_found[ad_id][2]:
                    live_found[ad_id] = (u, card_snip, tier)
        time.sleep(0.5)
    return live_found


def search_yahoo_bing(session, known_brokers):
    found = {}
    q_list = list(QUERIES)
    random.shuffle(q_list)
    for q in q_list[:18]:
        encoded = urllib.parse.quote(q)
        for y_url in [
            f"https://search.yahoo.com/search?p={encoded}&b=1",
            f"https://search.yahoo.com/search?p={encoded}&b=11"
        ]:
            try:
                r = session.get(y_url, timeout=10)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "lxml")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        target = href.split("RU=")[1].split("/RK=")[0] if "RU=" in href else href
                        clean_u, ad_id = normalize_dubizzle_url(target)
                        if clean_u and ad_id and ad_id not in found:
                            parent = a.find_parent(["div", "li"])
                            snip = parent.get_text(" ", strip=True) if parent else a.get_text(" ", strip=True)
                            if not any(bad in snip for bad in EXCLUDE_CITIES) and not is_likely_broker_card(snip, known_brokers):
                                found[ad_id] = (clean_u, snip, 1)
            except Exception:
                pass
            time.sleep(0.15)

        b_url = f"https://www.bing.com/search?q={encoded}"
        try:
            r = session.get(b_url, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                for a in soup.find_all("a", href=True):
                    clean_u, ad_id = normalize_dubizzle_url(a["href"])
                    if clean_u and ad_id and ad_id not in found:
                        parent = a.find_parent(["li", "div"])
                        snip = parent.get_text(" ", strip=True) if parent else a.get_text(" ", strip=True)
                        if not any(bad in snip for bad in EXCLUDE_CITIES) and not is_likely_broker_card(snip, known_brokers):
                            found[ad_id] = (clean_u, snip, 1)
        except Exception:
            pass
        time.sleep(0.15)
    return found


def trim_after_report(text_src):
    if not text_src:
        return ""
    for marker in ["الإبلاغ عن هذا الإعلان", "قم بالإبلاغ عن هذا الإعلان", "سلامتك تهمنا"]:
        if marker in text_src:
            return text_src.split(marker)[0]
    return text_src


def check_ad_freshness(ad_sec):
    before_desc = ad_sec.split("الوصف")[0] if "الوصف" in ad_sec else ad_sec[:2200]
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
        if d >= 4:
            return 0, m_days.group(0)
        return 1, m_days.group(0)

    m_days2 = re.search(r"(\d+)\s*(?:أيام|ايام|يومًا|يوما|يوم)\s*(?:مضى|مضت)", header_txt)
    if m_days2:
        d = int(m_days2.group(1))
        if d >= 4:
            return 0, m_days2.group(0)
        return 1, m_days2.group(0)

    m_hours = re.search(
        r"منذ\s*(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)",
        header_txt
    )
    if m_hours:
        return 2, m_hours.group(0)

    m_hours2 = re.search(
        r"(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)\s*(?:مضى|مضت)",
        header_txt
    )
    if m_hours2:
        return 2, m_hours2.group(0)

    return 0, "OLD_OR_UNKNOWN_DATE"


def extract_cnt_and_seller(text_src):
    if not text_src:
        return 0, ""
    ad_sec = trim_after_report(text_src)
    clean_all = clean_markdown_to_text(ad_sec)

    cnt = 0
    for m in re.finditer(r"(?:ال)?(?:إ|ا)علان(?:ات)?\s*(?:ال)?نشط(?:ة|ه)?[^\d]{0,25}(\d{1,4})\b", clean_all):
        val = int(m.group(1))
        if 1 <= val <= 1500:
            cnt = val
    if cnt == 0:
        for m in re.finditer(r"\b(\d{1,4})[^\d]{0,15}(?:ال)?(?:إ|ا)علان(?:ات)?\s*(?:ال)?نشط", clean_all):
            val = int(m.group(1))
            if 1 <= val <= 1500:
                cnt = val

    seller = "مالك"
    if "عضو منذ" in clean_all:
        before_member = clean_all.split("عضو منذ")[-2]
        if "تم النشر بواسطة" in before_member:
            cand = before_member.split("تم النشر بواسطة")[-1].strip(" .-:|")
            if 1 <= len(cand) <= 55:
                seller = cand
    return cnt, seller


def extract_related_fresh(raw_text, known_brokers):
    related = {}
    for rid, (ru, rcard) in extract_links_from_text_or_html(raw_text).items():
        if any(bad in rcard for bad in EXCLUDE_CITIES):
            continue
        tier = get_card_tier(rcard)
        if tier == 0:
            continue
        if is_likely_broker_card(rcard, known_brokers):
            continue
        if any(w in rcard for w in NEW_CAIRO_WORDS):
            if re.search(r"(?:دقائق|دقيقة|ساعات|ساعة|منذ 1 يوم|منذ 2 أيام|منذ 3 أيام)", rcard) or "المالك" in rcard:
                related[rid] = (ru, rcard, tier)
    return related


def inspect_and_parse(req_sess, cffi_sess, ad_id, url, snippet, known_brokers):
    raw_s = jina_get(req_sess, cffi_sess, url)
    if not raw_s:
        return None, False, "NO_PAGE", {}

    related_today = extract_related_fresh(raw_s, known_brokers)

    if "لم يعد هذا الإعلان متاح" in raw_s or "هذا الإعلان لم يعد متاح" in raw_s or "هذا الإعلان غير متاح" in raw_s:
        return None, True, "EXPIRED", related_today

    ad_sec = trim_after_report(raw_s)
    tier, age_label = check_ad_freshness(ad_sec)
    if tier == 0 and age_label != "OLD_OR_UNKNOWN_DATE":
        print(f"Skipped Old Ad {ad_id}: Age={age_label}")
        return None, True, "OLD_AD", related_today

    cnt, seller = extract_cnt_and_seller(raw_s)
    fallback_s = ""
    if cnt == 0:
        fallback_s = jina_get(req_sess, cffi_sess, url + "?abs=1")
        if fallback_s:
            related_today.update(extract_related_fresh(fallback_s, known_brokers))
            if "لم يعد هذا الإعلان متاح" in fallback_s or "هذا الإعلان لم يعد متاح" in fallback_s:
                return None, True, "EXPIRED", related_today
            if tier == 0:
                tier, age_label = check_ad_freshness(trim_after_report(fallback_s))
            cnt2, seller2 = extract_cnt_and_seller(fallback_s)
            if cnt2 > 0:
                cnt = cnt2
            if seller == "مالك" and seller2 != "مالك":
                seller = seller2

    if tier == 0:
        print(f"Skipped Old Ad {ad_id}: Age={age_label}")
        return None, True, "OLD_AD", related_today

    if cnt == 0:
        return None, False, "NO_CNT", related_today

    if cnt > 4 and seller and seller != "مالك":
        known_brokers.add(seller)

    print(f"Checked Fresh Ad {ad_id} ({age_label}): Active_Ads={cnt} | Seller={seller}")

    if cnt not in (1, 2, 3, 4):
        if cnt > 8:
            return None, True, f"BROKER_{cnt}_ADS", {}
        limited_rel = dict(list(related_today.items())[-3:])
        return None, True, f"BROKER_{cnt}_ADS", limited_rel

    combined_raw = raw_s + "\n" + fallback_s
    desc_clean = ""
    for src in [ad_sec, trim_after_report(fallback_s)]:
        if src and "الوصف" in src:
            after_desc = src.split("الوصف")[-1]
            for stop_w in ["تم النشر بواسطة", "الموقع", "معرّف الإعلان", "معرف الإعلان", "رقم الإعلان", "اقرأ المزيد في التطبيق", "الكماليات"]:
                if stop_w in after_desc:
                    after_desc = after_desc.split(stop_w)[0]
            cand = clean_markdown_to_text(after_desc)
            if len(cand) > len(desc_clean):
                desc_clean = cand

    title_clean = ""
    m_h1 = re.search(r"^#\s+(.+)$", ad_sec, flags=re.M)
    if m_h1:
        title_clean = clean_markdown_to_text(m_h1.group(1))
    if not title_clean:
        m_t = re.search(r"Title:\s*(.+?)(?:\n|\|)", combined_raw)
        if m_t:
            title_clean = clean_markdown_to_text(m_t.group(1))

    top_sec = clean_markdown_to_text(ad_sec)
    details_sec = ""
    if "تفاصيل" in top_sec:
        details_sec = top_sec.split("تفاصيل")[-1][:250]

    full_check = f"{title_clean} {desc_clean} {top_sec} {snippet}"

    for bad_city in EXCLUDE_CITIES:
        if bad_city in f"{title_clean} {desc_clean}":
            return None, True, "EXCLUDED_AREA", related_today

    if not any(w in full_check for w in NEW_CAIRO_WORDS):
        return None, True, "NOT_NEW_CAIRO", related_today

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
        "scraped_at": now_iso
    }, True, f"ADDED_ADS_{cnt}", related_today


def priority_score(item_tuple):
    uid, u, snip, tier = item_tuple
    score = tier * 5000000000
    if "المالك" in snip or "بدون وسيط" in snip:
        score += 2000000000
    if 209000000 <= uid < 300000000:
        score += 1000000000 + uid
    else:
        score += uid
    return score


def scrape_all():
    existing_ads, checked_ids, known_brokers = load_existing()
    now_dt = datetime.now(CAIRO_TZ)
    kept_ads = {int(a["ad_id"]): a for a in existing_ads if "ad_id" in a}

    req_sess = std_requests.Session()
    cffi_sess = cffi_requests.Session(impersonate="chrome120")

    live_candidates = fetch_live_dubizzle_categories(req_sess, cffi_sess, known_brokers)
    search_candidates = search_yahoo_bing(cffi_sess, known_brokers)

    candidates = dict(search_candidates)
    candidates.update(live_candidates)

    for a in existing_ads:
        try:
            raw_seed = jina_get(req_sess, cffi_sess, a["url"], timeout_sec=22)
            for rid, rval in extract_related_fresh(raw_seed, known_brokers).items():
                if rid not in candidates or rval[2] > candidates[rid][2]:
                    candidates[rid] = rval
        except Exception:
            pass

    print(f"Total fresh candidates: {len(candidates)} | Kept ads: {len(kept_ads)}")

    unchecked = [
        (uid, u, snip, tier)
        for uid, (u, snip, tier) in candidates.items()
        if uid not in kept_ads and uid not in checked_ids
    ]
    unchecked.sort(key=priority_score, reverse=True)
    print(f"Unchecked candidates to inspect: {len(unchecked)}")

    stats = {}
    inspected = 0
    queue = list(unchecked)
    queued_ids = {x[0] for x in queue}

    while queue and inspected < 65:
        uid, u, snip, tier = queue.pop(0)
        if uid in kept_ads or uid in checked_ids:
            continue
        if is_likely_broker_card(snip, known_brokers):
            checked_ids.add(uid)
            continue
        inspected += 1
        try:
            item, mark_checked, reason, discovered_today = inspect_and_parse(
                req_sess, cffi_sess, uid, u, snip, known_brokers
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
            for rid, (ru, rsnip, rtier) in sorted(discovered_today.items(), key=lambda x: (x[1][2], x[0])):
                if rid not in kept_ads and rid not in checked_ids and rid not in queued_ids:
                    queue.insert(0, (rid, ru, rsnip, rtier))
                    queued_ids.add(rid)
        except Exception as e:
            print(f"[{inspected}] Error {uid}: {e}")

        time.sleep(1.0 if reason in ("OLD_AD", "EXPIRED") else 2.2)

    print(f"Inspection Summary: {stats}")

    final_ads = list(kept_ads.values())
    final_ads.sort(key=lambda x: (x.get("fresh_tier", 1), x.get("ad_id", 0)), reverse=True)

    out = {
        "last_scrape": now_dt.strftime("%Y/%m/%d, %I:%M %p"),
        "total_ads": len(final_ads),
        "checked_ids_today_v7": sorted(list(checked_ids))[-5000:],
        "known_brokers": sorted(list(known_brokers))[-1000:],
        "ads": final_ads
    }
    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(final_ads)} verified fresh New Cairo owner ads.")


if __name__ == "__main__":
    scrape_all()
