import os, sys, re, json, time, random, stat, subprocess, threading, hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from DrissionPage import ChromiumPage, ChromiumOptions

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

AI_SERVER_URL = "https://gamal216.pythonanywhere.com"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ads.json")
SEEN_FILE = os.path.join(BASE_DIR, "seen_links_local.json")
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.json")
PROFILE_DIR = os.path.join(BASE_DIR, "chrome_clean_profile")

MAX_ADS_STORED = 450
MAX_CANDIDATES_PER_RUN = 120
MAX_WORKERS = 6
STATE_LOCK = threading.Lock()
BROWSER_LOCK = threading.Lock()

DUBIZZLE_SOURCES = [
    {"cat": "شقق", "deal": "إيجار", "en": "Apartments (Rent)", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/"},
    {"cat": "شقق", "deal": "تمليك", "en": "Apartments (Sale)", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/"},
    {"cat": "فلل", "deal": "إيجار", "en": "Villas (Rent)", "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/"},
    {"cat": "فلل", "deal": "تمليك", "en": "Villas (Sale)", "url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/"},
    {"cat": "تجاري", "deal": "إيجار", "en": "Commercial (Rent)", "url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/"},
    {"cat": "تجاري", "deal": "تمليك", "en": "Commercial (Sale)", "url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/"}
]

ZONE_MAPPING = {"النرجس": "النرجس", "نرجس": "النرجس", "الياسمين": "الياسمين", "ياسمين": "الياسمين", "البنفسج": "البنفسج", "بنفسج": "البنفسج", "اللوتس": "اللوتس", "لوتس": "اللوتس", "الأندلس": "الأندلس", "الاندلس": "الأندلس", "اندلس": "الأندلس", "القرنفل": "القرنفل", "قرنفل": "القرنفل", "تمر حنة": "التمر حنة", "التمر حنة": "التمر حنة", "جاردينيا": "جاردينيا", "جنوب الأكاديمية": "جنوب الأكاديمية", "جنوب الاكاديمية": "جنوب الأكاديمية", "شرق الأكاديمية": "شرق الأكاديمية", "شرق الاكاديمية": "شرق الأكاديمية", "المستثمرين": "المستثمرين", "الشويفات": "الشويفات", "شويفات": "الشويفات", "أبو الهول": "أبو الهول", "ابو الهول": "أبو الهول", "دار مصر": "دار مصر", "سكن مصر": "سكن مصر", "جنة": "جنة مصر", "القطامية": "القطامية", "قطامية": "القطامية", "التسعين": "شارع التسعين", "شارع التسعين": "شارع التسعين", "ميفيدا": "ميفيدا", "هايد بارك": "هايد بارك", "ماونتن فيو": "ماونتن فيو", "التجمع الأول": "التجمع الأول", "التجمع الاول": "التجمع الأول", "التجمع الثالث": "التجمع الثالث", "التجمع الخامس": "التجمع الخامس"}
FORBIDDEN_ZONES = ["الرحاب", "رحاب", "rehab", "مدينتي", "مدينتى", "madinaty", "المستقبل", "mostakbal", "سمات", "بيت الوطن", "بيت وطن", "beit al watan", "beit el watan", "bayt al watan", "النورث هاوس", "شمال الرحاب", "العبور", "الشروق", "مدينة بدر", "مدينه بدر", "هليوبوليس الجديدة", "العاصمة الإدارية", "العاصمه الاداريه", "العاشر من رمضان", "6 أكتوبر", "أكتوبر", "الشيخ زايد", "زايد", "المعادي", "زهراء المعادي", "المقطم", "الهضبة الوسطى", "مدينة نصر", "مصر الجديدة", "شيراتون", "النزهة", "عين شمس", "السلام", "جسر السويس", "حدائق القبة", "المرج", "شبرا", "حلوان", "15 مايو", "الزمالك", "المهندسين", "الدقي", "العجوزة", "الهرم", "فيصل", "حدائق الأهرام", "حدائق الاهرام", "حدائق أكتوبر", "الساحل الشمالي", "العين السخنة"]
INSTALLMENT_KEYWORDS = ["قسط", "تقسيط", "بالتقسيط", "أقساط", "اقساط", "تسهيلات", "فترة سداد", "سنوات سداد", "بمقدم", "مقدم", "دفعة", "دفعات", "متبقي", "المتبقي", "أوفر", "اوفر", "أوفر برايس", "down payment", "downpayment", "installment", "installments", "payment plan"]
CASH_NEGATIONS = ["بدون تقسيط", "لا يوجد تقسيط", "ممنوع التقسيط", "وليس تقسيط", "مش تقسيط", "بدون أقساط", "بدون اقساط", "خالص الثمن", "خالصة الثمن", "خالصه الثمن", "ليس عليها أقساط", "ليس عليها اقساط", "لا يوجد أقساط", "لا يوجد اقساط", "مسدد بالكامل", "مسددة بالكامل", "مسدده بالكامل", "غير متاح تقسيط", "البيع كاش فقط", "كاش فقط", "كاش ولا تقبل التمويل", "كاش نهائي"]
COMPANY_NAME_KEYWORDS = ["شركه", "عقارات", "تسويق", "مكتب", "استثمار", "تطوير", "جروب", "هوم", "هاوس", "بروكر", "ريال استيت", "real estate", "properties", "property", "broker", "brokers", "agency", "group", "developments", "investment", "hub", "home", "house", "egypt"]
HINDI_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def normalize_ar(text):
    if not text: return ""
    t = str(text).translate(HINDI_MAP).lower()
    t = re.sub(r'[\u0640\u064B-\u065F]', '', t)
    t = re.sub(r'[إأآا]', 'ا', t)
    t = re.sub(r'ة', 'ه', t)
    t = re.sub(r'ى', 'ي', t)
    return re.sub(r'\s+', ' ', t).strip()

def is_company_like_name(name):
    norm = normalize_ar(name)
    if not norm or norm == normalize_ar("مالك مباشر (دوبيزل)"):
        return False
    return any(normalize_ar(k) in norm for k in COMPANY_NAME_KEYWORDS)

def get_deterministic_ad_id(url, html=""):
    m_url = re.search(r'ID(\d{6,12})', url, re.I)
    if m_url:
        return f"dub_{m_url.group(1)}"
    if html:
        m_html = re.search(r'(?:رقم\s*الإعلان|رقم\s*الاعلان|Ad\s*ID)\s*[:\-]?\s*(\d{6,12})', html.translate(HINDI_MAP), re.I)
        if m_html:
            return f"dub_{m_html.group(1)}"
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:10]
    return f"dub_{h}"

def clean_publisher_name(name):
    if not name: return "مالك مباشر (دوبيزل)"
    s = re.sub(r'<[^>]+>', ' ', str(name))
    s = re.sub(r'(?:path\s+d=|M\d+\.\d+|viewBox|xmlns|svg|fill=)', ' ', s, flags=re.I)
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip(" -_|:,.")
    words = s.split()
    half = len(words) // 2
    if half >= 1 and len(words) % 2 == 0 and [w.lower() for w in words[:half]] == [w.lower() for w in words[half:]]:
        s = " ".join(words[:half])
    if not s or len(s) < 2 or len(s) > 55 or re.search(r'[<>{}\[\]=/\\]', s):
        return "مالك مباشر (دوبيزل)"
    return s

def detect_sub_zone(full_text):
    for key, official in ZONE_MAPPING.items():
        if normalize_ar(key) in normalize_ar(full_text):
            return official
    return "القاهرة الجديدة"

def extract_local_specs(main_text, combined_blob):
    area, rooms = None, None
    clean_t = main_text.translate(HINDI_MAP)
    m_area = re.search(r'(\d{2,5})\s*(?:م٢|م2|متر\s*مربع|متر|sqm|m2)\b', clean_t, re.I)
    if m_area and 25 <= int(m_area.group(1)) <= 10000:
        area = f"{m_area.group(1)} م²"
    else:
        m_aj = re.search(r'"(?:ft|area|size|surface)"\s*:\s*"?(\d{2,5})"?', combined_blob, re.I)
        if m_aj and 25 <= int(m_aj.group(1)) <= 10000:
            area = f"{m_aj.group(1)} م²"

    m_rooms = re.search(r'(\d{1,2})\s*(?:غرف\s*نوم|غرفه\s*نوم|غرف|غرفة|bedrooms|beds)\b', clean_t, re.I)
    if m_rooms and 1 <= int(m_rooms.group(1)) <= 20:
        rooms = f"{m_rooms.group(1)} غرف"
    else:
        m_rj = re.search(r'"(?:rooms|bedrooms|beds)"\s*:\s*"?(\d{1,2})"?', combined_blob, re.I)
        if m_rj and 1 <= int(m_rj.group(1)) <= 20:
            rooms = f"{m_rj.group(1)} غرف"
    return area, rooms

def is_forbidden_or_installment(title, desc, deal, price_num):
    raw_combined = re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', f"{title} {desc}")
    norm_text = normalize_ar(raw_combined)
    for idx, bad in enumerate(FORBIDDEN_ZONES):
        if normalize_ar(bad) in norm_text:
            return True, f"Forbidden Zone (#{idx+1})"
    if deal == "تمليك":
        if int(price_num or 0) < 1500000:
            return True, f"Invalid/Downpayment Price ({price_num})"
        temp = norm_text
        for neg in CASH_NEGATIONS:
            temp = temp.replace(normalize_ar(neg), " ")
        for inst in INSTALLMENT_KEYWORDS:
            if normalize_ar(inst) in temp:
                return True, "Installment Ad"
        if re.search(r'\b\d+\s*%\s*(مقدم|تعاقد|دفعه|down)', temp):
            return True, "Installment % Downpayment"
    return False, "OK"

def parse_price_strict(raw_val, deal="تمليك"):
    if not raw_val: return 0
    s = str(raw_val).translate(HINDI_MAP)
    for m in re.findall(r'\d[\d,]*', s):
        val = int(m.replace(',', ''))
        if deal == "إيجار" and 3000 <= val <= 1500000: return val
        if deal == "تمليك" and 1500000 <= val <= 600000000: return val
    return 0

def strip_related_ads_section(html):
    for marker in ["إعلانات مشابهة", "إعلانات ذات صلة", "Related ads", "Similar ads"]:
        idx = html.find(marker)
        if idx > 1500: return html[:idx]
    return html

def extract_dubizzle_links_from_html(html):
    links = []
    if not html: return links
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].split("#")[0].strip()
        if "/ad/" in href and len(href) > 15:
            full = href if href.startswith("http") else f"https://www.dubizzle.com.eg{href}"
            if full not in links: links.append(full)
    for m in re.findall(r'((?:https?://(?:www\.)?dubizzle\.com\.eg)?/[a-zA-Z0-9_\-/]+/ad/[^\s"\'<>]+)', html):
        clean_u = m.split("?")[0].split("#")[0].strip()
        full_u = clean_u if clean_u.startswith("http") else f"https://www.dubizzle.com.eg{clean_u}"
        if full_u not in links and len(full_u) > 30: links.append(full_u)
    return links

class SmartHybridEngine:
    def __init__(self):
        self.cookies = {}
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self._local = threading.local()
        self.page = None
        self.use_browser_fetch = False

    def get_worker_session(self):
        if not hasattr(self._local, "session"):
            try: s = cffi_requests.Session(impersonate="chrome120")
            except Exception: s = cffi_requests.Session(impersonate="chrome110")
            s.headers.update({
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.dubizzle.com.eg/",
            })
            if self.cookies: s.cookies.update(self.cookies)
            self._local.session = s
        return self._local.session

    def ensure_anchor_browser(self, test_url):
        if self.page is not None:
            return True
        try:
            os.makedirs(PROFILE_DIR, exist_ok=True)
            co = ChromiumOptions()
            for c in [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ]:
                if os.path.exists(c):
                    co.set_browser_path(c)
                    break
            co.set_paths(local_port=9555, user_data_path=PROFILE_DIR)
            co.no_imgs(True)
            co.mute(True)
            co.set_argument("--disable-blink-features=AutomationControlled")
            co.set_argument("--disable-extensions")
            self.page = ChromiumPage(addr_or_opts=co)
            cur_u = (self.page.url or "").lower()
            if "dubizzle.com.eg" not in cur_u:
                self.page.get(test_url, timeout=12)
                for _ in range(8):
                    time.sleep(1.0)
                    try:
                        t = self.page.run_js("return document.title || '';") or ""
                        if t and "Just a moment" not in t and len(t) > 3: break
                    except Exception: pass
            ua = self.page.run_js("return navigator.userAgent;")
            if ua: self.user_agent = ua
            for ck in (self.page.cookies() or []):
                if ck.get("name") and ck.get("value"):
                    self.cookies[ck["name"]] = ck["value"]
            return True
        except Exception as e:
            print(f"[Browser Port 9555 Error] {e}")
            return False

    def warmup(self):
        test_url = DUBIZZLE_SOURCES[0]["url"]
        html = self.cffi_fetch(test_url, is_warmup=True)
        if html and len(extract_dubizzle_links_from_html(html)) >= 5:
            print("[Engine] Pure curl_cffi connected directly! (0% Browser RAM)")
            return

        print("[Engine] Connecting to Chrome on port 9555 to sync Cloudflare clearance...")
        if self.ensure_anchor_browser(test_url):
            if hasattr(self._local, "session"): delattr(self._local, "session")
            html2 = self.cffi_fetch(test_url, is_warmup=True)
            if html2 and len(extract_dubizzle_links_from_html(html2)) >= 5:
                print("[Engine] curl_cffi verified with Chrome cookies! Closing Chrome completely (0% RAM)...")
                try:
                    self.page.quit()
                    self.page = None
                except Exception: pass
                return
            print("[Engine] Activated Zero-Navigation Background window.fetch() inside single anchor tab (port 9555)!")
            self.use_browser_fetch = True

    def cffi_fetch(self, url, is_warmup=False):
        if not is_warmup:
            time.sleep(random.uniform(0.5, 1.4))
        s = self.get_worker_session()
        for _ in range(2):
            try:
                r = s.get(url, timeout=15)
                if r.status_code == 200 and len(r.text) > 5000 and "Just a moment" not in r.text[:1500] and "/notfound" not in str(r.url):
                    return r.text
            except Exception:
                time.sleep(0.4)
        return ""

    def browser_background_fetch_single(self, url):
        time.sleep(random.uniform(0.4, 1.2))
        with BROWSER_LOCK:
            if not self.page:
                return ""
            js_code = """
            window.__single_done = false;
            window.__single_html = '';
            const targetUrl = arguments[0];
            (async () => {
                try {
                    const r = await fetch(targetUrl, {
                        method: 'GET',
                        credentials: 'include',
                        headers: {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
                    });
                    if (r.ok) {
                        window.__single_html = await r.text();
                    }
                } catch (e) {}
                window.__single_done = true;
            })();
            return true;
            """
            try:
                self.page.run_js(js_code, url)
                for _ in range(35):
                    time.sleep(0.25)
                    if self.page.run_js("return window.__single_done === true;"):
                        return self.page.run_js("return window.__single_html || '';") or ""
            except Exception:
                pass
        return ""

    def fetch_html(self, url, is_warmup=False):
        if not self.use_browser_fetch:
            h = self.cffi_fetch(url, is_warmup=is_warmup)
            if h:
                return h
        if self.page is not None or self.ensure_anchor_browser(DUBIZZLE_SOURCES[0]["url"]):
            self.use_browser_fetch = True
            return self.browser_background_fetch_single(url)
        return ""

    def get_category_links(self, url, label=""):
        html = self.fetch_html(url, is_warmup=False)
        links = extract_dubizzle_links_from_html(html)
        mode = "ZeroNav-Fetch" if self.use_browser_fetch else "cffi-Turbo"
        print(f"[{mode}] {label} -> {'200 OK' if links else 'Empty'} (Extracted {len(links)} ads)")
        return links

    def close(self):
        if self.page:
            try: self.page.quit()
            except Exception: pass

def extract_direct_ad_info(full_html, deal, blacklist):
    main_html = strip_related_ads_section(full_html)
    soup = BeautifulSoup(main_html, "html.parser")
    full_soup = BeautifulSoup(full_html, "html.parser")
    for tag in soup.find_all(["header", "nav", "footer"]): tag.decompose()

    h1 = soup.find("h1") or full_soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else ""
    if not title:
        og_t = full_soup.find("meta", {"property": "og:title"})
        title = og_t["content"].strip() if og_t and og_t.get("content") else ""
    title = re.sub(r'\s*\|\s*(?:دوبيزل|dubizzle).*$', '', title, flags=re.I).strip()
    if not title or len(title) < 4: return None, "Empty title", None

    desc = ""
    desc_el = soup.find(attrs={"aria-label": "Description"}) or soup.find("div", {"data-testid": "description"})
    if desc_el: desc = desc_el.get_text(" ", strip=True)
    if not desc:
        og_d = full_soup.find("meta", {"property": "og:description"}) or full_soup.find("meta", {"name": "description"})
        if og_d and og_d.get("content"): desc = og_d["content"].strip()

    price_num = 0
    for meta_sel in [{"property": "product:price:amount"}, {"property": "og:price:amount"}, {"name": "twitter:data1"}]:
        tag = full_soup.find("meta", meta_sel)
        if tag and tag.get("content"):
            price_num = parse_price_strict(tag.get("content"), deal)
            if price_num > 0: break
    if price_num == 0:
        price_el = soup.find(attrs={"aria-label": "Price"})
        if price_el: price_num = parse_price_strict(price_el.get_text(" ", strip=True), deal)
    if price_num == 0:
        clean_h = main_html.translate(HINDI_MAP)
        for pat in [r'"price"\s*:\s*"?(\d[\d,]*)"?', r'(?:EGP|ج\.?م|جنيه|LE)\s*(\d[\d,]{3,11})', r'(\d[\d,]{3,11})\s*(?:ج\.?م|جنيه|EGP|LE)']:
            m = re.search(pat, clean_h, re.I)
            if m:
                price_num = parse_price_strict(m.group(1), deal)
                if price_num > 0: break

    is_bad, bad_reason = is_forbidden_or_installment(title, desc, deal, price_num)
    if is_bad: return None, bad_reason, None

    main_text = soup.get_text(" ", strip=True)
    norm_main_text = normalize_ar(main_text)

    nd_script = full_soup.find("script", {"id": "__NEXT_DATA__"})
    if nd_script and nd_script.string:
        next_data_str = nd_script.string
    else:
        scripts_list = [s.string or "" for s in full_soup.find_all("script") if s.string and any(k in s.string for k in ("activeAds", "seller", "profile", "الإعلانات النشطة", "user"))]
        next_data_str = " ".join(scripts_list)[:200000]

    combined_blob = f"{next_data_str} {main_html}".translate(HINDI_MAP)
    seller_id, is_agency = "", False
    hrefs = [a["href"] for a in soup.find_all("a", href=True)]

    for h in hrefs:
        h_clean = str(h).split("?")[0].rstrip("/").strip()
        m_p = re.search(r'/(?:ar/|en/)?profile/([a-zA-Z0-9_-]{5,})', h_clean)
        if m_p:
            seller_id = f"prof_{m_p.group(1)}"
            break
    if not seller_id:
        m_p2 = re.search(r'/(?:ar/|en/)?profile/([a-zA-Z0-9_-]{5,})', combined_blob)
        if m_p2: seller_id = f"prof_{m_p2.group(1)}"
    if not seller_id:
        m_uid = re.search(r'"(?:sellerId|userId|externalID)"\s*:\s*"?([a-zA-Z0-9_-]{5,})"?', combined_blob)
        if m_uid: seller_id = f"uid_{m_uid.group(1)}"

    for h in hrefs:
        h_clean = str(h).split("?")[0].rstrip("/").strip()
        m_c = re.search(r'/(?:ar/|en/)?companies/([a-zA-Z0-9_-]{3,})', h_clean)
        if m_c and not h_clean.endswith("/companies"):
            seller_id = f"comp_{m_c.group(1)[:30]}"
            is_agency = True
            break

    pub_raw = ""
    m_pub_orig = re.search(
        r'(?:تم\s*النشر\s*بواسطة|تم\s*النشر\s*بواسطه|مدرج\s*من\s*قبل|listed\s*by|posted\s*by)\s*[:\-]?\s*(.+?)(?=\s*(?:عضو\s*منذ|الإعلانات\s*النشطة|الاعلانات\s*النشطه|إعلانات\s*نشطة|member\s*since|active\s*ads|رؤية\s*ملف|إظهار\s*الرقم|اظهار\s*الرقم|$))',
        main_text, re.I
    )
    if m_pub_orig: pub_raw = m_pub_orig.group(1).strip()
    if not pub_raw:
        m_seller = re.search(r'"sellerName"\s*:\s*"([^"]+)"', combined_blob) or re.search(r'"user"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', combined_blob)
        if m_seller: pub_raw = m_seller.group(1).strip()

    publisher_clean = clean_publisher_name(pub_raw)
    company_name_key = f"compname_{normalize_ar(publisher_clean)}" if is_company_like_name(publisher_clean) else ""
    safe_bl_key = seller_id or company_name_key or None

    with STATE_LOCK:
        in_bl = (seller_id and seller_id in blacklist) or (company_name_key and company_name_key in blacklist)
    if in_bl:
        return None, f"Blacklisted Broker ({safe_bl_key})", None

    if is_agency or re.search(r'(?:company\s*profile|verified\s*business|share\s*agency\s*profile|شركة\s*موثقة|مكتب\s*عقاري)', norm_main_text, re.I):
        return None, f"Agency Account ({publisher_clean})", safe_bl_key

    active_count, count_source = 0, ""

    for el in soup.find_all(string=re.compile(r'الإعلانات\s*النشطة|الاعلانات\s*النشطه|Active\s*ads', re.I)):
        for candidate_box in ([el.parent, el.parent.parent] if (el.parent and el.parent.parent) else [el.parent]):
            if not candidate_box: continue
            box_txt = normalize_ar(candidate_box.get_text(" ", strip=True))
            box_txt = re.sub(r'(?:عضو\s*منذ|member\s*since)\s*\d{4}', ' ', box_txt)
            nums = [int(x) for x in re.findall(r'\b(\d{1,5})\b', box_txt) if int(x) >= 1 and not (1990 <= int(x) <= 2030)]
            if nums:
                active_count = nums[0]
                count_source = f"DOM Box ({active_count} active ads)"
                break
        if active_count > 0:
            break

    if active_count == 0:
        m_after = re.search(r'(?:الاعلانات\s*النشطه|اعلانات\s*نشطه|active\s*ads)\s*[:\-]?\s*(\d{1,5})\b', norm_main_text, re.I)
        if m_after and int(m_after.group(1)) >= 1:
            active_count = int(m_after.group(1))
            count_source = f"Ad Page Badge ({active_count} active ads)"

    if active_count == 0:
        no_year_text = re.sub(r'(?:عضو\s*منذ|member\s*since)\s*\d{4}', ' ', norm_main_text, flags=re.I)
        m_before = re.search(r'\b(\d{1,4})\s*(?:الاعلانات\s*النشطه|اعلانات\s*نشطه|اعلان\s*نشط|active\s*ads)', no_year_text, re.I)
        if m_before and int(m_before.group(1)) >= 1:
            active_count = int(m_before.group(1))
            count_source = f"Ad Page Text ({active_count} active ads)"

    if active_count == 0:
        for pat in [r'"activeAdsCount"\s*:\s*(\d+)', r'"active_ads_count"\s*:\s*(\d+)', r'"activeAds"\s*:\s*(\d+)', r'"listedAdsCount"\s*:\s*(\d+)', r'"userAdsCount"\s*:\s*(\d+)', r'"adsCount"\s*:\s*(\d+)', r'"totalAds"\s*:\s*(\d+)']:
            m_j = re.search(pat, combined_blob)
            if m_j and int(m_j.group(1)) >= 1:
                active_count = int(m_j.group(1))
                count_source = f"__NEXT_DATA__ JSON ({active_count} active ads)"
                break

    if active_count >= 5:
        return None, f"Broker Count ({active_count} active ads > 4)", safe_bl_key
    if not (1 <= active_count <= 4):
        return None, "Unverified active ads count (0 found on ad page)", None

    local_area, local_rooms = extract_local_specs(main_text, combined_blob)
    return {
        "title": title, "desc": desc, "price_num": price_num,
        "publisher_clean": publisher_clean, "active_count": active_count,
        "count_source": count_source, "local_area": local_area, "local_rooms": local_rooms
    }, "OK", None

def inspect_ad_worker(item, engine, blacklist):
    url, cat, deal, en_label = item["url"], item["cat"], item["deal"], item["en"]
    html = engine.fetch_html(url, is_warmup=False)
    if not html:
        return {"url": url, "ad": None, "reason": "Failed to fetch ad HTML", "bl_key": None, "loaded": False}
    info, reason, bl_key = extract_direct_ad_info(html, deal, blacklist)
    if not info:
        return {"url": url, "ad": None, "reason": reason, "bl_key": bl_key, "loaded": True}

    title, desc, price_num = info["title"], info["desc"], info["price_num"]
    publisher_clean, active_count, count_source = info["publisher_clean"], info["active_count"], info["count_source"]
    ai_area, ai_rooms = info["local_area"], info["local_rooms"]

    try:
        r = requests.post(
            f"{AI_SERVER_URL}/analyze",
            json={"title": title, "description": desc, "publisher": publisher_clean, "deal": deal, "cat": cat, "price_num": price_num, "source": "دوبيزل", "active_ads_count": active_count, "dubizzle_strict_count_only": True},
            timeout=6
        )
        if r.status_code == 200:
            res = r.json()
            if res.get("decision") == "مرفوض":
                return {"url": url, "ad": None, "reason": "AI Rejected (Broker Pattern)", "bl_key": None, "loaded": True}
            if not ai_area and res.get("area"): ai_area = res.get("area")
            if not ai_rooms and res.get("rooms"): ai_rooms = res.get("rooms")
    except Exception:
        pass

    sub_zone = detect_sub_zone(f"{title} {desc}")
    ad_obj = {
        "id": get_deterministic_ad_id(url, html),
        "title": title, "link": url, "url": url,
        "price": f"{price_num:,} ج.م", "price_num": price_num,
        "cat": cat, "category": cat, "deal": deal, "type": deal,
        "zone": sub_zone, "location": sub_zone, "source": "دوبيزل",
        "publisher": f"{publisher_clean} ({active_count} إعلان نشط)",
        "active_ads_count": active_count, "area": ai_area, "rooms": ai_rooms,
        "description": desc[:500], "timestamp": int(time.time()),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    return {"url": url, "ad": ad_obj, "reason": f"Owner Verified ({count_source})", "bl_key": None, "loaded": True, "en": en_label}

def load_json_list(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, list): return d
        except Exception: pass
    return []

def safe_write_json(path, data):
    for _ in range(3):
        try:
            if os.path.exists(path):
                try: os.chmod(path, stat.S_IWRITE)
                except Exception: pass
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception: time.sleep(0.2)
    return False

def save_state(current_ads, seen_links, blacklist, push_to_github=False):
    with STATE_LOCK:
        final_ads = current_ads[:MAX_ADS_STORED]
        safe_write_json(DATA_FILE, final_ads)
        safe_write_json(SEEN_FILE, list(seen_links)[-6000:])
        safe_write_json(BLACKLIST_FILE, list(blacklist)[-6000:])
        if push_to_github:
            try:
                subprocess.run(["git", "add", "ads.json"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                subprocess.run(["git", "commit", "-m", "Instant Owner Update (Dubizzle 1-4 Active Ads)"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                res = subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                if res.returncode == 0:
                    print(f"    --> [LIVE SYNC] Pushed ads.json to GitHub & Website! (Total Owners: {len(final_ads)})")
                else:
                    print(f"    --> [LOCAL SAVE] Saved ads.json locally! (Total Owners: {len(final_ads)})")
            except Exception:
                print(f"    --> [LOCAL SAVE] Saved ads.json locally! (Total Owners: {len(final_ads)})")

def clean_existing_dubizzle_only_db(ads_list):
    cleaned, seen_u = [], set()
    for ad in ads_list:
        if not isinstance(ad, dict) or ad.get("source") != "دوبيزل": continue
        u = ad.get("link") or ad.get("url") or ""
        if not u or u in seen_u or "dubizzle.com.eg" not in u: continue
        cnt = int(ad.get("active_ads_count", 0) or 0)
        if not (1 <= cnt <= 4):
            m_c = re.search(r'\((\d+)\s*(?:إعلان|اعلان|عقار)', str(ad.get("publisher", "")))
            cnt = int(m_c.group(1)) if m_c else 0
            if not (1 <= cnt <= 4): continue
            ad["active_ads_count"] = cnt
        deal = ad.get("deal") or ad.get("type") or "تمليك"
        p_num = parse_price_strict(ad.get("price_num") or ad.get("price"), deal)
        bad, _ = is_forbidden_or_installment(ad.get("title", ""), ad.get("description", ""), deal, p_num)
        if bad: continue
        raw_p = re.sub(r'\(\d+.*?\)$', '', str(ad.get("publisher", ""))).strip()
        ad["publisher"] = f"{clean_publisher_name(raw_p)} ({cnt} إعلان نشط)"
        ad["price_num"], ad["price"] = p_num, f"{p_num:,} ج.م"
        seen_u.add(u)
        cleaned.append(ad)
    return cleaned

def main():
    print("=== Starting Smart Hybrid Parallel Dubizzle Radar (1-4 Active Ads | No Profile Visits) ===")
    raw_existing = load_json_list(DATA_FILE)
    current_ads = clean_existing_dubizzle_only_db(raw_existing)
    seen_links = set(load_json_list(SEEN_FILE))
    blacklist = {k for k in load_json_list(BLACKLIST_FILE) if not str(k).startswith("name_")}

    if len(raw_existing) - len(current_ads) > 0:
        print(f"[Purge] Removed {len(raw_existing) - len(current_ads)} non-compliant ads from ads.json")
        save_state(current_ads, seen_links, blacklist, push_to_github=True)

    existing_urls = {(a.get("link") or a.get("url")) for a in current_ads}
    engine = SmartHybridEngine()
    engine.warmup()

    candidates, candidate_urls = [], set()
    for page_num in (1, 2, 3):
        if len(candidates) >= MAX_CANDIDATES_PER_RUN: break
        for src in DUBIZZLE_SOURCES:
            if len(candidates) >= MAX_CANDIDATES_PER_RUN: break
            page_url = src["url"] if page_num == 1 else f"{src['url']}?page={page_num}"
            links = engine.get_category_links(page_url, label=f"{src['en']} p.{page_num}")
            for lnk in links:
                if lnk not in existing_urls and lnk not in seen_links and lnk not in candidate_urls:
                    candidate_urls.add(lnk)
                    candidates.append({"url": lnk, "cat": src["cat"], "deal": src["deal"], "en": src["en"]})
                    if len(candidates) >= MAX_CANDIDATES_PER_RUN: break

    total_cand = len(candidates)
    print(f"\n[Parallel Inspector] Launching ThreadPoolExecutor (max_workers={MAX_WORKERS}) for {total_cand} new ads...")
    total_added, completed_idx = 0, 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(inspect_ad_worker, item, engine, blacklist) for item in candidates]
        for fut in as_completed(futures):
            completed_idx += 1
            try: res = fut.result()
            except Exception as e:
                print(f"  [{completed_idx}/{total_cand}] [ERROR] Worker exception: {e}")
                continue
            u = res["url"]
            if res.get("loaded"):
                with STATE_LOCK: seen_links.add(u)
            if res.get("bl_key"):
                with STATE_LOCK: blacklist.add(res["bl_key"])
            ad_obj = res.get("ad")
            if ad_obj:
                with STATE_LOCK:
                    current_ads.insert(0, ad_obj)
                    existing_urls.add(u)
                    total_added += 1
                print(f"  [{completed_idx}/{total_cand}] [+ ACCEPTED OWNER] {res.get('en')} | {ad_obj['publisher']} | Price: {ad_obj['price_num']:,} EGP")
                save_state(current_ads, seen_links, blacklist, push_to_github=(total_added % 5 == 0))
            else:
                print(f"  [{completed_idx}/{total_cand}] [- REJECTED] {res.get('reason')}")
                if completed_idx % 20 == 0:
                    save_state(current_ads, seen_links, blacklist, push_to_github=False)

    engine.close()
    save_state(current_ads, seen_links, blacklist, push_to_github=(total_added > 0))
    print(f"\n=== Run Complete: Added ({total_added}) New Owners | Total Owners in DB: ({len(current_ads)}) | Blacklisted Brokers: ({len(blacklist)}) ===")

if __name__ == "__main__":
    main()
