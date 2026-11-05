import json
import random
import re
import time
import urllib.parse
from html import unescape
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import requests as std_requests
from curl_cffi import requests as cffi_requests

CAIRO_TZ = timezone(timedelta(hours=2))
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
BASE_URL = "https://www.dubizzle.com.eg"

UNBAN_RUN64_IDS = {
    208757422, 504375098, 504374875, 504374456, 504374076, 504373179,
    504373057, 504373017, 504371180, 504302278, 504301229, 504257454,
    504250492, 503355592, 504374761, 504204009, 504212045, 503806877
}

QUERIES = [
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "من المالك" -الرحاب -مدينتي -الشروق -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "من المالك" -الرحاب -مدينتي -الشروق -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "بدون وسيط" -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "بدون وسيط" -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "النرجس" "من المالك"',
    'site:dubizzle.com.eg/ad/ "اللوتس" "من المالك"',
    'site:dubizzle.com.eg/ad/ "الياسمين" "من المالك"',
    'site:dubizzle.com.eg/ad/ "البنفسج" "من المالك"',
    'site:dubizzle.com.eg/ad/ "بيت الوطن" "من المالك"',
    'site:dubizzle.com.eg/ad/ "الأندلس" "من المالك"',
    'site:dubizzle.com.eg/ad/ "جنوب الأكاديمية" "من المالك"',
    'site:dubizzle.com.eg/ad/ "المستثمرين" "من المالك"',
    'site:dubizzle.com.eg/ad/ "التجمع الأول" "من المالك"',
    'site:dubizzle.com.eg/ad/ "التجمع الثالث" "من المالك"'
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
}

BROKER_CODE_PATTERN = re.compile(
    r"(?:\bكود\s*[:\-]?\s*[A-Za-z0-9\u0660-\u0669]{2,10}\b|\bcode\s*[:\-]?\s*[A-Za-z0-9]{2,10}\b)",
    re.IGNORECASE,
)

STRICT_FORBIDDEN_EVERYWHERE = [
    "مصر الجديدة", "مصر الجديده", "heliopolis", "مدينة نصر", "مدينه نصر", "nasr city",
    "زهراء مدينة نصر", "الكوربة", "أرض الجولف", "ارض الجولف", "روكسي", "الماظة",
    "ألماظة", "شيراتون", "النزهة", "عباس العقاد", "مكرم عبيد", "مصطفى النحاس",
    "جاردينيا سيتي", "جسر السويس", "عين شمس", "حدائق القبة", "شبرا", "حلوان",
    "المعادي", "الشيخ زايد", "6 أكتوبر", "المقطم"
]

STRICT_FORBIDDEN_LOCATIONS = STRICT_FORBIDDEN_EVERYWHERE + [
    "تاج سيتي", "taj city", "الرحاب", "مدينة الرحاب", "rehab city",
    "al rehab", "مدينتي", "مدينتى", "madinaty", "الشروق", "مدينة الشروق", "shorouk",
    "مدينة المستقبل", "المستقبل سيتي", "mostakbal", "future city", "بدر", "مدينة بدر",
    "العبور", "العاصمة الإدارية", "new capital"
]

STRICT_NEW_CAIRO_HEADER = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "القطامية", "القطاميه", "5th settlement",
    "new cairo", "1st settlement", "3rd settlement", "katameya"
]

NEW_CAIRO_WORDS = STRICT_NEW_CAIRO_HEADER + [
    "التجمع", "النرجس", "اللوتس", "الأندلس", "الاندلس", "الياسمين", "البنفسج",
    "جنوب الأكاديمية", "الاكاديمية", "شرق الأكاديمية", "المستثمرين", "بيت الوطن",
    "القرنفل", "تمر حنة", "ابو الهول", "أبو الهول", "الشويفات", "الداون تاون",
    "التسعين", "كايرو فيستيفال", "كايرو فستيفال", "ميفيدا", "ماونتن فيو", "هايد بارك",
    "بالم هيلز", "سوديك", "فيليت", "ايست تاون", "ايستاون", "زيد ايست", "دار مصر",
    "سكن مصر", "الجولدن سكوير", "فيلدج جيت", "سيتي جيت", "ليك فيو", "الحي التكميلي",
    "الدبلوماسيين", "ارابيلا", "لافيستا", "الباتيو", "مون فالي", "ذا سكوير", "فيفث سكوير"
]

SELLER_BROKER_WORDS = [
    "real estate", "realestate", "properties", "property", "investment", "investments",
    "development", "developments", "group", "agency", "consultancy", "consulting",
    "broker", "brokers", "marketing", "hospitality", "coldwell", "remax", "houseology",
    "westfield", "conquer", "sadan", "retaj", "colombus", "aspire", "privilege",
    "signature", "imkan", "closer", "el rabeh", "green home", "home group", "4 c",
    "egy property", "gate real estate", "al hayah", "elnemr", "scouts", "falcon",
    "redefine", "elviro", "wall street", "prime location", "choice", "damas", "ebtkar",
    "home hub", "lotus flower", "black code", "diamant", "maqam", "mavista",
    "brand real estate", "alofok", "new home", "fekra re", "almaz", "nch", "apex",
    "el nemr", "make money", "the landmark", "owner 59", "ghp", "backyard", "irtkaz",
    "strive", "landmax", "aqarpedia", "circle realestate", "estimate", "global stay",
    "views real estate", "egypt best", "roy real estate", "alfa development", "tawabek",
    "spade", "heritage", "platinum", "el shazly", "maak real estate", "tarek mamdouh",
    "mustafa ghanima", "ahmed essam ahmed", "mostafa hamdon", "new avenue",
    "للتسويق", "للاستثمار", "للتطوير", "للمقاولات", "للعقارات", "التسويق العقاري",
    "الاستثمار العقاري", "التطوير العقاري", "شركة موثقة", "الالمانية للتنمية",
    "وايت هوم", "بيتي للمقاولات", "النمر للتطوير", "ثقة العقارية", "شيلد للاسكان"
]


def is_broker_seller_name(name_str):
    if not name_str:
        return False
    low = name_str.lower().strip()
    for w in SELLER_BROKER_WORDS:
        if w in low:
            return True
    return False


class PacedJinaClient:
    def __init__(self):
        self.req_sess = std_requests.Session()
        self.cffi_sess = cffi_requests.Session(impersonate="chrome120")
        self.last_call_ts = 0.0

    def _wait_pace(self, min_gap=3.3):
        now = time.time()
        elapsed = now - self.last_call_ts
        if elapsed < min_gap:
            time.sleep(min_gap - elapsed)
        self.last_call_ts = time.time()

    def get_ad_markdown(self, url, timeout_sec=26):
        j_url = "https://r.jina.ai/" + url
        for attempt in range(2):
            self._wait_pace(3.3)
            sess = self.cffi_sess if attempt == 0 else self.req_sess
            try:
                r = sess.get(j_url, headers=HEADERS, timeout=timeout_sec)
                if r.status_code == 429 or "Too Many Requests" in r.text or "RateLimitExceeded" in r.text:
                    print("   [RateLimit] Pausing 14s to clear Jina window...")
                    time.sleep(14.0)
                    self.last_call_ts = time.time()
                    continue
                if r.status_code == 200 and len(r.text) > 500:
                    if (
                        "تم النشر بواسطة" in r.text
                        or "/ad/" in r.text
                        or "الوصف" in r.text
                        or "لم يعد هذا الإعلان متاح" in r.text
                        or "هذا الإعلان غير متاح" in r.text
                    ):
                        return r.text
            except Exception:
                pass
        return ""


def _strip_html(value):
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return unescape(value)


def normalize_dubizzle_url(raw_u):
    if not raw_u:
        return None, None
    u = urllib.parse.unquote(urllib.parse.unquote(str(raw_u))).strip()
    u = re.sub(r"^https?://(?:www\.)?dubizzle\.com\.eg/+en/ad/", "https://www.dubizzle.com.eg/ad/", u)
    u = re.sub(r"^/+en/ad/", "/ad/", u)
    if u.startswith("/ad/"):
        u = BASE_URL + u
    m = re.search(r"(https?://(?:www\.)?dubizzle\.com\.eg/ad/[^\s\"'<>)\]]+?-ID(\d+)\.html)", u, re.I)
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
        return ad_id >= 209345000
    if ad_id >= 500000000:
        return ad_id >= 504340000
    return False


def clean_markdown_to_text(md):
    txt = (md or "").translate(AR_DIGITS)
    txt = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"\bImage\s*\d+:?\b", " ", txt, flags=re.I)
    txt = re.sub(r"[*#_`~>|]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def get_card_tier_and_label(card_text):
    t = card_text.translate(AR_DIGITS)
    m_h = re.search(r"منذ\s*(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)", t)
    if m_h:
        return 3, m_h.group(0)
    m_h_en = re.search(r"\b(\d+)\s*(mins?|minutes?|hours?)\s*ago\b", t, re.I)
    if m_h_en:
        unit = "دقائق" if "min" in m_h_en.group(2).lower() else "ساعات"
        return 3, f"منذ {m_h_en.group(1)} {unit}"

    m_d = re.search(r"منذ\s*(\d+)\s*(?:أيام|ايام|يوم)", t)
    if m_d:
        d = int(m_d.group(1))
        if d >= 2:
            return 0, m_d.group(0)
        return 2, m_d.group(0)
    m_d_en = re.search(r"\b(\d+)\s*days?\s*ago\b", t, re.I)
    if m_d_en:
        d = int(m_d_en.group(1))
        if d >= 2:
            return 0, f"منذ {d} أيام"
        return 2, "منذ 1 يوم"

    if re.search(r"منذ\s*(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة)", t) or re.search(
        r"\b(week|weeks|month|months|year)\s*ago\b", t, re.I
    ):
        return 0, "OLD"

    return 0, "UNKNOWN"


def extract_cards_from_jina_page(raw_md):
    results = {}
    blocked_ids = set()
    if not raw_md or "شاهد المزيد من إعلانات" in raw_md:
        return results

    last_end = 0
    for m in re.finditer(r"(?:https?://(?:www\.)?dubizzle\.com\.eg)?/+(?:en/)?ad/[^\s\"'<>)\]]+?-ID(\d+)\.html", raw_md):
        clean_u, ad_id = normalize_dubizzle_url(m.group(0))
        if not clean_u or not ad_id:
            continue

        bullet_pos = raw_md.rfind("* [", max(last_end, m.start() - 650), m.start())
        start_pos = bullet_pos if bullet_pos != -1 else max(last_end, m.start() - 360)
        close_paren = raw_md.find(")", m.end(), min(len(raw_md), m.end() + 220))
        end_pos = close_paren + 1 if close_paren != -1 else min(len(raw_md), m.end() + 120)
        last_end = end_pos

        card_raw = raw_md[start_pos:end_pos]
        if "-200x150." in card_raw or "Verified Badge" in card_raw:
            blocked_ids.add(ad_id)
            results.pop(ad_id, None)
            continue
        if ad_id in blocked_ids:
            continue

        card_snip = clean_markdown_to_text(card_raw)
        if any(bad in card_snip.lower() for bad in STRICT_FORBIDDEN_LOCATIONS) or is_broker_seller_name(card_snip):
            continue

        tier, age_lbl = get_card_tier_and_label(card_snip)
        if tier < 2:
            continue
        if not any(w in card_snip.lower() for w in NEW_CAIRO_WORDS):
            continue

        if ad_id not in results or tier > results[ad_id][2]:
            results[ad_id] = (clean_u, card_snip, tier, age_lbl)

    return results


def search_yahoo_bing_recent(session):
    found = {}
    q_list = list(QUERIES)
    random.shuffle(q_list)
    for q in q_list[:12]:
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
                        if clean_u and ad_id and is_recent_id_for_search(ad_id) and ad_id not in found:
                            parent = a.find_parent(["div", "li"])
                            snip = parent.get_text(" ", strip=True) if parent else a.get_text(" ", strip=True)
                            if not any(bad in snip.lower() for bad in STRICT_FORBIDDEN_LOCATIONS) and not is_broker_seller_name(snip):
                                found[ad_id] = (clean_u, snip, 2, "منذ ساعات")
            except Exception:
                pass
            time.sleep(0.15)
    return found


def trim_before_footer_markers(text_src):
    if not text_src:
        return ""
    for marker in ["الإبلاغ عن هذا الإعلان", "قم بالإبلاغ عن هذا الإعلان", "سلامتك تهمنا"]:
        if marker in text_src:
            text_src = text_src.split(marker)[0]
    return text_src


def extract_cnt_and_seller_from_text(text_src):
    if not text_src:
        return 0, ""
    ad_sec = trim_before_footer_markers(text_src)
    clean_all = clean_markdown_to_text(_strip_html(ad_sec))

    seller = ""
    if "عضو منذ" in clean_all:
        before_member = clean_all.split("عضو منذ")[-2]
        if "تم النشر بواسطة" in before_member:
            cand = before_member.split("تم النشر بواسطة")[-1].strip(" .-:|")
            if 1 <= len(cand) <= 55:
                seller = cand

    clean_no_year = re.sub(r"عضو\s*منذ\s*\d{4}", " ", clean_all)
    clean_no_year = re.sub(r"\b20[0-2]\d\b", " ", clean_no_year)

    counts = []
    for m in re.finditer(r"\b(\d{1,4})[\s:|\-•.]{0,6}(?:ال)?(?:إ|ا)علان(?:ات)?\s*(?:ال)?نشط", clean_no_year):
        val = int(m.group(1))
        if 1 <= val <= 1500:
            counts.append(val)
    for m in re.finditer(r"(?:ال)?(?:إ|ا)علان(?:ات)?\s*(?:ال)?نشط(?:ة|ه)?[\s:|\-•.]{0,6}(\d{1,4})\b", clean_no_year):
        val = int(m.group(1))
        if 1 <= val <= 1500:
            counts.append(val)
    for m in re.finditer(r"\b(\d{1,4})\s*active\s*ads?\b", clean_no_year, re.I):
        val = int(m.group(1))
        if 1 <= val <= 1500:
            counts.append(val)
    for m in re.finditer(r"published\s*ads?\s*\(?(\d{1,4})\)?", clean_no_year, re.I):
        val = int(m.group(1))
        if 1 <= val <= 1500:
            counts.append(val)

    cnt = max(counts) if counts else 0
    if "شركة موثقة" in clean_all or is_broker_seller_name(seller):
        cnt = max(cnt, 99)

    return cnt, seller


def classify_deal_category_subtype(listing_type, url, title_clean, desc_clean, price_num):
    deal = "إيجار" if listing_type == "rent" else "بيع"
    u_dec = urllib.parse.unquote(url or "").lower()
    t_and_d = f"{title_clean} {desc_clean[:180]}".lower()

    if any(w in u_dec for w in ["rent", "إيجار", "ايجار", "للايجار", "للإيجار"]) or any(
        w in t_and_d for w in ["للإيجار", "للايجار", "إيجار", "ايجار", "for rent", "monthly"]
    ):
        deal = "إيجار"
    elif 0 < price_num < 150000:
        deal = "إيجار"

    subtype = "شقة"
    if any(w in t_and_d for w in ["دوبلكس", "دوبليكس", "duplex"]):
        subtype = "دوبلكس"
    elif any(w in t_and_d for w in ["بنتهاوس", "penthouse"]):
        subtype = "بنتهاوس"
    elif any(w in t_and_d for w in ["تاون هاوس", "توين هاوس", "فيلا", "ڤيلا", "ستاند الون", "villa", "townhouse", "twin house", "ivilla", "stand alone"]):
        subtype = "فيلا"
    elif any(w in t_and_d for w in ["سطح", "رووف", "روف", "roof"]):
        subtype = "سطح"
    elif any(w in t_and_d for w in ["شقة فندقية", "شقه فندقيه", "فندقية", "serviced", "hotel apartment"]):
        subtype = "شقة فندقية"
    elif any(w in t_and_d for w in ["ستوديو", "استوديو", "studio"]):
        subtype = "ستوديو"
    elif any(w in t_and_d for w in ["غرفة للإيجار", "غرفه للايجار", "غرفة مفروشة", "room for rent"]):
        subtype = "غرفة"
    elif any(w in f"{title_clean} {u_dec}".lower() for w in ["مكتب", "إداري", "اداري", "عيادة", "عياده", "محل", "تجاري", "تجارى", "معرض", "صيدلية", "commercial", "office", "clinic", "retail", "shop", "medical"]):
        subtype = "عقار تجاري"

    if subtype == "فيلا":
        category = "فلل للإيجار" if deal == "إيجار" else "فلل للبيع"
    elif subtype == "عقار تجاري":
        category = "عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"
    else:
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"

    return deal, category, subtype


def load_existing():
    kept = {}
    sellers_cache = {}
    checked_ids = {504371289, 504371232, 504371218, 504371178, 209365202}

    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            sellers_cache = data.get("sellers_cache_v2", {})
            checked_ids |= (
                set(data.get("checked_ids_v2", []))
                | set(data.get("checked_ids_v1", []))
                | set(data.get("checked_ids_today_v11", []))
            )
            for a in data.get("ads", []):
                aid = int(a.get("ad_id", 0))
                if not aid or aid in checked_ids:
                    continue
                if a.get("verified_v11") is True or a.get("verified_v12") is True:
                    kept[aid] = a
    except Exception:
        pass

    for uid in UNBAN_RUN64_IDS:
        checked_ids.discard(uid)

    return kept, sellers_cache, checked_ids


def check_ad_freshness_strict(ad_sec):
    before_desc = ad_sec.split("الوصف")[0] if "الوصف" in ad_sec else ad_sec[:2200]
    header_txt = clean_markdown_to_text(before_desc)

    m_old = re.search(
        r"منذ\s*(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة|سنه|سنوات)",
        header_txt
    )
    if m_old:
        return 0, m_old.group(0)

    m_days = re.search(r"منذ\s*(\d+)\s*(?:أيام|ايام|يومًا|يوما|يوم)", header_txt)
    if m_days:
        d = int(m_days.group(1))
        if d >= 2:
            return 0, m_days.group(0)
        return 2, m_days.group(0)

    m_hours = re.search(
        r"منذ\s*(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)",
        header_txt
    )
    if m_hours:
        return 3, m_hours.group(0)

    return 0, "OLD_OR_UNKNOWN_DATE"


def inspect_candidate(client, ch, sellers_cache):
    ad_id = ch["ad_id"]
    url = ch["url"]

    raw_md = client.get_ad_markdown(url, timeout_sec=25)
    if not raw_md:
        return None, False, "NO_PAGE", {}

    related_cards = extract_cards_from_jina_page(raw_md)

    if "لم يعد هذا الإعلان متاح" in raw_md or "هذا الإعلان لم يعد متاح" in raw_md or "هذا الإعلان غير متاح" in raw_md:
        return None, True, "EXPIRED", related_cards

    ad_sec = trim_before_footer_markers(raw_md)
    tier, age_label = check_ad_freshness_strict(ad_sec)
    if tier == 0 and age_label != "OLD_OR_UNKNOWN_DATE":
        print(f"Skipped Old Ad {ad_id}: Age={age_label}")
        return None, True, "OLD_AD", related_cards

    cnt, seller_name = extract_cnt_and_seller_from_text(raw_md)
    fallback_md = ""

    if cnt == 0:
        fallback_md = client.get_ad_markdown(url + "?abs=1", timeout_sec=25)
        if fallback_md:
            related_cards.update(extract_cards_from_jina_page(fallback_md))
            if "لم يعد هذا الإعلان متاح" in fallback_md or "هذا الإعلان لم يعد متاح" in fallback_md:
                return None, True, "EXPIRED", related_cards
            if tier == 0:
                tier, age_label = check_ad_freshness_strict(trim_before_footer_markers(fallback_md))
            c2, s2 = extract_cnt_and_seller_from_text(fallback_md)
            if c2 > cnt:
                cnt = c2
            if not seller_name and s2:
                seller_name = s2

    if tier == 0:
        print(f"Skipped Old Ad {ad_id}: Age={age_label}")
        return None, True, "OLD_AD", related_cards

    if cnt == 0:
        return None, False, "NO_CNT", related_cards

    seller_name = seller_name or "مالك"
    sellers_cache[seller_name] = cnt

    print(f"Checked Fresh Ad {ad_id} ({age_label}): Active_Ads={cnt} | Seller={seller_name}")

    if cnt not in (1, 2, 3, 4):
        return None, True, f"BROKER_{cnt}_ADS", {}

    combined_md = raw_md + "\n" + fallback_md
    desc_clean = ""
    for src in [ad_sec, trim_before_footer_markers(fallback_md)]:
        if src and "الوصف" in src:
            after_d = src.split("الوصف")[-1]
            for sw in ["تم النشر بواسطة", "الموقع", "معرّف الإعلان", "معرف الإعلان", "رقم الإعلان", "اقرأ المزيد في التطبيق", "الكماليات"]:
                if sw in after_d:
                    after_d = after_d.split(sw)[0]
            cand_d = clean_markdown_to_text(after_d)
            if len(cand_d) > len(desc_clean):
                desc_clean = cand_d

    title_clean = ""
    m_h1 = re.search(r"^#\s+(.+)$", ad_sec, flags=re.M)
    if m_h1:
        title_clean = clean_markdown_to_text(m_h1.group(1))
    if not title_clean:
        m_t = re.search(r"Title:\s*(.+?)(?:\n|\|)", combined_md)
        if m_t:
            title_clean = clean_markdown_to_text(m_t.group(1))

    if BROKER_CODE_PATTERN.search(desc_clean) or BROKER_CODE_PATTERN.search(title_clean):
        print(f"Skipped Broker Code Pattern in Ad {ad_id}")
        return None, True, "BROKER_CODE", {}

    before_desc_clean = clean_markdown_to_text(ad_sec.split("الوصف")[0] if "الوصف" in ad_sec else ad_sec[:1800])
    loc_box_clean = clean_markdown_to_text(combined_md.split("الموقع")[-1][:220]) if "الموقع" in combined_md else ""
    official_loc_and_title = f"{title_clean} {before_desc_clean} {loc_box_clean}".lower()
    entire_ad_text = f"{official_loc_and_title} {desc_clean}".lower()

    for bad_city in STRICT_FORBIDDEN_EVERYWHERE:
        if bad_city in entire_ad_text:
            print(f"Skipped Excluded Area ({bad_city}) in Ad {ad_id}")
            return None, True, "EXCLUDED_AREA", {}

    for bad_sat in STRICT_FORBIDDEN_LOCATIONS:
        if bad_sat in official_loc_and_title:
            print(f"Skipped Excluded Location ({bad_sat}) in Ad {ad_id}")
            return None, True, "EXCLUDED_AREA", {}

    if not any(w in official_loc_and_title for w in STRICT_NEW_CAIRO_HEADER):
        print(f"Skipped Non-New-Cairo Location in Ad {ad_id}")
        return None, True, "NOT_NEW_CAIRO", {}

    top_sec = clean_markdown_to_text(ad_sec)
    all_price_text = f"{top_sec} {desc_clean}"
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
    m_area = re.search(r"(?:المساحة|مساحة|المساحه)[^\d]{0,12}(\d{2,4})", all_price_text)
    if not m_area:
        m_area = re.search(r"\b(\d{2,4})\s*(?:متر|م2|م²|sqm)\b", all_price_text, re.I)
    if m_area:
        area = f"{m_area.group(1)} م²"

    beds = ""
    m_beds = re.search(r"(?:غرف نوم|غرف|غرفة)[^\d]{0,8}(\d{1,2})", all_price_text)
    if m_beds and 1 <= int(m_beds.group(1)) <= 12:
        beds = f"{m_beds.group(1)} غرف"

    baths = ""
    m_baths = re.search(r"(?:الحمامات|حمامات|حمام)[^\d]{0,8}(\d{1,2})", all_price_text)
    if m_baths and 1 <= int(m_baths.group(1)) <= 10:
        baths = f"{m_baths.group(1)} حمام"

    deal, category, subtype = classify_deal_category_subtype(
        ch.get("listing_type", "sale"), url, title_clean, desc_clean, price_num
    )

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
        "seller_name": seller_name,
        "seller_ads_count": cnt,
        "fresh_tier": tier,
        "description": f"[{age_label}] " + (desc_clean[:680] if desc_clean else title_clean),
        "url": url,
        "today_verified": True,
        "verified_v12": True,
        "scraped_at": datetime.now(CAIRO_TZ).isoformat(),
    }, True, f"ADDED_OWNER_{cnt}", related_cards


def candidate_priority(ch):
    uid = ch["ad_id"]
    tier = ch.get("tier", 2)
    txt = f"{ch.get('title', '')} {urllib.parse.unquote(ch.get('url', ''))}"
    score = tier * 30000000000
    if any(w in txt for w in ["من المالك", "بدون وسيط", "المالك مباشر", "من-المالك", "بدون-وسيط", "from the owner", "owner"]):
        score += 10000000000
    if 209340000 <= uid < 300000000:
        score += 5000000000
    score += uid
    return score


def scrape_all():
    kept_ads, sellers_cache, checked_ids = load_existing()
    client = PacedJinaClient()
    now_cairo = datetime.now(CAIRO_TZ)

    print(f"Kept existing owners: {len(kept_ads)} | Known sellers: {len(sellers_cache)}")

    candidate_map = {}

    if 208757422 not in kept_ads:
        candidate_map[208757422] = {
            "ad_id": 208757422,
            "url": "https://www.dubizzle.com.eg/ad/%D8%B4%D9%82%D8%A9-%D8%A3%D8%B1%D8%B6%D9%8A-180%D9%85-%D9%84%D9%84%D8%A8%D9%8A%D8%B9-%D8%A8%D8%A7%D9%84%D8%AA%D8%AC%D9%85%D8%B9-%D8%A7%D9%84%D8%AE%D8%A7%D9%85%D8%B3-%D8%A7%D9%84%D8%AD%D9%8A-%D8%A7%D9%84%D8%AB%D8%A7%D9%84%D8%AB-%D9%85%D9%88%D9%82%D8%B9-%D9%85%D9%85%D9%8A%D8%B2-ID208757422.html",
            "listing_type": "sale",
            "title": "شقة أرضي 180م للبيع بالتجمع الخامس الحي الثالث",
            "tier": 3,
            "age_label": "منذ ساعات",
        }

    search_found = search_yahoo_bing_recent(client.cffi_sess)
    for sid, (su, ssnip, stier, sage) in search_found.items():
        if sid not in kept_ads and sid not in checked_ids:
            candidate_map[sid] = {
                "ad_id": sid,
                "url": su,
                "listing_type": "sale",
                "title": ssnip[:120],
                "tier": stier,
                "age_label": sage,
            }

    for a in list(kept_ads.values()):
        try:
            seed_md = client.get_ad_markdown(a["url"], timeout_sec=24)
            for rid, (ru, rsnip, rtier, rage) in extract_cards_from_jina_page(seed_md).items():
                if rid not in kept_ads and rid not in checked_ids:
                    if rid not in candidate_map or rtier > candidate_map[rid]["tier"]:
                        candidate_map[rid] = {
                            "ad_id": rid,
                            "url": ru,
                            "listing_type": "rent" if a.get("deal") == "إيجار" else "sale",
                            "title": rsnip[:120],
                            "tier": rtier,
                            "age_label": rage,
                        }
        except Exception:
            pass

    queue = sorted(candidate_map.values(), key=candidate_priority, reverse=True)
    queued_ids = {c["ad_id"] for c in queue}

    print(f"Total fresh candidates queued for inspection: {len(queue)}")

    inspected = 0
    stats = {}

    while queue and inspected < 55:
        ch = queue.pop(0)
        ad_id = ch["ad_id"]
        if ad_id in kept_ads or ad_id in checked_ids:
            continue

        inspected += 1
        try:
            item, mark_checked, reason, new_related = inspect_candidate(client, ch, sellers_cache)
            stats[reason] = stats.get(reason, 0) + 1
            if mark_checked:
                checked_ids.add(ad_id)
            if item:
                kept_ads[ad_id] = item
                print(
                    f"[{inspected}] >>> ADDED OWNER: {ad_id} | {item['category']} ({item['subtype']}) | "
                    f"{item['price_text']} | {item['seller_name']} (Active Ads: {item['seller_ads_count']})"
                )
            added_q = False
            for rid, (ru, rsnip, rtier, rage) in new_related.items():
                if rid not in kept_ads and rid not in checked_ids and rid not in queued_ids:
                    queue.append({
                        "ad_id": rid,
                        "url": ru,
                        "listing_type": ch.get("listing_type", "sale"),
                        "title": rsnip[:120],
                        "tier": rtier,
                        "age_label": rage,
                    })
                    queued_ids.add(rid)
                    added_q = True
            if added_q:
                queue.sort(key=candidate_priority, reverse=True)
        except Exception as e:
            print(f"[{inspected}] Error {ad_id}: {e}")

    print(f"Inspection Summary: {stats}")

    final_ads = list(kept_ads.values())
    final_ads.sort(key=lambda x: (x.get("fresh_tier", 2), x.get("ad_id", 0)), reverse=True)

    out = {
        "last_scrape": now_cairo.strftime("%Y/%m/%d, %I:%M %p"),
        "total_ads": len(final_ads),
        "checked_ids_v2": sorted(list(checked_ids))[-5000:],
        "sellers_cache_v2": sellers_cache,
        "ads": final_ads,
    }
    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(final_ads)} verified fresh New Cairo owner ads.")


if __name__ == "__main__":
    scrape_all()
