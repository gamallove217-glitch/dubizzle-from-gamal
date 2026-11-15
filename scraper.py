import os, sys, re, json, time, random
from datetime import datetime
import requests
from bs4 import BeautifulSoup

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from DrissionPage import ChromiumPage, ChromiumOptions
    HAS_DRISSION = True
except ImportError:
    HAS_DRISSION = False

AI_SERVER_URL = "https://gamal216.pythonanywhere.com"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ads.json")
SEEN_FILE = os.path.join(BASE_DIR, "seen_links.json")
PROFILE_DIR = os.path.join(BASE_DIR, "edge_profile")
MAX_ADS_STORED = 450
MAX_CANDIDATES_PER_RUN = 80

DUBIZZLE_SOURCES = [
    {"cat": "شقق", "deal": "إيجار", "en": "Apartments (Rent)", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo-fifth-settlement/"},
    {"cat": "فلل", "deal": "إيجار", "en": "Villas (Rent)", "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo-fifth-settlement/"},
    {"cat": "تجاري", "deal": "إيجار", "en": "Commercial (Rent)", "url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo-fifth-settlement/"},
    {"cat": "شقق", "deal": "تمليك", "en": "Apartments (Sale)", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo-fifth-settlement/"},
    {"cat": "فلل", "deal": "تمليك", "en": "Villas (Sale)", "url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo-fifth-settlement/"},
    {"cat": "تجاري", "deal": "تمليك", "en": "Commercial (Sale)", "url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo-fifth-settlement/"},
    {"cat": "أراضي", "deal": "تمليك", "en": "Lands (Sale)", "url": "https://www.dubizzle.com.eg/properties/land-for-sale/new-cairo-fifth-settlement/"}
]

ZONE_MAPPING = {
    "النرجس": "النرجس", "نرجس": "النرجس", "الياسمين": "الياسمين", "ياسمين": "الياسمين",
    "البنفسج": "البنفسج", "بنفسج": "البنفسج", "اللوتس": "اللوتس", "لوتس": "اللوتس",
    "الأندلس": "الأندلس", "الاندلس": "الأندلس", "اندلس": "الأندلس", "القرنفل": "القرنفل",
    "قرنفل": "القرنفل", "تمر حنة": "التمر حنة", "التمر حنة": "التمر حنة", "جاردينيا": "جاردينيا",
    "جنوب الأكاديمية": "جنوب الأكاديمية", "جنوب الاكاديمية": "جنوب الأكاديمية",
    "شرق الأكاديمية": "شرق الأكاديمية", "شرق الاكاديمية": "شرق الأكاديمية",
    "المستثمرين": "المستثمرين", "الشويفات": "الشويفات", "شويفات": "الشويفات",
    "أبو الهول": "أبو الهول", "ابو الهول": "أبو الهول", "دار مصر": "دار مصر",
    "سكن مصر": "سكن مصر", "جنة": "جنة مصر", "القطامية": "القطامية", "قطامية": "القطامية",
    "التسعين": "شارع التسعين", "شارع التسعين": "شارع التسعين", "ميفيدا": "ميفيدا",
    "هايد بارك": "هايد بارك", "ماونتن فيو": "ماونتن فيو", "التجمع الأول": "التجمع الأول",
    "التجمع الاول": "التجمع الأول", "التجمع الثالث": "التجمع الثالث", "التجمع الخامس": "التجمع الخامس"
}

FORBIDDEN_ZONES = [
    "الرحاب", "رحاب", "rehab", "مدينتي", "مدينتى", "madinaty", "المستقبل", "mostakbal", "سمات",
    "بيت الوطن", "بيت وطن", "beit al watan", "beit el watan", "bayt al watan", "النورث هاوس", "شمال الرحاب",
    "العبور", "الشروق", "مدينة بدر", "مدينه بدر", "هليوبوليس الجديدة", "العاصمة الإدارية", "العاصمه الاداريه",
    "العاشر من رمضان", "6 أكتوبر", "أكتوبر", "الشيخ زايد", "زايد", "المعادي", "زهراء المعادي", "المقطم",
    "الهضبة الوسطى", "مدينة نصر", "مصر الجديدة", "شيراتون", "النزهة", "عين شمس", "السلام", "جسر السويس",
    "حدائق القبة", "المرج", "شبرا", "حلوان", "15 مايو", "الزمالك", "المهندسين", "الدقي", "العجوزة",
    "الهرم", "فيصل", "حدائق الأهرام", "حدائق الاهرام", "حدائق أكتوبر", "الساحل الشمالي", "العين السخنة"
]

INSTALLMENT_KEYWORDS = [
    "قسط", "تقسيط", "بالتقسيط", "أقساط", "اقساط", "تسهيلات", "فترة سداد", "سنوات سداد",
    "بمقدم", "مقدم", "دفعة", "دفعات", "متبقي", "المتبقي", "أوفر", "اوفر", "أوفر برايس",
    "down payment", "downpayment", "installment", "installments", "payment plan"
]

CASH_NEGATIONS = [
    "بدون تقسيط", "لا يوجد تقسيط", "ممنوع التقسيط", "وليس تقسيط", "مش تقسيط", "بدون أقساط", "بدون اقساط",
    "خالص الثمن", "خالصة الثمن", "خالصه الثمن", "ليس عليها أقساط", "ليس عليها اقساط", "لا يوجد أقساط",
    "لا يوجد اقساط", "مسدد بالكامل", "مسددة بالكامل", "مسدده بالكامل", "غير متاح تقسيط", "البيع كاش فقط",
    "كاش فقط", "كاش ولا تقبل التمويل", "كاش نهائي"
]

HINDI_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def normalize_ar(text):
    if not text:
        return ""
    t = str(text).translate(HINDI_MAP).lower()
    t = re.sub(r'[\u0640\u064B-\u065F]', '', t)
    t = re.sub(r'[إأآا]', 'ا', t)
    t = re.sub(r'ة', 'ه', t)
    t = re.sub(r'ى', 'ي', t)
    return re.sub(r'\s+', ' ', t).strip()

def clean_publisher_name(name):
    if not name:
        return "مالك مباشر (دوبيزل)"
    s = re.sub(r'<[^>]+>', ' ', str(name))
    s = re.sub(r'(?:path\s+d=|M\d+\.\d+|viewBox|xmlns|svg|fill=)', ' ', s, flags=re.I)
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip(" -_|:,.")
    if not s or len(s) < 2 or len(s) > 55 or re.search(r'[<>{}\[\]=/\\]', s):
        return "مالك مباشر (دوبيزل)"
    return s

def detect_sub_zone(full_text):
    for key, official in ZONE_MAPPING.items():
        if normalize_ar(key) in normalize_ar(full_text):
            return official
    return "القاهرة الجديدة"

def is_forbidden_or_installment(title, desc, deal, price_num):
    raw_combined = re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', f"{title} {desc}")
    norm_text = normalize_ar(raw_combined)
    for bad in FORBIDDEN_ZONES:
        if normalize_ar(bad) in norm_text:
            return True, f"Forbidden Zone ({bad})"
    if deal == "تمليك":
        if int(price_num or 0) < 1500000:
            return True, f"Invalid/Downpayment Price ({price_num})"
        temp = norm_text
        for neg in CASH_NEGATIONS:
            temp = temp.replace(normalize_ar(neg), " ")
        for inst in INSTALLMENT_KEYWORDS:
            if normalize_ar(inst) in temp:
                return True, f"Installment Ad ({inst})"
        if re.search(r'\b\d+\s*%\s*(مقدم|تعاقد|دفعه|down)', temp):
            return True, "Installment % Downpayment"
    return False, "OK"

def parse_price_strict(raw_val, deal="تمليك"):
    if not raw_val:
        return 0
    s = str(raw_val).translate(HINDI_MAP)
    m_all = re.findall(r'\d[\d,]*', s)
    for m in m_all:
        val = int(m.replace(',', ''))
        if deal == "إيجار" and 3000 <= val <= 1500000:
            return val
        if deal == "تمليك" and 1500000 <= val <= 600000000:
            return val
    return 0

def extract_price_from_meta_and_html(soup, html_text, deal="تمليك"):
    for meta_sel in [
        {"property": "product:price:amount"},
        {"property": "og:price:amount"},
        {"name": "twitter:data1"}
    ]:
        tag = soup.find("meta", meta_sel)
        if tag and tag.get("content"):
            p = parse_price_strict(tag.get("content"), deal)
            if p > 0:
                return p
    for script in soup.find_all("script", type="application/ld+json"):
        if script.string:
            m = re.search(r'"price"\s*:\s*"?(\d[\d,]*)"?', script.string)
            if m:
                p = parse_price_strict(m.group(1), deal)
                if p > 0:
                    return p
    for meta_desc in [{"property": "og:title"}, {"property": "og:description"}, {"name": "description"}]:
        tag = soup.find("meta", meta_desc)
        if tag and tag.get("content"):
            m_egp = re.search(r'(\d[\d,]{3,11})\s*(?:ج\.?م|جنيه|EGP|LE)', tag.get("content").translate(HINDI_MAP), re.I)
            if m_egp:
                p = parse_price_strict(m_egp.group(1), deal)
                if p > 0:
                    return p
    price_el = soup.find(attrs={"aria-label": "Price"})
    if price_el:
        p = parse_price_strict(price_el.get_text(" ", strip=True), deal)
        if p > 0:
            return p
    clean_html = html_text.translate(HINDI_MAP)
    for pat in [r'"price"\s*:\s*(\d{4,10})', r'(\d[\d,]{4,11})\s*(?:ج\.?م|جنيه|EGP)']:
        m = re.search(pat, clean_html, re.I)
        if m:
            p = parse_price_strict(m.group(1), deal)
            if p > 0:
                return p
    return 0

class RealBrowserEngine:
    def __init__(self):
        self.page = None

    def find_windows_browser(self):
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def start(self):
        if self.page is not None:
            return True
        if not HAS_DRISSION:
            print("[ERROR] DrissionPage is missing! Run: pip install DrissionPage")
            return False
        try:
            os.makedirs(PROFILE_DIR, exist_ok=True)
            co = ChromiumOptions()
            b_path = self.find_windows_browser()
            if b_path:
                co.set_browser_path(b_path)
                print(f"[Browser] Using: {b_path}")
            co.set_paths(local_port=9333, user_data_path=PROFILE_DIR)
            co.no_imgs(True)
            co.mute(True)
            co.set_argument("--disable-blink-features=AutomationControlled")
            self.page = ChromiumPage(addr_or_opts=co)
            return True
        except Exception as e:
            print(f"[Browser Start Error] {e}")
            return False

    def fetch_page(self, url, label=""):
        if not self.start():
            return ""
        try:
            self.page.get(url, retry=1, interval=1, timeout=25)
            time.sleep(1.5)
            html = self.page.html or ""
            for wait_step in range(8):
                if ("Just a moment" in html[:2500] or "Checking your browser" in html[:2500] or len(html) < 3500):
                    if wait_step == 0 and label:
                        print("  [Cloudflare Check] Waiting a few seconds for browser verification...")
                    time.sleep(2.5)
                    html = self.page.html or ""
                else:
                    break
            if len(html) > 4000 and "Just a moment" not in html[:1500]:
                return html
            if label:
                print(f"[Dubizzle Local] {label} -> Blocked or Empty (len={len(html)})")
            return ""
        except Exception as e:
            if label:
                print(f"[Dubizzle Local] {label} -> Fetch Error: {e}")
            return ""

    def close(self):
        try:
            if self.page:
                self.page.quit()
        except Exception:
            pass

def extract_dubizzle_links(html):
    links = []
    if not html:
        return links
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].strip()
        if "/ad/" in href and ("-ID" in href or href.endswith(".html")):
            full = href if href.startswith("http") else f"https://www.dubizzle.com.eg{href}"
            if full not in links:
                links.append(full)
    for m in re.findall(r'(https?://(?:www\.)?dubizzle\.com\.eg/[^\s"\'<>]+/ad/[^\s"\'<>]+-ID\d+\.html)', html):
        clean_u = m.split("?")[0]
        if clean_u not in links:
            links.append(clean_u)
    return links

def extract_profile_url(soup, html):
    for a in soup.find_all("a", href=True):
        h = a["href"].strip()
        if "/profile/" in h or "/companies/" in h:
            return h if h.startswith("http") else f"https://www.dubizzle.com.eg{h}"
    m = re.search(r'(https?://(?:www\.)?dubizzle\.com\.eg/(?:ar/|en/)?(?:profile|companies)/[^\s"\'<>]+)', html)
    if m:
        return m.group(1)
    m2 = re.search(r'"(\/(?:ar\/|en\/)?(?:profile|companies)\/[^"\'<>]+)"', html)
    if m2:
        return f"https://www.dubizzle.com.eg{m2.group(1)}"
    return ""

def count_dubizzle_active_ads(ad_html, ad_soup, profile_url, engine):
    if "/companies/" in str(profile_url).lower():
        return 99, "Company Account (/companies/)"
    raw_ad_text = ad_soup.get_text(" ", strip=True).translate(HINDI_MAP)
    if re.search(r'(?:company\s*profile|verified\s*business|share\s*agency\s*profile|شركة\s*موثقة|مكتب\s*عقاري)', raw_ad_text, re.I):
        return 99, "Agency/Company Account"
    for pat in [
        r'"activeAdsCount"\s*:\s*(\d+)',
        r'"totalAds"\s*:\s*(\d+)',
        r'"adsCount"\s*:\s*(\d+)',
        r'"listedAdsCount"\s*:\s*(\d+)'
    ]:
        m = re.search(pat, ad_html)
        if m:
            c = int(m.group(1))
            if c >= 1:
                return c, f"Ad JSON ({c} active ads)"
    m_txt = re.search(r'(?:Active\s*Ads\s*(\d+)|(\d+)\s*(?:إعلانات\s*نشطة|إعلان\s*نشط|اعلانات\s*نشطه|اعلان\s*نشط|active\s*ads|published\s*ads|ads\s*posted))', raw_ad_text, re.I)
    if m_txt:
        c = int(m_txt.group(1) or m_txt.group(2))
        if c >= 1:
            return c, f"Seller Badge ({c} active ads)"
    if not profile_url:
        return 0, "No profile URL found"
    prof_html = engine.fetch_page(profile_url)
    if not prof_html or len(prof_html) < 2000:
        return 0, "Could not load seller profile"
    prof_soup = BeautifulSoup(prof_html, "html.parser")
    prof_text = prof_soup.get_text(" ", strip=True).translate(HINDI_MAP)
    for pat in [
        r'"activeAdsCount"\s*:\s*(\d+)',
        r'"totalAds"\s*:\s*(\d+)',
        r'"adsCount"\s*:\s*(\d+)',
        r'"total"\s*:\s*(\d+)'
    ]:
        m = re.search(pat, prof_html)
        if m and int(m.group(1)) >= 1:
            c = int(m.group(1))
            return c, f"Profile JSON ({c} active ads)"
    m_p = re.search(r'(?:Showing|عرض)?\s*(?:\d+\s*[-–]\s*\d+\s*(?:of|من)\s*)?(\d+)\s*(?:إعلانات|إعلان|اعلانات|اعلان|Ads|ad|results|نتيجة)', prof_text, re.I)
    if m_p and int(m_p.group(1)) >= 1:
        c = int(m_p.group(1))
        return c, f"Profile Counter ({c} active ads)"
    ad_cards = extract_dubizzle_links(prof_html)
    if len(ad_cards) >= 1:
        return len(ad_cards), f"Profile Cards ({len(ad_cards)} active ads)"
    return 0, "Unverified ad count"

def parse_dubizzle_ad(url, cat, deal, engine):
    html = engine.fetch_page(url)
    if not html or len(html) < 2500:
        return None, "Failed to load ad page"
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""
    if not title:
        og_t = soup.find("meta", {"property": "og:title"})
        title = og_t["content"].strip() if og_t and og_t.get("content") else ""
    title = re.sub(r'\s*\|\s*(?:دوبيزل|dubizzle).*$', '', title, flags=re.I).strip()
    if not title or len(title) < 5:
        return None, "Empty title"
    desc = ""
    desc_el = soup.find(attrs={"aria-label": "Description"}) or soup.find("div", {"data-testid": "description"})
    if desc_el:
        desc = desc_el.get_text(" ", strip=True)
    if not desc:
        og_d = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
        if og_d and og_d.get("content"):
            desc = og_d["content"].strip()
    price_num = extract_price_from_meta_and_html(soup, html, deal)
    is_bad, bad_reason = is_forbidden_or_installment(title, desc, deal, price_num)
    if is_bad:
        return None, bad_reason
    prof_url = extract_profile_url(soup, html)
    active_count, count_info = count_dubizzle_active_ads(html, soup, prof_url, engine)
    if not (1 <= active_count <= 4):
        return None, f"Broker/Count Rule (1-4): {count_info}"
    pub_raw = "مالك مباشر (دوبيزل)"
    m_seller = re.search(r'"sellerName"\s*:\s*"([^"]+)"', html) or re.search(r'"user"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', html)
    if m_seller:
        pub_raw = m_seller.group(1).strip()
    publisher_clean = clean_publisher_name(pub_raw)
    ai_area, ai_rooms = None, None
    try:
        r = requests.post(
            f"{AI_SERVER_URL}/analyze",
            json={
                "title": title, "description": desc, "publisher": publisher_clean,
                "deal": deal, "cat": cat, "price_num": price_num,
                "source": "دوبيزل", "active_ads_count": active_count,
                "dubizzle_strict_count_only": True
            },
            timeout=10
        )
        if r.status_code == 200:
            res = r.json()
            if res.get("decision") == "مرفوض":
                return None, f"AI Rejected ({res.get('reason', '')})"
            ai_area = res.get("area")
            ai_rooms = res.get("rooms")
    except Exception:
        pass
    sub_zone = detect_sub_zone(f"{title} {desc}")
    price_formatted = f"{price_num:,} ج.م"
    return {
        "id": f"dub_{abs(hash(url)) % 1000000000}",
        "title": title,
        "link": url,
        "url": url,
        "price": price_formatted,
        "price_num": price_num,
        "cat": cat,
        "category": cat,
        "deal": deal,
        "type": deal,
        "zone": sub_zone,
        "location": sub_zone,
        "source": "دوبيزل",
        "publisher": f"{publisher_clean} ({active_count} إعلان نشط)",
        "active_ads_count": active_count,
        "area": ai_area,
        "rooms": ai_rooms,
        "description": desc[:500],
        "timestamp": int(time.time()),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }, f"Owner Verified ({count_info})"

def load_json_list(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []

def clean_existing_dubizzle_only_db(ads_list):
    cleaned = []
    seen_u = set()
    for ad in ads_list:
        if not isinstance(ad, dict):
            continue
        if ad.get("source") != "دوبيزل":
            continue
        u = ad.get("link") or ad.get("url") or ""
        if not u or u in seen_u or "dubizzle.com.eg" not in u:
            continue
        cnt = int(ad.get("active_ads_count", 0) or 0)
        if not (1 <= cnt <= 4):
            m_c = re.search(r'\((\d+)\s*(?:إعلان|اعلان|عقار)', str(ad.get("publisher", "")))
            cnt = int(m_c.group(1)) if m_c else 0
            if not (1 <= cnt <= 4):
                continue
            ad["active_ads_count"] = cnt
        deal = ad.get("deal") or ad.get("type") or "تمليك"
        p_num = parse_price_strict(ad.get("price_num") or ad.get("price"), deal)
        bad, _ = is_forbidden_or_installment(ad.get("title", ""), ad.get("description", ""), deal, p_num)
        if bad:
            continue
        raw_p = re.sub(r'\(\d+.*?\)$', '', str(ad.get("publisher", ""))).strip()
        ad["publisher"] = f"{clean_publisher_name(raw_p)} ({cnt} إعلان نشط)"
        ad["price_num"] = p_num
        ad["price"] = f"{p_num:,} ج.م"
        seen_u.add(u)
        cleaned.append(ad)
    return cleaned

def main():
    print("=== Starting Local Dubizzle Radar (Edge Browser - 1 to 4 Active Ads Only) ===")
    raw_existing = load_json_list(DATA_FILE)
    existing_ads = clean_existing_dubizzle_only_db(raw_existing)
    purged_count = len(raw_existing) - len(existing_ads)
    if purged_count > 0:
        print(f"[Purge] Removed {purged_count} polluted/non-Dubizzle ads from ads.json")
    existing_urls = {(a.get("link") or a.get("url")) for a in existing_ads}
    seen_links = set(load_json_list(SEEN_FILE))
    engine = RealBrowserEngine()
    candidates = []
    for page_num in (1, 2, 3):
        for src in DUBIZZLE_SOURCES:
            page_url = src["url"] if page_num == 1 else f"{src['url']}?page={page_num}"
            label = f"{src['en']} p.{page_num}"
            html = engine.fetch_page(page_url, label=label)
            links = extract_dubizzle_links(html)
            if html:
                print(f"[Dubizzle Local] {label} -> 200 OK (Extracted {len(links)} ads)")
            for lnk in links:
                if lnk not in existing_urls and lnk not in seen_links:
                    if not any(c["url"] == lnk for c in candidates):
                        candidates.append({"url": lnk, "cat": src["cat"], "deal": src["deal"], "en": src["en"]})
            time.sleep(random.uniform(1.0, 1.8))
    print(f"[Dubizzle Local] Total new candidates to inspect: {len(candidates)}")
    added_ads = []
    for idx, item in enumerate(candidates[:MAX_CANDIDATES_PER_RUN], 1):
        u = item["url"]
        seen_links.add(u)
        ad_obj, status_msg = parse_dubizzle_ad(u, item["cat"], item["deal"], engine)
        if ad_obj:
            added_ads.append(ad_obj)
            existing_urls.add(u)
            print(f"  [{idx}] [+ ACCEPTED OWNER] {item['en']} | Active Ads: {ad_obj['active_ads_count']} | Price: {ad_obj['price_num']:,} EGP")
        else:
            print(f"  [{idx}] [- REJECTED] {status_msg}")
        time.sleep(random.uniform(1.0, 1.8))
    engine.close()
    final_ads = (added_ads + existing_ads)[:MAX_ADS_STORED]
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(final_ads, f, ensure_ascii=False, indent=2)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen_links)[-4000:], f, ensure_ascii=False)
    print(f"=== Run Complete: Added ({len(added_ads)}) New Owners | Total Verified Owners in DB: ({len(final_ads)}) ===")

if __name__ == "__main__":
    main()
