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
BAN_TOPIC = "gamal_masyada_bans_2738_v1"

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
    "العاشر من رمضان", "المقطم", "الهضبة الوسطى",
    "عقارات مصايف للبيع", "عقارات مصايف للإيجار", "عقارات مصايف"
]

EXCLUDE_CITIES = STRICT_FORBIDDEN_EVERYWHERE + [
    "الرحاب", "مدينة الرحاب", "مدينتي", "مدينتى", "الشروق", "مدينة الشروق",
    "مدينة المستقبل", "المستقبل سيتي", "بدر", "مدينة بدر", "العبور", "العاصمة الإدارية",
    "تاج سيتي"
]

RECOVER_OWNER_URLS = {
    209421299: "https://www.dubizzle.com.eg/ad/%D8%B1%D9%88%D9%81-%D9%84%D9%84%D8%A5%D9%8A%D8%AC%D8%A7%D8%B1-%D8%A8%D9%85%D8%AF%D8%AE%D9%84-%D9%81%D9%86%D8%AF%D9%82%D9%8A-%D9%88%D8%A7%D8%B3%D8%A7%D9%86%D8%B3%D9%8A%D8%B1-%D9%81%D9%8A-%D8%A7%D9%84%D8%A8%D9%86%D9%81%D8%B3%D8%AC-%D9%81%D9%8A%D9%84%D8%A7%D8%AA-ID209421299.html",
    208976669: "https://www.dubizzle.com.eg/ad/%D8%B4%D9%82%D8%A9-%D9%84%D9%84%D8%A7%D9%8A%D8%AC%D8%A7%D8%B1-%D8%A8%D8%AF%D8%A7%D8%B1-%D9%85%D8%B5%D8%B1-%D8%A7%D9%84%D9%82%D8%B1%D9%86%D9%81%D9%84-ID208976669.html"
}

LIVE_DUBIZZLE_GROUPS = [
    [
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/",
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/5th-settlement/",
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/"
    ],
    [
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/",
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/5th-settlement/",
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/"
    ],
    [
        "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/",
        "https://www.dubizzle.com.eg/properties/villas-for-sale/5th-settlement/",
        "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/"
    ],
    [
        "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/",
        "https://www.dubizzle.com.eg/properties/villas-for-rent/5th-settlement/",
        "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/"
    ],
    [
        "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/",
        "https://www.dubizzle.com.eg/properties/commercial-for-sale/5th-settlement/",
        "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/"
    ],
    [
        "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/",
        "https://www.dubizzle.com.eg/properties/commercial-for-rent/5th-settlement/",
        "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/"
    ],
    [
        "https://www.dubizzle.com.eg/properties/buildings-lands/new-cairo/",
        "https://www.dubizzle.com.eg/properties/buildings-lands/5th-settlement/",
        "https://www.dubizzle.com.eg/properties/buildings-lands/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/"
    ]
]

QUERIES = [
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "من المالك" -الرحاب -مدينتي -الشروق -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "من المالك" -الرحاب -مدينتي -الشروق -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "بدون وسيط" -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "بدون وسيط" -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "فلل للبيع" "القاهرة الجديدة" -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "فلل للإيجار" "القاهرة الجديدة" -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "فيلا منفصلة" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "تاون هاوس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "توين هاوس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "عقار تجارى للبيع" "القاهرة الجديدة"',
    'site:dubizzle.com.eg/ad/ "عقار تجارى للإيجار" "القاهرة الجديدة"',
    'site:dubizzle.com.eg/ad/ "مكتب" "التجمع الخامس" -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "عيادة" "التجمع الخامس" -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "محل" "التجمع الخامس" -"مصر الجديدة" -"مدينة نصر"',
    'site:dubizzle.com.eg/ad/ "مبانى و أراضى" "القاهرة الجديدة"',
    'site:dubizzle.com.eg/ad/ "قطعة أرض" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "أرض للبيع" "بيت الوطن" "التجمع"',
    'site:dubizzle.com.eg/ad/ "عمارة للبيع" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "النرجس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "اللوتس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "الياسمين" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "البنفسج" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "بيت الوطن" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "الأندلس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "جنوب الأكاديمية" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "المستثمرين" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "القرنفل" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "تمر حنة" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "أبو الهول" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "الشويفات" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "التجمع الأول" "القاهرة الجديدة"',
    'site:dubizzle.com.eg/ad/ "التجمع الثالث" "القاهرة الجديدة"',
    'site:dubizzle.com.eg/ad/ "القطامية" "القاهرة الجديدة"',
    'site:dubizzle.com.eg/ad/ "دار مصر" "التجمع"',
    'site:dubizzle.com.eg/ad/ "سكن مصر" "التجمع"',
    'site:dubizzle.com.eg/ad/ "جنة" "التجمع"',
    'site:dubizzle.com.eg/ad/ "ميفيدا" "التجمع"',
    'site:dubizzle.com.eg/ad/ "ماونتن فيو" "التجمع"',
    'site:dubizzle.com.eg/ad/ "هايد بارك" "التجمع"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "دوبلكس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "بنتهاوس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "ستوديو" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "شقة فندقية" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "روف" "التجمع الخامس"'
]


def strip_villa_neighborhood_names(txt):
    s = txt or ""
    for phrase in [
        "البنفسج فيلات", "النرجس فيلات", "الياسمين فيلات", "القرنفل فيلات",
        "جنوب الاكاديمية فيلات", "جنوب الأكاديمية فيلات", "شرق الاكاديمية فيلات",
        "شرق الأكاديمية فيلات", "التجمع الخامس فيلات", "منطقة الفيلات", "حي الفيلات",
        "فيو فيلا", "فيو الفيلات", "داخل فيلا", "في فيلا", "بفيلا"
    ]:
        s = s.replace(phrase, " ")
    return s


def classify_deal_category_subtype(url, title_clean, desc_clean, before_desc_clean, price_num):
    u_dec = urllib.parse.unquote(url).lower()
    t_and_u = f"{title_clean} {u_dec}".lower()
    header_str = (before_desc_clean or "").lower()

    deal = "بيع"
    if any(w in header_str for w in ["للإيجار", "للايجار", "غرض العقار للإيجار", "غرض العقار للايجار"]) or any(
        w in t_and_u for w in ["rent", "إيجار", "ايجار", "للايجار", "للإيجار", "مفروش", "شهري"]
    ):
        deal = "إيجار"
    elif 0 < price_num < 150000:
        deal = "إيجار"

    if any(w in header_str for w in ["مبانى و أراضى", "مباني و أراضي", "مباني واراضي", "buildings-lands"]) or any(
        w in t_and_u for w in ["قطعة أرض", "قطعه ارض", "أرض للبيع", "ارض للبيع", "أرض سكنية", "ارض سكنيه", "أرض تجارية", "عمارة كاملة", "عماره كامله", "عمارة للبيع", "عماره للبيع", "مبنى كامل"]
    ):
        return deal, "مبانى و أراضى", "مبانى و أراضى"

    if any(w in header_str for w in ["عقار تجارى", "عقار تجاري", "عقارات تجارية", "commercial-for"]) or any(
        w in t_and_u for w in ["مكتب", "إداري", "اداري", "عيادة", "عياده", "محل ", "محل للبيع", "محل للايجار", "محل للإيجار", "تجاري", "تجارى", "معرض", "صيدلية", "صيدليه", "مقر اداري", "مقر إداري", "مبنى تجاري", "مبنى إداري", "مخزن", "مصنع", "مطعم", "كافيه"]
    ):
        category = "عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"
        return deal, category, "عقار تجاري"

    if any(w in t_and_u for w in ["شقة فندقية", "شقه فندقيه", "فندقية", "فندقيه", "serviced"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "شقة فندقية"

    if any(w in t_and_u for w in ["ستوديو", "استوديو", "studio"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "ستوديو"

    if any(w in t_and_u for w in ["غرفة للإيجار", "غرفه للايجار", "غرفة مفروشة", "غرفة مشتركة", "سكن طلاب", "غرفة "]):
        return "إيجار", "شقق للإيجار", "غرفة"

    if any(w in t_and_u for w in ["دوبلكس", "دوبليكس", "duplex"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "دوبلكس"

    if any(w in t_and_u for w in ["بنتهاوس", "penthouse"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "بنتهاوس"

    if any(w in t_and_u for w in ["سطح", "رووف", "روف ", "روف-", "roof"]) or t_and_u.startswith("روف"):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "سطح"

    if any(w in t_and_u for w in ["شقة", "شقه", "apartment"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "شقة"

    cleaned_t_and_h = strip_villa_neighborhood_names(f"{t_and_u} {header_str}")
    if any(w in header_str for w in ["فلل للبيع", "فلل للإيجار", "فلل للايجار", "villas-for"]) or any(
        w in cleaned_t_and_h for w in ["فيلا منفصلة", "فيلا مستقلة", "تاون هاوس", "توين هاوس", "ستاند الون", "فيلا للبيع", "فيلا للايجار", "فيلا للإيجار", "ڤيلا", "townhouse", "twinhouse", "standalone"]
    ):
        category = "فلل للإيجار" if deal == "إيجار" else "فلل للبيع"
        return deal, category, "فيلا"

    category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
    return deal, category, "شقة"


def fetch_manual_bans_from_cloud():
    manual_ad_ids = set()
    manual_accounts = set()
    try:
        r = std_requests.get(f"https://ntfy.sh/{BAN_TOPIC}/json?poll=1&since=all", timeout=12)
        if r.status_code == 200:
            for line in r.text.strip().split("\n"):
                if not line:
                    continue
                try:
                    pkt = json.loads(line)
                    msg = pkt.get("message")
                    if msg:
                        b = json.loads(msg)
                        if b.get("ad_id"):
                            manual_ad_ids.add(int(b["ad_id"]))
                        sname = str(b.get("seller_name", "")).lower().strip()
                        if sname and sname not in ("مالك", "المالك"):
                            manual_accounts.add(f"name:{sname}")
                        sacc = str(b.get("account_id", "")).lower().strip()
                        if sacc and sacc not in ("name:مالك", "name:المالك"):
                            manual_accounts.add(sacc)
                except Exception:
                    pass
    except Exception:
        pass
    return manual_ad_ids, manual_accounts


def load_existing():
    kept = []
    hard_banned_ids = {
        504371289, 504371232, 504371218, 504371178, 209365202,
        209420390, 504354549, 504144709
    }
    banned_accounts = set()

    cloud_ban_ids, cloud_ban_accs = fetch_manual_bans_from_cloud()
    hard_banned_ids |= cloud_ban_ids
    banned_accounts |= cloud_ban_accs

    checked = set(hard_banned_ids)

    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            banned_accounts |= set(data.get("banned_accounts_v7", []))
            banned_accounts.discard("name:مالك")
            banned_accounts.discard("name:المالك")

            for a in data.get("ads", []):
                aid = int(a.get("ad_id", 0))
                raw_sname = str(a.get("seller_name", "")).lower().strip()
                sname = f"name:{raw_sname}" if raw_sname not in ("", "مالك", "المالك") else ""
                sacc = str(a.get("account_id", "")).lower().strip()
                if sacc in ("name:مالك", "name:المالك"):
                    sacc = ""
                if aid in hard_banned_ids or (sname and sname in banned_accounts) or (sacc and sacc in banned_accounts):
                    hard_banned_ids.add(aid)
                    checked.add(aid)
                    continue
                if a.get("verified_v11") is True or a.get("verified_v12") is True:
                    deal, cat, sub = classify_deal_category_subtype(
                        a.get("url", ""),
                        a.get("title", ""),
                        a.get("description", ""),
                        "",
                        int(a.get("price_num", 0))
                    )
                    a["deal"] = deal
                    a["category"] = cat
                    a["subtype"] = sub
                    kept.append(a)

            checked |= set(data.get("checked_ids_v7", []))
    except Exception:
        pass

    kept_ids = {int(a["ad_id"]) for a in kept if "ad_id" in a}
    for rec_id in RECOVER_OWNER_URLS:
        if rec_id not in kept_ids and rec_id not in hard_banned_ids:
            checked.discard(rec_id)

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
        return ad_id >= 208950000
    if ad_id >= 500000000:
        return ad_id >= 503900000
    return False


def clean_markdown_to_text(md):
    txt = (md or "").translate(AR_DIGITS)
    txt = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"\bImage\s*\d+:?\b", " ", txt, flags=re.I)
    txt = re.sub(r"[*#_`~>]+", " ", txt)
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


def direct_dubizzle_fallback(cffi_sess, url, timeout_sec=20):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        r = cffi_sess.get(url, headers=headers, timeout=timeout_sec)
        if r.status_code == 200 and len(r.text) > 1000:
            soup = BeautifulSoup(r.text, "lxml")
            h1 = soup.find("h1")
            title_line = f"# {h1.get_text(' ', strip=True)}\n" if h1 else ""
            links_buf = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/ad/" in href or "/profile/" in href or "/companies/" in href:
                    full_h = "https://www.dubizzle.com.eg" + href if href.startswith("/") else href
                    links_buf.append(f"[{a.get_text(' ', strip=True)}]({full_h})")
            body_txt = soup.get_text(" ", strip=True)
            if "تم النشر بواسطة" in body_txt or "الوصف" in body_txt or "لم يعد هذا الإعلان متاح" in body_txt:
                return title_line + "\n" + body_txt + "\n" + "\n".join(links_buf)
    except Exception:
        pass
    return ""


def jina_get(req_sess, cffi_sess, url, timeout_sec=26):
    j_url = "https://r.jina.ai/" + url
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    for attempt in range(3):
        for sess in (cffi_sess, req_sess):
            try:
                r = sess.get(j_url, headers=headers, timeout=timeout_sec)
                if r.status_code == 429 or "Too Many Requests" in r.text or "RateLimitExceeded" in r.text:
                    time.sleep(8.0 + attempt * 4.0)
                    continue
                if r.status_code == 200 and len(r.text) > 500:
                    if "تم النشر بواسطة" in r.text or "/ad/" in r.text or "لم يعد هذا الإعلان متاح" in r.text:
                        return r.text
            except Exception:
                pass
        time.sleep(2.0 + attempt * 2.0)

    return direct_dubizzle_fallback(cffi_sess, url)


def fetch_live_dubizzle_categories(req_sess, cffi_sess):
    live_found = {}
    for group in LIVE_DUBIZZLE_GROUPS:
        cat_url = random.choice(group)
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
        time.sleep(1.0)
    return live_found


def search_engines(session):
    found = {}
    q_list = list(QUERIES)
    random.shuffle(q_list)
    for q in q_list[:20]:
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

    ad_main = text_src
    for marker in ["شاهد المزيد من إعلانات", "الإبلاغ عن هذا الإعلان", "قم بالإبلاغ عن هذا الإعلان"]:
        if marker in ad_main:
            ad_main = ad_main.split(marker)[0]

    clean_all = clean_markdown_to_text(ad_main)

    seller = "مالك"
    if "تم النشر بواسطة" in clean_all:
        after_pub = clean_all.split("تم النشر بواسطة")[-1]
        for stop_m in ["عضو منذ", "شركة موثقة", "الإعلانات النشطة", "إعلانات نشطة", "شاهد الملف"]:
            if stop_m in after_pub:
                after_pub = after_pub.split(stop_m)[0]
        cand = after_pub.strip(" .-:|")
        if 1 <= len(cand) <= 55:
            seller = cand

    if seller in ("مالك", "المالك") and account_id:
        seller = account_id

    if not account_id and seller and seller not in ("مالك", "المالك"):
        account_id = f"name:{seller.lower().strip()}"

    seller_box = clean_all.split("تم النشر بواسطة")[-1][:280] if "تم النشر بواسطة" in clean_all else clean_all
    clean_no_year = re.sub(r"عضو\s*منذ\s*\d{4}", " ||| ", seller_box)
    clean_no_year = re.sub(r"\b20[0-2]\d\b", " ||| ", clean_no_year)

    counts = []
    for m in re.finditer(r"\b(\d{1,4})[\s:\-•.]{0,8}(?:ال)?(?:إ|ا|أ)علان(?:ات)?\s*(?:ال)?نشط", clean_no_year):
        val = int(m.group(1))
        if 1 <= val <= 3000:
            counts.append(val)
    for m in re.finditer(r"(?:ال)?(?:إ|ا|أ)علان(?:ات)?\s*(?:ال)?نشط(?:ة|ه)?[\s:\-•.]{0,8}(\d{1,4})\b", clean_no_year):
        val = int(m.group(1))
        if 1 <= val <= 3000:
            counts.append(val)

    cnt = min(counts) if counts else 0

    if "شركة موثقة" in clean_all or "/companies/" in text_src:
        cnt = max(cnt, 99)

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


def inspect_and_parse(req_sess, c
