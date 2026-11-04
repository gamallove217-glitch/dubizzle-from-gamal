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
    "التجمع الثالث", "التجمع", "النرجس", "اللوتس", "الأندلس", "الاندلس", "الياسمين",
    "البنفسج", "جنوب الأكاديمية", "الاكاديمية", "شرق الأكاديمية", "المستثمرين",
    "بيت الوطن", "القرنفل", "تمر حنة", "جاردينيا", "ابو الهول", "أبو الهول",
    "النخيل", "الشويفات", "الداون تاون", "التسعين", "القطامية", "القطاميه",
    "كايرو فيستيفال", "ميفيدا", "ماونتن فيو", "هايد بارك", "بالم هيلز", "سوديك",
    "فيليت", "ايست تاون", "زيد ايست", "تريو", "ازار", "دار مصر", "سكن مصر",
    "جنة", "الجامعة الأمريكية", "الجامعه الامريكيه", "الجولدن سكوير", "فيلدج جيت",
    "village gate", "auc"
]

EXCLUDE_CITIES = [
    "الرحاب", "مدينة الرحاب", "مدينتي", "مدينتى", "الشروق", "مدينة الشروق",
    "مدينة المستقبل", "المستقبل سيتي", "بدر", "مدينة بدر", "العبور", "العاصمة الإدارية",
    "الإسكندرية", "الاسكندرية", "سموحة", "العجمي", "برج العرب", "الساحل الشمالي",
    "العين السخنة", "الغردقة", "شرم الشيخ", "المنصورة", "طنطا", "أسيوط",
    "الشيخ زايد", "6 أكتوبر", "٦ أكتوبر", "حدائق أكتوبر", "الهرم", "فيصل",
    "المهندسين", "المعادي", "زهراء المعادي", "مدينة نصر", "مصر الجديدة", "العاشر من رمضان"
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
            kept = [
                a for a in data.get("ads", [])
                if a.get("today_verified") is True
            ]
            return (
                kept,
                set(data.get("checked_ids_today_v3", []))
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
    if ad_id >= 300000000 or ad_id < 208500000:
        return None, None
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
            r = req_sess.get(j_url, headers=headers, timeout=22)
            if r.status_code == 200 and len(r.text) > 500:
                if "Too Many Requests" not in r.text and "RateLimitExceeded" not in r.text:
                    if "تم النشر بواسطة" in r.text or "/ad/" in r.text or "لم يعد هذا الإعلان متاح" in r.text:
                        return r.text
        except Exception:
            pass
        try:
            r2 = cffi_sess.get(j_url, headers=headers, timeout=22)
            if r2.status_code == 200 and len(r2.text) > 500:
                if "Too Many Requests" not in r2.text and "RateLimitExceeded" not in r2.text:
                    if "تم النشر بواسطة" in r2.text or "/ad/" in r2.text or "لم يعد هذا الإعلان متاح" in r2.text:
                        return r2.text
        except Exception:
            pass
        time.sleep(1.2)

    return ""


def search_yahoo_bing(session):
    found = {}
    q_list = list(QUERIES)
    random.shuffle(q_list)

    for q in q_list[:24]:
        encoded = urllib.parse.quote(q)
        for b_start in [1, 11]:
            y_url = f"https://search.yahoo.com/search?p={encoded}&b={b_start}"
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
            time.sleep(0.2)

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
        time.sleep(0.2)

    return found


def clean_markdown_to_text(md):
    txt = (md or "").translate(AR_DIGITS)
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
    before_desc = ad_sec.split("الوصف")[0] if "الوصف" in ad_sec else ad_sec[:2200]
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
    if m_days and int(m_days.group(1)) >= 3:
        return False, m_days.group(0)

    m_days2 = re.search(r"(\d+)\s*(?:أيام|ايام|يومًا|يوما|يوم)\s*(?:مضى|مضت)", header_txt)
    if m_days2 and int(m_days2.group(1)) >= 3:
        return False, m_days2.group(0)

    m_today = re.search(
        r"منذ\s*(\d+)?\s*(دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه|ثواني|ثانية|اليوم|يوم|أيام|ايام)",
        header_txt
    )
    if m_today:
        return True, m_today.group(0)

    m_today2 = re.search(
        r"(\d+)?\s*(دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه|يومًا|يوما|يوم|أيام|ايام)\s*(?:مضى|مضت)",
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

    check_str = f"{title_clean} {top_sec[:900]} {desc_clean[:200]} {url}"

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
        if rid < 300000000 and rid >= 209000000:
            rctx_clean = clean_markdown_to_text(rctx)
            if not any(bad in rctx_clean for bad in EXCLUDE_CITIES):
                if re.search(r"(?:دقائق|دقيقة|ساعات|ساعة|منذ 1 يوم|منذ 2 أيام)", rctx_clean) or rid >= 209350000:
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

    print(f"Checked TODAY Individual Ad {ad_id} ({age_label}): Active_Ads={cnt} | Seller={seller}")

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
    full_check = f"{title_clean} {desc_clean} {top_sec} {snippet}"

    for bad_city in EXCLUDE_CITIES:
        if bad_city in f"{title_clean} {desc_clean}":
            print(f"   -> Excluded City ({bad_city}): {title_clean[:50]}")
            return None, True, "EXCLUDED_AREA", related_today

    if not any(w in full_check for w in NEW_CAIRO_WORDS):
        print(f"   -> Not New Cairo: {title_clean[:60]}")
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
        "today_verified": True,
        "scraped_at": now_iso
    }, True, f"ADDED_TODAY_ADS_{cnt}", related_today


def scrape_all():
    existing_ads, checked_ids = load_existing()
    now_dt = datetime.now(CAIRO_TZ)

    kept_ads = {int(a["ad_id"]): a for a in existing_ads if "ad_id" in a}

    req_sess = std_requests.Session()
    cffi_sess = cffi_requests.Session(impersonate="chrome120")

    candidates = search_yahoo_bing(cffi_sess)
    print(f"Found {len(candidates)} individual candidate URLs (209xxx only) | Kept ads: {len(kept_ads)}")

    unchecked = [
        (uid, u, snip, is_live)
        for uid, (u, snip, is_live) in candidates.items()
        if uid not in kept_ads and uid not in checked_ids and 209000000 <= uid < 300000000
    ]
    unchecked.sort(key=lambda x: x[0], reverse=True)
    print(f"Newest 209xxx individual candidates to inspect: {len(unchecked)}")

    stats = {}
    inspected = 0
    queue = list(unchecked)
    queued_ids = {x[0] for x in queue}

    while queue and inspected < 45:
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
            for rid, (ru, rsnip, rlive) in sorted(discovered_today.items(), key=lambda x: x[0], reverse=True):
                if rid not in kept_ads and rid not in checked_ids and rid not in queued_ids:
                    queue.insert(0, (rid, ru, rsnip, True))
                    queued_ids.add(rid)
        except Exception as e:
            print(f"[{inspected}] Error {uid}: {e}")

        time.sleep(3.2)

    print(f"Inspection Summary: {stats}")

    final_ads = list(kept_ads.values())
    final_ads.sort(key=lambda x: x.get("ad_id", 0), reverse=True)

    out = {
        "last_scrape": now_dt.strftime("%Y/%m/%d, %I:%M %p"),
        "total_ads": len(final_ads),
        "checked_ids_today_v3": sorted(list(checked_ids))[-5000:],
        "ads": final_ads
    }
    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(final_ads)} verified TODAY New Cairo ads.")


if __name__ == "__main__":
    scrape_all()
