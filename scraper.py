import json, time, re, os
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
import requests, cloudscraper
from bs4 import BeautifulSoup

API_KEY = "1fbcb4ca0bad271b0780c0a848e8c05b"
SCHEMA_VERSION = 15
SEVEN_DAYS = 7 * 24 * 3600

QUERIES = [
    ("شقة للايجار التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار القاهرة الجديدة", "إيجار", "شقق"),
    ("شقة للبيع التجمع الخامس", "بيع", "شقق"),
    ("شقة للبيع القاهرة الجديدة", "بيع", "شقق"),
    ("شقة للايجار الرحاب مدينتي", "إيجار", "شقق"),
    ("شقة للبيع الرحاب مدينتي", "بيع", "شقق"),
    ("دوبلكس التجمع الخامس", "بيع", "شقق"),
    ("بنتهاوس استوديو التجمع الخامس", "إيجار", "شقق"),
    ("فيلا تاون هاوس التجمع الخامس", "بيع", "فيلا"),
    ("مكتب محل عيادة التجمع الخامس", "إيجار", "تجاري وإداري")
]

NC_PLACES = ["التجمع", "القاهرة الجديدة", "القاهره الجديده", "الرحاب", "مدينتي", "مدينتى", "النرجس", "اللوتس", "الياسمين", "البنفسج", "الشويفات", "الأندلس", "الاندلس", "بيت الوطن", "الأكاديمية", "المستثمرين", "القطامية", "ميفيدا", "هايد بارك", "ماونتن فيو", "بالم هيلز", "سراي", "التسعين", "القرنفل", "تاج سيتي", "جاردينيا", "دار مصر", "سكن مصر", "جنة", "الباتيو", "المراسم", "new cairo", "5th settlement", "rehab", "madinaty"]
BAD_CITIES = ["العبور", "لوران", "سموحة", "الإسكندرية", "الاسكندرية", "أكتوبر", "اكتوبر", "زايد", "الشروق", "بدر", "المعادي", "مدينة نصر", "مصر الجديدة", "النزهة", "المقطم", "الهرم", "فيصل", "الدقي", "المهندسين", "حلوان", "شبرا", "الساحل", "السخنة", "الغردقة", "طنطا", "المنصورة", "العاصمة الإدارية"]
BAD_SELLERS = ["real estate", "properties", "property", "investment", "development", "consultancy", "agency", "broker", "group", "homes", "aqar", "للتسويق", "للاستثمار", "للتنمية", "للتطوير", "شركة", "el rabeh", "go homes", "quality square", "بانوراما"]
GONE_WORDS = ["لم يتم العثور على تطابقات", "قد تم بيعه أو إزالته", "تم بيعه أو إزالته", "هذا الإعلان غير متاح", "بمقدم", "دفعة الأولى", "دفعه اولى", "أقساط على", "كود الوحدة", "**"]

def fetch_results(q_text):
    items = []
    q_full = f"site:dubizzle.com.eg/ad/ {q_text}"
    try:
        r = requests.get("https://api.scraperapi.com/structured/google/search", params={"api_key": API_KEY, "query": q_full, "hl": "ar", "gl": "eg"}, timeout=25)
        if r.status_code == 200:
            for x in r.json().get("organic_results", []):
                items.append((x.get("link", ""), x.get("title", ""), x.get("snippet", "")))
            if items:
                return items
    except Exception:
        pass
    try:
        sc = cloudscraper.create_scraper()
        uh = sc.get("https://search.yahoo.com/search", params={"p": q_full, "n": "20"}, timeout=20)
        if uh.status_code == 200:
            soup = BeautifulSoup(uh.text, "html.parser")
            for div in soup.select("div.algo, div.Sr"):
                a = div.find("a", href=True)
                if not a:
                    continue
                href = a["href"]
                if "RU=" in href:
                    href = unquote(href.split("RU=")[1].split("/RK=")[0])
                t = a.get_text(" ", strip=True)
                p = div.find("div", class_=re.compile(r"compText|fc-falcon"))
                s = p.get_text(" ", strip=True) if p else ""
                items.append((href, t, s))
    except Exception:
        pass
    return items

def parse_item(url, raw_t, raw_s, def_deal, def_cat, blocked):
    url = url.split("?")[0]
    if "dubizzle.com.eg" not in url or "/ad/" not in url or "/companies/" in url:
        return None
    main_s = raw_s.split("الإبلاغ عن هذا الإعلان")[0].split("قم بالإبلاغ عن هذا الإعلان")[0]
    if main_s.count(";") >= 2 and "ج.م" in main_s:
        main_s = " ".join([p for p in main_s.split(";") if "ج.م" not in p])
    title = re.sub(r"\s*[-|]\s*(?:شقق|فلل|عقار|دوبيزل|dubizzle).*$", "", raw_t, flags=re.I).strip()
    comb = (title + " " + main_s).lower()
    if any(g in comb for g in GONE_WORDS) or any(b in title.lower() for b in BAD_CITIES):
        return None
    if not any(n in title.lower() for n in NC_PLACES):
        return None

    m_id = re.search(r"رقم الإعلان\s*(\d+)", main_s) or re.search(r"-ID(\d+)", url, re.I) or re.search(r"\b([25]0\d{7})\b", comb)
    ad_id = int(m_id.group(1)) if m_id else int(time.time())
    if ad_id >= 500000000:
        return None

    m_cnt = re.search(r"(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]\s*[:：]?\s*(\d+)", main_s) or re.search(r"(\d+)\s*(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]", main_s)
    cnt = int(m_cnt.group(1)) if m_cnt else 1
    if cnt > 4:
        if cnt > 7:
            blocked.add(url)
        return None

    m_sel = re.search(r"تم النشر بواسطة\s*([^\.\|\n]{2,30}?)(?:\s*عضو منذ|\s*الإعلانات|\.|$)", main_s)
    seller = m_sel.group(1).strip() if m_sel else "مالك مباشر"
    if any(bs in seller.lower() for bs in BAD_SELLERS) or seller in blocked:
        blocked.add(seller)
        return None

    price_txt, price_num = "موضح داخل الإعلان", 1
    m_p = re.search(r"([\d,]{4,12})\s*(?:ج\.م|جنيه|EGP)", comb, re.I) or re.search(r"(?:ج\.م|EGP)\s*([\d,]{4,12})", comb, re.I)
    if m_p and m_p.group(1).replace(",", "").isdigit() and int(m_p.group(1).replace(",", "")) >= 2000:
        price_num = int(m_p.group(1).replace(",", ""))
        price_txt = f"{price_num:,} ج.م"

    m_ar = re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢)", comb, re.I)
    area = (m_ar.group(1) + " م²") if m_ar else "مدرج بالإعلان"
    t_low = title.lower()
    deal = "إيجار" if any(w in t_low for w in ["للايجار", "للإيجار", "ايجار", "إيجار", "مفروش"]) else ("بيع" if any(w in t_low for w in ["للبيع", "بيع", "تمليك"]) else def_deal)
    cat, sub = def_cat, ("شقة" if def_cat == "شقق" else def_cat)
    for k, c, s in [("مكتب", "تجاري وإداري", "تجاري وإداري"), ("محل", "تجاري وإداري", "تجاري وإداري"), ("عيادة", "تجاري وإداري", "تجاري وإداري"), ("بنتهاوس", "شقق", "بنتهاوس"), ("دوبلكس", "شقق", "دوبلكس"), ("استوديو", "شقق", "استوديو"), ("فيلا", "فيلا", "فيلا"), ("تاون", "فيلا", "فيلا"), ("شقة", "شقق", "شقة")]:
        if k in t_low:
            cat, sub = c, s
            break

    return {"schema_version": SCHEMA_VERSION, "ad_id": ad_id, "title": title, "url": url, "price_text": price_txt, "price_num": price_num, "deal": deal, "category": cat, "subtype": sub, "location": "القاهرة الجديدة", "area": area, "beds": "", "baths": "", "description": main_s.split("تم النشر بواسطة")[0].strip() or title, "seller_name": seller, "seller_profile": seller if seller != "مالك مباشر" else url, "seller_ads_count": cnt}

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
    for q_txt, deal, cat in QUERIES:
        time.sleep(2)
        for u, t, s in fetch_results(q_txt):
            if u in seen:
                continue
            item = parse_item(u, t, s, deal, cat, blocked)
            if item:
                seen.add(item["url"])
                item["scraped_timestamp"] = now_ts
                item["scraped_date"] = now_str
                new_ads.append(item)
    final = sorted(new_ads + old_ads, key=lambda x: x.get("ad_id", 0), reverse=True)
    owners = len({a["seller_profile"] for a in final})
    json.dump({"last_scrape": now_str, "total": len(final), "owners_count": owners, "blocked_count": len(blocked), "blocked_users": list(blocked), "ads": final}, open("ads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Done. Saved {len(final)} ads.")

if __name__ == "__main__":
    scrape_all()
# === END OF FILE ===
