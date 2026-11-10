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
MAX_RUNTIME_SECONDS = 9 * 60
BAN_TOPIC = "gamal_masyada_bans_2738_v1"

STRICT_NEW_CAIRO_HEADER = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "القطامية", "القطاميه",
    "new cairo", "5th settlement", "fifth settlement", "first settlement", "third settlement", "katameya",
    "حي أول", "حي اول", "حي ثاني", "حي تاني", "حي ثالث", "حي رابع", "حي خامس",
    "الحي الأول", "الحي الاول", "الحي الثاني", "الحي التاني", "الحي الثالث", "الحي الرابع", "الحي الخامس"
]

NEW_CAIRO_WORDS = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "التجمع", "الحي الأول", "الحي الاول", "الحي الثاني",
    "الحي التاني", "الحي الثالث", "الحي التالت", "الحي الرابع", "الحي الخامس",
    "حي أول", "حي اول", "حي ثاني", "حي تاني", "حي ثالث", "حي رابع", "حي خامس",
    "النرجس", "اللوتس", "الأندلس", "الاندلس", "الياسمين", "البنفسج",
    "جنوب الأكاديمية", "جنوب الاكاديمية", "الاكاديمية", "شرق الأكاديمية", "شرق الاكاديمية",
    "المستثمرين", "النورث هاوس", "القرنفل", "تمر حنة", "اللؤلؤة", "ابو الهول", "أبو الهول",
    "جاردينيا هايتس", "غرب الجولف", "غرب أرابيلا", "غرب ارابيلا", "أرابيلا", "ارابيلا",
    "الشويفات", "الداون تاون", "التسعين", "القطامية", "القطاميه", "فاطمة الشربتلي", "الشربتلي",
    "كايرو فيستيفال", "كايرو فستيفال", "ميفيدا", "ماونتن فيو", "هايد بارك", "بالم هيلز",
    "سوديك", "فيليت", "ايست تاون", "ايستاون", "زيد ايست", "تريو", "ازار", "دار مصر",
    "سكن مصر", "جنة", "الجامعة الأمريكية", "الجامعه الامريكيه", "الجولدن سكوير",
    "فيلدج جيت", "سيتي جيت", "ليك فيو", "مكسيم", "الحي التكميلي", "الدبلوماسيين",
    "لافيستا", "الباتيو", "مون فالي", "ذا سكوير", "فيفث سكوير", "سراي",
    "new cairo", "5th settlement", "fifth settlement", "katameya"
]

STRICT_FORBIDDEN_EVERYWHERE = [
    "مصر الجديدة", "مصر الجديده", "مدينة نصر", "مدينه نصر", "زهراء مدينة نصر",
    "الكوربة", "أرض الجولف", "ارض الجولف", "ميدان الحجاز", "روكسي", "الميريلاند",
    "الماظة", "ألماظة", "شيراتون", "النزهة", "النزهه", "عباس العقاد", "مكرم عبيد",
    "مصطفى النحاس", "الحي العاشر", "جاردينيا سيتي", "جسر السويس", "عين شمس",
    "حدائق القبة", "شبرا", "حلوان", "الزمالك", "وسط البلد", "رمسيس", "العباسية",
    "الإسكندرية", "الاسكندرية", "سموحة", "العجمي", "برج العرب", "الساحل الشمالي",
    "العين السخنة", "الغردقة", "شرم الشيخ", "المنصورة", "طنطا", "أسيوط",
    "الشيخ زايد", "6 أكتوبر", "٦ أكتوبر", "حدائق أكتوبر", "الهرم", "حدائق الأهرام",
    "فيصل", "المهندسين", "الدقي", "العجوزة", "المعادي", "زهراء المعادي",
    "العاشر من رمضان", "المقطم", "الهضبة الوسطى",
    "شاليه للبيع", "شاليه للإيجار", "شاليه للايجار", "راس الحكمة", "رأس الحكمة", "مراسي", "الجونة"
]

EXCLUDE_CITIES = STRICT_FORBIDDEN_EVERYWHERE + [
    "الرحاب", "مدينة الرحاب", "مدينتي", "مدينتى", "الشروق", "مدينة الشروق",
    "مدينة المستقبل", "المستقبل سيتي", "بدر", "مدينة بدر", "العبور", "العاصمة الإدارية", "تاج سيتي"
]

FRONTEND_SANITIZE_WORDS = [
    "مصر الجديدة", "مصر الجديده", "مدينة نصر", "مدينه نصر", "زهراء مدينة نصر",
    "الكوربة", "أرض الجولف", "ارض الجولف", "ميدان الحجاز", "روكسي", "الماظة", "ألماظة",
    "شيراتون", "النزهة", "عباس العقاد", "مكرم عبيد", "مصطفى النحاس",
    "الرحاب", "مدينتي", "الشروق", "العاصمة الإدارية", "مدينة المستقبل", "عقارات مصايف"
]

DUBIZZLE_CATEGORY_BASES = [
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/villas-for-sale/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/",
    "https://www.dubizzle.com.eg/properties/villas-for-rent/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/commercial-for-sale/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/",
    "https://www.dubizzle.com.eg/properties/commercial-for-rent/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/buildings-lands/new-cairo/",
    "https://www.dubizzle.com.eg/properties/buildings-lands/5th-settlement/"
]

PRIORITY_RECOVER_IDS = [207686431]


def strip_tashkeel(s):
    return re.sub(r"[\u064b-\u065f\u0670\u0640]+", "", s or "")


def clean_markdown_to_text(md):
    txt = strip_tashkeel((md or "").translate(AR_DIGITS))
    txt = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"\bImage\s*\d+:?\b", " ", txt, flags=re.I)
    txt = re.sub(r"[*#_`~>]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def has_beit_el_watan_or_installments(title_txt, desc_txt, url_txt=""):
    full = strip_tashkeel(f"{title_txt} {desc_txt} {urllib.parse.unquote(url_txt)}".translate(AR_DIGITS))
    bw_cleaned = re.sub(
        r"(?:قريب[ةه]?\s*من|تبعد\s*[^\n,.]{0,20}عن|يبعد\s*[^\n,.]{0,20}عن|بجوار|أمام|امام|على\s*بعد\s*[^\n,.]{0,20}من|طريق|فاصل\s*مع)\s*(?:منطقة\s*|حي\s*)?(?:بيت\s*الوطن|بيت\s*وطن)",
        " ", full, flags=re.I
    )
    if re.search(r"(?:بيت\s*الوطن|بيت\s*وطن|beit[\s\-]*el[\s\-]*watan|bait[\s\-]*el[\s\-]*watan)", bw_cleaned, flags=re.I):
        return True, "EXCLUDED_BEIT_EL_WATAN"

    inst_cleaned = re.sub(
        r"(?:بدون|من\s*غير|لا\s*يوجد|مفيش|غير\s*متاح|وليس|مش|خالص[ةه]?|مدفوع[ةه]?|شامل[ةه]?|مسدد[ةه]?|انتهت)\s*(?:أي\s*|كل\s*|جميع\s*)?(?:ال)?(?:أقساط|اقساط|تقسيط|دفعات)",
        " ", full, flags=re.I
    )
    inst_cleaned = re.sub(r"كاش\s*(?:فقط\s*)?(?:وليس|مش|بدون)\s*(?:تقسيط|أقساط|اقساط)", " ", inst_cleaned, flags=re.I)
    if re.search(
        r"(?:\bبالتقسيط\b|\bتقسيط\b|\bأقساط\b|\bاقساط\b|تسهيلات\s*في\s*السداد|تسهيلات\s*بالسداد|مقدم\s*\d+\s*%|والباقي\s*على\s*\d+|أوفر\s*برايس|اوفر\s*برايس|بقسط\s*شهري|قسط\s*ربع\s*سنوي)",
        inst_cleaned, flags=re.I
    ):
        return True, "EXCLUDED_INSTALLMENTS"
    return False, ""


def sanitize_desc_for_frontend(text):
    s = text or ""
    for w in FRONTEND_SANITIZE_WORDS:
        s = s.replace(w, " ")
    return re.sub(r"\s+", " ", s).strip()


def strip_villa_neighborhood_names(txt):
    s = txt or ""
    for p in [
        "البنفسج فيلات", "النرجس فيلات", "الياسمين فيلات", "القرنفل فيلات",
        "جنوب الاكاديمية فيلات", "جنوب الأكاديمية فيلات", "شرق الاكاديمية فيلات",
        "شرق الأكاديمية فيلات", "التجمع الخامس فيلات", "منطقة الفيلات", "حي الفيلات",
        "فيو فيلا", "فيو الفيلات", "داخل فيلا", "في فيلا", "بفيلا", "بفيلا خاصة", "فيلا خاصة"
    ]:
        s = s.replace(p, " ")
    return s


def classify_deal_category_subtype(url, title_clean, desc_clean, before_desc_clean, price_num):
    u_dec = urllib.parse.unquote(url).lower()
    t_low = (title_clean or "").lower()
    t_and_u = f"{t_low} {u_dec}".lower()
    header_str = (before_desc_clean or "").lower()

    deal = "بيع"
    if any(w in header_str for w in ["للإيجار", "للايجار", "غرض العقار للإيجار", "غرض العقار للايجار", "monthly", "شهريا", "شهرياً"]) or any(
        w in t_and_u for w in ["rent", "إيجار", "ايجار", "للايجار", "للإيجار", "مفروش", "شهري"]
    ):
        deal = "إيجار"
    elif 0 < price_num < 150000:
        deal = "إيجار"

    is_explicit_apt = any(w in t_low for w in ["شقة", "شقه", "دور كامل", "apartment", "flat", "دوبلكس", "دوبليكس", "بنتهاوس", "ستوديو", "استوديو", "studio", "رووف", "روف"])

    if (any(w in header_str for w in ["مبانى و أراضى", "مباني و أراضي", "مباني واراضي", "buildings-lands"]) or any(
        w in t_and_u for w in ["قطعة أرض", "قطعه ارض", "أرض للبيع", "ارض للبيع", "أرض سكنية", "ارض سكنيه", "أرض تجارية", "عمارة كاملة", "عماره كامله", "عمارة للبيع", "عماره للبيع", "مبنى كامل"]
    )) and not is_explicit_apt:
        return deal, "مبانى و أراضى", "مبانى و أراضى"

    if (any(w in header_str for w in ["عقار تجارى", "عقار تجاري", "عقارات تجارية", "commercial-for"]) or any(
        w in t_and_u for w in ["retail", "shop", "medical", "clinic", "office", "business park", "مكتب", "إداري", "اداري", "عيادة", "عياده", "محل ", "محل للبيع", "محل للايجار", "محل للإيجار", "تجاري", "تجارى", "معرض", "صيدلية", "صيدليه", "مقر اداري", "مقر إداري", "مبنى تجاري", "مبنى إداري", "مخزن", "مصنع", "مطعم", "كافيه"]
    )) and not is_explicit_apt:
        return deal, ("عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"), "عقار تجاري"

    if any(w in t_and_u for w in ["شقة فندقية", "شقه فندقيه", "فندقية", "فندقيه", "serviced"]):
        return deal, ("شقق للإيجار" if deal == "إيجار" else "شقق للبيع"), "شقة فندقية"
    if any(w in t_and_u for w in ["ستوديو", "استوديو", "studio"]):
        return deal, ("شقق للإيجار" if deal == "إيجار" else "شقق للبيع"), "ستوديو"
    if any(w in t_and_u for w in ["غرفة للإيجار", "غرفه للايجار", "غرفة مفروشة", "غرفة مشتركة", "سكن طلاب"]) and not is_explicit_apt and (0 < price_num < 150000):
        return "إيجار", "شقق للإيجار", "غرفة"
    if any(w in t_and_u for w in ["دوبلكس", "دوبليكس", "duplex"]):
        return deal, ("شقق للإيجار" if deal == "إيجار" else "شقق للبيع"), "دوبلكس"
    if any(w in t_and_u for w in ["بنتهاوس", "penthouse"]):
        return deal, ("شقق للإيجار" if deal == "إيجار" else "شقق للبيع"), "بنتهاوس"
    if any(w in t_and_u for w in ["سطح", "رووف", "روف ", "روف-", "roof"]) or t_and_u.startswith("روف"):
        return deal, ("شقق للإيجار" if deal == "إيجار" else "شقق للبيع"), "سطح"
    if any(w in t_and_u for w in ["شقة", "شقه", "دور كامل", "apartment"]):
        return deal, ("شقق للإيجار" if deal == "إيجار" else "شقق للبيع"), "شقة"

    cleaned_t_and_h = strip_villa_neighborhood_names(f"{t_and_u} {header_str}")
    if any(w in header_str for w in ["فلل للبيع", "فلل للإيجار", "فلل للايجار", "villas-for"]) or any(
        w in cleaned_t_and_h for w in ["فيلا منفصلة", "فيلا مستقلة", "تاون هاوس", "توين هاوس", "ستاند الون", "فيلا للبيع", "فيلا للايجار", "فيلا للإيجار", "ڤيلا", "townhouse", "twinhouse", "standalone"]
    ):
        return deal, ("فلل للإيجار" if deal == "إيجار" else "فلل للبيع"), "فيلا"

    return deal, ("شقق للإيجار" if deal == "إيجار" else "شقق للبيع"), "شقة"


def fetch_manual_bans_from_cloud():
    manual_ad_ids, manual_accounts = set(), set()
    try:
        r = std_requests.get(f"https://ntfy.sh/{BAN_TOPIC}/json?poll=1&since=all", timeout=10)
        if r.status_code == 200:
            for line in r.text.strip().split("\n"):
                if not line:
                    continue
                try:
                    msg = json.loads(line).get("message")
                    if msg:
                        b = json.loads(msg)
                        if b.get("ad_id"):
                            manual_ad_ids.add(int(b["ad_id"]))
                        sn = str(b.get("seller_name", "")).lower().strip()
                        if sn and sn not in ("مالك", "المالك"):
                            manual_accounts.add(f"name:{sn}")
                        sa = str(b.get("account_id", "")).lower().strip()
                        if sa and sa not in ("name:مالك", "name:المالك"):
                            manual_accounts.add(sa)
                except Exception:
                    pass
    except Exception:
        pass
    return manual_ad_ids, manual_accounts


def load_existing():
    kept = []
    hard_banned_ids = {
        504371289, 504371232, 504371218, 504371178, 209365202,
        209420390, 504354549, 504144709, 504397712
    }
    banned_accounts = {"name:ghada"}
    preserved_top_keys = {}

    cloud_ban_ids, cloud_ban_accs = fetch_manual_bans_from_cloud()
    hard_banned_ids |= cloud_ban_ids
    banned_accounts |= cloud_ban_accs
    checked = set(hard_banned_ids)

    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for k in ("last_run_report", "checked_extra_v15", "checked_extra_v16", "telegram_chat_ids", "telegram_welcomed_ids", "notified_ids_v1"):
                if k in data:
                    preserved_top_keys[k] = data[k]

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
                if int(a.get("seller_ads_count", 1)) > 4:
                    hard_banned_ids.add(aid)
                    checked.add(aid)
                    continue
                if aid in hard_banned_ids or (sname and sname in banned_accounts) or (sacc and sacc in banned_accounts):
                    hard_banned_ids.add(aid)
                    checked.add(aid)
                    continue
                is_bad_bw_inst, _ = has_beit_el_watan_or_installments(a.get("title", ""), a.get("description", ""), a.get("url", ""))
                if is_bad_bw_inst:
                    checked.add(aid)
                    continue
                if a.get("verified_v11") is True or a.get("verified_v12") is True:
                    if a.get("source", "دوبيزل") == "دوبيزل":
                        deal, cat, sub = classify_deal_category_subtype(a.get("url", ""), a.get("title", ""), a.get("description", ""), "", int(a.get("price_num", 0)))
                        a["deal"], a["category"], a["subtype"] = deal, cat, sub
                        a["description"] = sanitize_desc_for_frontend(a.get("description", ""))
                    kept.append(a)

            if "checked_ids_v12" in data:
                checked |= set(data.get("checked_ids_v12", []))
            else:
                for old_cid in data.get("checked_ids_v7", []):
                    cid_int = int(old_cid)
                    if cid_int >= 504375000 and cid_int not in hard_banned_ids:
                        continue
                    if 207000000 <= cid_int < 300000000 and cid_int not in hard_banned_ids:
                        continue
                    checked.add(cid_int)
    except Exception:
        pass

    for pid in PRIORITY_RECOVER_IDS:
        checked.discard(pid)

    return kept, checked, banned_accounts, preserved_top_keys


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
    p = urllib.parse.urlsplit(m.group(1))
    return f"https://www.dubizzle.com.eg{urllib.parse.quote(p.path, safe='/-._~')}", int(m.group(2))


def get_card_tier(card_text):
    t = strip_tashkeel(card_text.translate(AR_DIGITS))
    if re.search(r"منذ\s*(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)", t) or re.search(r"(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)\s*(?:مضى|مضت)", t):
        return 3
    m_d = re.search(r"منذ\s*(\d+)\s*(?:أيام|ايام|يوما|يوم)", t) or re.search(r"(\d+)\s*(?:أيام|ايام|يوما|يوم)\s*(?:مضى|مضت)", t)
    if m_d:
        d = int(m_d.group(1))
        return 2 if d == 1 else (1 if d <= 5 else 1)
    return 1


def extract_links_from_text_or_html(raw_content):
    links = {}
    if not raw_content:
        return links
    for m in re.finditer(r"(?:https?://(?:www\.)?dubizzle\.com\.eg)?/+(?:en/)?ad/[^\s\"'<>)\]]+?-ID(\d+)\.html", raw_content):
        clean_u, ad_id = normalize_dubizzle_url(m.group(0))
        if not clean_u or not ad_id:
            continue
        window = raw_content[max(0, m.start() - 180):min(len(raw_content), m.end() + 180)]
        card_snip = clean_markdown_to_text(window)
        if ad_id not in links or len(card_snip) > len(links[ad_id][1]):
            links[ad_id] = (clean_u, card_snip)
    return links


def direct_dubizzle_fetch(cffi_sess, url, timeout_sec=16):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ar-EG,ar;q=0.9"
    }
    try:
        r = cffi_sess.get(url, headers=headers, timeout=timeout_sec)
        if r.status_code == 200 and len(r.text) > 1000 and "Just a moment" not in r.text:
            soup = BeautifulSoup(r.text, "lxml")
            h1 = soup.find("h1")
            title_line = f"# {h1.get_text(' ', strip=True)}\n" if h1 else ""
            links_buf = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/ad/" in href or "/profile/" in href or "/companies/" in href:
                    full_h = "https://www.dubizzle.com.eg" + href if href.startswith("/") else href
                    links_buf.append(f"[{a.get_text(' ', strip=True)}]({full_h})")
            for tag in soup.find_all(["nav", "header", "footer", "script", "style"]):
                tag.decompose()
            body_txt = soup.get_text(" ", strip=True)
            if "تم النشر بواسطة" in body_txt or "الوصف" in body_txt or "لم يعد هذا الإعلان متاح" in body_txt or links_buf:
                return title_line + "\n" + body_txt + "\n" + "\n".join(links_buf)
    except Exception:
        pass
    return ""


def jina_get(req_sess, cffi_sess, url, timeout_sec=22):
    j_url = "https://r.jina.ai/" + url
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
        "Accept-Language": "ar-EG,ar;q=0.9"
    }
    for attempt in range(2):
        for sess in (cffi_sess, req_sess):
            try:
                r = sess.get(j_url, headers=headers, timeout=timeout_sec)
                if r.status_code == 429 or "Too Many Requests" in r.text:
                    time.sleep(5.0 + attempt * 3.0)
                    continue
                if r.status_code == 200 and len(r.text) > 500:
                    if "تم النشر بواسطة" in r.text or "/ad/" in r.text or "لم يعد هذا الإعلان متاح" in r.text:
                        return r.text
            except Exception:
                pass
        time.sleep(1.2)
    return direct_dubizzle_fetch(cffi_sess, url, timeout_sec=16)


def fetch_live_dubizzle_categories(req_sess, cffi_sess):
    live_found, all_cat_pages = {}, []
    for base in DUBIZZLE_CATEGORY_BASES:
        all_cat_pages.extend([base, base + "?page=2", base + "?page=3", base + "?page=4"])
    random.shuffle(all_cat_pages)
    for cat_url in all_cat_pages[:16]:
        raw_txt = direct_dubizzle_fetch(cffi_sess, cat_url, timeout_sec=15) or jina_get(req_sess, cffi_sess, cat_url, timeout_sec=20)
        if raw_txt:
            for ad_id, (u, card_snip) in extract_links_from_text_or_html(raw_txt).items():
                tier = get_card_tier(card_snip)
                if ad_id not in live_found or tier > live_found[ad_id][2]:
                    live_found[ad_id] = (u, card_snip, tier)
        time.sleep(0.5)

    for pid in PRIORITY_RECOVER_IDS:
        if pid not in live_found:
            for s_url in [f"https://search.yahoo.com/search?p=site:dubizzle.com.eg+ID{pid}", f"https://www.bing.com/search?q=site:dubizzle.com.eg+ID{pid}"]:
                try:
                    r = cffi_sess.get(s_url, timeout=8)
                    if r.status_code == 200:
                        for ad_id, (u, snip) in extract_links_from_text_or_html(urllib.parse.unquote(r.text)).items():
                            live_found[ad_id] = (u, snip, 3)
                except Exception:
                    pass
            if pid not in live_found:
                live_found[pid] = (f"https://www.dubizzle.com.eg/ad/apartment-for-rent-in-5th-settlement-ID{pid}.html", "التجمع الخامس القاهرة الجديدة", 3)
    return live_found


def slice_from_h1(raw_text):
    m_h1 = re.search(r"^#\s+.+$", raw_text, flags=re.M)
    return raw_text[max(0, m_h1.start() - 180):] if m_h1 else raw_text


def check_ad_freshness(raw_text):
    sliced = slice_from_h1(raw_text)
    before_desc = sliced.split("الوصف")[0] if "الوصف" in sliced else (sliced.split("وصف")[0] if "وصف" in sliced else sliced[:2200])
    header_txt = clean_markdown_to_text(before_desc)

    m_old = re.search(r"منذ\s*(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة|سنه|سنوات)", header_txt) or re.search(
        r"(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة|سنه|سنوات)\s*(?:مضى|مضت)", header_txt
    )
    if m_old:
        return 0, m_old.group(0)

    m_days = re.search(r"منذ\s*(\d+)\s*(?:أيام|ايام|يوما|يوم)", header_txt) or re.search(
        r"(\d+)\s*(?:أيام|ايام|يوما|يوم)\s*(?:مضى|مضت)", header_txt
    )
    if m_days:
        d = int(m_days.group(1))
        return (0, m_days.group(0)) if d > 5 else ((2 if d == 1 else 1), m_days.group(0))

    m_hours = re.search(r"منذ\s*(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)", header_txt) or re.search(
        r"(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)\s*(?:مضى|مضت)", header_txt
    )
    if m_hours:
        return 3, m_hours.group(0)

    if "أمس" in header_txt or "اليوم" in header_txt:
        return 2, "اليوم/أمس"

    return 0, "OLD_OR_UNKNOWN_DATE"


def extract_seller_account_and_active_ads(text_src):
    if not text_src:
        return 0, "", ""
    account_id = ""
    m_prof = re.search(r"dubizzle\.com\.eg/(?:en/)?(?:profile|companies)/([^\s\"'/?#)\]]+)", text_src)
    if m_prof:
        account_id = m_prof.group(1).strip().lower()

    same_seller_cards = len(extract_same_seller_ads_to_ban(text_src))

    ad_main = text_src
    for marker in ["شاهد المزيد من إعلانات", "الإبلاغ عن هذا الإعلان", "قم بالإبلاغ عن هذا الإعلان", "معرّف الإعلان", "معرف الإعلان"]:
        if marker in ad_main:
            ad_main = ad_main.split(marker)[0]

    clean_all = clean_markdown_to_text(ad_main)
    seller = "مالك"
    if "تم النشر بواسطة" in clean_all:
        after_pub = clean_all.split("تم النشر بواسطة")[-1]
        for stop_m in ["عضو منذ", "شركة موثقة", "الإعلانات النشطة", "إعلانات نشطة", "اعلانات نشطة", "شاهد الملف"]:
            if stop_m in after_pub:
                after_pub = after_pub.split(stop_m)[0]
        cand = after_pub.strip(" .-:|")
        if 1 <= len(cand) <= 55:
            seller = cand

    if seller in ("مالك", "المالك") and account_id:
        seller = account_id
    if not account_id and seller and seller not in ("مالك", "المالك"):
        account_id = f"name:{seller.lower().strip()}"

    seller_box = clean_all.split("تم النشر بواسطة")[-1][:320] if "تم النشر بواسطة" in clean_all else clean_all
    clean_no_year = re.sub(r"عضو\s*منذ\s*\d{4}", " ||| ", seller_box)
    clean_no_year = re.sub(r"\b(?:19\d\d|20[0-2]\d)\b", " ||| ", clean_no_year)

    counts = []
    for m in re.finditer(
        r"\b(\d{1,4})[\s:\-•.]{0,8}(?:ال)?(?:إ|ا|أ)علان(?:ات)?\s*(?:ال)?نشط|(?:ال)?(?:إ|ا|أ)علان(?:ات)?\s*(?:ال)?نشط(?:ة|ه)?[\s:\-•.]{0,8}(\d{1,4})\b",
        clean_no_year
    ):
        val = int(m.group(1) or m.group(2))
        if 1 <= val <= 3000:
            counts.append(val)

    cnt = max(counts) if counts else 0
    if same_seller_cards > cnt:
        cnt = same_seller_cards
    if "شركة موثقة" in clean_all or "/companies/" in text_src:
        cnt = max(cnt, 99)
    return cnt, seller, account_id


def extract_same_seller_ads_to_ban(raw_text):
    banned_ad_ids = set()
    if raw_text and "شاهد المزيد من إعلانات" in raw_text:
        for m in re.finditer(r"-ID(\d+)\.html", raw_text.split("شاهد المزيد من إعلانات", 1)[1][:4000]):
            banned_ad_ids.add(int(m.group(1)))
    return banned_ad_ids


def extract_related_fresh(raw_text, exclude_ids=None):
    related = {}
    if not raw_text:
        return related
    exclude_ids = exclude_ids or set()
    for rid, (ru, rcard) in extract_links_from_text_or_html(raw_text).items():
        if rid in exclude_ids or any(bad in rcard for bad in STRICT_FORBIDDEN_EVERYWHERE):
            continue
        tier = get_card_tier(rcard)
        if any(w in rcard.lower() for w in [x.lower() for x in NEW_CAIRO_WORDS]):
            related[rid] = (ru, rcard, tier)
    return related


def inspect_and_parse(req_sess, cffi_sess, ad_id, url, snippet, banned_accounts, checked_ids):
    raw_s = jina_get(req_sess, cffi_sess, url)
    if not raw_s:
        return None, False, "NO_PAGE", {}
    if any(x in raw_s for x in ["لم يعد هذا الإعلان متاح", "هذا الإعلان لم يعد متاح", "هذا الإعلان غير متاح"]):
        return None, True, "EXPIRED", {}

    tier, age_label = check_ad_freshness(raw_s)
    if tier == 0 and age_label != "OLD_OR_UNKNOWN_DATE":
        return None, True, "OLD_AD", {}

    cnt, seller, account_id = extract_seller_account_and_active_ads(raw_s)
    sname_key = f"name:{seller.lower().strip()}" if (seller and seller not in ("مالك", "المالك")) else ""
    if (account_id and account_id in banned_accounts) or (sname_key and sname_key in banned_accounts):
        checked_ids.update(extract_same_seller_ads_to_ban(raw_s))
        return None, True, "BANNED_ACCOUNT", {}

    fallback_s = ""
    if cnt == 0 or tier == 0:
        fallback_s = direct_dubizzle_fetch(cffi_sess, url) or jina_get(req_sess, cffi_sess, url + "?abs=1")
        if fallback_s:
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
        return None, True, "OLD_AD", {}
    if cnt == 0:
        return None, False, "NO_CNT", {}

    print(f"Checked Ad {ad_id} ({age_label}): Active_Ads={cnt} | Seller={seller}")

    if cnt not in (1, 2, 3, 4):
        if cnt != 99:
            if account_id and account_id not in ("name:مالك", "name:المالك"):
                banned_accounts.add(account_id)
            if seller and seller not in ("مالك", "المالك"):
                banned_accounts.add(f"name:{seller.lower().strip()}")
            checked_ids.update(extract_same_seller_ads_to_ban(raw_s))
        return None, True, f"BANNED_BROKER_{cnt}_ADS", {}

    related_today = extract_related_fresh(raw_s, exclude_ids=checked_ids)
    sliced_raw = slice_from_h1(raw_s)
    combined_raw = sliced_raw + "\n" + (slice_from_h1(fallback_s) if fallback_s else "")
    desc_clean = ""
    for src in [sliced_raw, fallback_s]:
        if src:
            split_word = "الوصف" if "الوصف" in src else ("وصف" if "وصف" in src else "")
            if split_word:
                after_desc = src.split(split_word, 1)[-1]
                for stop_w in ["تم النشر بواسطة", "الموقع", "معرّف الإعلان", "معرف الإعلان", "رقم الإعلان", "اقرأ المزيد في التطبيق", "المرافق", "الكماليات"]:
                    if stop_w in after_desc:
                        after_desc = after_desc.split(stop_w)[0]
                cand = clean_markdown_to_text(after_desc)
                if len(cand) > len(desc_clean):
                    desc_clean = cand

    m_h1 = re.search(r"^#\s+(.+)$", raw_s, flags=re.M)
    title_clean = clean_markdown_to_text(m_h1.group(1)) if m_h1 else ""
    top_sec = clean_markdown_to_text(sliced_raw.split("تم النشر بواسطة")[0] if "تم النشر بواسطة" in sliced_raw else sliced_raw[:2500])
    before_desc_clean = clean_markdown_to_text(sliced_raw.split("الوصف")[0] if "الوصف" in sliced_raw else sliced_raw[:1500])
    loc_box_clean = clean_markdown_to_text(combined_raw.split("الموقع")[-1][:240]) if "الموقع" in combined_raw else ""

    official_loc_and_title = f"{title_clean} {before_desc_clean} {loc_box_clean} {urllib.parse.unquote(url)}"
    entire_ad_text = f"{official_loc_and_title} {desc_clean}"

    for bad_sat in EXCLUDE_CITIES:
        if bad_sat in f"{title_clean} {loc_box_clean}":
            return None, True, "EXCLUDED_AREA", {}

    is_bw_or_inst, bw_reason = has_beit_el_watan_or_installments(official_loc_and_title, desc_clean, url)
    if is_bw_or_inst:
        print(f"Skipped {bw_reason} in Ad {ad_id}")
        return None, True, bw_reason, {}

    if not any(w.lower() in entire_ad_text.lower() for w in STRICT_NEW_CAIRO_HEADER):
        return None, True, "NOT_NEW_CAIRO", {}
    if not any(w.lower() in entire_ad_text.lower() for w in NEW_CAIRO_WORDS):
        return None, True, "NOT_NEW_CAIRO", {}

    all_price_text = f"{top_sec} {desc_clean} {clean_markdown_to_text(snippet)}"
    price_num = 0
    for pm in re.finditer(r"(?:ج\.م|جنيه|جم|EGP)\s*(\d[\d,]{3,11})|(\d[\d,]{3,11})\s*(?:ج\.م|جنيه|جم|EGP)", all_price_text):
        val = int((pm.group(1) or pm.group(2)).replace(",", ""))
        if val >= 2000:
            price_num = val
            break
    if price_num == 0:
        m_mil = re.search(r"(\d+(?:\.\d+)?)\s*مليون", all_price_text)
        if m_mil:
            price_num = int(float(m_mil.group(1)) * 1000000)

    price_text = f"{price_num:,} ج.م" if price_num > 0 else "مدرج بالإعلان"
    m_area = re.search(r"(?:المساحة|مساحة|المساحه|Area)[^\d]{0,15}(\d{2,4})|\b(\d{2,4})\s*(?:متر|م2|م²|sqm)\b", top_sec + " " + desc_clean, re.I)
    area = f"{m_area.group(1) or m_area.group(2)} م²" if m_area else "مدرج بالإعلان"
    m_beds = re.search(r"(?:غرف نوم|غرف|غرفة|Bedrooms|أسرة)[^\d]{0,10}(\d{1,2})|(\d{1,2})\s*(?:غرف نوم|غرف|أسرة)", top_sec + " " + desc_clean, re.I)
    b_val = (m_beds.group(1) or m_beds.group(2)) if m_beds else ""
    beds = f"{b_val} غرف" if (b_val and 1 <= int(b_val) <= 12) else ""
    m_baths = re.search(r"(?:الحمامات|حمامات|حمام|Bathrooms)[^\d]{0,10}(\d{1,2})|(\d{1,2})\s*(?:حمامات|حمام)", top_sec + " " + desc_clean, re.I)
    ba_val = (m_baths.group(1) or m_baths.group(2)) if m_baths else ""
    baths = f"{ba_val} حمام" if (ba_val and 1 <= int(ba_val) <= 10) else ""

    deal, category, subtype = classify_deal_category_subtype(url, title_clean, desc_clean, before_desc_clean, price_num)
    now_iso = datetime.now(CAIRO_TZ).isoformat()
    safe_desc = sanitize_desc_for_frontend(desc_clean[:680] if desc_clean else title_clean)

    return {
        "ad_id": ad_id, "source": "دوبيزل", "title": title_clean[:130] or "وحدة بالقاهرة الجديدة",
        "price_num": price_num, "price_text": price_text, "area": area, "beds": beds, "baths": baths,
        "deal": deal, "category": category, "subtype": subtype, "seller_name": seller,
        "account_id": account_id, "seller_ads_count": cnt, "fresh_tier": tier,
        "description": f"[{age_label}] {safe_desc}", "url": url,
        "today_verified": True, "verified_v12": True, "scraped_at": now_iso
    }, True, f"ADDED_OWNER_{cnt}_ADS", related_today


def scrape_all():
    run_start = time.time()
    existing_ads, checked_ids, banned_accounts, preserved_top_keys = load_existing()
    now_dt = datetime.now(CAIRO_TZ)
    kept_ads = {int(a["ad_id"]): a for a in existing_ads if "ad_id" in a}
    req_sess, cffi_sess = std_requests.Session(), cffi_requests.Session(impersonate="chrome120")

    for a in [x for x in list(kept_ads.values()) if x.get("source", "دوبيزل") == "دوبيزل"][:6]:
        try:
            aid = int(a["ad_id"])
            raw_chk = jina_get(req_sess, cffi_sess, a["url"], timeout_sec=16)
            if raw_chk:
                cnt_now, s_now, acc_now = extract_seller_account_and_active_ads(raw_chk)
                if cnt_now > 4:
                    print(f"Removed previously saved Ad {aid} ({s_now}): Active_Ads increased to {cnt_now}")
                    kept_ads.pop(aid, None)
                    checked_ids.add(aid)
                    if acc_now and acc_now not in ("name:مالك", "name:المالك"):
                        banned_accounts.add(acc_now)
        except Exception:
            pass

    candidates = fetch_live_dubizzle_categories(req_sess, cffi_sess)
    for a in [x for x in list(kept_ads.values()) if x.get("source", "دوبيزل") == "دوبيزل"][:8]:
        try:
            raw_seed = jina_get(req_sess, cffi_sess, a["url"], timeout_sec=18)
            for rid, rval in extract_related_fresh(raw_seed, exclude_ids=checked_ids).items():
                if rid not in candidates or rval[2] > candidates[rid][2]:
                    candidates[rid] = rval
            time.sleep(0.4)
        except Exception:
            pass

    unchecked = [(uid, u, snip, tier) for uid, (u, snip, tier) in candidates.items() if uid not in kept_ads and uid not in checked_ids]
    unchecked.sort(key=lambda x: (1 if x[0] in PRIORITY_RECOVER_IDS else 0, x[3], x[0]), reverse=True)
    queue = list(unchecked[:55])
    queued_ids = {x[0] for x in queue}

    stats, inspected = {}, 0
    while queue and (time.time() - run_start) < MAX_RUNTIME_SECONDS:
        uid, u, snip, tier = queue.pop(0)
        if uid in kept_ads or uid in checked_ids:
            continue
        inspected += 1
        try:
            item, mark_checked, reason, discovered_today = inspect_and_parse(req_sess, cffi_sess, uid, u, snip, banned_accounts, checked_ids)
            stats[reason] = stats.get(reason, 0) + 1
            if mark_checked:
                checked_ids.add(uid)
            if item:
                kept_ads[uid] = item
                print(f"[{inspected}] ADDED: {uid} | {item['category']} | {item['price_text']} | Active Ads: {item['seller_ads_count']}")
            for rid, (ru, rsnip, rtier) in discovered_today.items():
                if rid not in kept_ads and rid not in checked_ids and rid not in queued_ids and len(queue) < 65:
                    queue.append((rid, ru, rsnip, rtier))
                    queued_ids.add(rid)
        except Exception as e:
            print(f"Error {uid}: {e}")
        time.sleep(0.8)

    print(f"Total inspected this run: {inspected}")
    print(f"Inspection Summary: {stats}")
    final_ads = sorted(list(kept_ads.values()), key=lambda x: (x.get("fresh_tier", 2), x.get("ad_id", 0)), reverse=True)

    out = {
        "last_scrape": now_dt.strftime("%Y/%m/%d, %I:%M %p"), "total_ads": len(final_ads),
        "checked_ids_v7": sorted(list(checked_ids))[-5000:], "checked_ids_v12": sorted(list(checked_ids))[-5000:],
        "banned_accounts_v7": sorted(list(banned_accounts))[-2000:], "ads": final_ads
    }
    for k, v in preserved_top_keys.items():
        out[k] = v
    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    scrape_all()
