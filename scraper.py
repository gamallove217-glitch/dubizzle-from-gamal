import json
import random
import re
import time
import urllib.parse
import requests as std_requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except Exception:
    HAS_DDGS = False

CAIRO_TZ = timezone(timedelta(hours=2))

NEW_CAIRO_WORDS = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع", "الخامس", "الأول", "الاول",
    "الثالث", "الرحاب", "مدينتي", "الشروق", "المستقبل", "النرجس", "اللوتس",
    "الأندلس", "الاندلس", "الياسمين", "البنفسج", "جنوب الأكاديمية", "الاكاديمية",
    "المستثمرين", "بيت الوطن", "القرنفل", "تمر حنة", "جاردينيا", "ابو الهول",
    "أبو الهول", "النخيل", "الشويفات", "الداون تاون", "كايرو فيستيفال",
    "ميفيدا", "ماونتن فيو", "هايد بارك", "بالم هيلز", "سوديك", "فيليت",
    "ايست تاون", "زيد ايست", "تريو", "ازار", "تاج سيتي", "سراي", "البوسكو",
    "دار مصر", "سكن مصر", "جنة", "الجامعة الأمريكية", "الجامعه الامريكيه", "auc"
]

EXCLUDE_CITIES = [
    "الإسكندرية", "الاسكندرية", "سموحة", "العجمي", "برج العرب", "الساحل الشمالي",
    "العين السخنة", "الغردقة", "شرم الشيخ", "المنصورة", "طنطا", "أسيوط",
    "الشيخ زايد", "6 أكتوبر", "٦ أكتوبر", "حدائق أكتوبر", "الهرم", "فيصل", "المهندسين"
]

QUERIES = [
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "من المالك"',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "من المالك"',
    'site:dubizzle.com.eg/ad/ "الرحاب" "من المالك"',
    'site:dubizzle.com.eg/ad/ "مدينتي" "من المالك"',
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
    'site:dubizzle.com.eg/ad/ "الشروق" "من المالك"',
    'site:dubizzle.com.eg/ad/ "دار مصر" "التجمع"',
    'site:dubizzle.com.eg/ad/ "سكن مصر" "التجمع"',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "الوسطاء يمتنعون"',
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "الوسطاء يمتنعون"',
    'site:dubizzle.com.eg/ad/ "الرحاب" "الوسطاء يمتنعون"',
    'site:dubizzle.com.eg/ad/ "مدينتي" "الوسطاء يمتنعون"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "الرحاب"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "مدينتي"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "النرجس"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "اللوتس"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "النرجس"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "اللوتس"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "البنفسج"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "الياسمين"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "الرحاب"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "مدينتي"',
    'site:dubizzle.com.eg/ad/ "دوبلكس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "بنتهاوس" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "فيلا" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "مفروش" "التجمع الخامس"'
]


def load_existing():
    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return (
                data.get("ads", []),
                set(data.get("checked_ids_v5", []))
            )
    except Exception:
        return [], set()


def normalize_dubizzle_url(raw_u):
    u = urllib.parse.unquote(urllib.parse.unquote(raw_u))
    m = re.search(r"(https?://(?:www\.)?dubizzle\.com\.eg/[^\s\"'<>]+?-ID(\d+)\.html)", u)
    if not m:
        return None, None
    full_u = m.group(1)
    ad_id = int(m.group(2))
    p = urllib.parse.urlsplit(full_u)
    clean_path = urllib.parse.quote(p.path, safe="/-._~")
    return f"https://www.dubizzle.com.eg{clean_path}", ad_id


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
                            found[ad_id] = (clean_u, snip)
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
                        found[ad_id] = (clean_u, snip)
        except Exception:
            pass
        time.sleep(0.25)

    if HAS_DDGS:
        try:
            with DDGS() as ddgs:
                for q in q_list[:10]:
                    for res in ddgs.text(q, max_results=20):
                        clean_u, ad_id = normalize_dubizzle_url(res.get("href", ""))
                        if clean_u and ad_id and ad_id not in found:
                            found[ad_id] = (clean_u, res.get("title", "") + " " + res.get("body", ""))
                    time.sleep(0.4)
        except Exception:
            pass

    return found


def jina_get(req_sess, cffi_sess, url):
    j_url = "https://r.jina.ai/" + url
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    for attempt in range(2):
        try:
            r = req_sess.get(j_url, headers=headers, timeout=25)
            if r.status_code == 200 and len(r.text) > 500:
                if "Too Many Requests" not in r.text and "RateLimitExceeded" not in r.text:
                    return r.text
        except Exception:
            pass
        try:
            r2 = cffi_sess.get(j_url, timeout=25)
            if r2.status_code == 200 and len(r2.text) > 500:
                if "Too Many Requests" not in r2.text and "RateLimitExceeded" not in r2.text:
                    return r2.text
        except Exception:
            pass
        time.sleep(2.0)
    return ""


def clean_markdown_to_text(md):
    txt = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", md)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"[*#_`~>|]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def extract_cnt_and_seller(text_src):
    if not text_src:
        return 0, ""

    ad_sec = text_src
    for marker in ["الإعلانات ذات الصلة", "إعلانات ذات صلة", "اعلانات ذات صلة", "إعلانات مشابهة", "اعلانات مشابهة"]:
        if marker in ad_sec:
            ad_sec = ad_sec.split(marker)[0]

    clean_all = clean_markdown_to_text(ad_sec)

    cnt = 0
    for m in re.finditer(r"(?:ال)?(?:إ|ا)علان(?:ات)?\s*(?:ال)?نشط(?:ة|ه)?\s*:?\s*(\d+)", clean_all):
        cnt = int(m.group(1))
    if cnt == 0:
        for m in re.finditer(r"(\d+)\s*(?:ال)?(?:إ|ا)علان(?:ات)?\s*(?:ال)?نشط", clean_all):
            cnt = int(m.group(1))

    seller = "مالك"
    if "عضو منذ" in clean_all:
        before_member = clean_all.split("عضو منذ")[-2]
        if "تم النشر بواسطة" in before_member:
            cand = before_member.split("تم النشر بواسطة")[-1].strip(" .-:|")
            if 1 <= len(cand) <= 55:
                seller = cand

    return cnt, seller


def inspect_and_parse(req_sess, cffi_sess, ad_id, url, snippet):
    raw_s = jina_get(req_sess, cffi_sess, url)
    cnt, seller = extract_cnt_and_seller(raw_s)

    fallback_s = ""
    if cnt == 0:
        fallback_s = jina_get(req_sess, cffi_sess, url + "?abs=1")
        cnt2, seller2 = extract_cnt_and_seller(fallback_s)
        if cnt2 > 0:
            cnt = cnt2
        if seller == "مالك" and seller2 != "مالك":
            seller = seller2

    if cnt == 0 and snippet:
        cnt_s, seller_s = extract_cnt_and_seller(snippet)
        if cnt_s > 0:
            cnt = cnt_s

    combined_raw = (raw_s or "") + "\n" + (fallback_s or "")
    if not combined_raw.strip():
        return None, False, "NO_PAGE"

    if "لم يعد هذا الإعلان متاح" in combined_raw or "هذا الإعلان لم يعد متاح" in combined_raw or "هذا الإعلان غير متاح" in combined_raw:
        return None, True, "EXPIRED"

    if cnt == 0:
        return None, False, "NO_CNT"

    if cnt not in (1, 2, 3, 4):
        return None, True, f"BROKER_{cnt}_ADS"

    ad_sec = raw_s if len(raw_s) >= len(fallback_s) else fallback_s
    for marker in ["الإعلانات ذات الصلة", "إعلانات ذات صلة", "اعلانات ذات صلة", "إعلانات مشابهة", "اعلانات مشابهة"]:
        if marker in ad_sec:
            ad_sec = ad_sec.split(marker)[0]

    desc_clean = ""
    for src in [ad_sec, fallback_s, raw_s]:
        if src and "الوصف" in src:
            after_desc = src.split("الوصف", 1)[1]
            for stop_w in ["تم النشر بواسطة", "الموقع", "معرّف الإعلان", "معرف الإعلان", "رقم الإعلان", "قم بالإبلاغ", "الإبلاغ عن", "الكماليات"]:
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

    full_check = f"{title_clean} {desc_clean} {snippet}"

    for bad_city in EXCLUDE_CITIES:
        if bad_city in full_check:
            return None, True, "OTHER_CITY"

    if not any(w in full_check for w in NEW_CAIRO_WORDS):
        return None, True, "NOT_NEW_CAIRO"

    top_sec = clean_markdown_to_text(ad_sec[:2500])
    price_num = 0
    for pm in re.finditer(r"(\d[\d,]{3,11})\s*(?:ج\.م|جنيه|EGP)", top_sec + " " + desc_clean + " " + snippet):
        val = int(pm.group(1).replace(",", ""))
        if val >= 2000:
            price_num = val
            break

    if price_num == 0:
        m_mil = re.search(r"(\d+(?:\.\d+)?)\s*مليون", top_sec + " " + desc_clean + " " + snippet)
        if m_mil:
            price_num = int(float(m_mil.group(1)) * 1000000)

    if price_num == 0:
        return None, True, "NO_PRICE"

    price_text = f"{price_num:,} ج.م"

    area = "مدرج بالإعلان"
    m_area = re.search(r"(?:المساحة|مساحة|المساحه)[^\d]{0,10}(\d{2,4})", top_sec + " " + desc_clean)
    if not m_area:
        m_area = re.search(r"\b(\d{2,4})\s*(?:متر|م2|م²|sqm)\b", top_sec + " " + desc_clean, re.I)
    if m_area:
        area = f"{m_area.group(1)} م²"

    beds = ""
    m_beds = re.search(r"(?:غرف نوم|غرف|غرفة)\s*:?\s*(\d{1,2})", top_sec + " " + desc_clean)
    if not m_beds:
        m_beds = re.search(r"(\d{1,2})\s*(?:غرف|غرفة نوم)", top_sec + " " + desc_clean)
    if m_beds and 1 <= int(m_beds.group(1)) <= 12:
        beds = f"{m_beds.group(1)} غرف"

    baths = ""
    m_baths = re.search(r"(?:الحمامات|حمامات|حمام)\s*:?\s*(\d{1,2})", top_sec + " " + desc_clean)
    if not m_baths:
        m_baths = re.search(r"(\d{1,2})\s*(?:حمام|حمامات)", top_sec + " " + desc_clean)
    if m_baths and 1 <= int(m_baths.group(1)) <= 10:
        baths = f"{m_baths.group(1)} حمام"

    deal = "بيع"
    if any(w in url.lower() for w in ["rent", "إيجار", "ايجار", "للايجار", "للإيجار"]) or any(
        w in (title_clean + " " + desc_clean[:120]) for w in ["للإيجار", "للايجار", "إيجار", "ايجار", "مفروش", "شهري"]
    ):
        deal = "إيجار"
    elif price_num < 150000:
        deal = "إيجار"

    subtype = "شقة"
    check_type_str = title_clean + " " + desc_clean[:180] + " " + url
    if any(w in check_type_str for w in ["دوبلكس", "دوبليكس", "duplex"]):
        subtype = "دوبلكس"
    elif any(w in check_type_str for w in ["بنتهاوس", "رووف", "روف", "penthouse"]):
        subtype = "بنتهاوس"
    elif any(w in check_type_str for w in ["استوديو", "ستوديو", "studio"]):
        subtype = "استوديو"
    elif any(w in check_type_str for w in ["تاون هاوس", "توين هاوس", "فيلا", "ستاند الون", "villa", "townhouse", "twin"]):
        subtype = "فيلا"
    elif any(w in check_type_str for w in ["مكتب", "إداري", "اداري", "عيادة", "عياده", "محل", "تجاري", "office", "clinic", "shop"]):
        subtype = "تجاري وإداري"

    category = "فيلا" if subtype == "فيلا" else ("تجاري وإداري" if subtype == "تجاري وإداري" else "شقق و دوبلكس")

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
        "description": desc_clean[:700] if desc_clean else title_clean,
        "url": url,
        "scraped_at": now_iso
    }, True, f"ADDED_ADS_{cnt}"


def scrape_all():
    existing_ads, checked_ids = load_existing()
    now_dt = datetime.now(CAIRO_TZ)

    kept_ads = {}
    for ad in existing_ads:
        try:
            aid = int(ad.get("ad_id", 0))
            cnt = int(ad.get("seller_ads_count") or 1)
            if aid > 0 and cnt in (1, 2, 3, 4) and int(ad.get("price_num") or 0) >= 2000:
                kept_ads[aid] = ad
        except Exception:
            continue

    search_sess = cffi_requests.Session(impersonate="chrome120")
    candidates = search_yahoo_bing(search_sess)
    print(f"Found {len(candidates)} candidate URLs | Existing ads: {len(kept_ads)}")

    unchecked = [
        (uid, u, snip)
        for uid, (u, snip) in candidates.items()
        if uid not in kept_ads and uid not in checked_ids
    ]
    random.shuffle(unchecked)
    print(f"Unchecked candidates to inspect: {len(unchecked)}")

    req_sess = std_requests.Session()
    jina_cffi_sess = cffi_requests.Session(impersonate="chrome120")

    stats = {}
    inspected = 0
    for uid, u, snip in unchecked:
        if inspected >= 55:
            break
        inspected += 1
        try:
            item, mark_checked, reason = inspect_and_parse(req_sess, jina_cffi_sess, uid, u, snip)
            stats[reason] = stats.get(reason, 0) + 1
            if mark_checked:
                checked_ids.add(uid)
            if item:
                kept_ads[uid] = item
                print(f"[{inspected}] ADDED: {uid} | {item['deal']} | {item['price_text']} | {item['seller_name']} (Active Ads: {item['seller_ads_count']})")
        except Exception as e:
            print(f"[{inspected}] Error {uid}: {e}")

        time.sleep(3.5)

    print(f"Inspection Summary: {stats}")

    final_ads = list(kept_ads.values())
    final_ads.sort(key=lambda x: x.get("ad_id", 0), reverse=True)

    out = {
        "last_scrape": now_dt.strftime("%Y/%m/%d, %I:%M %p"),
        "total_ads": len(final_ads),
        "checked_ids_v5": sorted(list(checked_ids))[-5000:],
        "ads": final_ads
    }
    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(final_ads)} ads with 1 to 4 active listings.")


if __name__ == "__main__":
    scrape_all()
