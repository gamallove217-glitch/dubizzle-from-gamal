import json, time, re, os
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
import requests
from curl_cffi import requests as creq
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

SCHEMA_VERSION = 24
SEVEN_DAYS = 7 * 24 * 3600
FLARE_URL = "http://localhost:8191/v1"

CATEGORY_URLS = [
    ("https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/", "إيجار", "شقق"),
    ("https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/?page=2", "إيجار", "شقق"),
    ("https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/", "بيع", "شقق"),
    ("https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/?page=2", "بيع", "شقق"),
    ("https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/", "إيجار", "فيلا"),
    ("https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/", "بيع", "فيلا"),
    ("https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/", "إيجار", "تجاري وإداري"),
    ("https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/", "بيع", "تجاري وإداري")
]

QUERIES = [
    ("شقة للايجار التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار التجمع الخامس من المالك", "إيجار", "شقق"),
    ("شقة للايجار القاهرة الجديدة", "إيجار", "شقق"),
    ("شقة مفروشة للايجار التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار النرجس التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار اللوتس التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار الياسمين أو البنفسج التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار جاردينيا أو دار مصر أو سكن مصر التجمع", "إيجار", "شقق"),
    ("شقة للايجار الأندلس أو المستثمرين أو القطامية التجمع", "إيجار", "شقق"),
    ("شقة للبيع التجمع الخامس", "بيع", "شقق"),
    ("شقة للبيع التجمع الخامس من المالك", "بيع", "شقق"),
    ("شقة للبيع القاهرة الجديدة", "بيع", "شقق"),
    ("شقة للبيع النرجس أو اللوتس أو الياسمين التجمع", "بيع", "شقق"),
    ("شقة للبيع البنفسج أو الأندلس أو بيت الوطن التجمع", "بيع", "شقق"),
    ("شقة للبيع جاردينيا أو دار مصر أو سكن مصر التجمع", "بيع", "شقق"),
    ("شقة للايجار الرحاب", "إيجار", "شقق"),
    ("شقة للبيع الرحاب", "بيع", "شقق"),
    ("شقة للايجار مدينتي", "إيجار", "شقق"),
    ("شقة للبيع مدينتي", "بيع", "شقق"),
    ("دوبلكس للايجار أو للبيع التجمع الخامس", "بيع", "شقق"),
    ("بنتهاوس أو روف التجمع الخامس", "بيع", "شقق"),
    ("استوديو أو غرفة للايجار التجمع الخامس", "إيجار", "شقق"),
    ("فيلا أو تاون هاوس للايجار التجمع الخامس", "إيجار", "فيلا"),
    ("فيلا أو تاون هاوس للبيع التجمع الخامس", "بيع", "فيلا"),
    ("مكتب اداري للايجار التجمع الخامس", "إيجار", "تجاري وإداري"),
    ("محل أو عيادة التجمع الخامس أو الرحاب أو مدينتي", "إيجار", "تجاري وإداري")
]

NC_PLACES = ["التجمع", "القاهرة الجديدة", "القاهره الجديده", "الرحاب", "مدينتي", "مدينتى", "النرجس", "اللوتس", "الياسمين", "البنفسج", "الشويفات", "الأندلس", "الاندلس", "بيت الوطن", "الأكاديمية", "المستثمرين", "القطامية", "ميفيدا", "هايد بارك", "ماونتن فيو", "بالم هيلز", "سراي", "التسعين", "القرنفل", "تاج سيتي", "جاردينيا", "دار مصر", "سكن مصر", "جنة", "الباتيو", "المراسم", "لاروزا", "new cairo", "5th settlement", "rehab", "madinaty"]
BAD_CITIES = ["العبور", "لوران", "سموحة", "الإسكندرية", "الاسكندرية", "أكتوبر", "اكتوبر", "زايد", "الشروق", "بدر", "المعادي", "مدينة نصر", "مصر الجديدة", "النزهة", "المقطم", "الهرم", "فيصل", "الدقي", "المهندسين", "حلوان", "شبرا", "الساحل", "السخنة", "الغردقة", "طنطا", "المنصورة", "العاصمة الإدارية"]
BAD_SELLERS = ["real estate", "properties", "property", "investment", "development", "consultancy", "agency", "broker", "group", "homes", "aqar", "للتسويق", "للاستثمار", "للتنمية", "للتطوير", "شركة", "el rabeh", "go homes", "quality square", "بانوراما", "سوق العقارات", "عقارات مصر"]
GONE_WORDS = ["لم يتم العثور على تطابقات", "قد تم بيعه أو إزالته", "تم بيعه أو إزالته", "هذا الإعلان غير متاح", "يتعذر العثور على الصفحة"]

def clean_markdown_to_text(raw_md):
    txt = raw_md.split("Markdown Content:")[-1] if "Markdown Content:" in raw_md else raw_md
    txt = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]*)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+|%[0-9A-Fa-f]{2}", " ", txt)
    txt = re.sub(r"[*#_`~>|]+|\s+", " ", txt).strip()
    return txt

def flare_get(url):
    try:
        r3 = requests.get(f"https://r.jina.ai/{url}", timeout=16)
        if r3.status_code == 200 and len(r3.text) > 500:
            if "dubizzle.com.eg/motors)" in r3.text:
                return ""
            m_t = re.search(r"^Title:\s*(.+)$", r3.text, re.M)
            t_hdr = f"TITLE_HDR: {m_t.group(1).strip()} | " if m_t else ""
            cleaned = clean_markdown_to_text(r3.text)
            if "تم النشر بواسطة" in cleaned:
                return t_hdr + cleaned
    except Exception:
        pass
    try:
        r = requests.post(FLARE_URL, json={"cmd": "request.get", "url": url, "maxTimeout": 30000}, timeout=35)
        if r.status_code == 200:
            html = r.json().get("solution", {}).get("response", "")
            if len(html) > 1000 and "just a moment" not in html.lower():
                soup = BeautifulSoup(html, "html.parser")
                for s in soup(["script", "style", "noscript"]):
                    s.decompose()
                return soup.get_text(" ", strip=True)
    except Exception:
        pass
    return ""

def discover_candidates():
    cands = []
    for cat_url, deal, cat in CATEGORY_URLS:
        try:
            rj = requests.get(f"https://r.jina.ai/{cat_url}", timeout=18)
            if rj.status_code == 200:
                for m in re.finditer(r"(https://www\.dubizzle\.com\.eg/ad/[^\s\)\"'\]]+-ID\d+\.html)", rj.text):
                    cands.append((m.group(1), "", "", deal, cat))
        except Exception:
            pass
        time.sleep(1)

    for q_txt, deal, cat in QUERIES:
        q_full = f"site:dubizzle.com.eg/ad/ {q_txt}"
        try:
            for r in DDGS().text(q_full, region="eg-ar", max_results=15):
                cands.append((r.get("href", ""), r.get("title", ""), r.get("body", ""), deal, cat))
        except Exception:
            pass
        try:
            ry = creq.get("https://search.yahoo.com/search", params={"p": q_full, "n": "20"}, impersonate="chrome120", timeout=15)
            if ry.status_code == 200:
                soup = BeautifulSoup(ry.text, "html.parser")
                for div in soup.select("div.algo, div.dd.algo"):
                    a = div.find("a", href=True)
                    if not a:
                        continue
                    href = a["href"]
                    if "RU=" in href:
                        href = unquote(href.split("RU=")[1].split("/RK=")[0])
                    if "dubizzle.com.eg/ad/" in href:
                        p = div.find("div", class_=re.compile(r"compText|s-desc"))
                        cands.append((href, a.get_text(" ", strip=True), p.get_text(" ", strip=True) if p else "", deal, cat))
        except Exception:
            pass
        try:
            rb = creq.get("https://www.bing.com/search", params={"q": q_full, "count": "20"}, impersonate="chrome120", timeout=15)
            if rb.status_code == 200:
                soup = BeautifulSoup(rb.text, "html.parser")
                for li in soup.select("li.b_algo"):
                    a = li.find("a", href=True)
                    if a and "dubizzle.com.eg/ad/" in a["href"]:
                        p = li.find("p")
                        cands.append((a["href"], a.get_text(" ", strip=True), p.get_text(" ", strip=True) if p else "", deal, cat))
        except Exception:
            pass
        time.sleep(1)
    return cands

def inspect_and_parse(url, raw_t, fallback_s, def_deal, def_cat, blocked):
    url = url.split("?")[0]
    if "dubizzle.com.eg" not in url or "/ad/" not in url or "/companies/" in url:
        return None
    if re.search(r"-ID5\d{8}", url):
        return None

    raw_s = flare_get(url)
    if not raw_s or any(g in raw_s.lower() for g in GONE_WORDS):
        return None

    before_rep = raw_s.split("الإبلاغ عن هذا الإعلان")[0].split("قم بالإبلاغ عن هذا الإعلان")[0]
    if "تم النشر بواسطة" not in before_rep:
        return None

    seller_box = before_rep.rsplit("تم النشر بواسطة", 1)[-1]
    m_sel = re.search(r"^\s*([^\.\|]{2,35}?)(?:\s+عضو منذ|\s+(?:ال)?[إأآا]علانات|\s+نشطة|$)", seller_box)
    if not m_sel:
        return None
    seller = m_sel.group(1).strip()
    if any(bs in seller.lower() for bs in BAD_SELLERS) or seller in blocked or "الاتجاهات" in seller or "ذات الصلة" in seller:
        blocked.add(seller)
        return None

    m_cnt = re.search(r"(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]\s*[:：]?\s*(\d+)", seller_box) or re.search(r"(\d+)\s*(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]", seller_box)
    cnt = int(m_cnt.group(1)) if m_cnt else 1
    if cnt < 1 or cnt > 4:
        if cnt > 7:
            blocked.add(seller)
        return None

    m_id = re.search(r"(?:رقم|معرف)\s*الإعلان\s*[:：]?\s*(\d+)", before_rep) or re.search(r"-ID(\d+)", url, re.I)
    ad_id = int(m_id.group(1)) if m_id else int(time.time())
    if ad_id >= 500000000:
        return None

    ad_sec = before_rep.rsplit("تم النشر بواسطة", 1)[0]
    if "الاتجاهات والمؤشرات" in ad_sec:
        ad_sec = ad_sec.rsplit("الاتجاهات والمؤشرات", 1)[0]
    for menu_cut in ["الإعلانات ذات الصلة", "شاشات وأجهزة", "حديقة و أماكن خارجية", "إكسسوارات صالون"]:
        if menu_cut in ad_sec:
            ad_sec = ad_sec.split(menu_cut, 1)[-1]

    m_hdr = re.search(r"TITLE_HDR:\s*(.+?)\s*\|", raw_s)
    base_t = m_hdr.group(1).strip() if m_hdr else raw_t
    clean_t = re.sub(r"^.*?https?://[^\s]+(?:\s*›\s*[^\s]+)*\s*", "", base_t)
    clean_t = re.sub(r"^دوبيزل\s*", "", clean_t)
    clean_t = re.sub(r"\s*[-|]\s*(?:شقق|فلل|عقار|دوبيزل|dubizzle).*$", "", clean_t, flags=re.I).strip() or "عقار بالقاهرة الجديدة"

    comb = (clean_t + " " + ad_sec + " " + fallback_s).lower()
    if any(b in clean_t.lower() for b in BAD_CITIES) or not any(n in comb for n in NC_PLACES):
        return None

    price_txt, price_num = "موضح داخل الإعلان", 1
    m_p = re.search(r"(?:ج\.م|EGP)\s*([\d,]{4,12})", ad_sec + " " + fallback_s, re.I) or re.search(r"([\d,]{4,12})\s*(?:ج\.م|جنيه|جنية|EGP)", ad_sec + " " + fallback_s, re.I)
    if m_p and m_p.group(1).replace(",", "").isdigit() and int(m_p.group(1).replace(",", "")) >= 2000:
        price_num = int(m_p.group(1).replace(",", ""))
        price_txt = f"{price_num:,} ج.م"
    else:
        m_mil = re.search(r"(\d+(?:\.\d+)?)\s*(?:مليون|ملايين)", ad_sec + " " + fallback_s)
        if m_mil:
            price_num = int(float(m_mil.group(1)) * 1000000)
            price_txt = f"{price_num:,} ج.م"

    m_ar = re.search(r"المساحة\s*\(?م[٢2²]?\)?\s*[:：]?\s*(\d{2,4})", comb, re.I) or re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢)", comb, re.I)
    area = (m_ar.group(1) + " م²") if m_ar else "مدرج بالإعلان"
    m_bd = re.search(r"غرف\s*نوم\s*[:：]?\s*([1-9])\b", comb) or re.search(r"\b([1-9])\s*(?:غرف|غرفة)\b", comb)
    beds = (m_bd.group(1) + " غرف") if m_bd else ""
    m_bt = re.search(r"الحمامات\s*[:：]?\s*([1-9])\b", comb) or re.search(r"\b([1-9])\s*(?:حمام|حمامات)\b", comb)
    baths = (m_bt.group(1) + " حمام") if m_bt else ""

    raw_desc = ""
    for d_kw in [" الوصف ", " وصف "]:
        if d_kw in ad_sec:
            raw_desc = ad_sec.rsplit(d_kw, 1)[-1]
            break
    if not raw_desc:
        raw_desc = fallback_s or clean_t
    for cut in ["اقرأ المزيد", "الكماليات", "المرافق", "الموقع"]:
        if cut in raw_desc:
            raw_desc = raw_desc.split(cut, 1)[0]
    desc_clean = re.sub(r"\s+", " ", raw_desc).strip()
    if len(desc_clean) < 15 or any(w in desc_clean for w in ["غيار سيارات", "أثاث مكتبي", "قطع غيار", "موتوسيكلات"]):
        desc_clean = fallback_s or clean_t

    t_low = clean_t.lower()
    deal = "إيجار" if any(w in t_low for w in ["للايجار", "للإيجار", "ايجار", "إيجار", "مفروش"]) else ("بيع" if any(w in t_low for w in ["للبيع", "بيع", "تمليك"]) else def_deal)
    cat, sub = def_cat, ("شقة" if def_cat == "شقق" else def_cat)
    for k, c, s in [("مكتب", "تجاري وإداري", "تجاري وإداري"), ("محل", "تجاري وإداري", "تجاري وإداري"), ("عيادة", "تجاري وإداري", "تجاري وإداري"), ("بنتهاوس", "شقق", "بنتهاوس"), ("دوبلكس", "شقق", "دوبلكس"), ("استوديو", "شقق", "استوديو"), ("فيلا", "فيلا", "فيلا"), ("تاون", "فيلا", "فيلا"), ("شقة", "شقق", "شقة"), ("شقه", "شقق", "شقة")]:
        if k in t_low:
            cat, sub = c, s
            break

    return {"schema_version": SCHEMA_VERSION, "ad_id": ad_id, "title": clean_t, "url": url, "price_text": price_txt, "price_num": price_num, "deal": deal, "category": cat, "subtype": sub, "location": "القاهرة الجديدة", "area": area, "beds": beds, "baths": baths, "description": desc_clean[:500], "seller_name": seller, "seller_profile": seller, "seller_ads_count": cnt}

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
    print(f"Total candidates found: {len(cands)}")
    for u, t, s, deal, cat in cands[:140]:
        u_clean = u.split("?")[0]
        if u_clean in seen or "dubizzle.com.eg/ad/" not in u_clean:
            continue
        seen.add(u_clean)
        item = inspect_and_parse(u_clean, t, s, deal, cat, blocked)
        if item:
            item["scraped_timestamp"] = now_ts
            item["scraped_date"] = now_str
            new_ads.append(item)
            print(f"Added: {item['title']} | {item['price_text']} | {item['seller_name']}")
        time.sleep(2)
    final = sorted(new_ads + old_ads, key=lambda x: x.get("ad_id", 0), reverse=True)
    owners = len({a["seller_profile"] for a in final})
    json.dump({"last_scrape": now_str, "total": len(final), "owners_count": owners, "blocked_count": len(blocked), "blocked_users": list(blocked), "ads": final}, open("ads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Done. Saved {len(final)} ads.")

if __name__ == "__main__":
    scrape_all()
# === END OF FILE ===
