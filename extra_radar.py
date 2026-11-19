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
AQ_LIVE_BACKUP_FILE = os.path.join(BASE_DIR, "aqarmap_live_ads.json")
CLEAN_V100_FLAG = os.path.join(BASE_DIR, "clean_aq_v100.flag")
TG_CONFIG_TOPIC = "gamal_vip_tg_9941_sec"
WARP_PROXY = "socks5h://127.0.0.1:40000"
MIN_CASH_SALE_PRICE = 1200000
MAX_AGE_DAYS = 2
AUTO_LOOP_MINUTES = 45
HINDI_MAP = str.maketrans({"٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9", "٬": ",", "،": ",", "٫": "."})
BIDI_REGEX = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]')

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
    "للإنشاءات", "للانشاءات", "اللوتس العقارية", "البيت المصري"
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
    "كود الوحدة", "كود الوحده", "كود العقار", "كود الشقة", "كود الفيلا", "الكود المرجعي",
    "متاح لدينا", "يتوفر لدينا", "متوفر لدينا", "لدينا أكثر من", "متاح لدينا اكثر من",
    "متاح مساحات مختلفة", "مساحات مختلفة", "مساحات مختلفه", "متوفر لدينا وحدات", "متاح لدينا وحدات",
    "استمرار لعروضنا", "والواقع يتحدث عنا", "امتلك وحدتك", "احجز وحدتك", "اختار وحدتك", "الشركة العالمية للعقارات"
]

AQARMAP_SOURCES = [
    {"cat": "شقق", "deal": "إيجار", "en": "Apartments (Rent)", "max_p": 5, "url": "https://aqarmap.com.eg/ar/for-rent/apartment/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "شقق", "deal": "إيجار", "en": "Furnished Apts (Rent)", "max_p": 4, "url": "https://aqarmap.com.eg/ar/for-rent/furnished-apartment/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "فلل", "deal": "إيجار", "en": "Villas (Rent)", "max_p": 3, "url": "https://aqarmap.com.eg/ar/for-rent/villa/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "تجاري", "deal": "إيجار", "en": "Commercial (Rent)", "max_p": 3, "url": "https://aqarmap.com.eg/ar/for-rent/commercial/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "تجاري", "deal": "إيجار", "en": "Administrative (Rent)", "max_p": 3, "url": "https://aqarmap.com.eg/ar/for-rent/administrative/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "تجاري", "deal": "إيجار", "en": "Medical (Rent)", "max_p": 2, "url": "https://aqarmap.com.eg/ar/for-rent/medical/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "أراضي", "deal": "إيجار", "en": "Buildings (Rent)", "max_p": 2, "url": "https://aqarmap.com.eg/ar/for-rent/building/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "أراضي", "deal": "إيجار", "en": "Lands (Rent)", "max_p": 2, "url": "https://aqarmap.com.eg/ar/for-rent/land/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "شقق", "deal": "تمليك", "en": "Apartments (Cash Sale)", "max_p": 5, "url": "https://aqarmap.com.eg/ar/for-sale/apartment/cairo/new-cairo/?payment_method=1&sort=publishedAt"},
    {"cat": "شقق", "deal": "تمليك", "en": "Apartments (All Sale)", "max_p": 4, "url": "https://aqarmap.com.eg/ar/for-sale/apartment/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "فلل", "deal": "تمليك", "en": "Villas (Cash Sale)", "max_p": 3, "url": "https://aqarmap.com.eg/ar/for-sale/villa/cairo/new-cairo/?payment_method=1&sort=publishedAt"},
    {"cat": "فلل", "deal": "تمليك", "en": "Villas (All Sale)", "max_p": 3, "url": "https://aqarmap.com.eg/ar/for-sale/villa/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "تجاري", "deal": "تمليك", "en": "Commercial (Sale)", "max_p": 3, "url": "https://aqarmap.com.eg/ar/for-sale/commercial/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "تجاري", "deal": "تمليك", "en": "Administrative (Sale)", "max_p": 3, "url": "https://aqarmap.com.eg/ar/for-sale/administrative/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "تجاري", "deal": "تمليك", "en": "Medical (Sale)", "max_p": 2, "url": "https://aqarmap.com.eg/ar/for-sale/medical/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "أراضي", "deal": "تمليك", "en": "Lands (Sale)", "max_p": 3, "url": "https://aqarmap.com.eg/ar/for-sale/land/cairo/new-cairo/?sort=publishedAt"},
    {"cat": "أراضي", "deal": "تمليك", "en": "Buildings (Sale)", "max_p": 2, "url": "https://aqarmap.com.eg/ar/for-sale/building/cairo/new-cairo/?sort=publishedAt"},
]

def strip_bidi(text):
    if not text: return ""
    return BIDI_REGEX.sub("", str(text)).translate(HINDI_MAP)

def normalize_ar(text):
    t = strip_bidi(text).lower()
    t = re.sub(r'[\u0640\u064B-\u065F]', '', t)
    t = re.sub(r'[إأآا]', 'ا', t)
    t = re.sub(r'ة', 'ه', t)
    t = re.sub(r'ى', 'ي', t)
    return re.sub(r'\s+', ' ', t).strip()

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

def load_aqarmap_live_backup():
    if os.path.exists(AQ_LIVE_BACKUP_FILE):
        try:
            with open(AQ_LIVE_BACKUP_FILE, "r", encoding="utf-8") as f:
                arr = json.load(f)
                if isinstance(arr, list):
                    return [a for a in arr if is_valid_existing_extra_ad(a)]
        except Exception:
            pass
    return []

def save_aqarmap_live_backup(aq_ads_list):
    try:
        if os.path.exists(AQ_LIVE_BACKUP_FILE):
            try: os.chmod(AQ_LIVE_BACKUP_FILE, stat.S_IWRITE)
            except Exception: pass
        with open(AQ_LIVE_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(aq_ads_list[:150], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

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

def load_persistent_seen_ids():
    if not os.path.exists(CLEAN_V100_FLAG):
        try:
            with open(CLEAN_V100_FLAG, "w") as f: f.write("ok")
        except Exception: pass
        save_persistent_seen_ids(set())
        save_aqarmap_live_backup([])
        print("[AqarMap Full-Power Reset v10.0] Cleared old cache & broken links to scan all 17 AqarMap sources fresh!")
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
            "Upgrade-Insecure-Requests": "1"
        }
        self.warp_sess = cffi_requests.Session(impersonate="chrome120", proxies={"http": WARP_PROXY, "https": WARP_PROXY}) if self.warp_active else None
        if self.warp_sess:
            self.warp_sess.headers.update(base_headers)
        self.direct_sess = cffi_requests.Session(impersonate="chrome120")
        self.direct_sess.headers.update(base_headers)

    def _is_valid_html(self, html, req_regex=None):
        if not html or len(html) < 1500:
            return False
        if "Pardon Our Interruption" in html or "Just a moment..." in html or "<title>Attention Required!" in html:
            return False
        if req_regex and not re.search(req_regex, html):
            return False
        return True

    def get_html(self, raw_url, req_regex=None, require_listing_url=False):
        url = urllib.parse.quote(urllib.parse.unquote(raw_url), safe=":/?&=#%")
        statuses = []
        if self.warp_active and self.warp_sess:
            try:
                r = self.warp_sess.get(url, timeout=18, allow_redirects=True)
                final_u = str(r.url or url)
                if require_listing_url and "/ar/listing/" not in final_u:
                    return "", "Redirected_To_Search", final_u
                if r.status_code == 200 and self._is_valid_html(r.text, req_regex):
                    return r.text, "200 (WARP)", final_u
                statuses.append(f"WARP:{r.status_code}")
            except Exception:
                statuses.append("WARP:ERR")

        try:
            r = self.direct_sess.get(url, timeout=18, allow_redirects=True)
            final_u = str(r.url or url)
            if require_listing_url and "/ar/listing/" not in final_u:
                return "", "Redirected_To_Search", final_u
            if r.status_code == 200 and self._is_valid_html(r.text, req_regex):
                return r.text, "200 (Direct)", final_u
            statuses.append(f"Direct:{r.status_code}")
        except Exception:
            statuses.append("Direct:ERR")

        return "", " | ".join(statuses), url

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
    s = strip_bidi(re.sub(r'<[^>]+>', ' ', str(name)))
    s = re.sub(r'(?:تواصل\s*مع\s*المعلن|اتصل\s*لمعرفه\s*السعر|اتصل\s*لمعرفة\s*السعر|شاهد\s*كل\s*الاعلانات.*|شاهد\s*كل\s*الإعلانات.*|عرض\s*جميع\s*الإعلانات.*|عرض\s*جميع\s*الاعلانات.*|عضو\s*منذ.*|الإعلانات\s*النشطة.*|\(\d+.*?\)|\d+\s*عقار.*|عقار\s*واحد|عقارين|اتصال|اتصل|واتساب|رسالة|Avatar|الصورة\s*الشخصية|user\s*logo|ملاحظة|حفظ|مشاركة|شارك|إبلاغ|تابِع|تابع|التقييم.*)', ' ', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip(" -_|:,><.★⭐•·+")
    norm_s = normalize_ar(s)
    if any(bad_w in norm_s for bad_w in ("اتصل", "لمعرفه", "السعر", "تواصل", "المعلن", "ملاحظه", "مشاركه", "ابلاغ", "تسجيل", "دخول", "شركات", "موثوقه", "القاهره", "التجمع", "الجيزه")):
        return default_lbl
    if not s or len(s) < 2 or len(s) > 38 or re.search(r'[<>{}\[\]=/\\0-9]{4,}', s):
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
    if int(price_num or 0) < MIN_CASH_SALE_PRICE:
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

def parse_aqarmap_strict_2days_date(text_block):
    now_dt = datetime.now(CAIRO_TZ)
    now_ts = int(now_dt.timestamp())
    clean_t = strip_bidi(text_block)
    for m_ar_cal in re.finditer(r'\b(\d{1,2})\s+(يناير|فبراير|مارس|ابريل|أبريل|إبريل|مايو|يونيو|يونية|يوليو|يوليه|اغسطس|أغسطس|سبتمبر|اكتوبر|أكتوبر|نوفمبر|ديسمبر)\s+(202\d)\b', clean_t[:3000]):
        d_val = int(m_ar_cal.group(1))
        m_name = m_ar_cal.group(2)
        y_val = int(m_ar_cal.group(3))
        m_val = ARABIC_MONTHS.get(m_name, 0)
        if m_val > 0:
            try:
                ad_d = date(y_val, m_val, d_val)
                d_diff = (now_dt.date() - ad_d).days
                if d_diff < 0 or d_diff > MAX_AGE_DAYS:
                    return False, f"Old AqarMap Ad ({d_val} {m_name} {y_val} > {MAX_AGE_DAYS}d)", 0, 0
                if d_diff == 0:
                    return True, f"اليوم ({d_val} {m_name})", 3, now_ts - 3600
                elif d_diff == 1:
                    return True, f"منذ يوم ({d_val} {m_name})", 3, now_ts - 72000
                else:
                    return True, f"منذ يومين ({d_val} {m_name})", 2, now_ts - 150000
            except Exception:
                return False, "Invalid AqarMap Date", 0, 0
    return False, "Unverified AqarMap Date", 0, 0

def extract_aqarmap_candidates_from_search_html(html, src, seen_ids, extra_checked, banned_ids):
    out = []
    if not html:
        return out
    soup = BeautifulSoup(html, "html.parser")
    seen_local = set()
    for a in soup.find_all("a", href=re.compile(r'/ar/listing/\d{5,12}')):
        href_str = str(a.get("href", "")).split("?")[0].strip()
        m = re.search(r'^(/ar/listing/(\d{5,12})[^"\'\s<>\\]*)$', href_str)
        if not m:
            continue
        path, num_str = m.group(1), m.group(2)
        uid = int("91" + num_str)
        if uid in seen_local or uid in seen_ids or uid in extra_checked or uid in banned_ids:
            continue
        seen_local.add(uid)

        card = a
        for _ in range(4):
            if not card.parent:
                break
            p_txt = card.parent.get_text(" ", strip=True)
            if len(p_txt) > 650:
                break
            card = card.parent

        has_company_logo = False
        for img in card.find_all("img"):
            alt_t = strip_bidi(img.get("alt") or "").strip().lower()
            src_i = str(img.get("src") or "").lower()
            if "/companies/" in src_i or "company-logo" in src_i:
                has_company_logo = True
                break
            if "logo" in alt_t and "user logo" not in alt_t and "aqarmap" not in alt_t:
                has_company_logo = True
                break

        if has_company_logo:
            extra_checked.add(uid)
            continue

        card_txt = strip_bidi(card.get_text(" ", strip=True))
        norm_c = normalize_ar(card_txt)
        if any(normalize_ar(city) in norm_c for city in EXCLUDED_CITIES):
            extra_checked.add(uid)
            continue
        if src["deal"] != "إيجار" and any(k in norm_c for k in ("بالتقسيط", "قسط علي", "تكمله اقساط")):
            extra_checked.add(uid)
            continue

        seen_ids.add(uid)
        out.append({
            "ad_id": uid,
            "num_str": num_str,
            "source": "عقارماب",
            "en_src": "AqarMap",
            "url": "https://aqarmap.com.eg" + path,
            "cat": src["cat"],
            "deal": src["deal"]
        })
    return out

def extract_aqarmap_details(html, deal, expected_num_str, final_url):
    if "/ar/listing/" not in str(final_url):
        return None, "Redirected to Search Page"

    soup_full = BeautifulSoup(html, "html.parser")
    canonical_url = final_url
    can_tag = soup_full.find("link", {"rel": "canonical"}) or soup_full.find("meta", {"property": "og:url"})
    if can_tag:
        c_href = (can_tag.get("href") or can_tag.get("content") or "").strip()
        if c_href.startswith("http"):
            if "/ar/listing/" not in c_href:
                return None, "Canonical URL is Search Page (Deleted Ad)"
            canonical_url = c_href

    for tag in soup_full.find_all(["header", "nav", "footer", "script", "style", "noscript"]):
        tag.decompose()

    h1 = soup_full.find("h1")
    title = strip_bidi((h1.get_text(" ", strip=True) if h1 else "").split("|")[0]).strip()
    if not title or len(title) < 5:
        return None, "Empty title"

    full_txt = strip_bidi(soup_full.get_text(" ", strip=True))
    specs_start = full_txt.find("تفاصيل الإعلان")
    desc_start = full_txt.find("وصف الإعلان")
    seller_start = full_txt.rfind("تواصل مع المعلن")

    if specs_start == -1 or desc_start == -1:
        return None, "Redirected to Search Page (Missing Specs Table)"

    header_and_specs = full_txt[:specs_start + 1200]
    is_fresh_2d, age_label, fresh_tier, official_ts = parse_aqarmap_strict_2days_date(header_and_specs)
    if not is_fresh_2d:
        return None, age_label

    specs_txt = full_txt[specs_start:desc_start]
    norm_specs = normalize_ar(specs_txt)

    if expected_num_str and f"eg-{expected_num_str}" not in norm_specs:
        return None, f"Mismatched/Redirected Listing ID (Expected EG-{expected_num_str})"

    if re.search(r'نوع\s*المعلن\s*[:\-]?\s*(?:مسوق|مطور|شركه|وسيط|broker|developer)', norm_specs):
        return None, "AqarMap Role: Broker/Developer"
    if "مالك عقار" not in norm_specs:
        return None, "AqarMap Role: Not Verified Private Owner (مالك عقار)"
    if re.search(r'(?:سنه\s*التسليم|سنه\s*البناء)\s*[:\-]?\s*20(?:27|28|29|30)\b', norm_specs):
        return None, "Off-Plan Future Delivery (2027+)"

    desc_raw = full_txt[desc_start + len("وصف الإعلان"):]
    desc_cut = len(desc_raw)
    for marker in ["أظهر المزيد", "مزايا العقار", "وقت الوصول", "الموقع على الخريطة", "تواصل مع المعلن"]:
        idx_m = desc_raw.find(marker)
        if idx_m != -1 and idx_m < desc_cut:
            desc_cut = idx_m
    pure_desc = desc_raw[:min(2500, desc_cut)].strip()

    pub_name = "مالك مباشر"
    pub_ads = 1
    for m_sel in re.finditer(r'تواصل\s*مع\s*المعلن', html):
        idx_s = m_sel.start()
        seller_html = html[idx_s:idx_s + 4000]
        s_soup = BeautifulSoup(seller_html, "html.parser")
        s_block = strip_bidi(s_soup.get_text(" | ", strip=True))
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

    if price_num == 0:
        return None, "Missing/Zero Price"

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
        "age_label": age_label, "fresh_tier": fresh_tier, "real_ts": official_ts,
        "canonical_url": canonical_url
    }, "OK"

def is_valid_existing_extra_ad(ad):
    src = ad.get("source") or "دوبيزل"
    if src == "دوبيزل":
        return True
    if src != "عقارماب":
        return False
    if not ad.get("verified_aq_v100"):
        return False
    u = str(ad.get("url") or ad.get("link") or "")
    if "/ar/listing/" not in u:
        return False
    now_ts = int(datetime.now(CAIRO_TZ).timestamp())
    ad_ts = int(ad.get("first_seen_ts") or ad.get("timestamp") or 0)
    if ad_ts <= 0 or (now_ts - ad_ts) > ((MAX_AGE_DAYS + 1) * 86400):
        return False
    pub = ad.get("publisher", "")
    title = ad.get("title", "")
    desc = ad.get("description", "")
    zone = ad.get("zone", "")
    deal = ad.get("deal", "تمليك")
    price_num = int(ad.get("price_num", 0) or 0)
    if price_num <= 0:
        return False
    pub_ads = int(ad.get("pub_ads", 1) or 1)
    if pub_ads > 7 or is_company_name(pub):
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

def sync_ads_to_github_now(data_obj, new_aq_ads, existing_ads, extra_checked, tg_cfg, notified_ids, run_report, msg_label):
    disk_ads = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d_disk = json.load(f)
                if isinstance(d_disk, dict) and isinstance(d_disk.get("ads"), list):
                    disk_ads = d_disk["ads"]
        except Exception:
            pass

    all_pool = new_aq_ads + load_aqarmap_live_backup() + disk_ads + existing_ads + fetch_remote_ads_list()
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

    aq_live = [a for a in merged_ads if a.get("source") == "عقارماب"]
    save_aqarmap_live_backup(aq_live)

    now_str = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
    data_obj["updated_at"] = now_str
    data_obj["total"] = len(merged_ads)
    data_obj["last_run_report"] = run_report
    data_obj["ads"] = merged_ads
    data_obj["extra_checked_ids"] = list(extra_checked)[-10000:]
    data_obj["telegram_config"] = tg_cfg
    data_obj["telegram_notified_ids"] = list(notified_ids)[-5000:]

    if not os.environ.get("GITHUB_ACTIONS"):
        ok_p, p_info = atomic_write_and_git_push(data_obj, f"{msg_label} (AqarMap Live: {len(aq_live)})")
        if ok_p:
            print(f"    --> [LIVE SYNC] {msg_label} | AqarMap Live Owners on Site: ({len(aq_live)})!")
        else:
            print(f"    --> [LOCAL SAVE] {p_info}")
    return merged_ads, len(aq_live)

def guard_aqarmap_ads_during_sleep():
    aq_backup = load_aqarmap_live_backup()
    if not aq_backup or not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict) or not isinstance(d.get("ads"), list):
            return
        cur_ads = d["ads"]
        cur_aq_ids = {a.get("ad_id") for a in cur_ads if a.get("source") == "عقارماب" and is_valid_existing_extra_ad(a)}
        backup_ids = {a.get("ad_id") for a in aq_backup}
        has_invalid_extra = any((a.get("source") or "دوبيزل") != "دوبيزل" and not is_valid_existing_extra_ad(a) for a in cur_ads)
        if not backup_ids.issubset(cur_aq_ids) or has_invalid_extra:
            clean_pool = aq_backup + [a for a in cur_ads if is_valid_existing_extra_ad(a)]
            merged, seen_u = [], set()
            for ad in clean_pool:
                u = ad.get("url") or ad.get("link") or str(ad.get("ad_id"))
                if not u or u in seen_u: continue
                seen_u.add(u)
                merged.append(ad)
            merged.sort(key=lambda x: (int(x.get("first_seen_ts") or 0), int(x.get("ad_id") or 0)), reverse=True)
            d["ads"] = merged[:450]
            d["total"] = len(d["ads"])
            atomic_write_and_git_push(d, f"Auto-Restored Verified AqarMap Owners ({len(aq_backup)})")
            print(f"    --> [Anti-Overwrite Guard] Restored ({len(aq_backup)}) verified AqarMap owners to GitHub & Vercel!")
    except Exception:
        pass

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
    except Exception:
        pass
    if deal != "إيجار":
        ok = is_strict_cash_sale(title, visible_text, price_num)
        return ok, ("Owner" if ok else "Installment Suspect")
    return True, "Owner"

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
    extra_checked = load_persistent_seen_ids()
    banned_ids = set(data.get("banned_ad_ids", []))
    notified_ids = set(data.get("telegram_notified_ids", []))
    tg_cfg = sync_telegram_config(data.get("telegram_config", {}))
    run_report = data.get("last_run_report", {})

    fetcher = SmartFetcher()

    existing_ads, seen_existing_u = [], set()
    purged_count = 0
    for ad in raw_existing:
        u = ad.get("url") or ad.get("link") or str(ad.get("ad_id"))
        if not u or u in seen_existing_u:
            continue
        if is_valid_existing_extra_ad(ad):
            if ad.get("source") == "عقارماب":
                html_chk, st_chk, final_u_chk = fetcher.get_html(u, require_listing_url=True)
                if st_chk == "Redirected_To_Search" or "/ar/listing/" not in final_u_chk:
                    purged_count += 1
                    print(f"[Purged Deleted/Redirected AqarMap Ad] {ad.get('title', '')[:40]}")
                    continue
            seen_existing_u.add(u)
            existing_ads.append(ad)
        else:
            purged_count += 1

    if purged_count > 0:
        print(f"[Instant Cleanup] Purged ({purged_count}) broken/redirected ads -> Pushing clean state to site now...")
        existing_ads, _ = sync_ads_to_github_now(data, [], existing_ads, extra_checked, tg_cfg, notified_ids, run_report, "Purged Broken AqarMap Links")

    seen_ids = {a.get("ad_id") for a in existing_ads if a.get("ad_id")}
    new_aq_ads = []
    aq_candidates = []

    for src in AQARMAP_SOURCES:
        max_p = src.get("max_p", 3)
        for page in range(1, max_p + 1):
            page_url = src["url"] if page == 1 else f"{src['url']}&page={page}"
            html, status_info, _ = fetcher.get_html(page_url, req_regex=r'/ar/listing/\d+')
            found_aq = extract_aqarmap_candidates_from_search_html(html, src, seen_ids, extra_checked, banned_ids)
            aq_candidates.extend(found_aq)
            print(f"[AqarMap] {src['en']} p.{page} -> {status_info} (Non-Company Candidates: {len(found_aq)})")
            time.sleep(random.uniform(0.4, 0.8))

    save_persistent_seen_ids(extra_checked)

    rent_aq = [x for x in aq_candidates if x["deal"] == "إيجار"]
    sale_aq = [x for x in aq_candidates if x["deal"] != "إيجار"]
    all_candidates = rent_aq[:180] + sale_aq[:180]
    print(f"\n[AqarMap Full-Power v10.0] Total Non-Company Candidates: {len(aq_candidates)} | Inspecting: {len(all_candidates)}")

    aq_added = 0
    total_c = len(all_candidates)

    for idx, item in enumerate(all_candidates, 1):
        uid = item["ad_id"]
        num_str = item.get("num_str", "")
        try:
            html, st_ad, final_url = fetcher.get_html(item["url"], require_listing_url=True)
            if st_ad == "Redirected_To_Search":
                extra_checked.add(uid)
                print(f"  [{idx}/{total_c}] [- REJECTED AqarMap] Redirected to Search Page (Deleted Ad)")
                continue
            if not html:
                continue

            info, reason = extract_aqarmap_details(html, item["deal"], num_str, final_url)

            if reason != "Empty title":
                extra_checked.add(uid)
                if idx % 15 == 0:
                    save_persistent_seen_ids(extra_checked)

            if not info:
                print(f"  [{idx}/{total_c}] [- REJECTED AqarMap] {reason}")
                continue

            is_owner, ai_reason = analyze_with_ai(
                info["title"], info["body_text"], info["pub_name"],
                item["deal"], item["cat"], info["price_num"], "عقارماب"
            )
            if not is_owner:
                print(f"  [{idx}/{total_c}] [- REJECTED AqarMap] {ai_reason}")
                continue

            real_post_ts = int(info.get("real_ts") or time.time())
            now_cairo = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
            verified_url = info.get("canonical_url") or final_url
            new_aq_ads.append({
                "ad_id": uid,
                "id": f"ext_{uid}",
                "source": "عقارماب",
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
                "verified_aq_v98": True,
                "verified_aq_v100": True,
                "url": verified_url,
                "link": verified_url,
                "verified_v12": True,
                "scraped_at": now_cairo,
                "date": datetime.fromtimestamp(real_post_ts, CAIRO_TZ).strftime("%Y-%m-%d %H:%M")
            })
            aq_added += 1
            print(f"  [{idx}/{total_c}] [+ ACCEPTED <=2D AQARMAP OWNER] ({info['age_label']}) | {info['pub_name']} ({info['pub_ads']} ads) | Price: {info['price_num']:,} EGP | ID: EG-{num_str}")
            if aq_added == 1 or aq_added % 2 == 0:
                existing_ads, _ = sync_ads_to_github_now(data, new_aq_ads, existing_ads, extra_checked, tg_cfg, notified_ids, run_report, f"Added +{aq_added} Verified AqarMap Owners")
            time.sleep(random.uniform(0.5, 0.8))
        except Exception:
            continue

    save_persistent_seen_ids(extra_checked)
    merged_ads, aq_total = sync_ads_to_github_now(data, new_aq_ads, existing_ads, extra_checked, tg_cfg, notified_ids, run_report, f"AqarMap Cycle Complete (+{aq_added} New)")
    print(f"=== AqarMap Cycle Complete: Added +{aq_added} New Owners | Total Verified AqarMap Owners on Site: {aq_total} ===")

def main():
    if os.environ.get("GITHUB_ACTIONS"):
        run_extra_radar()
        return
    print("=== Starting 24/7 Dedicated AqarMap Full-Power Radar v10.0 (Anti-Redirect + EG-ID Verified + <=2 Days) ===")
    cycle = 1
    while True:
        print(f"\n>>> Starting AqarMap Cycle #{cycle} at {datetime.now().strftime('%H:%M:%S')} <<<")
        try:
            run_extra_radar()
        except Exception as e:
            print(f"[AqarMap Radar Error] {e}")
        cycle += 1
        print(f"[Auto-Loop] Sleeping for {AUTO_LOOP_MINUTES} minutes (with 30s Anti-Overwrite Guard active)...")
        for _ in range(AUTO_LOOP_MINUTES * 2):
            time.sleep(30)
            guard_aqarmap_ads_during_sleep()

if __name__ == "__main__":
    main()
