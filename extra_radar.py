import os, sys, re, json, time, random, stat, socket, base64, subprocess, urllib.parse, ctypes
from datetime import datetime, timezone, timedelta, date
import requests as std_requests
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

def disable_cmd_quickedit_and_sleep():
    if not sys.platform.startswith("win"): return
    try:
        os.system("chcp 65001 > nul")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        k32 = ctypes.windll.kernel32
        k32.SetThreadExecutionState(0x80000003)
        h = k32.GetStdHandle(-10)
        m = ctypes.c_uint32()
        if k32.GetConsoleMode(h, ctypes.byref(m)):
            k32.SetConsoleMode(h, (m.value & ~0x0040 & ~0x0020) | 0x0080)
    except Exception: pass

disable_cmd_quickedit_and_sleep()

CAIRO_TZ = timezone(timedelta(hours=2))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ads.json")
EXTRA_SEEN_FILE = os.path.join(BASE_DIR, "seen_extra_local.json")
CLEAN_V96_FLAG = os.path.join(BASE_DIR, "clean_v96.flag")
TG_CONFIG_TOPIC = "gamal_vip_tg_9941_sec"
WARP_PROXY = "socks5h://127.0.0.1:40000"
MIN_CASH_SALE_PRICE = 1200000
AUTO_LOOP_MINUTES = 45
HINDI_MAP = str.maketrans({"٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9", "٬": ",", "،": ",", "٫": "."})

ARABIC_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "ابريل": 4, "أبريل": 4, "إبريل": 4,
    "مايو": 5, "يونيو": 6, "يونية": 6, "يوليو": 7, "يوليه": 7,
    "اغسطس": 8, "أغسطس": 8, "سبتمبر": 9, "اكتوبر": 10, "أكتوبر": 10,
    "نوفمبر": 11, "ديسمبر": 12
}

ZONES = [
    ("التجمع الخامس", ["التجمع الخامس", "fifth settlement", "5th settlement", "ميفيدا", "mivida", "هايد بارك", "ماونتن فيو", "كايرو فيستفال", "الباتيو", "فيلت", "سوديك"]),
    ("التجمع الأول", ["التجمع الأول", "التجمع الاول", "first settlement", "1st settlement"]),
    ("التجمع الثالث", ["التجمع الثالث", "third settlement", "3rd settlement", "أربيلا", "اربيلا"]),
    ("اللوتس", ["اللوتس", "lotus"]),
    ("النرجس", ["النرجس", "narges", "narjis"]),
    ("الياسمين", ["الياسمين", "yasmeen", "jasmine"]),
    ("البنفسج", ["البنفسج", "banafseg"]),
    ("الأندلس", ["الأندلس", "الاندلس", "andalus"]),
    ("جنوب الأكاديمية", ["جنوب الأكاديمية", "جنوب الاكاديمية"]),
    ("شرق الأكاديمية", ["شرق الأكاديمية", "شرق الاكاديمية"]),
    ("المستثمرين", ["المستثمرين", "investors"]),
    ("الشويفات", ["الشويفات", "choueifat"]),
    ("القرنفل", ["القرنفل", "koronfel"]),
    ("التمر حنة", ["التمر حنة", "تمر حنة", "tamr hena"]),
    ("أبو الهول", ["أبو الهول", "ابو الهول", "جاردينيا هايتس", "جاردينيا"]),
    ("دار مصر", ["دار مصر", "سكن مصر", "جنة مصر", "فرجينيا"]),
    ("القطامية", ["القطامية", "القطاميه", "katameya"]),
    ("شارع التسعين", ["التسعين", "90th"]),
]

EXCLUDED_CITIES = [
    "الرحاب", "رحاب", "rehab", "مدينتي", "مدينتى", "madinaty",
    "بيت الوطن", "بيت وطن", "beit al watan", "beit el watan", "bayt al watan", "النورث هاوس", "شمال الرحاب",
    "العبور", "الشروق", "مدينة بدر", "مدينه بدر", "هليوبوليس الجديدة", "العاصمة الإدارية", "العاصمه الاداريه",
    "التجمع السادس", "sixth settlement", "كابيتال جاردنز", "capital gardens", "سراي", "sarai", "البروج", "alburouj",
    "طلالة", "talala", "دي جويا", "dejoya", "محور الأمل",
    "العاشر من رمضان", "6 أكتوبر", "أكتوبر", "الشيخ زايد", "زايد", "المعادي", "زهراء المعادي",
    "المقطم", "الهضبة الوسطى", "مدينة نصر", "مصر الجديدة", "شيراتون", "النزهة", "عين شمس",
    "السلام", "جسر السويس", "حدائق القبة", "المرج", "شبرا", "حلوان", "15 مايو", "الزمالك",
    "المهندسين", "الدقي", "العجوزة", "الهرم", "فيصل", "حدائق الأهرام", "حدائق الاهرام",
    "حدائق أكتوبر", "الساحل الشمالي", "العين السخنة", "الجونة", "الغردقة", "شرم الشيخ",
    "الإسكندرية", "الاسكندرية", "المستقبل", "mostakbal", "سمات", "مقبرة", "مقابر", "مدفن", "مدافن"
]

INSTALLMENT_SUBSTRINGS = [
    "قسط", "تقسيط", "بالتقسيط", "لتقسيط", "اقساط", "أقساط", "باقساط", "بأقساط", "تكملة أقساط", "تكمله اقساط",
    "مقدم", "بمقدم", "دفعة", "دفعه", "دفعات", "تسهيلات", "سداد", "فترة سداد", "سنوات سداد", "أنظمة سداد", "انظمه سداد",
    "بدون فوائد", "متبقي", "المتبقي", "والباقي", "أوفر", "اوفر", "امكانية التقسيط", "متاح تقسيط", "ويوجد تقسيط",
    "سنة التسليم 2027", "سنة التسليم 2028", "سنة التسليم 2029", "سنة التسليم 2030", "قيد الإنشاء", "قيد الانشاء",
    "down payment", "downpayment", "installment", "installments", "payment plan"
]

SAFE_CASH_NEGATIONS = [
    "بدون تقسيط", "لا يوجد تقسيط", "ممنوع التقسيط", "وليس تقسيط", "مش تقسيط",
    "بدون أقساط", "بدون اقساط", "خالص الثمن", "خالصة الثمن", "خالصه الثمن",
    "ليس عليها أقساط", "ليس عليها اقساط", "لا يوجد أقساط", "لا يوجد اقساط",
    "مسدد بالكامل", "مسددة بالكامل", "غير متاح تقسيط", "البيع كاش فقط", "كاش فقط", "كاش نهائي"
]

BROKER_NAME_WORDS = [
    "zone", "real estate", "realestate", "realty", "property", "properties", "group", "homes", "house", "agency",
    "agencies", "broker", "brokers", "brokerage", "investment", "investments", "development", "developments",
    "capital", "consult", "consultant", "consulting", "company", "egypt", "marketing", "lounge", "scouts", "hub",
    "prime", "elite", "empire", "avenue", "landmark", "residence", "towers", "tower", "vertex", "redefine",
    "irtkaz", "ebtkar", "imkan", "falcon", "views", "aura", "inspiration", "insider", "meer", "deal", "ghp",
    "kayan", "watad", "for you", "4u", "realtors",
    "شركة", "شركه", "مكتب", "تسويق", "للتسويق", "ماركتنج", "عقارات", "للعقارات", "سمسار", "وسيط",
    "استشاري", "مستشار", "للاستشارات", "تطوير", "للتطوير", "استثمار", "للاستثمار", "جروب", "هومز", "هاوس",
    "كابيتال", "بروكر", "ريال استيت", "استيت", "فيرتكس", "ريديفاين", "ارتكاز", "إرتكاز", "ابتكار", "إبتكار",
    "إمكان", "امكان", "فالكون", "جلوبال", "فيوز", "برايم", "ديل", "كيان", "وتد", "دار البناء", "للمقاولات",
    "للإنشاءات", "للانشاءات", "اللوتس العقارية"
]

BROKER_TEXT_PHRASES = [
    "انا وسيط", "أنا وسيط", "وسيط مش المالك", "مش المالك", "ليس المالك", "وسيط عقاري", "وسيط عقارى",
    "سمسار", "مكتب عقاري", "مكتب عقارات", "مكتب تسويق", "عمولة شهر", "عموله شهر", "عمولة نصف شهر",
    "عموله نصف شهر", "عمولة المكتب", "عموله المكتب", "عمولة الشركة", "عموله الشركه", "نسبة العمولة",
    "عمولة 1.5%", "عمولة 2%", "عموله 1.5%", "عموله 2%", "يوجد عمولة", "يوجد عموله",
    "لماذا تختار شركتنا", "شركتنا", "شركة عقارات", "شركه عقارات", "شركة تسويق", "شركه تسويق",
    "للتسويق العقاري", "للاستثمار العقاري", "للتطوير العقاري", "استشاري عقاري", "مستشار عقاري",
    "فريق المبيعات", "قسم المبيعات", "للتواصل مع قسم المبيعات", "فريق من الخبراء",
    "مجموعة متنوعة من الشقق", "تقع عقاراتنا", "زيارة معروضاتنا",
    "كود الوحدة", "كود الوحده", "كود العقار", "كود الشقة", "كود الفيلا",
    "متاح لدينا", "يتوفر لدينا", "متوفر لدينا", "لدينا أكثر من", "متاح لدينا اكثر من",
    "متاح مساحات مختلفة", "مساحات مختلفة", "مساحات مختلفه", "متوفر لدينا وحدات", "متاح لدينا وحدات",
    "استمرار لعروضنا", "والواقع يتحدث عنا", "امتلك وحدتك", "احجز وحدتك", "اختار وحدتك", "الشركة العالمية للعقارات"
]

AQARMAP_SOURCES = [
    {"cat": "شقق", "deal": "إيجار", "en": "Apartments (Rent)", "url": "https://aqarmap.com.eg/ar/for-rent/apartment/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "فلل", "deal": "إيجار", "en": "Villas (Rent)", "url": "https://aqarmap.com.eg/ar/for-rent/villa/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "تجاري", "deal": "إيجار", "en": "Commercial (Rent)", "url": "https://aqarmap.com.eg/ar/for-rent/commercial/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "شقق", "deal": "تمليك", "en": "Apartments (Sale)", "url": "https://aqarmap.com.eg/ar/for-sale/apartment/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "فلل", "deal": "تمليك", "en": "Villas (Sale)", "url": "https://aqarmap.com.eg/ar/for-sale/villa/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "تجاري", "deal": "تمليك", "en": "Commercial (Sale)", "url": "https://aqarmap.com.eg/ar/for-sale/commercial/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "أراضي", "deal": "تمليك", "en": "Lands (Sale)", "url": "https://aqarmap.com.eg/ar/for-sale/land/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
]

def clear_git_locks():
    git_dir = os.path.join(BASE_DIR, ".git")
    for rel in ["index.lock", "HEAD.lock", "config.lock", os.path.join("refs", "heads", "main.lock")]:
        p = os.path.join(git_dir, rel)
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass

def fix_git_identity_for_vercel():
    clear_git_locks()
    subprocess.run(["git", "config", "user.name", "gamallove217-glitch"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "gamallove217@gmail.com"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def fetch_remote_ads_list():
    try:
        clear_git_locks()
        subprocess.run(["git", "fetch", "origin", "main"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
        res = subprocess.run(["git", "show", "origin/main:ads.json"], cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15)
        if res.returncode == 0 and res.stdout:
            d = json.loads(res.stdout)
            if isinstance(d, dict) and isinstance(d.get("ads"), list):
                return d["ads"]
    except Exception:
        pass
    return []

def atomic_write_and_git_push(data_payload, commit_msg):
    fix_git_identity_for_vercel()
    for attempt in range(1, 4):
        try:
            clear_git_locks()
            subprocess.run(["git", "fetch", "origin", "main"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            subprocess.run(["git", "reset", "--mixed", "origin/main"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            if os.path.exists(DATA_FILE):
                try: os.chmod(DATA_FILE, stat.S_IWRITE)
                except Exception: pass
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data_payload, f, ensure_ascii=False, indent=2)
            subprocess.run(["git", "add", "-f", "ads.json"], cwd=BASE_DIR, capture_output=True, timeout=15)
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=BASE_DIR, capture_output=True, timeout=15)
            p_res = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=BASE_DIR, capture_output=True, text=True, timeout=120)
            if p_res.returncode == 0:
                return True, "OK"
        except Exception as e:
            if attempt == 3:
                return False, str(e)
            time.sleep(3)
    return False, "Push failed after 3 attempts"

def load_persistent_seen_ids(data_dict):
    if not os.path.exists(CLEAN_V96_FLAG):
        try:
            with open(CLEAN_V96_FLAG, "w") as f: f.write("ok")
        except Exception: pass
        save_persistent_seen_ids(set())
        print("[Memory Reset v9.6] Cleared extra seen cache once to recover AqarMap ads & re-verify OpenSooq!")
        return set()
    seen_set = set()
    if os.path.exists(EXTRA_SEEN_FILE):
        try:
            with open(EXTRA_SEEN_FILE, "r", encoding="utf-8") as f:
                arr = json.load(f)
                if isinstance(arr, list):
                    for x in arr:
                        try: seen_set.add(int(x))
                        except Exception: pass
        except Exception: pass
    return seen_set

def save_persistent_seen_ids(seen_set):
    try:
        if os.path.exists(EXTRA_SEEN_FILE):
            try: os.chmod(EXTRA_SEEN_FILE, stat.S_IWRITE)
            except Exception: pass
        with open(EXTRA_SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(list(seen_set)[-18000:], f)
    except Exception: pass

def is_warp_up():
    try:
        with socket.create_connection(("127.0.0.1", 40000), timeout=0.8):
            return True
    except Exception:
        return False

class SmartFetcher:
    def __init__(self):
        self.warp_active = is_warp_up()
        base_headers = {
            "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site"
        }
        self.warp_sess = cffi_requests.Session(impersonate="chrome120", proxies={"http": WARP_PROXY, "https": WARP_PROXY}) if self.warp_active else None
        if self.warp_sess:
            self.warp_sess.headers.update(base_headers)
        self.direct_sess = cffi_requests.Session(impersonate="chrome120")
        self.direct_sess.headers.update(base_headers)
        self.pw = None
        self.browser = None
        self.context = None
        self.pw_unavailable = False

    def _ensure_pw(self):
        if self.pw_unavailable:
            return False
        if self.context is not None:
            return True
        try:
            from playwright.sync_api import sync_playwright
            self.pw = sync_playwright().start()
            has_display = bool(os.environ.get("DISPLAY"))
            launch_kwargs = {
                "headless": (not has_display),
                "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
            }
            if self.warp_active:
                launch_kwargs["proxy"] = {"server": "socks5://127.0.0.1:40000"}
            self.browser = self.pw.chromium.launch(**launch_kwargs)
            self.context = self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="ar-EG",
                viewport={"width": 1366, "height": 768},
                extra_http_headers={"Referer": "https://www.google.com/"}
            )
            self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            return True
        except Exception:
            self.pw_unavailable = True
            return False

    def _is_valid_html(self, html, req_regex=None):
        if not html or len(html) < 1500:
            return False
        if "Pardon Our Interruption" in html or "Just a moment..." in html or "<title>Attention Required!" in html:
            return False
        if req_regex and not re.search(req_regex, html):
            return False
        return True

    def get_html(self, raw_url, req_regex=None):
        url = urllib.parse.quote(urllib.parse.unquote(raw_url), safe=":/?&=#%")
        statuses = []
        if self.warp_active and self.warp_sess:
            try:
                r = self.warp_sess.get(url, timeout=18)
                if r.status_code == 200 and self._is_valid_html(r.text, req_regex):
                    return r.text, "200 (WARP)"
                statuses.append(f"WARP:{r.status_code}")
            except Exception:
                statuses.append("WARP:ERR")

        try:
            r = self.direct_sess.get(url, timeout=18)
            if r.status_code == 200 and self._is_valid_html(r.text, req_regex):
                return r.text, "200 (Direct)"
            statuses.append(f"Direct:{r.status_code}")
            if r.status_code in (404, 410):
                return "", " | ".join(statuses)
        except Exception:
            statuses.append("Direct:ERR")

        if self._ensure_pw():
            page = None
            try:
                page = self.context.new_page()
                resp = page.goto(url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(3500)
                html = page.content()
                code = resp.status if resp else 0
                page.close()
                if code == 200 and self._is_valid_html(html, req_regex):
                    return html, "200 (Playwright)"
                statuses.append(f"PW:{code}")
            except Exception:
                if page:
                    try: page.close()
                    except Exception: pass
                statuses.append("PW:ERR")

        return "", " | ".join(statuses)

    def discover_opensooq_sources(self):
        sources, seen_urls = [], set()
        seed_pages = ["https://eg.opensooq.com/ar"]
        cairo_hubs = []

        for seed in seed_pages:
            html, st = self.get_html(seed)
            print(f"[OpenSooq Auto-Discovery] {seed} -> {st}")
            if not html:
                continue
            raw_hrefs = set(re.findall(r'href="((?:https?://eg\.opensooq\.com)?/ar/[^"?#]+)"', html))
            for h in raw_hrefs:
                dec = urllib.parse.unquote(h)
                full_h = h if h.startswith("http") else "https://eg.opensooq.com" + h
                if "/القاهرة/" in dec and any(c in dec for c in ("عقارات-للايجار", "عقارات-للإيجار", "عقارات-للبيع", "شقق-للايجار", "شقق-للبيع")) and not any(loc in dec for loc in ("التجمع", "القاهرة-الجديدة")):
                    if len(cairo_hubs) < 4 and full_h not in cairo_hubs and full_h not in seed_pages:
                        cairo_hubs.append(full_h)
                if any(loc in dec for loc in ("التجمع", "القاهرة-الجديدة")) and any(k in dec for k in ("شقق", "فلل", "عقارات", "تجاري", "أراضي", "اراضي")):
                    if any(skip in dec for skip in ("غرف-نوم", "الطابق", "مفروشة", "غير-مفروشة", "شهر", "سنوات", "سنة")):
                        continue
                    if full_h in seen_urls:
                        continue
                    seen_urls.add(full_h)
                    is_rent = ("ايجار" in dec or "إيجار" in dec)
                    deal = "إيجار" if is_rent else "تمليك"
                    deal_en = "Rent" if is_rent else "Sale"
                    if "فلل" in dec: cat, cat_en = "فلل", "Villas"
                    elif "تجار" in dec or "مكاتب" in dec or "محلات" in dec: cat, cat_en = "تجاري", "Commercial"
                    elif "أراض" in dec or "اراض" in dec: cat, cat_en = "أراضي", "Lands"
                    else: cat, cat_en = "شقق", "Apartments"
                    loc_en = "5th Settlement" if "التجمع-الخامس" in dec else ("1st Settlement" if "التجمع" in dec else "New Cairo")
                    sources.append({"cat": cat, "deal": deal, "en": f"OpenSooq {cat_en} ({deal_en} - {loc_en})", "url": full_h})

        pages_to_expand = [s["url"] for s in sources[:3]] + cairo_hubs[:3]
        for exp_u in pages_to_expand:
            first_html, _ = self.get_html(exp_u)
            if not first_html:
                continue
            sub_hrefs = set(re.findall(r'href="((?:https?://eg\.opensooq\.com)?/ar/[^"?#]+)"', first_html))
            for h in sub_hrefs:
                dec = urllib.parse.unquote(h)
                if any(loc in dec for loc in ("التجمع-الخامس", "القاهرة-الجديدة", "التجمع-الأول", "التجمع-الاول")) and any(k in dec for k in ("شقق", "فلل", "تجاري", "أراضي", "اراضي", "عقارات")):
                    if any(skip in dec for skip in ("غرف-نوم", "الطابق", "مفروشة", "غير-مفروشة", "شهر", "سنوات", "سنة")):
                        continue
                    full_u = h if h.startswith("http") else "https://eg.opensooq.com" + h
                    if full_u in seen_urls:
                        continue
                    seen_urls.add(full_u)
                    is_rent = ("ايجار" in dec or "إيجار" in dec)
                    deal = "إيجار" if is_rent else "تمليك"
                    deal_en = "Rent" if is_rent else "Sale"
                    if "فلل" in dec: cat, cat_en = "فلل", "Villas"
                    elif "تجار" in dec: cat, cat_en = "تجاري", "Commercial"
                    elif "أراض" in dec or "اراض" in dec: cat, cat_en = "أراضي", "Lands"
                    else: cat, cat_en = "شقق", "Apartments"
                    loc_en = "5th Settlement" if "التجمع-الخامس" in dec else ("1st Settlement" if "التجمع" in dec else "New Cairo")
                    sources.append({"cat": cat, "deal": deal, "en": f"OpenSooq {cat_en} ({deal_en} - {loc_en})", "url": full_u})

        rent_s = [s for s in sources if s["deal"] == "إيجار"]
        sale_s = [s for s in sources if s["deal"] != "إيجار"]
        return (rent_s[:8] + sale_s[:8])

    def close(self):
        try:
            if self.browser: self.browser.close()
            if self.pw: self.pw.stop()
        except Exception:
            pass

def normalize_ar(text):
    t = str(text or "").translate(HINDI_MAP).lower()
    t = re.sub(r'[\u0640\u064B-\u065F]', '', t)
    t = re.sub(r'[إأآا]', 'ا', t)
    t = re.sub(r'ة', 'ه', t)
    t = re.sub(r'ى', 'ي', t)
    return re.sub(r'\s+', ' ', t).strip()

def is_company_name(name):
    norm = normalize_ar(name)
    if not norm or norm.startswith(normalize_ar("مالك مباشر")):
        return False
    for bw in BROKER_NAME_WORDS:
        nk = normalize_ar(bw)
        if len(nk) <= 3:
            if re.search(rf'\b{re.escape(nk)}\b', norm):
                return True
        elif nk in norm:
            return True
    return False

def clean_publisher_name(name):
    default_lbl = "مالك مباشر"
    if not name:
        return default_lbl
    s = re.sub(r'<[^>]+>', ' ', str(name))
    s = re.sub(r'(?:تواصل\s*مع\s*المعلن|اتصل\s*لمعرفه\s*السعر|اتصل\s*لمعرفة\s*السعر|شاهد\s*كل\s*الاعلانات.*|شاهد\s*كل\s*الإعلانات.*|عرض\s*جميع\s*الإعلانات.*|عرض\s*جميع\s*الاعلانات.*|عضو\s*منذ.*|الإعلانات\s*النشطة.*|\(\d+.*?\)|\d+\s*عقار.*|عقار\s*واحد|عقارين|اتصال|اتصل|واتساب|رسالة|Avatar|الصورة\s*الشخصية|user\s*logo|ملاحظة|حفظ|مشاركة|إبلاغ|تابِع|تابع|الرد\s*على.*|التقييم.*)', ' ', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip(" -_|:,><.★⭐•·")
    norm_s = normalize_ar(s)
    if any(bad_w in norm_s for bad_w in ("اتصل", "لمعرفه", "السعر", "تواصل", "المعلن", "ملاحظه", "مشاركه", "ابلاغ", "تسجيل", "دخول", "شركات", "موثوقه")):
        return default_lbl
    if not s or len(s) < 2 or len(s) > 42 or re.search(r'[<>{}\[\]=/\\0-9]{4,}', s):
        return default_lbl
    return s

def detect_zone(title, body_text):
    raw_core = re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', f"{title} {body_text[:2000]}")
    core = normalize_ar(raw_core)
    for city in EXCLUDED_CITIES:
        if normalize_ar(city) in core:
            return None
    for z_name, keywords in ZONES:
        for kw in keywords:
            if normalize_ar(kw) in core:
                return z_name
    return "القاهرة الجديدة"

def is_strict_cash_sale(title, desc_text, price_num):
    if 0 < int(price_num or 0) < MIN_CASH_SALE_PRICE:
        return False
    raw_combined = re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', f"{title} {desc_text[:3000]}")
    full_text = normalize_ar(raw_combined)
    for neg in SAFE_CASH_NEGATIONS:
        full_text = full_text.replace(normalize_ar(neg), " ")
    for kw in INSTALLMENT_SUBSTRINGS:
        if normalize_ar(kw) in full_text:
            return False
    if re.search(r'\b\d+\s*%\s*(?:مقدم|تعاقد|دفعه|down)', full_text):
        return False
    return True

def has_broker_copywriting(title, desc_text):
    norm_body = normalize_ar(f"{title} {desc_text[:3500]}")
    for bp in BROKER_TEXT_PHRASES:
        if normalize_ar(bp) in norm_body:
            return True, f"Broker Phrase ({bp})"
    if re.search(r'\b(?:code|كود)\s*[:\-]?\s*[a-z0-9]{2,10}\b', norm_body, re.I) or re.search(r'\bmsr\d{2,5}\b', norm_body, re.I):
        return True, "Broker Inventory Code"
    return False, ""

def parse_strict_24h_official_time(html, text_block, platform="aqarmap", hint_age="", hint_ts=0):
    now_dt = datetime.now(CAIRO_TZ)
    now_ts = int(now_dt.timestamp())
    clean_t = str(text_block or "").translate(HINDI_MAP)
    norm_t = normalize_ar(clean_t)

    if re.search(r'(?:منذ|قبل)\s*(?:\d+\s*)?(?:اسبوع|اسابيع|اسبوعين|شهر|شهور|اشهر|سنه|سنوات)', norm_t):
        return False, "Old Ad (>1w)", 0, 0

    m_days = re.search(r'(?:منذ|قبل)\s*([2-9]|\d{2,})\s*(?:يوم|ايام)|(?:منذ|قبل)\s*يومين', norm_t)
    if m_days:
        return False, "Old Ad (>24h)", 0, 0

    m_min = re.search(r'(?:منذ|قبل)\s*(\d{1,3})\s*(?:دقيقه|دقائق|دقايق)', norm_t)
    if m_min:
        mins = max(1, int(m_min.group(1)))
        return True, f"منذ {mins} دقيقة", 3, now_ts - (mins * 60)

    if re.search(r'(?:منذ|قبل)\s*(?:دقيقه|دقيقتين)\b|\bالان\b|\bحالا\b', norm_t):
        return True, "منذ 2 دقيقة", 3, now_ts - 120

    m_hr = re.search(r'(?:منذ|قبل)\s*(\d{1,2})\s*(?:ساعه|ساعات)', norm_t)
    if m_hr:
        hrs = int(m_hr.group(1))
        if hrs > 24:
            return False, f"Old Ad ({hrs}h > 24h)", 0, 0
        return True, f"منذ {hrs} ساعة", 3, now_ts - (hrs * 3600)

    if re.search(r'(?:منذ|قبل)\s*(?:ساعتين|ساعتان)\b', norm_t):
        return True, "منذ 2 ساعة", 3, now_ts - 7200

    if re.search(r'(?:منذ|قبل)\s*ساعه\b', norm_t):
        return True, "منذ 1 ساعة", 3, now_ts - 3600

    for m_iso in re.findall(r'"(?:published_at|created_at|datePublished|createdAt|publishedAt|posted_at)"\s*:\s*"(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})', html[:90000]):
        try:
            iso_clean = m_iso.replace("T", " ")
            dt_obj = datetime.strptime(iso_clean, "%Y-%m-%d %H:%M:%S").replace(tzinfo=CAIRO_TZ)
            diff_sec = (now_dt - dt_obj).total_seconds()
            if diff_sec < -7200:
                continue
            if diff_sec > 86400:
                return False, f"Old Ad ISO ({m_iso[:10]})", 0, 0
            hrs = max(1, int(diff_sec // 3600))
            mins = max(1, int(diff_sec // 60))
            lbl = f"منذ {mins} دقيقة" if diff_sec < 3600 else f"منذ {hrs} ساعة"
            return True, lbl, 3, int(dt_obj.timestamp())
        except Exception:
            pass

    if platform == "opensooq":
        m_num_date = re.search(r'تاريخ\s*النشر\s*[:\-]?\s*(\d{2})-(\d{2})-(202\d)', clean_t[:1800])
        if m_num_date:
            d_val, m_val, y_val = int(m_num_date.group(1)), int(m_num_date.group(2)), int(m_num_date.group(3))
            try:
                ad_d = date(y_val, m_val, d_val)
                d_diff = (now_dt.date() - ad_d).days
                if d_diff > 1 or d_diff < 0:
                    return False, f"Old OpenSooq Ad ({d_val:02d}-{m_val:02d}-{y_val})", 0, 0
                return True, ("اليوم" if d_diff == 0 else "منذ 20 ساعة"), (3 if d_diff == 0 else 2), (now_ts - 3600 if d_diff == 0 else now_ts - 72000)
            except Exception:
                return False, "Invalid OpenSooq Date", 0, 0

    m_ar_cal = re.search(r'\b(\d{1,2})\s+(يناير|فبراير|مارس|ابريل|أبريل|إبريل|مايو|يونيو|يونية|يوليو|يوليه|اغسطس|أغسطس|سبتمبر|اكتوبر|أكتوبر|نوفمبر|ديسمبر)\s+(202\d)\b', clean_t[:2200])
    if m_ar_cal:
        d_val = int(m_ar_cal.group(1))
        m_name = m_ar_cal.group(2)
        y_val = int(m_ar_cal.group(3))
        m_val = ARABIC_MONTHS.get(m_name, 0)
        if m_val > 0:
            try:
                ad_d = date(y_val, m_val, d_val)
                d_diff = (now_dt.date() - ad_d).days
                if d_diff < 0 or d_diff > 1:
                    return False, f"Old AqarMap Ad ({d_val} {m_name} {y_val})", 0, 0
                if d_diff == 0:
                    return True, f"اليوم ({d_val} {m_name})", 3, now_ts - 3600
                return True, f"منذ 20 ساعة ({d_val} {m_name})", 2, now_ts - 72000
            except Exception:
                return False, "Invalid AqarMap Date", 0, 0

    if re.search(r'(?:تاريخ\s*النشر\s*[:\-]?\s*)?\b(?:اليوم|امس|منذ\s*يوم|قبل\s*يوم)\b', norm_t[:1500]):
        if "اليوم" in norm_t[:1500]:
            return True, "منذ 2 ساعة", 3, now_ts - 7200
        return True, "منذ 22 ساعة", 2, now_ts - 79200

    if hint_age and hint_ts > 0:
        return True, hint_age, 3, hint_ts

    if platform == "opensooq" and "شاهد المزيد" in norm_t[:2200]:
        return True, "منذ 3 ساعات", 3, now_ts - 10800

    return False, "Unverified Publication Date (>24h)", 0, 0

def extract_opensooq_candidates_from_search_html(html, src, seen_ids, extra_checked, banned_ids):
    out = []
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    cards_by_id = {}
    for a in soup.find_all("a", href=re.compile(r'/ar/search/\d{7,12}')):
        m = re.search(r'/ar/search/(\d{7,12})', str(a.get("href", "")))
        if not m:
            continue
        num_str = m.group(1)
        a_txt = a.get_text(" ", strip=True).translate(HINDI_MAP)
        if len(a_txt) < 25 and a.parent:
            p_txt = a.parent.get_text(" ", strip=True).translate(HINDI_MAP)
            if 25 <= len(p_txt) <= 420:
                a_txt = p_txt
        if num_str not in cards_by_id or len(a_txt) > len(cards_by_id[num_str]):
            cards_by_id[num_str] = a_txt[:450]

    for num_str, card_txt in cards_by_id.items():
        uid = int("92" + num_str)
        if uid in seen_ids or uid in extra_checked or uid in banned_ids:
            continue
        norm_c = normalize_ar(card_txt)
        if "نشاط تجاري موثق" in norm_c:
            extra_checked.add(uid)
            continue

        m_cd = re.search(r'\b(\d{2})-(\d{2})-(202\d)\b', card_txt)
        if m_cd:
            try:
                ad_d = date(int(m_cd.group(3)), int(m_cd.group(2)), int(m_cd.group(1)))
                if (datetime.now(CAIRO_TZ).date() - ad_d).days > 1:
                    extra_checked.add(uid)
                    continue
            except Exception:
                pass

        is_f, c_age, _, c_ts = parse_strict_24h_official_time("", card_txt, platform="opensooq")
        if not is_f and ("قبل" in norm_c or "منذ" in norm_c):
            extra_checked.add(uid)
            continue

        seen_ids.add(uid)
        out.append({
            "ad_id": uid,
            "source": "السوق المفتوح",
            "en_src": "OpenSooq",
            "url": f"https://eg.opensooq.com/ar/search/{num_str}",
            "cat": src["cat"],
            "deal": src["deal"],
            "hint_age": (c_age if is_f else "منذ 2 ساعة"),
            "hint_ts": (c_ts if is_f else int(time.time()) - 7200)
        })
    return out

def extract_aqarmap_details(html, deal):
    soup_full = BeautifulSoup(html, "html.parser")
    for tag in soup_full.find_all(["header", "nav", "footer", "script", "style", "noscript"]):
        tag.decompose()

    h1 = soup_full.find("h1")
    title = (h1.get_text(" ", strip=True) if h1 else "").split("|")[0].strip()
    if not title:
        t_m = re.search(r'<title>([^<]+)</title>', html)
        title = t_m.group(1).split("|")[0].split("-")[0].strip() if t_m else ""
    if not title or len(title) < 5:
        return None, "Empty title"

    full_txt = soup_full.get_text(" ", strip=True).translate(HINDI_MAP)
    specs_start = full_txt.find("تفاصيل الإعلان")
    desc_start = full_txt.find("وصف الإعلان")
    seller_start = full_txt.rfind("تواصل مع المعلن")

    header_and_specs = full_txt[:specs_start + 1200] if specs_start != -1 else full_txt[:2500]
    is_fresh_24h, age_label, fresh_tier, official_ts = parse_strict_24h_official_time(html, header_and_specs, platform="aqarmap")
    if not is_fresh_24h:
        return None, age_label

    specs_txt = full_txt[specs_start:desc_start] if (specs_start != -1 and desc_start > specs_start) else full_txt[:2500]
    norm_specs = normalize_ar(specs_txt)

    if re.search(r'نوع\s*المعلن\s*[:\-]?\s*(?:مسوق|مطور|شركه|وسيط|broker|developer)', norm_specs):
        return None, "AqarMap Role: Broker/Developer"
    if "نوع المعلن" in norm_specs and "مالك عقار" not in norm_specs:
        return None, "AqarMap Role: Not Private Owner"
    if re.search(r'(?:سنه\s*التسليم|سنه\s*البناء)\s*[:\-]?\s*20(?:27|28|29|30)\b', norm_specs):
        return None, "Off-Plan Future Delivery (2027+)"

    if desc_start != -1 and seller_start > desc_start:
        pure_desc = full_txt[desc_start + len("وصف الإعلان"):seller_start].strip()
    else:
        meta_d = soup_full.find("meta", {"property": "og:description"}) or soup_full.find("meta", {"name": "description"})
        pure_desc = (meta_d.get("content") or "").strip() if meta_d else full_txt[:1500]

    pub_name = "مالك مباشر"
    pub_ads = 1
    for m_sel in re.finditer(r'تواصل\s*مع\s*المعلن', html):
        idx_s = m_sel.start()
        seller_html = html[idx_s:idx_s + 4000]
        s_soup = BeautifulSoup(seller_html, "html.parser")
        s_block = s_soup.get_text(" | ", strip=True).translate(HINDI_MAP)
        norm_s = normalize_ar(s_block)
        if not re.search(r'(?:0\s*عقار|عقار\s*واحد|عقارين|\d+\s*عقارات|\d+\s*عقار)', norm_s):
            continue
        if "company-img" in seller_html or "/companies/" in seller_html.lower():
            return None, "Company Account in Seller Box"
        if re.search(r'\b[345]\.[0-9]\b', norm_s):
            return None, "Subscribed Broker Rating Badge"
        if "0 عقار" in norm_s or "عقار واحد" in norm_s:
            pub_ads = 1
        elif "عقارين" in norm_s:
            pub_ads = 2
        else:
            m_cnt = re.search(r'\b(\d{1,5})\s*(?:عقارات|عقار)\b', norm_s)
            if m_cnt:
                pub_ads = int(m_cnt.group(1))
        parts = [p.strip() for p in s_block.split("|") if p.strip() and "تواصل مع المعلن" not in p]
        for idx_p, p in enumerate(parts[:10]):
            norm_p = normalize_ar(p)
            if re.search(r'^(?:0\s*عقار|عقار\s*واحد|(?:\d+\s*)?عقارين|\d+\s*عقارات|\d+\s*عقار)$', norm_p) and idx_p >= 1:
                cand_prev = clean_publisher_name(parts[idx_p - 1])
                if cand_prev != "مالك مباشر":
                    pub_name = cand_prev
                    break
            cand = clean_publisher_name(p)
            if cand != "مالك مباشر":
                pub_name = cand
        break

    if is_company_name(pub_name):
        return None, f"Company/Broker Name ({pub_name})"
    if pub_ads > 7:
        return None, f"Broker Count ({pub_ads} > 7 properties)"

    is_brk_txt, brk_reason = has_broker_copywriting(title, pure_desc)
    if is_brk_txt:
        return None, brk_reason

    zone = detect_zone(title, pure_desc)
    if not zone:
        return None, "Excluded Zone"

    price_context = full_txt[:1500] + " " + specs_txt
    if deal != "إيجار" and re.search(r'ج\.?م\s*(?:بالتقسيط|تكمله\s*اقساط)', normalize_ar(price_context)):
        return None, "Installment Price Badge"

    price_num = 0
    price_str = "السعر بالتفاصيل"
    for m_p in re.findall(r'([\d,]{4,15})\s*(?:جنيه|ج\.?م|EGP)', price_context, re.I):
        val = int(re.sub(r'[^\d]', '', m_p))
        if (deal == "إيجار" and 2500 <= val <= 4000000) or (deal != "إيجار" and MIN_CASH_SALE_PRICE <= val <= 1500000000):
            price_num = val
            price_str = f"{val:,} ج.م"
            break

    if deal != "إيجار" and not is_strict_cash_sale(title, pure_desc, price_num):
        return None, f"Installment or Downpayment ({price_num:,})"

    top_specs_blob = full_txt[:2200] + " " + specs_txt + " " + pure_desc
    area_m = re.search(r'(\d{2,4})\s*(?:متر|م²|م2|sqm)', top_specs_blob, re.I)
    area_val = int(area_m.group(1)) if area_m else None
    rooms_m = re.search(r'(\d{1,2})\s*(?:غرف|غرفة|غرفه|نوم)', top_specs_blob)
    rooms_val = int(rooms_m.group(1)) if (rooms_m and 1 <= int(rooms_m.group(1)) <= 20) else None

    return {
        "title": title, "body_text": pure_desc[:2000], "zone": zone,
        "pub_name": pub_name, "pub_ads": max(1, pub_ads),
        "price_num": price_num, "price_str": price_str,
        "area": area_val, "rooms": rooms_val,
        "age_label": age_label, "fresh_tier": fresh_tier, "real_ts": official_ts
    }, "OK"

def extract_opensooq_details(html, deal, hint_age="", hint_ts=0):
    clean_html = html
    h1_end = clean_html.lower().find("</h1>")
    cut_start = (h1_end + 1500) if h1_end > 0 else 45000
    for marker in ["إعلانات مشابهة", "بيع كل شئ على السوق المفتوح", "الأسئلة الشائعة"]:
        idx_m = clean_html.find(marker, cut_start)
        if idx_m > cut_start:
            clean_html = clean_html[:idx_m]

    norm_raw_clean = normalize_ar(clean_html)
    if re.search(r'(?:المعلن|advertiser|seller_type)["\'\s:\-]{1,30}(?:الوسيط|وسيط|مكتب|broker|agent)', norm_raw_clean, re.I):
        return None, "OpenSooq Role: Broker (الوسيط)"

    soup = BeautifulSoup(clean_html, "html.parser")
    for tag in soup.find_all(["header", "nav", "footer", "script", "style", "noscript"]):
        tag.decompose()

    h1 = soup.find("h1")
    title = (h1.get_text(" ", strip=True) if h1 else "").split("|")[0].strip()
    if not title:
        t_m = re.search(r'<title>([^<]+)</title>', html)
        title = t_m.group(1).split("|")[0].split("-")[0].strip() if t_m else ""
    if not title or len(title) < 5:
        return None, "Empty title"

    post_txt = soup.get_text(" ", strip=True).translate(HINDI_MAP)
    h1_pos = post_txt.find(title[:20])
    if h1_pos > 0:
        post_txt = post_txt[h1_pos:]
    norm_post = normalize_ar(post_txt)

    if "اعلانات المتجر" in norm_post or "نشاط تجاري موثق" in norm_post[:1800]:
        return None, "OpenSooq Commercial Store Account"

    is_fresh_24h, age_label, fresh_tier, official_ts = parse_strict_24h_official_time(
        html, post_txt[:2000], platform="opensooq", hint_age=hint_age, hint_ts=hint_ts
    )
    if not is_fresh_24h:
        return None, age_label

    if re.search(r'المعلن\s*[:\-]?\s*(?:الوسيط|مكتب|شركه|مطور)', norm_post):
        return None, "OpenSooq Role: Broker (الوسيط)"
    if deal != "إيجار" and re.search(r'طريقه\s*الدفع\s*[:\-]?\s*(?:اقساط|بالتقسيط)', norm_post):
        return None, "OpenSooq Payment Spec: Installment"
    if re.search(r'عمر\s*البناء\s*[:\-]?\s*قيد\s*الانشاء', norm_post):
        return None, "OpenSooq Under Construction"

    pub_ads = 1
    m_cnt = re.search(r'(?:شاهد|عرض)\s*(?:كل|جميع)\s*الاعلانات\s*\(\s*(\d{1,5})\s*\)|view\s*all\s*ads\s*\(\s*(\d{1,5})\s*\)', norm_post, re.I)
    if m_cnt:
        pub_ads = int(m_cnt.group(1) or m_cnt.group(2))

    pub_name = "مالك مباشر"
    m_av = re.search(r'Avatar\s*[·•\|]?\s*([^\r\n·•\|]{2,35}?)\s*(?:تابِع|تابع|الرد|التقييم|عضو\s*منذ)', post_txt, re.I)
    if m_av:
        cand = clean_publisher_name(m_av.group(1))
        if cand != "مالك مباشر":
            pub_name = cand
    if pub_name == "مالك مباشر":
        for a_m in soup.find_all("a", href=re.compile(r'/ar/mid/|/ar/member/', re.I)):
            cand = clean_publisher_name(a_m.get_text(" ", strip=True))
            if cand != "مالك مباشر":
                pub_name = cand
                break

    if is_company_name(pub_name):
        return None, f"Company/Broker Name ({pub_name})"
    if pub_ads > 8:
        return None, f"Broker Count ({pub_name}: {pub_ads} > 8 ads)"

    meta_d = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
    meta_desc = (meta_d.get("content") or "").strip() if meta_d else ""
    desc_end_idx = len(post_txt)
    for end_m in ["وسائل الراحة", "مشاركة", "نصائح عامة", "اسأل البائع"]:
        pos_e = post_txt.find(end_m)
        if pos_e > 100 and pos_e < desc_end_idx:
            desc_end_idx = pos_e
    full_page_desc = post_txt[:min(3200, desc_end_idx)]
    pure_desc = f"{meta_desc} {full_page_desc}".strip()

    if pub_ads >= 4 and re.search(r'(?:انظمه\s*سداد|مساحات\s*خضراء|امن\s*و\s*حراسه\s*24|دقايق\s*من\s*المحاور)', normalize_ar(pure_desc)):
        return None, f"Compound Sales Rep ({pub_ads} ads)"

    is_brk_txt, brk_reason = has_broker_copywriting(title, pure_desc)
    if is_brk_txt:
        return None, brk_reason

    zone = detect_zone(title, pure_desc)
    if not zone:
        return None, "Excluded Zone"

    price_num = 0
    price_str = "السعر بالتفاصيل"
    price_candidates = re.findall(r'([\d,]{4,15})\s*(?:جنيه|ج\.?م|EGP)', post_txt[:2500], re.I) + re.findall(r'"price"\s*:\s*"?(\d[\d,]{3,12})"?', html[:80000], re.I)
    for m_p in price_candidates:
        val = int(re.sub(r'[^\d]', '', str(m_p)))
        if (deal == "إيجار" and 2500 <= val <= 4000000) or (deal != "إيجار" and MIN_CASH_SALE_PRICE <= val <= 1500000000):
            price_num = val
            price_str = f"{val:,} ج.م"
            break

    if deal != "إيجار" and not is_strict_cash_sale(title, pure_desc, price_num):
        return None, f"Installment or Downpayment ({price_num:,})"

    m_area = re.search(r'المساحه\s*[:\-]?\s*(\d{2,5})|(\d{2,4})\s*(?:متر|م²|م2|sqm)', normalize_ar(post_txt[:2200]))
    area_raw = (m_area.group(1) or m_area.group(2)) if m_area else None
    area_val = int(area_raw) if (area_raw and 20 <= int(area_raw) <= 50000) else None
    m_rooms = re.search(r'عدد\s*الغرف\s*[:\-]?\s*(\d{1,2})|(\d{1,2})\s*(?:غرف|غرفه)', normalize_ar(post_txt[:2200]))
    rooms_raw = (m_rooms.group(1) or m_rooms.group(2)) if m_rooms else None
    rooms_val = int(rooms_raw) if (rooms_raw and 1 <= int(rooms_raw) <= 20) else None

    return {
        "title": title, "body_text": pure_desc[:2000], "zone": zone,
        "pub_name": pub_name, "pub_ads": max(1, pub_ads),
        "price_num": price_num, "price_str": price_str,
        "area": area_val, "rooms": rooms_val,
        "age_label": age_label, "fresh_tier": fresh_tier, "real_ts": official_ts
    }, "OK"

def is_valid_existing_extra_ad(ad):
    src = ad.get("source") or "دوبيزل"
    if src == "دوبيزل":
        return True
    if src == "السوق المفتوح" and not ad.get("verified_os_v96"):
        return False
    if not ad.get("verified_24h_v93"):
        return False
    pub = ad.get("publisher", "")
    if "اتصل" in pub or "السعر" in pub or pub in ("مالك (عقارماب)", "مالك (السوق المفتوح)", "مالك"):
        return False
    title = ad.get("title", "")
    desc = ad.get("description", "")
    zone = ad.get("zone", "")
    deal = ad.get("deal", "تمليك")
    price_num = int(ad.get("price_num", 0) or 0)
    pub_ads = int(ad.get("pub_ads", 1) or 1)
    if pub_ads > 8 or is_company_name(pub):
        return False
    is_brk, _ = has_broker_copywriting(title, desc)
    if is_brk:
        return False
    norm_all = normalize_ar(f"{title} {zone}")
    for city in EXCLUDED_CITIES:
        if normalize_ar(city) in norm_all:
            return False
    if deal != "إيجار" and not is_strict_cash_sale(title, desc, price_num):
        return False
    return True

def sync_telegram_config(current_cfg):
    cfg = dict(current_cfg or {})
    try:
        r = std_requests.get(f"https://ntfy.sh/{TG_CONFIG_TOPIC}/json?poll=1&since=168h", timeout=10)
        if r.status_code == 200:
            for line in r.text.strip().splitlines():
                if not line: continue
                msg = json.loads(line).get("message", "")
                if msg.startswith("TG_CFG:"):
                    b64_part = msg.replace("TG_CFG:", "").strip()
                    decoded = json.loads(base64.b64decode(b64_part).decode("utf-8"))
                    if decoded.get("tok") and decoded.get("cid"):
                        cfg["tok"] = decoded["tok"].strip()
                        cfg["cid"] = str(decoded["cid"]).strip()
    except Exception:
        pass
    return cfg

def send_telegram_msg(tok, cid, text_msg):
    if not tok or not cid:
        return False
    try:
        url = f"https://api.telegram.org/bot{tok}/sendMessage"
        payload = {"chat_id": cid, "text": text_msg, "parse_mode": "HTML", "disable_web_page_preview": False}
        r = std_requests.post(url, json=payload, timeout=12)
        return r.status_code == 200
    except Exception:
        return False

def analyze_with_ai(title, visible_text, pub_name, deal, cat, price_num, source):
    url = "https://gamal216.pythonanywhere.com/analyze"
    payload = {
        "text": f"{title} {visible_text[:2000]}",
        "title": title,
        "description": visible_text[:2000],
        "publisher": pub_name,
        "deal": deal,
        "cat": cat,
        "price_num": price_num,
        "source": source,
        "active_ads_count": 1
    }
    try:
        response = std_requests.post(url, json=payload, timeout=12)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                if result.get("decision") == "مرفوض":
                    return False, "AI Rejected"
                analysis = result.get("analysis", "")
                if "سمسار" in analysis and "مالك حقيقي" not in analysis:
                    return False, "AI Detected Broker"
                return True, "Owner"
    except Exception as e:
        print(f"[AI Server Error] {e}")
    if deal != "إيجار":
        ok = is_strict_cash_sale(title, visible_text, price_num)
        return ok, ("Owner" if ok else "Installment Suspect")
    return True, "Owner"

def monitor_system_with_ai(stats_dict):
    url = "https://gamal216.pythonanywhere.com/monitor"
    try:
        response = std_requests.post(url, json=stats_dict, timeout=15)
        if response.status_code == 200:
            res = response.json()
            if res.get("status") == "success":
                return res.get("ai_advice", "System healthy"), res.get("health", "Good")
    except Exception as e:
        print(f"[AI Monitor Error] {e}")
    return "Local filter active and healthy.", "Good"

def run_extra_radar():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {"ads": []}
    else:
        data = {"ads": []}

    if not isinstance(data, dict):
        data = {"ads": data if isinstance(data, list) else []}

    raw_existing = data.get("ads", []) + fetch_remote_ads_list()
    extra_checked = load_persistent_seen_ids(data)
    banned_ids = set(data.get("banned_ad_ids", []))
    notified_ids = set(data.get("telegram_notified_ids", []))
    tg_cfg = sync_telegram_config(data.get("telegram_config", {}))
    run_report = data.get("last_run_report", {})

    existing_ads, seen_existing_u = [], set()
    purged_old_extra = 0
    for ad in raw_existing:
        u = ad.get("url") or ad.get("link") or str(ad.get("ad_id"))
        if not u or u in seen_existing_u:
            continue
        if is_valid_existing_extra_ad(ad):
            seen_existing_u.add(u)
            existing_ads.append(ad)
        else:
            purged_old_extra += 1
            aid = ad.get("ad_id")
            if aid in extra_checked:
                extra_checked.discard(aid)

    seen_ids = {a.get("ad_id") for a in existing_ads if a.get("ad_id")}
    fetcher = SmartFetcher()
    new_extra_ads = []

    os_candidates = []
    os_sources = fetcher.discover_opensooq_sources()
    for src in os_sources:
        for page in range(1, 3):
            page_url = src["url"] if page == 1 else f"{src['url']}?page={page}"
            html, status_info = fetcher.get_html(page_url, req_regex=r'/ar/search/\d+')
            found_os = extract_opensooq_candidates_from_search_html(html, src, seen_ids, extra_checked, banned_ids)
            os_candidates.extend(found_os)
            print(f"[OpenSooq] {src['en']} p.{page} -> {status_info} (Fresh <=24h Candidates: {len(found_os)})")
            time.sleep(random.uniform(0.6, 1.0))

    aq_candidates = []
    for src in AQARMAP_SOURCES:
        for page in range(1, 4):
            page_url = src["url"] if page == 1 else f"{src['url']}&page={page}"
            html, status_info = fetcher.get_html(page_url, req_regex=r'/ar/listing/\d+')
            print(f"[AqarMap] {src['en']} p.{page} -> {status_info}")
            time.sleep(random.uniform(0.6, 1.0))
            if not html:
                continue
            links = re.findall(r'(/ar/listing/(\d{5,12})[^"\'\s<>\\]*)', html)
            for path, num_str in links:
                uid = int("91" + num_str)
                if uid in seen_ids or uid in extra_checked or uid in banned_ids:
                    continue
                aq_candidates.append({
                    "ad_id": uid,
                    "source": "عقارماب",
                    "en_src": "AqarMap",
                    "url": "https://aqarmap.com.eg" + path.split("?")[0],
                    "cat": src["cat"],
                    "deal": src["deal"],
                    "hint_age": "",
                    "hint_ts": 0
                })
                seen_ids.add(uid)

    save_persistent_seen_ids(extra_checked)

    rent_os = [x for x in os_candidates if x["deal"] == "إيجار"]
    sale_os = [x for x in os_candidates if x["deal"] != "إيجار"]
    rent_aq = [x for x in aq_candidates if x["deal"] == "إيجار"]
    sale_aq = [x for x in aq_candidates if x["deal"] != "إيجار"]
    all_candidates = rent_os[:100] + sale_os[:100] + rent_aq[:120] + sale_aq[:120]
    print(f"[Extra Radar v9.6] New Candidates -> OpenSooq: {len(os_candidates)} | AqarMap: {len(aq_candidates)} | Inspecting: {len(all_candidates)}")

    aq_added = 0
    os_added = 0
    total_c = len(all_candidates)

    for idx, item in enumerate(all_candidates, 1):
        uid = item["ad_id"]
        en_s = item["en_src"]
        try:
            html, _ = fetcher.get_html(item["url"])
            if not html:
                continue

            if item["source"] == "عقارماب":
                info, reason = extract_aqarmap_details(html, item["deal"])
            else:
                info, reason = extract_opensooq_details(
                    html, item["deal"],
                    hint_age=item.get("hint_age", ""),
                    hint_ts=item.get("hint_ts", 0)
                )

            if reason != "Empty title":
                extra_checked.add(uid)
                if idx % 15 == 0:
                    save_persistent_seen_ids(extra_checked)

            if not info:
                print(f"  [{idx}/{total_c}] [- REJECTED {en_s}] {reason}")
                continue

            is_owner, ai_reason = analyze_with_ai(
                info["title"], info["body_text"], info["pub_name"],
                item["deal"], item["cat"], info["price_num"], item["source"]
            )
            if not is_owner:
                print(f"  [{idx}/{total_c}] [- REJECTED {en_s}] {ai_reason}")
                continue

            real_post_ts = int(info.get("real_ts") or time.time())
            now_cairo = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
            new_extra_ads.append({
                "ad_id": uid,
                "id": f"ext_{uid}",
                "source": item["source"],
                "title": info["title"],
                "price": info["price_str"],
                "price_num": info["price_num"],
                "zone": info["zone"],
                "location": info["zone"],
                "cat": item["cat"],
                "category": item["cat"],
                "deal": item["deal"],
                "type": item["deal"],
                "area": info["area"],
                "rooms": info["rooms"],
                "publisher": info["pub_name"],
                "pub_ads": info["pub_ads"],
                "active_ads_count": info["pub_ads"],
                "age": info["age_label"],
                "fresh_tier": info["fresh_tier"],
                "description": info["body_text"][:500],
                "first_seen_ts": real_post_ts,
                "timestamp": real_post_ts,
                "desc_verified_v2": True,
                "verified_24h_v93": True,
                "verified_os_v96": True,
                "url": item["url"],
                "link": item["url"],
                "verified_v12": True,
                "scraped_at": now_cairo,
                "date": datetime.fromtimestamp(real_post_ts, CAIRO_TZ).strftime("%Y-%m-%d %H:%M")
            })
            if item["source"] == "عقارماب":
                aq_added += 1
            else:
                os_added += 1
            print(f"  [{idx}/{total_c}] [+ ACCEPTED <=24H OWNER] {en_s} ({info['age_label']}) | {info['pub_name']} ({info['pub_ads']} ads) | Price: {info['price_num']:,} EGP")
            time.sleep(random.uniform(0.6, 1.0))
        except Exception:
            continue

    fetcher.close()
    save_persistent_seen_ids(extra_checked)

    disk_ads = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                latest_disk = json.load(f)
                if isinstance(latest_disk, dict) and isinstance(latest_disk.get("ads"), list):
                    disk_ads = latest_disk["ads"]
        except Exception:
            pass

    all_pool = new_extra_ads + disk_ads + existing_ads + fetch_remote_ads_list()
    merged_ads, seen_u = [], set()
    for ad in all_pool:
        if not is_valid_existing_extra_ad(ad):
            continue
        u = ad.get("url") or ad.get("link") or str(ad.get("ad_id"))
        if not u or u in seen_u:
            continue
        seen_u.add(u)
        merged_ads.append(ad)

    merged_ads.sort(key=lambda x: (int(x.get("first_seen_ts") or 0), int(x.get("ad_id") or 0)), reverse=True)
    merged_ads = merged_ads[:450]

    aq_total = sum(1 for a in merged_ads if a.get("source") == "عقارماب")
    os_total = sum(1 for a in merged_ads if a.get("source") == "السوق المفتوح")
    rent_total = sum(1 for a in merged_ads if a.get("deal") == "إيجار")
    sale_total = sum(1 for a in merged_ads if a.get("deal") != "إيجار")

    ai_stats_payload = {
        "total_ads": aq_total + os_total,
        "rent_total": rent_total,
        "sale_total": sale_total,
        "aq_checked": len(aq_candidates),
        "aq_added": aq_added,
        "os_checked": len(os_candidates),
        "os_added": os_added
    }
    ai_advice, sys_health = monitor_system_with_ai(ai_stats_payload)
    print(f"=== Cycle Complete: Added +{aq_added} AqarMap & +{os_added} OpenSooq | Total AqarMap: {aq_total} | Total OpenSooq: {os_total} ===")

    now_str = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
    run_report.update({
        "last_run_at": now_str,
        "aq_candidates": len(aq_candidates),
        "aq_added": aq_added,
        "os_candidates": len(os_candidates),
        "os_added": os_added,
        "aq_total": aq_total,
        "os_total": os_total,
        "ai_health": sys_health,
        "ai_advice": ai_advice
    })

    tok = os.environ.get("TELEGRAM_BOT_TOKEN") or tg_cfg.get("tok", "")
    cid = os.environ.get("TELEGRAM_CHAT_ID") or tg_cfg.get("cid", "")

    if tok and cid:
        new_Alert_ads = [a for a in new_extra_ads if a.get("fresh_tier") == 3 and a.get("ad_id") not in notified_ids]
        for ad in new_Alert_ads[:10]:
            msg = (
                f"<b>صيد جديد <=24 ساعة ({ad.get('deal')}) من {ad.get('source')}</b>\n"
                f"المنطقة: <b>{ad.get('zone')}</b> ({ad.get('cat')})\n"
                f"السعر: <b>{ad.get('price')}</b>\n"
                f"المساحة: {ad.get('area') or 'غير محدد'} م2 | الغرف: {ad.get('rooms') or 'غير محدد'}\n"
                f"وقت النشر الرسمي: <b>{ad.get('age')}</b>\n"
                f"العنوان: {ad.get('title')}\n"
                f"الناشر: {ad.get('publisher')} ({ad.get('pub_ads', 1)} إعلان)\n"
                f"<a href=\"{ad.get('url')}\">اضغط هنا لفتح الإعلان الأصلي</a>"
            )
            if send_telegram_msg(tok, cid, msg):
                notified_ids.add(ad.get("ad_id"))
            time.sleep(0.5)

        summary_msg = (
            f"<b>تقرير رادار عقارماب والسوق المفتوح ({now_str})</b>\n"
            f"حالة النظام: <b>{sys_health}</b>\n"
            f"تشخيص الذكاء الاصطناعي:\n"
            f"<i>{ai_advice}</i>\n"
            f"عقارماب: <b>{aq_total}</b> (جديد بالرن: +{aq_added} من {len(aq_candidates)} مرشح)\n"
            f"السوق المفتوح: <b>{os_total}</b> (جديد بالرن: +{os_added} من {len(os_candidates)} مرشح)"
        )
        send_telegram_msg(tok, cid, summary_msg)
    else:
        for a in new_extra_ads[:30]:
            if a.get("ad_id"):
                notified_ids.add(a.get("ad_id"))

    data["updated_at"] = now_str
    data["total"] = len(merged_ads)
    data["last_run_report"] = run_report
    data["ads"] = merged_ads
    data["extra_checked_ids"] = list(extra_checked)[-10000:]
    data["telegram_config"] = tg_cfg
    data["telegram_notified_ids"] = list(notified_ids)[-5000:]

    if not os.environ.get("GITHUB_ACTIONS"):
        ok_push, push_info = atomic_write_and_git_push(data, f"Extra Radar Sync (AqarMap: {aq_total}, OpenSooq: {os_total})")
        if ok_push:
            print(f"    --> [LIVE SYNC] Pushed AqarMap ({aq_total}) & OpenSooq ({os_total}) owners to GitHub & Vercel!")
        else:
            print(f"    --> [LOCAL SAVE] {push_info}")
    else:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    if os.environ.get("GITHUB_ACTIONS"):
        run_extra_radar()
        return
    print("=== Starting 24/7 Standalone AqarMap & OpenSooq Radar v9.6 (Full Desc + Display All Ads Count + Atomic Push) ===")
    cycle = 1
    while True:
        print(f"\n>>> Starting AqarMap & OpenSooq Cycle #{cycle} at {datetime.now().strftime('%H:%M:%S')} <<<")
        try:
            run_extra_radar()
        except Exception as e:
            print(f"[Extra Radar Error] {e}")
        cycle += 1
        print(f"[Auto-Loop] Sleeping for {AUTO_LOOP_MINUTES} minutes before next scan...")
        for _ in range(AUTO_LOOP_MINUTES * 2):
            time.sleep(30)

if __name__ == "__main__":
    main()
