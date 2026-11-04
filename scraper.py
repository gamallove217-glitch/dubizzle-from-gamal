import json
import random
import re
import time
import urllib.parse
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except Exception:
    HAS_DDGS = False

CAIRO_TZ = timezone(timedelta(hours=2))

BROKER_WORDS = [
    "شركة", "شركه", "مكتب", "عقارات", "للعقارات", "للتسويق", "تسويق",
    "استثمار", "للاستثمار", "تطوير", "للتطوير", "بروكر", "سمسار", "وسيط",
    "الوسيط", "وكيل", "وكالة", "وكاله", "مجموعة", "مجموعه", "جروب", "قروب",
    "فرصة", "فرصه", "الفرصة", "إعمار", "اعمار", "سوديك", "ماونتن", "بالم",
    "طلعت مصطفى", "هايد بارك", "تاج مصر", "معمار", "الأهلي", "الاهلي",
    "عقاري", "العقارية", "العقاريه", "مستشار", "خبير", "إدارة", "ادارة",
    "كمبوندات", "مشاريع", "مشروعات", "تسهيلات", "بدون فوائد", "أقساط",
    "اقساط", "تقسيط", "مقدم", "بمقدم", "استلام فوري", "أول سكن", "اول سكن",
    "عمولة", "عموله", "بعمولة", "بعموله", "داون تاون", "ريماكس", "كولدويل",
    "دار مصر", "سكن مصر", "جنة", "جنه", "شقق للايجار", "شقق للبيع",
    "عقارات مصر", "عقارات التجمع", "عقارات القاهرة", "مبيعات", "قسم المبيعات",
    "real estate", "realestate", "property", "properties", "broker", "brokerage",
    "agency", "agent", "consultancy", "consultant", "investment", "investments",
    "development", "developments", "developer", "group", "holding", "company",
    "corp", "corporation", "llc", "ltd", "inc", "homes", "home", "house",
    "houses", "housing", "living", "residence", "residences", "residential",
    "commercial", "capital", "ventures", "partners", "solutions", "services",
    "management", "marketing", "sales", "leasing", "rentals", "find", "finder",
    "egypt", "cairo", "new cairo", "tagamoa", "rehab", "madinaty", "compound",
    "compounds", "projects", "units", "apartments", "villas", "offices",
    "prime", "elite", "luxury", "royal", "golden", "gold", "star", "stars",
    "diamond", "platinum", "master", "pro", "plus", "max", "remax", "era",
    "coldwell", "banker", "sotheby", "knight", "frank", "savills", "jll",
    "cb", "cbre", "b2b", "hub", "gate", "gates", "key", "keys", "deal",
    "deals", "land", "lands", "builders", "construction", "contracting",
    "interior", "design", "decor", "finishing", "turnkey", "invest",
    "advisors", "advisor", "experts", "expert", "network", "global",
    "international", "world", "wide", "united", "union", "trust", "trusted",
    "first", "one", "top", "best", "smart", "modern", "future", "vision",
    "dream", "dreams", "life", "style", "lifestyle", "urban", "city",
    "town", "downtown", "uptown", "park", "view", "views", "heights",
    "hills", "palm", "oasis", "gardens", "garden", "avenue", "plaza",
    "tower", "towers", "center", "centre", "point", "square", "corner",
    "spot", "zone", "area", "district", "sector", "phase", "stage"
]

BODY_BROKER_PHRASES = [
    "شركة عقارات", "مكتب عقارات", "للتسويق العقاري", "استثمار عقاري",
    "لدينا شقق", "لدينا فيلات", "متاح لدينا", "متوفر لدينا", "يوجد لدينا",
    "شركتنا", "مكتبنا", "فريق المبيعات", "خدمة العملاء", "عروض أخرى",
    "وحدات أخرى", "مساحات مختلفة", "أدوار متكررة", "استلام فوري بالتقسيط"
]

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
    'site:dubizzle.com.eg/ad/ "المستقبل" "من المالك"',
    'site:dubizzle.com.eg/ad/ "التجمع الخامس" "الوسطاء يمتنعون"',
    'site:dubizzle.com.eg/ad/ "القاهرة الجديدة" "الوسطاء يمتنعون"',
    'site:dubizzle.com.eg/ad/ "الرحاب" "الوسطاء يمتنعون"',
    'site:dubizzle.com.eg/ad/ "مدينتي" "الوسطاء يمتنعون"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "التجمع الخامس" "المالك"',
    'site:dubizzle.com.eg/ad/ "شقة للايجار" "الرحاب" "المالك"',
    'site:dubizzle.com.eg/ad/ "شقة للايجار" "مدينتي" "المالك"',
    'site:dubizzle.com.eg/ad/ "مفروش" "التجمع الخامس" "المالك"',
    'site:dubizzle.com.eg/ad/ "دوبلكس" "التجمع الخامس" "المالك"',
    'site:dubizzle.com.eg/ad/ "بنتهاوس" "التجمع الخامس" "المالك"',
    'site:dubizzle.com.eg/ad/ "فيلا" "التجمع الخامس" "المالك"',
    'site:dubizzle.com.eg/ad/ "تاون هاوس" "التجمع الخامس" "المالك"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "النرجس"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "اللوتس"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "البنفسج"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "الياسمين"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "الرحاب"',
    'site:dubizzle.com.eg/ad/ "شقة للبيع" "مدينتي"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "التجمع الخامس"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "الرحاب"',
    'site:dubizzle.com.eg/ad/ "شقة للإيجار" "مدينتي"'
]


def load_existing():
    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return (
                data.get("ads", []),
                set(data.get("blocked_users", [])),
                set(data.get("checked_ids_v2", []))
            )
    except Exception:
        return [], set(), set()


def is_broker_name(name):
    if not name or len(name.strip()) < 2:
        return True
    low = name.lower().strip()
    for w in BROKER_WORDS:
        if w in low:
            return True
    return False


def extract_ad_url_and_id(raw_url):
    try:
        u = urllib.parse.unquote(raw_url)
        m = re.search(r"(https?://(?:www\.)?dubizzle\.com\.eg/[^\s\"'<>]+?-ID(\d+)\.html)", u)
        if m:
            return m.group(1), int(m.group(2))
    except Exception:
        pass
    return None, None


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
                        if "RU=" in href:
                            part = href.split("RU=")[1].split("/RK=")[0]
                            clean_u, ad_id = extract_ad_url_and_id(part)
                        else:
                            clean_u, ad_id = extract_ad_url_and_id(href)
                        if clean_u and ad_id and ad_id < 500000000 and ad_id not in found:
                            found[ad_id] = (clean_u, a.get_text(" ", strip=True))
            except Exception:
                pass
            time.sleep(0.3)

        b_url = f"https://www.bing.com/search?q={encoded}"
        try:
            r = session.get(b_url, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                for a in soup.find_all("a", href=True):
                    clean_u, ad_id = extract_ad_url_and_id(a["href"])
                    if clean_u and ad_id and ad_id < 500000000 and ad_id not in found:
                        found[ad_id] = (clean_u, a.get_text(" ", strip=True))
        except Exception:
            pass
        time.sleep(0.3)

    if HAS_DDGS:
        try:
            with DDGS() as ddgs:
                for q in q_list[:10]:
                    for res in ddgs.text(q, max_results=20):
                        clean_u, ad_id = extract_ad_url_and_id(res.get("href", ""))
                        if clean_u and ad_id and ad_id < 500000000 and ad_id not in found:
                            found[ad_id] = (clean_u, res.get("title", "") + " " + res.get("body", ""))
                    time.sleep(0.5)
        except Exception:
            pass

    return found


def jina_get(session, url):
    j_url = "https://r.jina.ai/" + url
    for _ in range(2):
        try:
            r = session.get(j_url, timeout=25)
            if r.status_code == 200 and len(r.text) > 500:
                if "Too Many Requests" not in r.text and "RateLimitExceeded" not in r.text:
                    return r.text
        except Exception:
            pass
        time.sleep(2)
    return ""


def clean_markdown_to_text(md):
    txt = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", md)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"[*#_`~>|]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def inspect_and_parse(session, ad_id, url, snippet, blocked):
    if ad_id >= 500000000:
        return None, True

    raw_s = jina_get(session, url)
    fallback_s = ""
    if "تم النشر بواسطة" not in raw_s or "إعلانات نشطة" not in raw_s:
        fallback_s = jina_get(session, url + "?abs=1")

    if not raw_s and not fallback_s:
        return None, False

    combined_raw = raw_s + "\n" + fallback_s
    if "لم يعد هذا الإعلان متاح" in combined_raw or "هذا الإعلان لم يعد متاح" in combined_raw:
        return None, True

    ad_sec = raw_s if len(raw_s) > 600 else fallback_s
    for marker in ["إعلانات ذات صلة", "اعلانات ذات صلة", "إعلانات مشابهة", "اعلانات مشابهة"]:
        if marker in ad_sec:
            ad_sec = ad_sec.split(marker)[0]

    seller = ""
    cnt = 0

    for src in [ad_sec, fallback_s, raw_s]:
        if not src or "تم النشر بواسطة" not in src:
            continue
        idx = src.find("تم النشر بواسطة")
        seller_block = src[idx:idx + 650]
        block_clean = clean_markdown_to_text(seller_block)

        if not seller:
            m_name = re.search(
                r"تم النشر بواسطة\s+(.+?)(?:\s+عضو منذ|\s+إعلانات نشطة|\s+اعلانات نشطة|\s+إعلان نشط|\s+\d+\s+إعلان|\s+معرّف|\s+معرف|\s+قم بالإبلاغ)",
                block_clean
            )
            if m_name:
                seller = m_name.group(1).strip()

        if cnt == 0:
            m_cnt = re.search(r"(?:إعلانات نشطة|اعلانات نشطة|إعلان نشط|اعلان نشط)\s*:?\s*(\d+)", block_clean)
            if not m_cnt:
                m_cnt = re.search(r"(\d+)\s*(?:إعلانات نشطة|اعلانات نشطة|إعلان نشط|اعلان نشط)", block_clean)
            if m_cnt:
                cnt = int(m_cnt.group(1))
            elif "عضو منذ" in block_clean and seller:
                cnt = 1

    if not seller and "تم النشر بواسطة" not in combined_raw:
        return None, False

    if not seller or seller in blocked or is_broker_name(seller):
        if seller:
            blocked.add(seller)
        return None, True

    if cnt < 1 or cnt > 4:
        if cnt > 4:
            blocked.add(seller)
        return None, True

    desc_clean = ""
    for src in [ad_sec, fallback_s]:
        if "الوصف" in src:
            after_desc = src.split("الوصف", 1)[1]
            for stop_w in ["تم النشر بواسطة", "الموقع", "معرّف الإعلان", "معرف الإعلان", "قم بالإبلاغ", "أول سكن"]:
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
            return None, True

    if not any(w in full_check for w in NEW_CAIRO_WORDS):
        return None, True

    for phrase in BODY_BROKER_PHRASES:
        if phrase in desc_clean:
            return None, True

    top_sec = clean_markdown_to_text(ad_sec[:2500])
    price_num = 0
    for pm in re.finditer(r"(\d[\d,]{3,11})\s*(?:ج\.م|جنيه|EGP)", top_sec):
        val = int(pm.group(1).replace(",", ""))
        if val >= 2500:
            price_num = val
            break

    if price_num == 0:
        for pm in re.finditer(r"(\d[\d,]{3,11})\s*(?:ج\.م|جنيه|EGP)", desc_clean):
            val = int(pm.group(1).replace(",", ""))
            if val >= 2500:
                price_num = val
                break

    if price_num == 0:
        return None, True

    price_text = f"{price_num:,} ج.م"

    area = "مدرج بالإعلان"
    m_area = re.search(r"(?:المساحة|مساحة|المساحه)\s*:?\s*(\d{2,4})", top_sec + " " + desc_clean)
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
        "title": title_clean[:130] if title_clean else "وحدة سكنية بالقاهرة الجديدة من المالك",
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
    }, True


def scrape_all():
    existing_ads, blocked, checked_ids = load_existing()
    now_dt = datetime.now(CAIRO_TZ)

    kept_ads = {}
    for ad in existing_ads:
        try:
            aid = int(ad.get("ad_id", 0))
            if aid <= 0 or aid >= 500000000:
                continue
            if is_broker_name(ad.get("seller_name", "")):
                continue
            if int(ad.get("seller_ads_count") or 1) > 4:
                continue
            if int(ad.get("price_num") or 0) < 2500:
                continue
            kept_ads[aid] = ad
        except Exception:
            continue

    session = cffi_requests.Session(impersonate="chrome120")
    candidates = search_yahoo_bing(session)
    print(f"Found {len(candidates)} candidate URLs | Existing valid ads: {len(kept_ads)}")

    seller_freq = {}
    unchecked = []
    for uid, (u, snip) in candidates.items():
        if uid >= 500000000:
            checked_ids.add(uid)
            continue
        if uid in kept_ads or uid in checked_ids:
            continue
        unchecked.append((uid, u, snip))

    random.shuffle(unchecked)
    print(f"Unchecked candidates to inspect: {len(unchecked)}")

    inspected = 0
    for uid, u, snip in unchecked:
        if inspected >= 65:
            break
        inspected += 1
        try:
            item, mark_checked = inspect_and_parse(session, uid, u, snip, blocked)
            if mark_checked:
                checked_ids.add(uid)
            if item:
                sname = item["seller_name"]
                seller_freq[sname] = seller_freq.get(sname, 0) + 1
                if seller_freq[sname] <= 4:
                    kept_ads[uid] = item
                    print(f"Added: {uid} | {item['deal']} | {item['price_text']} | {sname}")
                else:
                    blocked.add(sname)
                    kept_ads.pop(uid, None)
        except Exception as e:
            print(f"Skip {uid}: {e}")

        time.sleep(3.5)

    final_ads = [
        ad for ad in kept_ads.values()
        if ad.get("seller_name") not in blocked and not is_broker_name(ad.get("seller_name", ""))
    ]
    final_ads.sort(key=lambda x: x.get("ad_id", 0), reverse=True)

    out = {
        "last_scrape": now_dt.strftime("%Y/%m/%d, %I:%M %p"),
        "total_ads": len(final_ads),
        "blocked_count": len(blocked),
        "blocked_users": sorted(list(blocked))[:500],
        "checked_ids_v2": sorted(list(checked_ids))[-4000:],
        "ads": final_ads
    }
    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(final_ads)} verified owner ads.")


if __name__ == "__main__":
    scrape_all()
