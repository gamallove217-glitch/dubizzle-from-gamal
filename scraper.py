import json, time, re, os
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
import requests
from curl_cffi import requests as creq
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

SCHEMA_VERSION = 24
SEVEN_DAYS = 7 * 24 * 3600

QUERIES = [
    ("شقة للايجار التجمع الخامس من المالك", "إيجار", "شقق"),
    ("شقة للبيع التجمع الخامس من المالك", "بيع", "شقق"),
    ("شقة للايجار التجمع الخامس", "إيجار", "شقق"),
    ("شقة للبيع التجمع الخامس", "بيع", "شقق"),
    ("شقة للايجار القاهرة الجديدة من المالك", "إيجار", "شقق"),
    ("شقة للبيع القاهرة الجديدة من المالك", "بيع", "شقق"),
    ("شقة مفروشة للايجار التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار النرجس التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار اللوتس التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار الياسمين البنفسج التجمع الخامس", "إيجار", "شقق"),
    ("شقة للايجار جاردينيا دار مصر سكن مصر التجمع", "إيجار", "شقق"),
    ("شقة للايجار الأندلس المستثمرين القطامية التجمع", "إيجار", "شقق"),
    ("شقة للبيع النرجس اللوتس الياسمين التجمع", "بيع", "شقق"),
    ("شقة للبيع البنفسج الأندلس بيت الوطن التجمع", "بيع", "شقق"),
    ("شقة للبيع جاردينيا دار مصر سكن مصر التجمع", "بيع", "شقق"),
    ("شقة للايجار الرحاب", "إيجار", "شقق"),
    ("شقة للبيع الرحاب", "بيع", "شقق"),
    ("شقة للايجار مدينتي", "إيجار", "شقق"),
    ("شقة للبيع مدينتي", "بيع", "شقق"),
    ("دوبلكس التجمع الخامس", "بيع", "شقق"),
    ("بنتهاوس روف التجمع الخامس", "بيع", "شقق"),
    ("استوديو غرفة للايجار التجمع الخامس", "إيجار", "شقق"),
    ("فيلا تاون هاوس للايجار التجمع الخامس", "إيجار", "فيلا"),
    ("فيلا تاون هاوس للبيع التجمع الخامس", "بيع", "فيلا"),
    ("مكتب اداري للايجار التجمع الخامس", "إيجار", "تجاري وإداري"),
    ("محل عيادة التجمع الخامس الرحاب مدينتي", "إيجار", "تجاري وإداري")
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

def jina_get(url):
    for attempt in range(2):
        try:
            r3 = requests.get(f"https://r.jina.ai/{url}", timeout=18)
            if r3.status_code == 429:
                print("Jina rate limit hit, cooling down 22s...")
                time.sleep(22)
                continue
            if r3.status_code == 200 and len(r3.text) > 500:
                if "dubizzle.com.eg/motors)" in r3.text:
                    return ""
                m_t = re.search(r"^Title:\s*(.+)$", r3.text, re.M)
                t_hdr = f"TITLE_HDR: {m_t.group(1).strip()} | " if m_t else ""
                cleaned = clean_markdown_to_text(r3.text)
                if "تم النشر بواسطة" in cleaned:
                    return t_hdr + cleaned
            return ""
        except Exception:
            time.sleep(3)
    return ""

def discover_candidates():
    cands = []
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
        time.sleep(0.5)
    return cands

def inspect_and_parse(url, raw_t, fallback_s, def_deal, def_cat, blocked):
    raw_s = jina_get(url)
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
    seen_ids, seen_urls = set(), set()
    if os.path.exists("ads.json"):
        try:
            d = json.load(open("ads.json", "r", encoding="utf-8"))
            for a in d.get("ads", []):
                aid = a.get("ad_id", 0)
                if a.get("schema_version") == SCHEMA_VERSION and (now_ts - a.get("scraped_timestamp", now_ts)) < SEVEN_DAYS and aid < 500000000 and aid not in seen_ids:
                    old_ads.append(a)
                    seen_ids.add(aid)
                    seen_urls.add(a.get("url", ""))
            blocked = set(d.get("blocked_users", []))
        except Exception:
            pass

    cands = discover_candidates()
    print(f"Total raw candidates: {len(cands)}")
    new_ads = []
    inspected = 0
    for u, t, s, deal, cat in cands:
        if inspected >= 95:
            break
        u_clean = u.split("?")[0]
        if "dubizzle.com.eg/ad/" not in u_clean or "/companies/" in u_clean or u_clean in seen_urls:
            continue
        m_uid = re.search(r"-ID(\d+)", u_clean, re.I)
        uid = int(m_uid.group(1)) if m_uid else 0
        if uid >= 500000000 or (uid and uid in seen_ids):
            continue
        pre_txt = (t + " " + s).lower()
        if any(b in t.lower() for b in BAD_CITIES) or any(g in pre_txt for g in GONE_WORDS):
            continue
        m_pre_cnt = re.search(r"(?:ال)?[إأآا]علانات\s*(?:ال)?نشط[ةه]\s*[:：]?\s*(\d+)", pre_txt)
        if m_pre_cnt and int(m_pre_cnt.group(1)) > 4:
            continue

        seen_urls.add(u_clean)
        if uid:
            seen_ids.add(uid)
        inspected += 1
        item = inspect_and_parse(u_clean, t, s, deal, cat, blocked)
        if item and item["ad_id"] not in {x["ad_id"] for x in new_ads + old_ads}:
            item["scraped_timestamp"] = now_ts
            item["scraped_date"] = now_str
            new_ads.append(item)
            print(f"[{inspected}] Added: {item['title']} | {item['price_text']} | {item['seller_name']}")
        time.sleep(3.5)

    final = sorted(new_ads + old_ads, key=lambda x: x.get("ad_id", 0), reverse=True)
    owners = len({a["seller_profile"] for a in final})
    json.dump({"last_scrape": now_str, "total": len(final), "owners_count": owners, "blocked_count": len(blocked), "blocked_users": list(blocked), "ads": final}, open("ads.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Done. Saved {len(final)} unique ads.")

if __name__ == "__main__":
    scrape_all()
# === END OF FILE ===
