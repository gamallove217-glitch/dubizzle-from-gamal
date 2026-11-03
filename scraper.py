import json, time, re, os
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
import requests
from curl_cffi import requests as creq
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

SCHEMA_VERSION = 21
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
    ("شقة للايجار القاهرة الجديدة", "إيجار", "شقق"),
    ("شقة مفروشة للايجار التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار النرجس أو اللوتس أو الياسمين أو البنفسج التجمع", "إيجار", "شقق"),
    ("شقة للايجار جاردينيا أو دار مصر أو سكن مصر التجمع", "إيجار", "شقق"),
    ("شقة للبيع التجمع الخامس", "بيع", "شقق"),
    ("شقة للبيع القاهرة الجديدة", "بيع", "شقق"),
    ("شقة للبيع النرجس أو اللوتس أو البنفسج أو الأندلس التجمع", "بيع", "شقق"),
    ("شقة للبيع بيت الوطن أو المستثمرين أو القطامية التجمع", "بيع", "شقق"),
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
BAD_SELLERS = ["real estate", "properties", "property", "investment", "development", "consultancy", "agency", "broker", "group", "homes", "aqar", "للتسويق", "للاستثمار", "للتنمية", "للتطوير", "شركة", "el rabeh", "go homes", "quality square", "بانوراما"]
DEAD_WORDS = ["لم يتم العثور على تطابقات", "قد تم بيعه أو إزالته", "تم بيعه أو إزالته", "هذا الإعلان غير متاح", "يتعذر العثور على الصفحة", "we couldn't find any matches", "no longer available"]

def fetch_page_text(url):
    try:
        r = requests.get(f"https://r.jina.ai/{url}", timeout=18)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception:
        pass
    try:
        r2 = requests.post(FLARE_URL, json={"cmd": "request.get", "url": url, "maxTimeout": 35000}, timeout=40)
        if r2.status_code == 200:
            html = r2.json().get("solution", {}).get("response", "")
            if len(html) > 1000 and "just a moment" not in html.lower():
                soup = BeautifulSoup(html, "html.parser")
                for s in soup(["script", "style", "noscript"]):
                    s.decompose()
                return soup.get_text("\n", strip=True)
    except Exception:
        pass
    return ""

def discover_candidates():
    cands = []
    for cat_url, deal, cat in CATEGORY_URLS:
        txt = fetch_page_text(cat_url)
        if txt:
            for m in re.finditer(r"(https://www\.dubizzle\.com\.eg/ad/[^\s\)\"'\]]+-ID\d+\.html)", txt):
                cands.append((m.group(1), "", deal, cat))
        time.sleep(1)

    for q_txt, deal, cat in QUERIES:
        q_full = f"site:dubizzle.com.eg/ad/ {q_txt}"
        try:
            for r in DDGS().text(q_full, region="eg-ar", max_results=18):
                cands.append((r.get("href", ""), r.get("title", ""), deal, cat))
        except Exception:
            pass
        time.sleep(1)
    return cands

def inspect_and_parse(url, fallback_t, def_deal, def_cat, blocked):
    url = url.split("?")[0]
    if "dubizzle.com.eg" not in url or "/ad/" not in url or "/companies/" in url:
        return None
    m_url_id = re.search(r"-ID(\d+)", url, re.I)
    url_id = int(m_url_id.group(1)) if m_url_id else 0
    if url_id >= 500000000:
        return None

    raw_page = fetch_page_text(url)
    if not raw_page or any(dw in raw_page.lower() for dw in DEAD_WORDS):
        return None
    if "تم النشر بواسطة" not in raw_page:
        return None

    before_report = raw_page.split("الإبلاغ عن هذا الإعلان")[0].split("قم بالإبلاغ عن هذا الإعلان")[0]
    seller_box = before_report.rsplit("تم النشر بواسطة", 1)[-1]

    m_cnt = re.search(r"(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]\s*[:：]?\s*(\d+)", seller_box) or re.search(r"(\d+)\s*(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]", seller_box)
    if not m_cnt:
        return None
    cnt = int(m_cnt.group(1))
    if cnt < 1 or cnt > 4:
        if cnt > 7:
            blocked.add(url)
        return None

    m_id = re.search(r"(?:رقم|معرف)\s*الإعلان\s*[:：]?\s*(\d+)", seller_box)
    ad_id = int(m_id.group(1)) if m_id else (url_id or int(time.time()))
    if ad_id >= 500000000:
        return None

    lines_sel = [ln.strip() for ln in seller_box.splitlines() if ln.strip() and not ln.strip().startswith("![") and "عضو منذ" not in ln and "نشطة" not in ln and "الإعلان" not in ln]
    seller = lines_sel[0][:30] if lines_sel else "مالك"
    seller = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", seller).strip()
    if any(bs in seller.lower() for bs in BAD_SELLERS) or seller in blocked:
        blocked.add(seller)
        return None

    m_title = re.search(r"^Title:\s*(.+)$", raw_page, re.M)
    clean_t = m_title.group(1).strip() if m_title else fallback_t
    clean_t = re.sub(r"\s*[-|]\s*(?:شقق|فلل|عقار|دوبيزل|dubizzle).*$", "", clean_t, flags=re.I).strip() or "عقار بالقاهرة الجديدة"

    before_seller = before_report.rsplit("تم النشر بواسطة", 1)[0]
    ad_body = before_seller.rsplit("الاتجاهات والمؤشرات", 1)[0] if "الاتجاهات والمؤشرات" in before_seller else before_seller
    if "الإعلانات ذات الصلة" in ad_body:
        ad_body = ad_body.split("الإعلانات ذات الصلة", 1)[-1]
    elif "المساحة" in ad_body:
        ad_body = ad_body[max(0, ad_body.find("المساحة") - 500):]

    if any(b in clean_t.lower() for b in BAD_CITIES) or not any(n in (clean_t + " " + ad_body).lower() for n in NC_PLACES):
        return None

    price_txt, price_num = "موضح داخل الإعلان", 1
    m_p = re.search(r"(?:ج\.م|EGP)\s*([\d,]{4,12})", ad_body, re.I) or re.search(r"([\d,]{4,12})\s*(?:ج\.م|جنيه|جنية|EGP)", ad_body, re.I)
    if m_p and m_p.group(1).replace(",", "").isdigit() and int(m_p.group(1).replace(",", "")) >= 2000:
        price_num = int(m_p.group(1).replace(",", ""))
        price_txt = f"{price_num:,} ج.م"

    m_ar = re.search(r"المساحة\s*\(?م[٢2²]?\)?\s*[:：\n]*\s*(\d{2,4})", ad_body, re.I) or re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢)", clean_t + " " + ad_body, re.I)
    area = (m_ar.group(1) + " م²") if m_ar else "مدرج بالإعلان"
    m_bd = re.search(r"غرف(?:\s*نوم)?\s*[:：\n]*\s*(\d+)", ad_body)
    beds = (m_bd.group(1) + " غرف") if m_bd else ""
    m_bt = re.search(r"الحمامات\s*[:：\n]*\s*(\d+)", ad_body)
    baths = (m_bt.group(1) + " حمام") if m_bt else ""

    desc_part = ad_body
    for kw in ["### الوصف", "## الوصف", "الوصف", "وصف"]:
        if kw in desc_part:
            desc_part = desc_part.rsplit(kw, 1)[-1]
            break
    for cut in ["اقرأ المزيد", "الكماليات", "المرافق", "الموقع"]:
        if cut in desc_part:
            desc_part = desc_part.split(cut, 1)[0]
    desc_lines = [ln.strip() for ln in desc_part.splitlines() if ln.strip() and not ln.strip().startswith("![") and "http" not in ln and "%D" not in ln and "سيارات" not in ln]
    clean_desc = " ".join(desc_lines)[:450].strip() or clean_t

    t_low = (clean_t + " " + clean_desc).lower()
    deal = "إيجار" if ("غرض العقار للإيجار" in ad_body or any(w in clean_t.lower() for w in ["للايجار", "للإيجار", "ايجار", "إيجار", "مفروش"])) else ("بيع" if any(w in clean_t.lower() for w in ["للبيع", "بيع", "تمليك"]) else def_deal)
    cat, sub = def_cat, ("شقة" if def_cat == "شقق" else def_cat)
    for k, c, s in [("مكتب", "تجاري وإداري", "تجاري وإداري"), ("محل", "تجاري وإداري", "تجاري وإداري"), ("عيادة", "تجاري وإداري", "تجاري وإداري"), ("بنتهاوس", "شقق", "بنتهاوس"), ("دوبلكس", "شقق", "دوبلكس"), ("استوديو", "شقق", "استوديو"), ("فيلا", "فيلا", "فيلا"), ("تاون", "فيلا", "فيلا"), ("شقة", "شقق", "شقة"), ("شقه", "شقق", "شقة")]:
        if k in clean_t.lower():
            cat, sub = c, s
            break

    return {"schema_version": SCHEMA_VERSION, "ad_id": ad_id, "title": clean_t, "url": url, "price_text": price_txt, "price_num": price_num, "deal": deal, "category": cat, "subtype": sub, "location": "القاهرة الجديدة", "area": area, "beds": beds, "baths": baths, "description": clean_desc, "seller_name": seller, "seller_profile": seller, "seller_ads_count": cnt}

def scrape_all():
    now_ts = int(time.time())
    now_str = datetime.now(timezone(timedelta(hours=2))).strftime("%Y/%m/%d، %I:%M %p")
    old_ads, blocked = [], set()
    if os.path.exists("ads.json"):
        try:
            d = json.load(open("ads.json", "r", encoding="utf-8"))
            old_ads = [a for a in d.get("ads", []) if a.get("schema_version") == SCHEMA_VERSION and (now_ts - a.get("scraped_timestamp", now_ts)) < SEVEN_DAYS]
            blocked = set(d.get("blocked_users", []))
        except Exception:
            pass
    seen = {a["url"] for a in old_ads}
    new_ads = []
    cands = discover_candidates()
    print(f"Total candidates: {len(cands)}")
    for u, t, deal, cat in cands:
        u_clean = u.split("?")[0]
        if u_clean in seen or "dubizzle.com.eg/ad/" not in u_clean:
            continue
        seen.add(u_clean)
        item = inspect_and_parse(u_clean, t, deal, cat, blocked)
        if item:
            item["scraped_timestamp"] = now_ts
            item["scraped_date"] = now_str
            new_ads.append(item)
            print(f"Verified Live Owner Ad: {item['title']} | {item['price_text']} | {item['seller_name']} ({item['seller_ads_count']})")
        time.sleep(2)
    final = sorted(new_ads + old_ads, key=lambda x: x.get("ad_id", 0), reverse=True)
    owners = len({a["seller_profile"] for a in final})
    json.dump({"last_scrape": now_str, "total": len(final), "owners_count": owners, "blocked_count": len(blocked), "blocked_users": list(blocked), "ads": final}, open("ads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Done. Saved {len(final)} live owner ads.")

if __name__ == "__main__":
    scrape_all()
# === END OF FILE ===
