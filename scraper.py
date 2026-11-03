import json, time, re, os
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
import requests, cloudscraper
from bs4 import BeautifulSoup

SCHEMA_VERSION = 16
SEVEN_DAYS = 7 * 24 * 3600

QUERIES = [
    ("ID2093 شقة للايجار التجمع الخامس ج.م", "إيجار", "شقق"),
    ("ID2093 شقة للبيع التجمع الخامس ج.م", "بيع", "شقق"),
    ("ID2093 القاهرة الجديدة ج.م", "بيع", "شقق"),
    ("ID2093 الرحاب مدينتي ج.م", "بيع", "شقق"),
    ("ID2092 شقة للايجار التجمع الخامس ج.م", "إيجار", "شقق"),
    ("ID2092 شقة للبيع التجمع الخامس ج.م", "بيع", "شقق"),
    ("ID2092 القاهرة الجديدة الرحاب مدينتي ج.م", "بيع", "شقق"),
    ("ID2093 دوبلكس بنتهاوس فيلا التجمع ج.م", "بيع", "فيلا"),
    ("ID2092 دوبلكس بنتهاوس فيلا التجمع ج.م", "بيع", "فيلا"),
    ("ID2093 مكتب محل عيادة استوديو التجمع ج.م", "إيجار", "تجاري وإداري"),
    ("شقة للايجار التجمع الخامس من المالك ج.م", "إيجار", "شقق"),
    ("شقة للبيع التجمع الخامس من المالك ج.م", "بيع", "شقق"),
    ("فيلا تاون هاوس التجمع الخامس من المالك ج.م", "بيع", "فيلا"),
    ("شقة الرحاب مدينتي من المالك ج.م", "إيجار", "شقق")
]

NC_PLACES = ["التجمع", "القاهرة الجديدة", "القاهره الجديده", "الرحاب", "مدينتي", "مدينتى", "النرجس", "اللوتس", "الياسمين", "البنفسج", "الشويفات", "الأندلس", "الاندلس", "بيت الوطن", "الأكاديمية", "المستثمرين", "القطامية", "ميفيدا", "هايد بارك", "ماونتن فيو", "بالم هيلز", "سراي", "التسعين", "القرنفل", "تاج سيتي", "جاردينيا", "دار مصر", "سكن مصر", "جنة", "الباتيو", "المراسم", "لاروزا", "new cairo", "5th settlement", "rehab", "madinaty"]
BAD_CITIES = ["العبور", "لوران", "سموحة", "الإسكندرية", "الاسكندرية", "أكتوبر", "اكتوبر", "زايد", "الشروق", "بدر", "المعادي", "مدينة نصر", "مصر الجديدة", "النزهة", "المقطم", "الهرم", "فيصل", "الدقي", "المهندسين", "حلوان", "شبرا", "الساحل", "السخنة", "الغردقة", "طنطا", "المنصورة", "العاصمة الإدارية"]
BAD_SELLERS = ["real estate", "properties", "property", "investment", "development", "consultancy", "agency", "broker", "group", "homes", "aqar", "للتسويق", "للاستثمار", "للتنمية", "للتطوير", "شركة", "el rabeh", "go homes", "quality square", "بانوراما"]
OLD_OR_GONE = ["لم يتم العثور على تطابقات", "قد تم بيعه أو إزالته", "تم بيعه أو إزالته", "هذا الإعلان غير متاح", "منذ 2 أسابيع", "منذ 3 أسابيع", "منذ 4 أسابيع", "منذ أسبوعين", "منذ شهر", "منذ أشهر", "بمقدم", "دفعة الأولى", "دفعه اولى", "أقساط على", "كود الوحدة", "**"]

SCRAPER = cloudscraper.create_scraper()

def fetch_yahoo(q_text):
    items = []
    q_full = f"site:dubizzle.com.eg/ad/ {q_text}"
    try:
        uh = SCRAPER.get("https://search.yahoo.com/search", params={"p": q_full, "n": "30"}, timeout=20)
        if uh.status_code == 200:
            soup = BeautifulSoup(uh.text, "html.parser")
            for div in soup.select("div.algo, div.Sr"):
                a = div.find("a", href=True)
                if not a:
                    continue
                href = a["href"]
                if "RU=" in href:
                    href = unquote(href.split("RU=")[1].split("/RK=")[0])
                h3 = div.find("h3")
                t = h3.get_text(" ", strip=True) if h3 else a.get_text(" ", strip=True)
                p = div.find("div", class_=re.compile(r"compText|fc-falcon"))
                s = p.get_text(" ", strip=True) if p else ""
                items.append((href, t, s))
    except Exception:
        pass
    return items

def fetch_price_for_id(ad_id, url):
    try:
        uh = SCRAPER.get("https://search.yahoo.com/search", params={"p": f'site:dubizzle.com.eg/ad/ "{ad_id}" "ج.م"', "n": "5"}, timeout=12)
        if uh.status_code == 200:
            txt = BeautifulSoup(uh.text, "html.parser").get_text(" ", strip=True)
            txt = txt.split("الإبلاغ عن هذا الإعلان")[0]
            m = re.search(r"([\d,]{4,12})\s*(?:ج\.م|جنيه|EGP)", txt) or re.search(r"(?:السعر|ج\.م|EGP)\s*([\d,]{4,12})", txt)
            if m and m.group(1).replace(",", "").isdigit():
                v = int(m.group(1).replace(",", ""))
                if v >= 2000:
                    return f"{v:,} ج.م", v
    except Exception:
        pass
    try:
        jr = requests.get(f"https://r.jina.ai/{url}", timeout=10)
        if jr.status_code == 200 and len(jr.text) > 400:
            if any(g in jr.text for g in ["لم يتم العثور على تطابقات", "قد تم بيعه أو إزالته"]):
                return "DEAD", 0
            top = jr.text.split("الإبلاغ عن هذا الإعلان")[0].split("الاتجاهات والمؤشرات")[0]
            m = re.search(r"([\d,]{4,12})\s*(?:ج\.م|جنيه|EGP)", top) or re.search(r"(?:ج\.م|EGP)\s*([\d,]{4,12})", top)
            if m and m.group(1).replace(",", "").isdigit():
                v = int(m.group(1).replace(",", ""))
                if v >= 2000:
                    return f"{v:,} ج.م", v
    except Exception:
        pass
    return "موضح داخل الإعلان", 1

def clean_title_text(raw_t):
    t = re.sub(r"^.*?https?://[^\s]+(?:\s*›\s*[^\s]+)*\s*", "", raw_t)
    t = re.sub(r"^دوبيزل\s*", "", t)
    t = re.sub(r"\s*[-|]\s*(?:شقق|فلل|عقار|دوبيزل|dubizzle).*$", "", t, flags=re.I)
    return t.strip()

def parse_item(url, raw_t, raw_s, def_deal, def_cat, blocked):
    url = url.split("?")[0]
    if "dubizzle.com.eg" not in url or "/ad/" not in url or "/companies/" in url:
        return None
    main_s = raw_s.split("الإبلاغ عن هذا الإعلان")[0].split("قم بالإبلاغ عن هذا الإعلان")[0]
    if main_s.count(";") >= 2 and "ج.م" in main_s:
        main_s = " ".join([p for p in main_s.split(";") if "ج.م" not in p])

    title = clean_title_text(raw_t)
    comb = f"{title} {main_s}".lower()
    if any(g in comb for g in OLD_OR_GONE) or any(b in title.lower() for b in BAD_CITIES):
        return None
    if not any(n in comb for n in NC_PLACES):
        return None

    m_id = re.search(r"-ID(\d+)", url, re.I) or re.search(r"رقم الإعلان\s*(\d+)", main_s) or re.search(r"\b(209\d{6})\b", comb)
    if not m_id:
        return None
    ad_id = int(m_id.group(1))
    if ad_id < 209050000 or ad_id >= 400000000:
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
    m_p = re.search(r"([\d,]{4,12})\s*(?:ج\.م|جنيه|EGP)", comb, re.I) or re.search(r"(?:السعر|ج\.م|EGP)\s*[:：]?\s*([\d,]{4,12})", comb, re.I)
    if m_p and m_p.group(1).replace(",", "").isdigit() and int(m_p.group(1).replace(",", "")) >= 2000:
        price_num = int(m_p.group(1).replace(",", ""))
        price_txt = f"{price_num:,} ج.م"
    else:
        p_txt, p_num = fetch_price_for_id(ad_id, url)
        if p_txt == "DEAD":
            return None
        price_txt, price_num = p_txt, p_num

    m_ar = re.search(r"المساحة\s*\(?م[٢2²]?\)?\s*[:：]?\s*(\d{2,4})", comb, re.I) or re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢|م\b)", comb, re.I)
    area = (m_ar.group(1) + " م²") if m_ar else "مدرج بالإعلان"
    m_bd = re.search(r"(?:غرف نوم|غرف)\s*[:：]?\s*(\d+)", comb) or re.search(r"(\d+)\s*(?:غرف|غرفة)", comb)
    beds = (m_bd.group(1) + " غرف") if m_bd else ""

    t_low = comb
    deal = "إيجار" if any(w in t_low for w in ["للايجار", "للإيجار", "ايجار", "إيجار", "مفروش"]) else ("بيع" if any(w in t_low for w in ["للبيع", "بيع", "تمليك"]) else def_deal)
    cat, sub = def_cat, ("شقة" if def_cat == "شقق" else def_cat)
    for k, c, s in [("مكتب", "تجاري وإداري", "تجاري وإداري"), ("محل", "تجاري وإداري", "تجاري وإداري"), ("عيادة", "تجاري وإداري", "تجاري وإداري"), ("بنتهاوس", "شقق", "بنتهاوس"), ("دوبلكس", "شقق", "دوبلكس"), ("استوديو", "شقق", "استوديو"), ("فيلا", "فيلا", "فيلا"), ("تاون", "فيلا", "فيلا"), ("توين", "فيلا", "فيلا"), ("شقة", "شقق", "شقة")]:
        if k in title.lower() or k in main_s.lower():
            cat, sub = c, s
            break

    return {"schema_version": SCHEMA_VERSION, "ad_id": ad_id, "title": title, "url": url, "price_text": price_txt, "price_num": price_num, "deal": deal, "category": cat, "subtype": sub, "location": "القاهرة الجديدة", "area": area, "beds": beds, "baths": "", "description": main_s.split("تم النشر بواسطة")[0].strip() or title, "seller_name": seller, "seller_profile": seller if seller != "مالك مباشر" else url, "seller_ads_count": cnt}

def scrape_all():
    now_ts = int(time.time())
    now_str = datetime.now(timezone(timedelta(hours=2))).strftime("%Y/%m/%d، %I:%M %p")
    old_ads, blocked = [], set()
    if os.path.exists("ads.json"):
        try:
            d = json.load(open("ads.json", "r", encoding="utf-8"))
            old_ads = [a for a in d.get("ads", []) if a.get("schema_version") == SCHEMA_VERSION and (now_ts - a.get("scraped_timestamp", now_ts)) < SEVEN_DAYS and 209050000 <= a.get("ad_id", 0) < 400000000]
            blocked = set(d.get("blocked_users", []))
        except Exception:
            pass
    seen = {a["url"] for a in old_ads}
    seen_ids = {a["ad_id"] for a in old_ads}
    new_ads = []
    for q_txt, deal, cat in QUERIES:
        time.sleep(1)
        for u, t, s in fetch_yahoo(q_txt):
            u_clean = u.split("?")[0]
            if u_clean in seen:
                continue
            item = parse_item(u_clean, t, s, deal, cat, blocked)
            if item and item["ad_id"] not in seen_ids:
                seen.add(item["url"])
                seen_ids.add(item["ad_id"])
                item["scraped_timestamp"] = now_ts
                item["scraped_date"] = now_str
                new_ads.append(item)
    final = sorted(new_ads + old_ads, key=lambda x: x.get("ad_id", 0), reverse=True)
    owners = len({a["seller_profile"] for a in final})
    json.dump({"last_scrape": now_str, "total": len(final), "owners_count": owners, "blocked_count": len(blocked), "blocked_users": list(blocked), "ads": final}, open("ads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Done. Saved {len(final)} active ID209 owner ads.")

if __name__ == "__main__":
    scrape_all()
# === END OF FILE ===
