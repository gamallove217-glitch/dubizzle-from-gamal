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

OLD_REMOVE_IDS = {
    209227117, 209176746, 208850747, 208666038,
    209266918, 209242647, 209221740, 209187579, 208592302
}

NEW_CAIRO_WORDS = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع", "النرجس", "اللوتس", "الأندلس", "الاندلس", "الياسمين",
    "البنفسج", "جنوب الأكاديمية", "الاكاديمية", "شرق الأكاديمية", "المستثمرين",
    "بيت الوطن", "القرنفل", "تمر حنة", "جاردينيا", "ابو الهول", "أبو الهول",
    "النخيل", "الشويفات", "الداون تاون", "التسعين", "القطامية", "القطاميه",
    "كايرو فيستيفال", "ميفيدا", "ماونتن فيو", "هايد بارك", "بالم هيلز", "سوديك",
    "فيليت", "ايست تاون", "زيد ايست", "تريو", "ازار", "دار مصر", "سكن مصر",
    "جنة", "الجامعة الأمريكية", "الجامعه الامريكيه", "الجولدن سكوير", "auc"
]

EXCLUDE_CITIES = [
    "الرحاب", "مدينة الرحاب", "مدينتي", "مدينتى", "الشروق", "مدينة الشروق",
    "مدينة المستقبل", "المستقبل سيتي", "بدر", "مدينة بدر", "العبور", "العاصمة الإدارية",
    "الإسكندرية", "الاسكندرية", "سموحة", "العجمي", "برج العرب", "الساحل الشمالي",
    "العين السخنة", "الغردقة", "شرم الشيخ", "المنصورة", "طنطا", "أسيوط",
    "الشيخ زايد", "6 أكتوبر", "٦ أكتوبر", "حدائق أكتوبر", "الهرم", "فيصل",
    "المهندسين", "المعادي", "زهراء المعادي", "مدينة نصر", "مصر الجديدة", "العاشر من رمضان"
]

LIVE_CATEGORY_URLS = [
    "https://www.dubizzle.com.eg/properties/apartments-for-rent/new-cairo/",
    "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/",
    "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/",
    "https://www.dubizzle.com.eg/properties/apartments-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/apartments-for-rent/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    "https://www.dubizzle.com.eg/properties/apartments-for-sale/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/"
]

QUERIES = [
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "من المالك" -الرحاب -مدينتي -الشروق',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "من المالك" -الرحاب -مدينتي -الشروق',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "بدون وسيط"',
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "بدون وسيط"',
    'site:dubizzle.com.eg/ad/ "التجمع" "مالك مباشر"',
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
    'site:dubizzle.com.eg/ad/ "جاردينيا" "من المالك"',
    'site:dubizzle.com.eg/ad/ "القرنفل" "من المالك"',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "الوسطاء يمتنعون"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "دوبلكس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "بنتهاوس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "ستوديو" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "غرفة" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "شقة فندقية" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "رووف" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "فيلا" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "مكتب" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "محل" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "عيادة" "التجمع الخامس"'
]


def load_existing():
    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return (
                data.get("ads", []),
                set(data.get("checked_ids_today_v2", []))
            )
    except Exception:
        return [], set()


def normalize_dubizzle_url(raw_u):
    u = urllib.parse.unquote(urllib.parse.unquote(raw_u)).strip()
    if u.startswith("/ad/"):
        u = "https://www.dubizzle.com.eg" + u
    m = re.search(r"(https?://(?:www\.)?dubizzle\.com\.eg/ad/[^\s\"'<>)\]]+?-ID(\d+)\.html)", u)
    if not m:
        return None, None
    full_u = m.group(1)
    ad_id = int(m.group(2))
    p = urllib.parse.urlsplit(full_u)
    clean_path = urllib.parse.quote(p.path, safe="/-._~")
    return f"https://www.dubizzle.com.eg{clean_path}", ad_id


def extract_links_from_text_or_html(raw_content):
    links = {}
    if not raw_content:
        return links
    for m in re.finditer(r"(?:https?://(?:www\.)?dubizzle\.com\.eg)?/ad/[^\s\"'<>)\]]+?-ID(\d+)\.html", raw_content):
        clean_u, ad_id = normalize_dubizzle_url(m.group(0))
        if clean_u and ad_id and ad_id not in links:
            start_pos = max(0, m.start() - 350)
            end_pos = min(len(raw_content), m.end() + 350)
            context_snip = raw_content[start_pos:end_pos]
            links[ad_id] = (clean_u, context_snip)
    return links


def jina_get(req_sess, cffi_sess, url, with_links=False):
    j_url = "https://r.jina.ai/" + url
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    if with_links:
        headers["X-With-Links-Summary"] = "true"

    for attempt in range(2):
        try:
            r = req_sess.get(j_url, headers=headers, timeout=25)
            if r.status_code == 200 and len(r.text) > 500:
                if "Too Many Requests" not in r.text and "RateLimitExceeded" not in r.text:
                    if "تم النشر بواسطة" in r.text or "/ad/" in r.text or "لم يعد هذا الإعلان متاح" in r.text:
                        return r.text
        except Exception:
            pass
        try:
            r2 = cffi_sess.get(j_url, headers=headers, timeout=25)
            if r2.status_code == 200 and len(r2.text) > 500:
                if "Too Many Requests" not in r2.text and "RateLimitExceeded" not in r2.text:
                    if "تم النشر بواسطة" in r2.text or "/ad/" in r2.text or "لم يعد هذا الإعلان متاح" in r2.text:
                        return r2.text
        except Exception:
            pass
        time.sleep(1.5)

    enc_u = urllib.parse.quote(url, safe="")
    for p_url in [
        f"https://api.codetabs.com/v1/proxy?quest={url}",
        f"https://api.allorigins.win/raw?url={enc_u}"
    ]:
        try:
            rp = req_sess.get(p_url, headers=headers, timeout=20)
            if rp.status_code == 200 and len(rp.text) > 800:
                if "تم النشر بواسطة" in rp.text or "/ad/" in rp.text or "لم يعد هذا الإعلان متاح" in rp.text:
                    return rp.text
        except Exception:
            pass

    return ""


def fetch_live_dubizzle_today(req_sess, cffi_sess):
    today_candidates = {}
    cat_list = list(LIVE_CATEGORY_URLS)
    random.shuffle(cat_list)
    for page_url in cat_list[:6]:
        raw = jina_get(req_sess, cffi_sess, page_url, with_links=True)
        if not raw:
            raw = jina_get(req_sess, cffi_sess, page_url + "?abs=1", with_links=True)
        extracted = extract_links_from_text_or_html(raw)
        for aid, (u, ctx) in extracted.items():
            if aid not in today_candidates:
                today_candidates[aid] = (u, ctx, True)
        time.sleep(2.0)
    print(f"Direct Live Dubizzle links extracted: {len(today_candidates)}")
    return today_candidates


def search_yahoo_bing(session, base_dict):
    found = dict(base_dict)
    q_list = list(QUERIES)
    random.shuffle(q_list)

    for q in q_list[:20]:
        encoded = urllib.parse.quote(q)
        y_url = f"https://search.yahoo.com/search?p={encoded}&b=1"
        try:
            r = session.get(y_url, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    target = href.split("RU=")[1].split("/RK=")[0] if "RU=" in href else href
                    clean_u, ad_id = normalize_dubizzle_url(target)
                    if clean_u and ad_id and ad_id not in found:
                        parent = a.find_parent(["div", "li"])
                        snip = parent.get_text(" ", strip=True) if parent else a.get_text(" ", strip=True)
                        found[ad_id] = (clean_u, snip, False)
        except Exception:
            pass
        time.sleep(0.25)

        b_url = f"https://www.bing.com/search?q={encoded}"
        try:
            r = session.get(b_url, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                for a in soup.find_all("a", href=True):
                    clean_u, ad_id = normalize_dubizzle_url(a["href"])
                    if clean_u and ad_id and ad_id not in found:
                        parent = a.find_parent(["li", "div"])
                        snip = parent.get_text(" ", strip=True) if parent else a.get_text(" ", strip=True)
                        found[ad_id] = (clean_u, snip, False)
        except Exception:
            pass
        time.sleep(0.25)

    return found


def clean_markdown_to_text(md):
    txt = (md or "").translate(AR_DIGITS)
    if "<html" in txt[:500].lower() or "<body" in txt[:1000].lower():
        soup = BeautifulSoup(txt, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        txt = soup.get_text(" ", strip=True).translate(AR_DIGITS)
    txt = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"[*#_`~>|]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def trim_after_report(text_src):
    if not text_src:
        return ""
    for marker in ["الإبلاغ عن هذا الإعلان", "قم بالإبلاغ عن هذا الإعلان", "سلامتك تهمنا"]:
        if marker in text_src:
            return text_src.split(marker)[0]
    return text_src


def check_is_today_ad(ad_sec):
    before_desc = ad_sec.split("الوصف")[0] if "الوصف" in ad_sec else ad_sec[:2000]
    header_txt = clean_markdown_to_text(before_desc)

    m_old = re.search(
        r"منذ\s*(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة|سنه|سنوات)",
        header_txt
    )
    if m_old:
        return False, m_old.group(0)

    m_old2 = re.search(
        r"(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة|سنه|سنوات)\s*(?:مضى|مضت)",
        header_txt
    )
    if m_old2:
        return False, m_old2.group(0)

    m_days = re.search(r"منذ\s*(\d+)\s*(?:أيام|ايام|يومًا|يوما|يوم)", header_txt)
    if m_days and int(m_days.group(1)) >= 2:
        return False, m_days.group(0)

    m_days2 = re.search(r"(\d+)\s*(?:أيام|ايام|يومًا|يوما|يوم)\s*(?:مضى|مضت)", header_txt)
    if m_days2 and int(m_days2.group(1)) >= 2:
        return False, m_days2.group(0)

    if re.search(r"منذ\s*(?:أيام|ايام)", header_txt):
        return False, "منذ أيام"

    m_today = re.search(
        r"منذ\s*(\d+)?\s*(دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه|ثواني|ثانية|اليوم|يوم\b)",
        header_txt
    )
    if m_today:
        return True, m_today.group(0)

    m_today2 = re.search(
        r"(\d+)?\s*(دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه|يومًا|يوما|يوم\b)\s*(?:مضى|مضت)",
        header_txt
    )
    if m_today2:
        return True, m_today2.group(0)

    return False, "OLD_OR_UNKNOWN_DATE"


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


def classify_deal_category_subtype(url, title_clean, desc_clean, top_sec, price_num):
    deal = "بيع"
    if any(w in url.lower() for w in ["rent", "إيجار", "ايجار", "للايجار", "للإيجار"]) or any(
        w in (title_clean + " " + desc_clean[:120]) for w in ["للإيجار", "للايجار", "إيجار", "ايجار", "مفروش", "شهري", "شهريا"]
    ):
        deal = "إيجار"
    elif 0 < price_num < 150000:
        deal = "إيجار"

    check_str = f"{title_clean} {top_sec[:600]} {desc_clean[:200]} {url}"

    subtype = "شقة"
    if any(w in check_str for w in ["مكتب", "إداري", "اداري", "عيادة", "عياده", "محل", "تجاري", "تجارى", "معرض", "صيدلية", "مقر اداري", "مبنى تجاري", "commercial", "office", "clinic", "shop"]):
        subtype = "عقار تجاري"
    elif any(w in check_str for w in ["تاون هاوس", "توين هاوس", "فيلا", "ڤيلا", "ستاند الون", "villa", "townhouse", "twin"]):
        subtype = "فيلا"
    elif any(w in check_str for w in ["دوبلكس", "دوبليكس", "duplex"]):
        subtype = "دوبلكس"
    elif any(w in check_str for w in ["بنتهاوس", "penthouse"]):
        subtype = "بنتهاوس"
    elif any(w in check_str for w in ["سطح", "رووف", "روف", "roof"]):
        subtype = "سطح"
    elif any(w in check_str for w in ["شقة فندقية", "شقه فندقيه", "فندقية", "فندقيه", "serviced"]):
        subtype = "شقة فندقية"
    elif any(w in check_str for w in ["ستوديو", "استوديو", "studio"]):
        subtype = "ستوديو"
    elif any(w in check_str for w in ["غرفة للإيجار", "غرفه للايجار", "غرفة مفروشة", "غرفة مشتركة", "سكن طلاب"]):
        subtype = "غرفة"

    if subtype == "فيلا":
        category = "فلل للإيجار" if deal == "إيجار" else "فلل للبيع"
    elif subtype == "عقار تجاري":
        category = "عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"
    else:
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"

    return deal, category, subtype


def inspect_and_parse(req_sess, cffi_sess, ad_id, url, snippet):
    raw_s = jina_get(req_sess, cffi_sess, url, with_links=True)
    if "لم يعد هذا الإعلان متاح" in raw_s or "هذا الإعلان لم يعد متاح" in raw_s or "هذا الإعلان غير متاح" in raw_s:
        return None, True, "EXPIRED", {}

    cnt, seller = extract_cnt_and_seller(raw_s)

    fallback_s = ""
    if cnt == 0:
        fallback_s = jina_get(req_sess, cffi_sess, url + "?abs=1", with_links=True)
        if "لم يعد هذا الإعلان متاح" in fallback_s or "هذا الإعلان لم يعد متاح" in fallback_s or "هذا الإعلان غير متاح" in fallback_s:
            return None, True, "EXPIRED", {}
        cnt2, seller2 = extract_cnt_and_seller(fallback_s)
        if cnt2 > 0:
            cnt = cnt2
        if seller == "مالك" and seller2 != "مالك":
            seller = seller2

    combined_raw = (raw_s or "") + "\n" + (fallback_s or "")
    if not combined_raw.strip():
        return None, False, "NO_PAGE", {}

    related_today = {}
    for rid, (ru, rctx) in extract_links_from_text_or_html(combined_raw).items():
        rctx_clean = clean_markdown_to_text(rctx)
        if not any(bad in rctx_clean for bad in EXCLUDE_CITIES):
            if re.search(r"(?:دقائق|دقيقة|ساعات|ساعة|منذ 1 يوم)", rctx_clean):
                related_today[rid] = (ru, rctx_clean, True)

    if "لم يعد هذا الإعلان متاح" in combined_raw or "هذا الإعلان لم يعد متاح" in combined_raw or "هذا الإعلان غير متاح" in combined_raw:
        return None, True, "EXPIRED", related_today

    ad_sec = trim_after_report(raw_s if len(raw_s) >= len(fallback_s) else fallback_s)

    is_today, age_label = check_is_today_ad(ad_sec)
    if not is_today:
        is_today2, age_label2 = check_is_today_ad(trim_after_report(fallback_s))
        if is_today2:
            is_today, age_label = True, age_label2

    if not is_today:
        print(f"Skipped Old Ad {ad_id}: Age={age_label}")
        return None, True, "OLD_AD", related_today

    if cnt == 0:
        return None, False, "NO_CNT", related_today

    print(f"Checked TODAY Ad {ad_id} ({age_label}): Active_Ads={cnt} | Seller={seller}")

    if cnt not in (1, 2, 3, 4):
        return None, True, f"BROKER_{cnt}_ADS", related_today

    desc_clean = ""
    for src in [ad_sec, trim_after_report(fallback_s), trim_after_report(raw_s)]:
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
    full_check = f"{title_clean} {desc_clean} {top_sec[:800]}"

    for bad_city in EXCLUDE_CITIES:
        if bad_city in full_check:
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
        for pm in re.finditer(r"(?:ج\.م|جنيه|جم|EGP)\s*(\d[\d,]{3,11})", all_price_text):
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
    if not m_beds:
        m_beds = re.search(r"(\d{1,2})\s*(?:غرف|غرفة نوم)", top_sec + " " + desc_clean)
    if m_beds and 1 <= int(m_beds.group(1)) <= 12:
        beds = f"{m_beds.group(1)} غرف"

    baths = ""
    m_baths = re.search(r"(?:الحمامات|حمامات|حمام)[^\d]{0,8}(\d{1,2})", top_sec + " " + desc_clean)
    if not m_baths:
        m_baths = re.search(r"(\d{1,2})\s*(?:حمام|حمامات)", top_sec + " " + desc_clean)
    if m_baths and 1 <= int(m_baths.group(1)) <= 10:
        baths = f"{m_baths.group(1)} حمام"

    deal, category, subtype = classify_deal_category_subtype(url, title_clean, desc_clean, top_sec, price_num)

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
        "description": f"[{age_label}] " + (desc_clean[:680] if desc_clean else title_clean),
        "url": url,
        "scraped_at": now_iso
    }, True, f"ADDED_TODAY_ADS_{cnt}", related_today


def priority_score(uid, is_live_today):
    base = 3000000000 if is_live_today else 0
    if 209280000 <= uid < 215000000:
        return base + 1000000000 + uid
    if uid >= 504250000:
        return base + 500000000 + uid
    return base + uid


def scrape_all():
    existing_ads, checked_ids = load_existing()
    now_dt = datetime.now(CAIRO_TZ)

    kept_ads = {}
    for ad in existing_ads:
        try:
            aid = int(ad.get("ad_id", 0))
            cnt = int(ad.get("seller_ads_count") or 1)
            if aid in OLD_REMOVE_IDS:
                checked_ids.add(aid)
                continue
            txt_check = f"{ad.get('title', '')} {ad.get('description', '')}"
            if any(bad in txt_check for bad in EXCLUDE_CITIES):
                checked_ids.add(aid)
                continue
            if aid > 0 and cnt in (1, 2, 3, 4):
                deal, cat, sub = classify_deal_category_subtype(
                    ad.get("url", ""),
                    ad.get("title", ""),
                    ad.get("description", ""),
                    "",
                    int(ad.get("price_num") or 0)
                )
                ad["deal"] = deal
                ad["category"] = cat
                ad["subtype"] = sub
                kept_ads[aid] = ad
        except Exception:
            continue

    req_sess = std_requests.Session()
    cffi_sess = cffi_requests.Session(impersonate="chrome120")

    live_today = fetch_live_dubizzle_today(req_sess, cffi_sess)
    candidates = search_yahoo_bing(cffi_sess, live_today)
    print(f"Total candidate URLs: {len(candidates)} | Kept ads: {len(kept_ads)}")

    unchecked = [
        (uid, u, snip, is_live)
        for uid, (u, snip, is_live) in candidates.items()
        if uid not in kept_ads and uid not in checked_ids and (is_live or uid >= 209280000 or uid >= 504250000)
    ]
    unchecked.sort(key=lambda x: priority_score(x[0], x[3]), reverse=True)
    print(f"Today/Newest unchecked candidates to inspect: {len(unchecked)}")

    stats = {}
    inspected = 0
    queue = list(unchecked)
    queued_ids = {x[0] for x in queue}

    while queue and inspected < 40:
        uid, u, snip, is_live = queue.pop(0)
        if uid in kept_ads or uid in checked_ids:
            continue
        inspected += 1
        try:
            item, mark_checked, reason, discovered_today = inspect_and_parse(req_sess, cffi_sess, uid, u, snip)
            stats[reason] = stats.get(reason, 0) + 1
            if mark_checked:
                checked_ids.add(uid)
            if item:
                kept_ads[uid] = item
                print(f"[{inspected}] ADDED TODAY: {uid} | {item['category']} ({item['subtype']}) | {item['price_text']} | {item['seller_name']} (Active Ads: {item['seller_ads_count']})")
            for rid, (ru, rsnip, rlive) in discovered_today.items():
                if rid not in kept_ads and rid not in checked_ids and rid not in queued_ids:
                    queue.insert(0, (rid, ru, rsnip, True))
                    queued_ids.add(rid)
        except Exception as e:
            print(f"[{inspected}] Error {uid}: {e}")

        time.sleep(3.5)

    print(f"Inspection Summary: {stats}")

    final_ads = list(kept_ads.values())
    final_ads.sort(key=lambda x: x.get("ad_id", 0), reverse=True)

    out = {
        "last_scrape": now_dt.strftime("%Y/%m/%d, %I:%M %p"),
        "total_ads": len(final_ads),
        "checked_ids_today_v2": sorted(list(checked_ids))[-5000:],
        "ads": final_ads
    }
    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(final_ads)} verified New Cairo ads.")


if __name__ == "__main__":
    scrape_all()
