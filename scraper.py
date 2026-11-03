import json, time, re, os
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
import requests
from curl_cffi import requests as creq
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

SCHEMA_VERSION = 20
SEVEN_DAYS = 7 * 24 * 3600
FLARE_URL = "http://localhost:8191/v1"

CATEGORY_URLS = [
    ("https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/", "إيجار", "شقق"),
    ("https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/", "بيع", "شقق"),
    ("https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/", "إيجار", "فيلا"),
    ("https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/", "بيع", "فيلا"),
    ("https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/", "إيجار", "تجاري وإداري"),
    ("https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/", "بيع", "تجاري وإداري")
]

QUERIES = [
    ("شقة للايجار التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار القاهرة الجديدة", "إيجار", "شقق"),
    ("شقة مفروشة للايجار التجمع الخامس", "إيجار", "شقق"),
    ("شقة للبيع التجمع الخامس", "بيع", "شقق"),
    ("شقة للبيع القاهرة الجديدة", "بيع", "شقق"),
    ("شقة للايجار الرحاب مدينتي", "إيجار", "شقق"),
    ("شقة للبيع الرحاب مدينتي", "بيع", "شقق"),
    ("دوبلكس التجمع الخامس", "بيع", "شقق"),
    ("بنتهاوس استوديو التجمع الخامس", "إيجار", "شقق"),
    ("فيلا تاون هاوس التجمع الخامس", "بيع", "فيلا"),
    ("مكتب محل عيادة التجمع الخامس", "إيجار", "تجاري وإداري")
]

NC_PLACES = ["التجمع", "القاهرة الجديدة", "القاهره الجديده", "الرحاب", "مدينتي", "مدينتى", "النرجس", "اللوتس", "الياسمين", "البنفسج", "الشويفات", "الأندلس", "الاندلس", "بيت الوطن", "الأكاديمية", "المستثمرين", "القطامية", "ميفيدا", "هايد بارك", "ماونتن فيو", "بالم هيلز", "سراي", "التسعين", "القرنفل", "تاج سيتي", "جاردينيا", "دار مصر", "سكن مصر", "جنة", "الباتيو", "المراسم", "لاروزا", "new cairo", "5th settlement", "rehab", "madinaty"]
BAD_CITIES = ["العبور", "لوران", "سموحة", "الإسكندرية", "الاسكندرية", "أكتوبر", "اكتوبر", "زايد", "الشروق", "بدر", "المعادي", "مدينة نصر", "مصر الجديدة", "النزهة", "المقطم", "الهرم", "فيصل", "الدقي", "المهندسين", "حلوان", "شبرا", "الساحل", "السخنة", "الغردقة", "طنطا", "المنصورة", "العاصمة الإدارية"]
BAD_SELLERS = ["real estate", "properties", "property", "investment", "development", "consultancy", "agency", "broker", "group", "homes", "aqar", "للتسويق", "للاستثمار", "للتنمية", "للتطوير", "شركة", "el rabeh", "go homes", "quality square", "بانوراما"]
GONE_WORDS = ["لم يتم العثور على تطابقات", "قد تم بيعه أو إزالته", "تم بيعه أو إزالته", "هذا الإعلان غير متاح", "منذ 2 أسابيع", "منذ 3 أسابيع", "منذ 4 أسابيع", "منذ أسبوعين", "منذ شهر", "منذ أشهر", "منذ سنة", "بمقدم", "دفعة الأولى", "دفعه اولى", "أقساط على", "كود الوحدة", "**"]

def flare_get(url, timeout_ms=45000):
    try:
        r = requests.post(FLARE_URL, json={"cmd": "request.get", "url": url, "maxTimeout": timeout_ms}, timeout=55)
        if r.status_code == 200:
            sol = r.json().get("solution", {})
            html = sol.get("response", "")
            if len(html) > 1000 and "just a moment" not in html.lower():
                return html
    except Exception:
        pass
    try:
        r2 = creq.get(url, impersonate="chrome120", timeout=20)
        if r2.status_code == 200 and len(r2.text) > 1000 and "just a moment" not in r2.text.lower():
            return r2.text
    except Exception:
        pass
    try:
        r3 = requests.get(f"https://r.jina.ai/{url}", timeout=15)
        if r3.status_code == 200 and len(r3.text) > 400:
            return r3.text
    except Exception:
        pass
    return ""

def discover_candidates():
    cands = []
    for cat_url, deal, cat in CATEGORY_URLS:
        html = flare_get(cat_url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=re.compile(r"/ad/.*-ID\d+")):
                u = a["href"].split("?")[0]
                u = "https://www.dubizzle.com.eg" + u if u.startswith("/") else u
                card_txt = a.find_parent("article").get_text(" ", strip=True) if a.find_parent("article") else a.get_text(" ", strip=True)
                cands.append((u, a.get("title") or a.get_text(" ", strip=True), card_txt, deal, cat))
            for m in re.finditer(r"(https://www\.dubizzle\.com\.eg/ad/[^\s\)\"']+-ID\d+\.html)", html):
                cands.append((m.group(1), "", "", deal, cat))

    for q_txt, deal, cat in QUERIES:
        q_full = f"site:dubizzle.com.eg/ad/ {q_txt}"
        try:
            for r in DDGS().text(q_full, region="eg-ar", max_results=20):
                cands.append((r.get("href", ""), r.get("title", ""), r.get("body", ""), deal, cat))
        except Exception:
            pass
        y_html = flare_get(f"https://search.yahoo.com/search?p={ requests.utils.quote(q_full) }&n=20", 30000)
        if y_html:
            soup = BeautifulSoup(y_html, "html.parser")
            for div in soup.select("div.algo, div.Sr"):
                a = div.find("a", href=True)
                if not a:
                    continue
                href = unquote(a["href"].split("RU=")[1].split("/RK=")[0]) if "RU=" in a["href"] else a["href"]
                p = div.find("div", class_=re.compile(r"compText|fc-falcon"))
                cands.append((href, a.get_text(" ", strip=True), p.get_text(" ", strip=True) if p else "", deal, cat))
    return cands

def inspect_and_parse(url, raw_t, raw_s, def_deal, def_cat, blocked):
    url = url.split("?")[0]
    if "dubizzle.com.eg" not in url or "/ad/" not in url or "/companies/" in url:
        return None
    m_id = re.search(r"-ID(\d+)", url, re.I) or re.search(r"رقم الإعلان\s*(\d+)", raw_s)
    ad_id = int(m_id.group(1)) if m_id else int(time.time())
    if ad_id >= 500000000 or (100000000 < ad_id < 204500000):
        return None

    page_html = flare_get(url, 35000)
    if page_html:
        soup = BeautifulSoup(page_html, "html.parser")
        for s in soup(["script", "style", "noscript"]):
            s.decompose()
        vis = soup.get_text(" ", strip=True)
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            raw_t = h1.get_text(strip=True)
        if len(vis) > 300:
            raw_s = vis

    main_s = raw_s.split("الإبلاغ عن هذا الإعلان")[0].split("قم بالإبلاغ عن هذا الإعلان")[0].split("الاتجاهات والمؤشرات")[0]
    if main_s.count(";") >= 2 and "ج.م" in main_s:
        main_s = " ".join([p for p in main_s.split(";") if "ج.م" not in p])

    clean_t = re.sub(r"^.*?https?://[^\s]+(?:\s*›\s*[^\s]+)*\s*", "", raw_t)
    clean_t = re.sub(r"^دوبيزل\s*", "", clean_t)
    clean_t = re.sub(r"\s*[-|]\s*(?:شقق|فلل|عقار|دوبيزل|dubizzle).*$", "", clean_t, flags=re.I).strip() or "عقار بالقاهرة الجديدة"

    comb = f"{clean_t} {main_s}".lower()
    if any(g in comb for g in GONE_WORDS) or any(b in clean_t.lower() for b in BAD_CITIES):
        return None
    if not any(n in comb for n in NC_PLACES):
        return None

    m_cnt = re.search(r"(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]\s*[:：]?\s*(\d+)", raw_s) or re.search(r"(\d+)\s*(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]", raw_s)
    cnt = int(m_cnt.group(1)) if m_cnt else 1
    if cnt > 4:
        if cnt > 7:
            blocked.add(url)
        return None

    m_sel = re.search(r"تم النشر بواسطة\s*([^\.\|\n]{2,30}?)(?:\s*عضو منذ|\s*الإعلانات|\.|$)", raw_s)
    seller = m_sel.group(1).strip() if m_sel else "مالك مباشر"
    if any(bs in seller.lower() for bs in BAD_SELLERS) or seller in blocked:
        blocked.add(seller)
        return None

    price_txt, price_num = "موضح داخل الإعلان", 1
    m_p = re.search(r"([\d,]{4,12})\s*(?:ج\.م|جنيه|جنية|EGP)", comb, re.I) or re.search(r"(?:السعر|ج\.م|EGP)\s*[:：]?\s*([\d,]{4,12})", comb, re.I)
    if m_p and m_p.group(1).replace(",", "").isdigit() and int(m_p.group(1).replace(",", "")) >= 2000:
        price_num = int(m_p.group(1).replace(",", ""))
        price_txt = f"{price_num:,} ج.م"

    m_ar = re.search(r"المساحة\s*\(?م[٢2²]?\)?\s*[:：]?\s*(\d{2,4})", comb, re.I) or re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢)", comb, re.I)
    area = (m_ar.group(1) + " م²") if m_ar else "مدرج بالإعلان"
    t_low = clean_t.lower()
    deal = "إيجار" if any(w in t_low for w in ["للايجار", "للإيجار", "ايجار", "إيجار", "مفروش"]) else ("بيع" if any(w in t_low for w in ["للبيع", "بيع", "تمليك"]) else def_deal)
    cat, sub = def_cat, ("شقة" if def_cat == "شقق" else def_cat)
    for k, c, s in [("مكتب", "تجاري وإداري", "تجاري وإداري"), ("محل", "تجاري وإداري", "تجاري وإداري"), ("عيادة", "تجاري وإداري", "تجاري وإداري"), ("بنتهاوس", "شقق", "بنتهاوس"), ("دوبلكس", "شقق", "دوبلكس"), ("استوديو", "شقق", "استوديو"), ("فيلا", "فيلا", "فيلا"), ("تاون", "فيلا", "فيلا"), ("شقة", "شقق", "شقة")]:
        if k in t_low:
            cat, sub = c, s
            break

    desc = main_s.split("تم النشر بواسطة")[0].strip()[:600] or clean_t
    return {"schema_version": SCHEMA_VERSION, "ad_id": ad_id, "title": clean_t, "url": url, "price_text": price_txt, "price_num": price_num, "deal": deal, "category": cat, "subtype": sub, "location": "القاهرة الجديدة", "area": area, "beds": "", "baths": "", "description": desc, "seller_name": seller, "seller_profile": seller if seller != "مالك مباشر" else url, "seller_ads_count": cnt}

def scrape_all():
    now_ts = int(time.time())
    now_str = datetime.now(timezone(timedelta(hours=2))).strftime("%Y/%m/%d، %I:%M %p")
    old_ads, blocked = [], set()
    if os.path.exists("ads.json"):
        try:
            d = json.load(open("ads.json", "r", encoding="utf-8"))
            old_ads = [a for a in d.get("ads", []) if a.get("schema_version") == SCHEMA_VERSION and (now_ts - a.get("scraped_timestamp", now_ts)) < SEVEN_DAYS and a.get("ad_id", 0) < 500000000]
            blocked = set(d.get("blocked_users", []))
        except Exception:
            pass
    seen = {a["url"] for a in old_ads}
    new_ads = []
    cands = discover_candidates()
    print(f"Discovered {len(cands)} raw candidates")
    for u, t, s, deal, cat in cands:
        u_clean = u.split("?")[0]
        if u_clean in seen or "dubizzle.com.eg/ad/" not in u_clean:
            continue
        seen.add(u_clean)
        item = inspect_and_parse(u_clean, t, s, deal, cat, blocked)
        if item:
            item["scraped_timestamp"] = now_ts
            item["scraped_date"] = now_str
            new_ads.append(item)
            if len(new_ads) >= 45:
                break
    final = sorted(new_ads + old_ads, key=lambda x: x.get("ad_id", 0), reverse=True)
    owners = len({a["seller_profile"] for a in final})
    json.dump({"last_scrape": now_str, "total": len(final), "owners_count": owners, "blocked_count": len(blocked), "blocked_users": list(blocked), "ads": final}, open("ads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Done. Saved {len(final)} ads.")

if __name__ == "__main__":
    scrape_all()
# === END OF FILE ===
