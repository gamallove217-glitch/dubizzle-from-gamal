import os, sys, re, json, time, random, stat, subprocess, threading, hashlib
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from DrissionPage import ChromiumPage, ChromiumOptions

if sys.platform.startswith("win"):
    try:
        import winsound
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        winsound = None
else:
    winsound = None

AI_SERVER_URL = "https://gamal216.pythonanywhere.com"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ads.json")
SEEN_FILE = os.path.join(BASE_DIR, "seen_links_local.json")
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.json")
PROFILE_DIR = os.path.join(BASE_DIR, "chrome_clean_profile")

MAX_ADS_STORED = 450
MAX_CANDIDATES_PER_RUN = 140
MAX_WORKERS = 3
AUTO_LOOP_MINUTES = 45
STATE_LOCK = threading.Lock()
BROWSER_LOCK = threading.Lock()
TURNSTILE_LOCK = threading.Lock()
ESC_QUOTE = chr(92) + '"'

DUBIZZLE_SOURCES = [
    {"cat_key": "apt", "cat": "شقق", "deal": "إيجار", "en": "Apartments (Rent)", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/"},
    {"cat_key": "apt", "cat": "شقق", "deal": "تمليك", "en": "Apartments (Sale)", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/"},
    {"cat_key": "villa", "cat": "فلل", "deal": "إيجار", "en": "Villas (Rent)", "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/"},
    {"cat_key": "villa", "cat": "فلل", "deal": "تمليك", "en": "Villas (Sale)", "url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/"},
    {"cat_key": "comm", "cat": "تجاري", "deal": "إيجار", "en": "Commercial (Rent)", "url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/"},
    {"cat_key": "comm", "cat": "تجاري", "deal": "تمليك", "en": "Commercial (Sale)", "url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/"},
    {"cat_key": "land", "cat": "أراضي", "deal": "AUTO", "en": "Buildings & Lands (Sale/Rent)", "url": "https://www.dubizzle.com.eg/properties/buildings-lands-for-sale/new-cairo/"}
]

ZONE_MAPPING = {"النرجس": "النرجس", "نرجس": "النرجس", "الياسمين": "الياسمين", "ياسمين": "الياسمين", "البنفسج": "البنفسج", "بنفسج": "البنفسج", "اللوتس": "اللوتس", "لوتس": "اللوتس", "الأندلس": "الأندلس", "الاندلس": "الأندلس", "اندلس": "الأندلس", "القرنفل": "القرنفل", "قرنفل": "القرنفل", "تمر حنة": "التمر حنة", "التمر حنة": "التمر حنة", "جاردينيا": "جاردينيا", "جنوب الأكاديمية": "جنوب الأكاديمية", "جنوب الاكاديمية": "جنوب الأكاديمية", "شرق الأكاديمية": "شرق الأكاديمية", "شرق الاكاديمية": "شرق الأكاديمية", "المستثمرين": "المستثمرين", "الشويفات": "الشويفات", "شويفات": "الشويفات", "أبو الهول": "أبو الهول", "ابو الهول": "أبو الهول", "دار مصر": "دار مصر", "سكن مصر": "سكن مصر", "جنة": "جنة مصر", "القطامية": "القطامية", "قطامية": "القطامية", "التسعين": "شارع التسعين", "شارع التسعين": "شارع التسعين", "ميفيدا": "ميفيدا", "هايد بارك": "هايد بارك", "ماونتن فيو": "ماونتن فيو", "التجمع الأول": "التجمع الأول", "التجمع الاول": "التجمع الأول", "التجمع الثالث": "التجمع الثالث", "التجمع الخامس": "التجمع الخامس"}
FORBIDDEN_ZONES = ["الرحاب", "رحاب", "rehab", "مدينتي", "مدينتى", "madinaty", "المستقبل", "mostakbal", "سمات", "بيت الوطن", "بيت وطن", "beit al watan", "beit el watan", "bayt al watan", "النورث هاوس", "شمال الرحاب", "العبور", "الشروق", "مدينة بدر", "مدينه بدر", "هليوبوليس الجديدة", "العاصمة الإدارية", "العاصمه الاداريه", "العاشر من رمضان", "6 أكتوبر", "أكتوبر", "الشيخ زايد", "زايد", "المعادي", "زهراء المعادي", "المقطم", "الهضبة الوسطى", "مدينة نصر", "مصر الجديدة", "شيراتون", "النزهة", "عين شمس", "السلام", "جسر السويس", "حدائق القبة", "المرج", "شبرا", "حلوان", "15 مايو", "الزمالك", "المهندسين", "الدقي", "العجوزة", "الهرم", "فيصل", "حدائق الأهرام", "حدائق الاهرام", "حدائق أكتوبر", "الساحل الشمالي", "العين السخنة", "مقبرة", "مقابر", "مدفن", "مدافن", "جبانة", "طريق السخنة"]
INSTALLMENT_KEYWORDS = ["قسط", "تقسيط", "بالتقسيط", "أقساط", "اقساط", "تسهيلات", "فترة سداد", "سنوات سداد", "بمقدم", "مقدم", "دفعة", "دفعات", "الدفعة المقدمة", "متبقي", "المتبقي", "أوفر", "اوفر", "أوفر برايس", "down payment", "downpayment", "installment", "installments", "payment plan"]
CASH_NEGATIONS = ["بدون تقسيط", "لا يوجد تقسيط", "ممنوع التقسيط", "وليس تقسيط", "مش تقسيط", "بدون أقساط", "بدون اقساط", "خالص الثمن", "خالصة الثمن", "خالصه الثمن", "ليس عليها أقساط", "ليس عليها اقساط", "لا يوجد أقساط", "لا يوجد اقساط", "مسدد بالكامل", "مسددة بالكامل", "مسدده بالكامل", "غير متاح تقسيط", "البيع كاش فقط", "كاش فقط", "كاش ولا تقبل التمويل", "كاش نهائي"]
COMPANY_NAME_KEYWORDS = ["شركه", "شركة", "عقارات", "للعقارات", "تسويق", "للتسويق", "مكتب", "استثمار", "تطوير", "جروب", "هوم", "هاوس", "بروكر", "ريال استيت", "استيت", "فيرتكس", "روي", "ايكو", "إيكو", "كابيتال", "كونسلت", "للاستشارات", "إعمار", "معمار", "vertex", "echo", "roy real", "real estate", "realestate", "estate", "estates", "realty", "properties", "property", "broker", "brokers", "brokerage", "agency", "group", "developments", "development", "investment", "investments", "hub", "home", "homes", "house", "egypt", "capital", "consultant", "consultancy", "consulting", "prime", "elite", "empire", "avenue", "landmark", "residence", "living", "towers", "tower"]
BROKER_DESC_PHRASES = ["لماذا تختار شركتنا", "شركتنا", "شركة عقارات", "شركه عقارات", "شركة تسويق", "شركه تسويق", "فيرتكس استيت", "vertex estate", "فريق من الخبراء", "مجموعة متنوعة من الشقق", "مجموعه متنوعه من الشقق", "تقع عقاراتنا", "زيارة معروضاتنا", "لو حابب تعرض معانا", "تعرض معانا وحدتك", "لدينا شقق", "متاح لدينا شقق", "متاح لدينا فيلات", "يوجد لدينا شقق", "يوجد لدينا فيلات", "لدينا أكثر من", "متاح لدينا اكثر من", "عمولة المكتب", "عموله المكتب", "عمولة الشركة", "عموله الشركه", "مكتب عمل جماعي", "غرف خاصه للشركات", "تظهر شركتكم بصوره", "كود الوحدة", "كود الوحده", "كود الشقة", "كود الشقه", "كود العقار", "كود الفيلا", "للتواصل مع قسم المبيعات", "مساحات مختلفة", "مساحات مختلفه", "متوفر لدينا وحدات", "متاح لدينا وحدات"]
BANNED_AD_IDS = {503407019, 504430732, 503219833}
HINDI_MAP = str.maketrans({"٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9", "٬": ",", "،": ",", "٫": "."})
FRONTEND_SCHEMA = {"wrap_object": True, "cat_map": {"apt": "شقق", "villa": "فلل", "comm": "تجاري", "land": "أراضي"}, "deal_map": {"rent": "إيجار", "sale": "تمليك"}}

def normalize_ar(text):
    if not text: return ""
    t = str(text).translate(HINDI_MAP).lower()
    t = re.sub(r'[\u0640\u064B-\u065F]', '', t)
    t = re.sub(r'[إأآا]', 'ا', t)
    t = re.sub(r'ة', 'ه', t)
    t = re.sub(r'ى', 'ي', t)
    return re.sub(r'\s+', ' ', t).strip()

def inspect_local_frontend_schema():
    idx_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(idx_path):
        try:
            with open(idx_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
            cat_sel = soup.find("select", {"id": "catFilter"})
            if cat_sel:
                for opt in cat_sel.find_all("option"):
                    val = (opt.get("value") or "").strip()
                    if not val or val == "ALL": continue
                    txt = normalize_ar(opt.get_text(" ", strip=True) + " " + val)
                    if "شقق" in txt: FRONTEND_SCHEMA["cat_map"]["apt"] = val
                    elif "فلل" in txt or "فيلات" in txt: FRONTEND_SCHEMA["cat_map"]["villa"] = val
                    elif "تجار" in txt: FRONTEND_SCHEMA["cat_map"]["comm"] = val
                    elif "اراض" in txt or "مبان" in txt: FRONTEND_SCHEMA["cat_map"]["land"] = val
            deal_sel = soup.find("select", {"id": "dealFilter"})
            if deal_sel:
                for opt in deal_sel.find_all("option"):
                    val = (opt.get("value") or "").strip()
                    if not val or val == "ALL": continue
                    txt = normalize_ar(opt.get_text(" ", strip=True) + " " + val)
                    if "ايجار" in txt: FRONTEND_SCHEMA["deal_map"]["rent"] = val
                    elif "تمليك" in txt or "بيع" in txt or "كاش" in txt: FRONTEND_SCHEMA["deal_map"]["sale"] = val
        except Exception:
            pass
    for src in DUBIZZLE_SOURCES:
        ck = src["cat_key"]
        if ck in FRONTEND_SCHEMA["cat_map"]: src["cat"] = FRONTEND_SCHEMA["cat_map"][ck]
        if src["deal"] in ("إيجار", "ايجار"): src["deal"] = FRONTEND_SCHEMA["deal_map"]["rent"]
        elif src["deal"] in ("تمليك", "بيع"): src["deal"] = FRONTEND_SCHEMA["deal_map"]["sale"]
    print(f"[Schema Sync] Categories: {FRONTEND_SCHEMA['cat_map']} | Deals: {FRONTEND_SCHEMA['deal_map']} | Loop: {AUTO_LOOP_MINUTES}m")

def clear_git_locks():
    git_dir = os.path.join(BASE_DIR, ".git")
    for rel in ["index.lock", "HEAD.lock", "config.lock", os.path.join("refs", "heads", "main.lock")]:
        p = os.path.join(git_dir, rel)
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass

def fix_git_identity_for_vercel():
    clear_git_locks()
    real_name, real_email = "gamallove217-glitch", "gamallove217@gmail.com"
    try:
        res = subprocess.run(["git", "log", "-n", "50", "--format=%an|%ae"], cwd=BASE_DIR, capture_output=True, text=True, timeout=10)
        for line in (res.stdout or "").splitlines():
            if "|" in line:
                n, e = line.strip().split("|", 1)
                if e and "radar.local" not in e.lower() and "@" in e:
                    real_name, real_email = n.strip(), e.strip()
                    break
    except Exception:
        pass
    subprocess.run(["git", "config", "user.name", real_name], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", real_email], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def format_elapsed_arabic(minutes_ago):
    if minutes_ago < 60:
        return f"منذ {max(1, int(minutes_ago))} دقيقة"
    return f"منذ {max(1, int(round(minutes_ago / 60.0)))} ساعة"

def parse_dubizzle_age_info(text, unescaped_json=""):
    now_ts = int(time.time())
    if text:
        norm = normalize_ar(text)
        m_old_w = re.search(r'(?:(\d+)\s*(?:اسبوع|اسابيع|شهر|شهور|اشهر|سنه|سنوات)\s*مضت|(?:منذ|قبل)\s*(?:\d+\s*)?(?:اسبوع|اسابيع|اسبوعين|شهر|شهور|اشهر|سنه|سنوات)|\b(?:\d+|a|an)\s*(?:weeks?|months?|years?)\s*ago\b)', norm, re.I)
        if m_old_w: return False, f"Old Ad ({m_old_w.group(0)})", 99999, now_ts - 604800, True

        m_old_d = re.search(r'(?:([2-9]|\d{2,})\s*(?:ايام|يوم)\s*مضت|يومين\s*مضت|(?:منذ|قبل)\s*([2-9]|\d{2,})\s*(?:ايام|يوم)|(?:منذ|قبل)\s*يومين|\b([2-9]|\d{2,})\s*days?\s*ago\b)', norm, re.I)
        if m_old_d: return False, f"Old Ad ({m_old_d.group(0)})", 99999, now_ts - 172800, True

        m_hr = re.search(r'(?:(\d{1,2})\s*(?:ساعه|ساعات)\s*مضت|(\d{1,2})\s*قبل\s*(?:ساعه|ساعات)|(?:منذ|قبل)\s*(\d{1,2})\s*(?:ساعه|ساعات)|\b(\d{1,2})\s*(?:hours?|hrs?)\s*ago\b)', norm, re.I)
        if m_hr:
            val = int(next(g for g in m_hr.groups() if g is not None))
            if val > 24: return False, f"Old Ad ({val}h > 24h)", val * 60, now_ts - (val * 3600), True
            return True, f"منذ {val} ساعة", val * 60, now_ts - (val * 3600), True

        if re.search(r'(?:ساعتين\s*مضت|(?:منذ|قبل)\s*ساعتين)', norm):
            return True, "منذ 2 ساعة", 120, now_ts - 7200, True
        if re.search(r'(?:ساعه\s*مضت|(?:منذ|قبل)\s*ساعه\b|\b(?:an|1)\s*hour\s*ago\b)', norm):
            return True, "منذ 1 ساعة", 60, now_ts - 3600, True

        m_min = re.search(r'(?:(\d{1,3})\s*(?:دقيقه|دقائق|دقايق)\s*مضت|(\d{1,3})\s*قبل\s*(?:دقيقه|دقائق|دقايق)|(?:منذ|قبل)\s*(\d{1,3})\s*(?:دقيقه|دقائق|دقايق)|\b(\d{1,3})\s*(?:minutes?|mins?)\s*ago\b)', norm, re.I)
        if m_min:
            val = int(next(g for g in m_min.groups() if g is not None))
            return True, f"منذ {val} دقيقة", max(1, val), now_ts - (val * 60), True

        if re.search(r'(?:دقيقتين\s*مضت|(?:منذ|قبل)\s*دقيقتين)', norm):
            return True, "منذ 2 دقيقة", 2, now_ts - 120, True
        if re.search(r'(?:دقيقه\s*مضت|(?:منذ|قبل)\s*دقيقه\b)', norm):
            return True, "منذ 1 دقيقة", 1, now_ts - 60, True

        m_sec = re.search(r'(?:(\d+)\s*(?:ثانيه|ثواني|ثوان)\s*مضت|(?:منذ|قبل)\s*(\d+)\s*(?:ثانيه|ثواني|ثوان)|\b(\d+)\s*(?:seconds?|secs?)\s*ago\b|\bالان\b|\bحالا\b|\bjust\s*now\b)', norm, re.I)
        if m_sec:
            return True, "منذ 1 دقيقة", 1, now_ts - 60, True

        if re.search(r'(?:1\s*يوم\s*مضت|يوم\s*مضت|1\s*قبل\s*يوم|(?:منذ|قبل)\s*(?:1\s*يوم|يوم\s*واحد|يوم\b)|\bامس\b|\byesterday\b)', norm, re.I):
            return True, "منذ 24 ساعة", 1440, now_ts - 86400, True

    if unescaped_json:
        m_iso = re.search(r'"(?:datePublished|listedAt)"\s*:\s*"(202\d-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+\-]\d{2}:?\d{2})?)"', unescaped_json)
        if m_iso:
            try:
                iso_s = m_iso.group(1).replace("Z", "+00:00")
                dt = datetime.fromisoformat(iso_s)
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                post_ts = int(dt.timestamp())
                mins_ago = int(max(60, now_ts - post_ts) // 60)
                if mins_ago > 1440:
                    return False, f"Old Ad ({mins_ago // 60}h > 24h)", mins_ago, post_ts, True
                return True, format_elapsed_arabic(mins_ago), mins_ago, post_ts, True
            except Exception:
                pass

    return True, "منذ ساعة", 60, now_ts - 3600, False

def is_company_like_name(name):
    norm = normalize_ar(name)
    if not norm or norm == normalize_ar("مالك مباشر"): return False
    for k in COMPANY_NAME_KEYWORDS:
        nk = normalize_ar(k)
        if len(nk) <= 3:
            if re.search(rf'\b{re.escape(nk)}\b', norm): return True
        elif nk in norm: return True
    if re.search(r'\b(?:real|estate|properties|property|broker|agency|group|developments|investment|homes|house|capital|consultant|prime|elite|empire|echo|roy|vertex)\b', norm, re.I):
        return True
    return False

def has_broker_copywriting(title, desc):
    norm_t = normalize_ar(f"{title} {desc}")
    for phrase in BROKER_DESC_PHRASES:
        if normalize_ar(phrase) in norm_t: return True, phrase
    return False, ""

def get_numeric_ad_id(url, html=""):
    m_url = re.search(r'ID(\d{6,12})', str(url), re.I)
    if m_url: return int(m_url.group(1))
    if html:
        m_html = re.search(r'(?:رقم\s*الإعلان|رقم\s*الاعلان|معرف\s*الإعلان|Ad\s*ID)\s*[:\-]?\s*(\d{6,12})', html.translate(HINDI_MAP), re.I)
        if m_html: return int(m_html.group(1))
    return int(hashlib.md5(str(url).encode("utf-8")).hexdigest()[:8], 16)

def clean_publisher_name(name):
    if not name: return "مالك مباشر"
    s = re.sub(r'<[^>]+>', ' ', str(name))
    s = re.sub(r'(?:path\s+d=|M\d+\.\d+|viewBox|xmlns|svg|fill=|رؤية\s*ملف|View\s*profile|تم\s*النشر\s*بواسطة|تم\s*النشر\s*بواسطه|الناشر|المعلن|عضو\s*منذ.*|الإعلانات\s*النشطة.*|الاعلانات\s*النشطه.*|إعلانات\s*نشطة.*|اعلانات\s*نشطه.*|\(\d+.*?\)|\(دوبيزل\))', ' ', s, flags=re.I)
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip(" -_|:,><.")
    words = s.split()
    half = len(words) // 2
    if half >= 1 and len(words) % 2 == 0 and [w.lower() for w in words[:half]] == [w.lower() for w in words[half:]]:
        s = " ".join(words[:half])
    if not s or len(s) < 2 or len(s) > 55 or re.search(r'[<>{}\[\]=/\\]', s):
        return "مالك مباشر"
    return s

def detect_sub_zone(full_text):
    for key, official in ZONE_MAPPING.items():
        if normalize_ar(key) in normalize_ar(full_text): return official
    return "القاهرة الجديدة"

def extract_local_specs(main_text, combined_blob):
    area, rooms = None, None
    clean_t = main_text.translate(HINDI_MAP)
    m_area = re.search(r'(\d{2,6})\s*(?:م٢|م2|متر\s*مربع|متر|sqm|m2)\b', clean_t, re.I)
    if m_area and 20 <= int(m_area.group(1)) <= 100000: area = str(int(m_area.group(1)))
    else:
        m_aj = re.search(r'"(?:ft|area|size|surface)"\s*:\s*"?(\d{2,6})"?', combined_blob, re.I)
        if m_aj and 20 <= int(m_aj.group(1)) <= 100000: area = str(int(m_aj.group(1)))
    m_rooms = re.search(r'(\d{1,2})\s*(?:غرف\s*نوم|غرفه\s*نوم|غرف|غرفة|أسرة|اسره|سرير|bedrooms|beds)\b', clean_t, re.I)
    if m_rooms and 1 <= int(m_rooms.group(1)) <= 20: rooms = str(int(m_rooms.group(1)))
    else:
        m_rj = re.search(r'"(?:rooms|bedrooms|beds)"\s*:\s*"?(\d{1,2})"?', combined_blob, re.I)
        if m_rj and 1 <= int(m_rj.group(1)) <= 20: rooms = str(int(m_rj.group(1)))
    return area, rooms

def parse_price_strict(raw_val, deal_norm="تمليك"):
    if not raw_val: return 0
    s = str(raw_val).translate(HINDI_MAP)
    is_rent = ("ايجار" in normalize_ar(deal_norm))
    for m in re.findall(r'\d[\d,\.]*', s):
        digits = re.sub(r'[^\d]', '', m)
        if not digits: continue
        val = int(digits)
        if is_rent and 2500 <= val <= 4000000: return val
        if not is_rent and 1000000 <= val <= 1500000000: return val
    return 0

def extract_best_price(full_soup, soup, main_html, combined_blob, deal):
    for meta_sel in [{"property": "product:price:amount"}, {"property": "og:price:amount"}, {"name": "twitter:data1"}]:
        tag = full_soup.find("meta", meta_sel)
        if tag and tag.get("content"):
            p = parse_price_strict(tag.get("content"), deal)
            if p > 0: return p
    for lbl in ["Price", "السعر"]:
        for el in (soup.find_all(attrs={"aria-label": lbl}) + full_soup.find_all(attrs={"aria-label": lbl})):
            p = parse_price_strict(el.get_text(" ", strip=True), deal)
            if p > 0: return p
    clean_main = main_html.translate(HINDI_MAP)
    clean_blob = combined_blob.translate(HINDI_MAP)
    for pat in [r'(?:EGP|ج\.?م|جنيه|LE)\s*(\d[\d,\.]{3,14})', r'(\d[\d,\.]{3,14})\s*(?:ج\.?م|جنيه|EGP|LE)', r'"(?:price|rawPrice|priceAmount|value)"\s*:\s*"?(\d[\d,]{4,12})"?']:
        for src_text in (clean_main, clean_blob):
            for m in re.findall(pat, src_text, re.I):
                p = parse_price_strict(m, deal)
                if p > 0: return p
    return 0

def is_forbidden_or_installment(title, desc, deal, price_num):
    raw_combined = re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', f"{title} {desc}")
    norm_text = normalize_ar(raw_combined)
    for idx, bad in enumerate(FORBIDDEN_ZONES):
        if normalize_ar(bad) in norm_text: return True, f"Forbidden Zone (#{idx+1})"
    is_brk_txt, brk_phrase = has_broker_copywriting(title, desc)
    if is_brk_txt: return True, f"Company Copywriting ({brk_phrase})"
    if "ايجار" not in normalize_ar(deal):
        if 0 < int(price_num or 0) < 1200000: return True, f"Downpayment Price ({price_num})"
        temp = norm_text
        for neg in CASH_NEGATIONS: temp = temp.replace(normalize_ar(neg), " ")
        for inst in INSTALLMENT_KEYWORDS:
            if normalize_ar(inst) in temp: return True, "Installment Ad"
        if re.search(r'\b\d+\s*%\s*(مقدم|تعاقد|دفعه|down)', temp): return True, "Installment % Downpayment"
    return False, "OK"

def strip_related_ads_section(html):
    for marker in ["إعلانات مشابهة", "إعلانات ذات صلة", "Related ads", "Similar ads"]:
        idx = html.find(marker)
        if idx > 1500: return html[:idx]
    return html

def is_turnstile_in_html(html):
    if not html: return False
    if "يرجى تأكيد أنك زائر حقيقي" in html or "حدد المربع أدناه" in html: return True
    if "التحقق الأمني" in html and "تأكيد أنك إنسان" in html: return True
    if "<title>Just a moment" in html[:3000]: return True
    return False

def extract_dubizzle_links_from_html(html, prefilter_cards=False):
    results, seen_u = [], set()
    if not html or is_turnstile_in_html(html): return results
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].split("#")[0].strip()
        if "/ad/" in href and len(href) > 15:
            full = href if href.startswith("http") else f"https://www.dubizzle.com.eg{href}"
            if full in seen_u: continue
            card_age, age_mins, real_ts = "منذ ساعة", 60, int(time.time()) - 3600
            if prefilter_cards:
                card = a.find_parent("article") or a.find_parent("li") or (a.parent.parent if a.parent else a)
                card_txt = ""
                if card:
                    c_date_el = card.find(attrs={"aria-label": "Creation date"}) or card.find(attrs={"aria-label": "تاريخ النشر"})
                    age_target_txt = c_date_el.get_text(" ", strip=True) if c_date_el else card.get_text(" ", strip=True)
                    card_txt = card.get_text(" ", strip=True)
                else:
                    age_target_txt = ""
                is_fresh, age_lbl, age_mins, real_ts, _ = parse_dubizzle_age_info(age_target_txt)
                if not is_fresh: continue
                card_age = age_lbl
                norm_c = normalize_ar(re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', card_txt))
                if "الدفعه المقدمه" in norm_c or "طريقه الدفع تقسيط" in norm_c or "down payment" in norm_c: continue
                if any(normalize_ar(bz) in norm_c for bz in FORBIDDEN_ZONES): continue
            seen_u.add(full)
            results.append((full, card_age, age_mins, real_ts))
    if not prefilter_cards and not results:
        for m in re.findall(r'((?:https?://(?:www\.)?dubizzle\.com\.eg)?/[a-zA-Z0-9_\-/]+/ad/[^\s"\'<>]+)', html):
            clean_u = m.split("?")[0].split("#")[0].strip()
            full_u = clean_u if clean_u.startswith("http") else f"https://www.dubizzle.com.eg{clean_u}"
            if full_u not in seen_u and len(full_u) > 30:
                seen_u.add(full_u)
                results.append((full_u, "منذ ساعة", 60, int(time.time()) - 3600))
    return results

class SmartHybridEngine:
    def __init__(self):
        self.page = None
        self.land_url_resolved = False

    def get_live_dom(self):
        if not self.page: return ""
        try:
            with BROWSER_LOCK:
                return self.page.run_js("return document.documentElement ? document.documentElement.outerHTML : '';") or ""
        except Exception:
            return ""

    def try_auto_solve_turnstile(self):
        if not self.page: return
        try:
            with BROWSER_LOCK:
                for iframe in self.page.eles("tag:iframe"):
                    src = str(iframe.attr("src") or "").lower()
                    title_attr = str(iframe.attr("title") or "").lower()
                    if any(k in src or k in title_attr for k in ("cloudflare", "turnstile", "challenge", "widget")):
                        try:
                            self.page.actions.move_to(iframe, offset_x=-95, offset_y=0).click()
                            return
                        except Exception: pass
                for txt in ["تأكيد أنك إنسان", "Verify you are human"]:
                    el = self.page.ele(f"text:{txt}", timeout=0.5)
                    if el:
                        try:
                            self.page.actions.move_to(el, offset_x=65, offset_y=0).click()
                            return
                        except Exception: pass
        except Exception:
            pass

    def wait_until_turnstile_cleared(self, max_wait_loops=35):
        if not self.page: return False
        with TURNSTILE_LOCK:
            time.sleep(1.5)
            for attempt in range(max_wait_loops):
                dom_now = self.get_live_dom()
                if not is_turnstile_in_html(dom_now) and ("/ad/" in dom_now or len(dom_now) > 25000):
                    time.sleep(2.0)
                    return True
                if attempt == 0:
                    print("[Security Solver] Turnstile detected! Attempting gentle click (or click once manually in Chrome)...")
                if attempt in (1, 5, 10):
                    self.try_auto_solve_turnstile()
                if attempt == 4 and winsound:
                    try: winsound.Beep(1000, 400)
                    except Exception: pass
                time.sleep(2.5)
            return not is_turnstile_in_html(self.get_live_dom())

    def ensure_anchor_browser(self, test_url):
        if self.page is not None:
            try:
                with BROWSER_LOCK: _ = self.page.run_js("return location.href;")
                if is_turnstile_in_html(self.get_live_dom()): self.wait_until_turnstile_cleared()
                return True
            except Exception:
                self.page = None
        try:
            os.makedirs(PROFILE_DIR, exist_ok=True)
            co = ChromiumOptions()
            for c in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")]:
                if os.path.exists(c):
                    co.set_browser_path(c)
                    break
            co.set_paths(local_port=9555, user_data_path=PROFILE_DIR)
            co.mute(True)
            self.page = ChromiumPage(addr_or_opts=co)
            with BROWSER_LOCK:
                cur_u = str(self.page.run_js("return location.href || '';") or "").lower()
            cur_dom = self.get_live_dom()
            if "dubizzle.com.eg" not in cur_u or len(cur_dom) < 5000:
                with BROWSER_LOCK: self.page.get(test_url, timeout=15)
            self.wait_until_turnstile_cleared(max_wait_loops=40)
            links_now = extract_dubizzle_links_from_html(self.get_live_dom(), prefilter_cards=False)
            print(f"[Engine] Anchor tab verified ready & clean! ({len(links_now)} ads visible)")
            return True
        except Exception as e:
            print(f"[Browser Port 9555 Info] {e}")
            return False

    def discover_land_slug_from_html(self, html):
        if self.land_url_resolved or not html: return
        for slug in re.findall(r'/properties/([a-z0-9\-]+)/', html, re.I):
            sl = slug.lower()
            if ("land" in sl or "building" in sl) and "new-cairo" not in sl:
                for src in DUBIZZLE_SOURCES:
                    if src["cat_key"] == "land":
                        src["url"] = f"https://www.dubizzle.com.eg/properties/{slug}/new-cairo/"
                        self.land_url_resolved = True
                        return

    def warmup(self):
        print("[Engine] Attaching to persistent Chrome session on port 9555 (Kept open 24/7)...")
        self.ensure_anchor_browser(DUBIZZLE_SOURCES[0]["url"])
        self.discover_land_slug_from_html(self.get_live_dom())

    def browser_background_fetch_single(self, url):
        time.sleep(random.uniform(0.45, 1.10))
        if not self.page and not self.ensure_anchor_browser(DUBIZZLE_SOURCES[0]["url"]): return ""
        if is_turnstile_in_html(self.get_live_dom()): self.wait_until_turnstile_cleared(max_wait_loops=35)
        req_id = f"req_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        js_start = """
        window.__fetches = window.__fetches || {};
        const reqId = arguments[0];
        const targetUrl = arguments[1];
        window.__fetches[reqId] = { done: false, status: 0, html: '' };
        (async () => {
            try {
                const r = await fetch(targetUrl, {
                    method: 'GET',
                    credentials: 'include',
                    headers: {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
                });
                window.__fetches[reqId].status = r.status;
                window.__fetches[reqId].html = await r.text();
            } catch (e) { window.__fetches[reqId].status = -1; }
            window.__fetches[reqId].done = true;
        })();
        return true;
        """
        try:
            with BROWSER_LOCK: self.page.run_js(js_start, req_id, url)
            for _ in range(35):
                time.sleep(0.25)
                with BROWSER_LOCK:
                    res_state = self.page.run_js(
                        "const f = (window.__fetches && window.__fetches[arguments[0]]); "
                        "if (!f || !f.done) return null; "
                        "const out = {status: f.status, html: f.html}; "
                        "delete window.__fetches[arguments[0]]; "
                        "return out;",
                        req_id
                    )
                if res_state and isinstance(res_state, dict):
                    st = int(res_state.get("status") or 0)
                    h = res_state.get("html") or ""
                    if st in (403, 429, 503) or is_turnstile_in_html(h):
                        with TURNSTILE_LOCK:
                            with BROWSER_LOCK: self.page.get(url, timeout=15)
                            self.wait_until_turnstile_cleared(max_wait_loops=40)
                            return self.get_live_dom()
                    return h
        except Exception:
            pass
        finally:
            try:
                with BROWSER_LOCK: self.page.run_js("if (window.__fetches) delete window.__fetches[arguments[0]];", req_id)
            except Exception: pass
        return ""

    def fetch_html(self, url, is_warmup=False):
        for attempt in range(3):
            h = self.browser_background_fetch_single(url)
            if h and not is_turnstile_in_html(h) and len(h) > 5000:
                if not self.land_url_resolved: self.discover_land_slug_from_html(h)
                return h
            if attempt == 1: self.wait_until_turnstile_cleared(max_wait_loops=25)
            time.sleep(1.5)
        return ""

    def get_category_links(self, url, label="", is_land=False):
        raw_pairs, fresh_pairs = [], []
        urls_to_try = [url]
        if is_land and "?page=" not in url:
            urls_to_try.extend(["https://www.dubizzle.com.eg/properties/buildings-lands/new-cairo/", "https://www.dubizzle.com.eg/properties/land-for-sale/new-cairo/"])
        for attempt in range(3):
            for u_try in urls_to_try:
                html = self.fetch_html(u_try, is_warmup=False)
                raw_pairs = extract_dubizzle_links_from_html(html, prefilter_cards=False)
                fresh_pairs = extract_dubizzle_links_from_html(html, prefilter_cards=True)
                if raw_pairs:
                    if is_land:
                        for src in DUBIZZLE_SOURCES:
                            if src["cat_key"] == "land": src["url"] = u_try.split("?")[0]
                    break
            if raw_pairs: break
            if attempt == 0:
                with BROWSER_LOCK:
                    try: self.page.get(urls_to_try[0], timeout=15)
                    except Exception: pass
            self.wait_until_turnstile_cleared(max_wait_loops=25)
            time.sleep(2.0)
        print(f"[ZeroNav-Fetch] {label} -> {'200 OK' if raw_pairs else 'Empty'} (Total: {len(raw_pairs)} | Fresh <=24h & Cash: {len(fresh_pairs)})")
        return fresh_pairs

    def verify_profile_published_count(self, profile_url):
        if not profile_url: return 0, ""
        h = self.fetch_html(profile_url, is_warmup=False)
        if not h: return 0, ""
        soup = BeautifulSoup(h, "html.parser")
        prof_name = ""
        for tag_n in ("h1", "h2"):
            el_n = soup.find(tag_n)
            if el_n:
                cand = clean_publisher_name(el_n.get_text(" ", strip=True))
                if cand != "مالك مباشر":
                    prof_name = cand
                    break
        txt = normalize_ar(soup.get_text(" ", strip=True))
        unesc_h = h.replace(ESC_QUOTE, '"').translate(HINDI_MAP)
        for m_p in re.findall(r'(?:الاعلانات\s*المنشوره|اعلانات\s*منشوره|الاعلانات\s*النشطه|اعلانات\s*نشطه|published\s*ads|active\s*ads)\s*[:\-]?\s*(\d{1,5})\b', txt, re.I):
            v = int(m_p)
            if v >= 1 and not (1990 <= v <= 2035): return v, prof_name
        txt_no_yr = re.sub(r'(?:عضو\s*منذ|member\s*since)\s*\d{4}', ' ', txt)
        for m_b in re.findall(r'\b(\d{1,5})\s*(?:الاعلانات\s*المنشوره|اعلانات\s*منشوره|الاعلانات\s*النشطه|اعلانات\s*نشطه|published\s*ads|active\s*ads)', txt_no_yr, re.I):
            v = int(m_b)
            if v >= 1 and not (1990 <= v <= 2035): return v, prof_name
        for pat_j in [r'"totalAds"\s*:\s*(\d+)', r'"publishedAdsCount"\s*:\s*(\d+)', r'"activeAdsCount"\s*:\s*(\d+)', r'"adsCount"\s*:\s*(\d+)']:
            m_j = re.search(pat_j, unesc_h)
            if m_j and int(m_j.group(1)) >= 1: return int(m_j.group(1)), prof_name
        ad_links_on_prof = extract_dubizzle_links_from_html(h, prefilter_cards=False)
        return len(ad_links_on_prof), prof_name

def extract_seller_card_details(full_soup, unescaped_blob):
    pub_raw, profile_url, seller_id, is_agency = "", "", "", False
    for a_tag in full_soup.find_all("a", href=True):
        h_clean = str(a_tag["href"]).split("?")[0].rstrip("/").strip()
        m_c = re.search(r'/(?:ar/|en/)?(?:companies|agencies)/([a-zA-Z0-9_\-]{3,})', h_clean, re.I)
        if m_c and not h_clean.endswith("/companies"):
            seller_id = f"comp_{m_c.group(1)[:35]}"
            profile_url = h_clean if h_clean.startswith("http") else f"https://www.dubizzle.com.eg{h_clean}"
            is_agency = True
        m_p = re.search(r'/(?:ar/|en/)?profile/([a-zA-Z0-9_\-]{4,})', h_clean, re.I)
        if m_p:
            if not seller_id: seller_id = f"prof_{m_p.group(1)[:35]}"
            if not profile_url: profile_url = h_clean if h_clean.startswith("http") else f"https://www.dubizzle.com.eg{h_clean}"
            a_txt = a_tag.get_text(" ", strip=True)
            if a_txt and not re.search(r'رؤية\s*ملف|View\s*profile|الإعلانات|عضو\s*منذ', a_txt, re.I) and 2 <= len(a_txt) <= 50:
                pub_raw = a_txt

    for lbl_el in full_soup.find_all(string=re.compile(r'تم\s*النشر\s*بواسطة|تم\s*النشر\s*بواسطه|Posted\s*by|Listed\s*by', re.I)):
        curr = lbl_el.parent
        for _ in range(6):
            if not curr: break
            c_txt = curr.get_text(" ", strip=True)
            if not profile_url:
                for a_in in curr.find_all("a", href=True):
                    hc = str(a_in["href"]).split("?")[0].strip()
                    if any(x in hc.lower() for x in ("/profile/", "/companies/", "/users/", "/agencies/")):
                        profile_url = hc if hc.startswith("http") else f"https://www.dubizzle.com.eg{hc}"
                        if "/companies/" in hc.lower() or "/agencies/" in hc.lower(): is_agency = True
                        break
            if re.search(r'عضو\s*منذ|الإعلانات\s*النشطة|إعلانات\s*نشطة|الاعلانات\s*النشطه|اعلانات\s*نشطه|Member\s*since|Active\s*ads', c_txt, re.I):
                after_lbl = re.split(r'تم\s*النشر\s*بواسطة|تم\s*النشر\s*بواسطه|Posted\s*by|Listed\s*by', c_txt, flags=re.I)[-1]
                before_meta = re.split(r'عضو\s*منذ|الإعلانات\s*النشطة|إعلانات\s*نشطة|الاعلانات\s*النشطه|اعلانات\s*نشطه|رؤية\s*ملف|إظهار\s*الرقم|Member\s*since|Active\s*ads', after_lbl, flags=re.I)[0]
                cand_name = clean_publisher_name(before_meta)
                if cand_name != "مالك مباشر":
                    pub_raw = cand_name
                    break
            curr = curr.parent
        if pub_raw: break

    if not pub_raw:
        full_text = full_soup.get_text(" ", strip=True)
        m_ft = re.search(r'(?:تم\s*النشر\s*بواسطة|تم\s*النشر\s*بواسطه|Posted\s*by|Listed\s*by)\s*[:\-]?\s*([^\r\n]{2,55}?)\s+(?:عضو\s*منذ|الإعلانات\s*النشطة|إعلانات\s*نشطة|الاعلانات\s*النشطه|اعلانات\s*نشطه|Member\s*since|Active\s*ads)', full_text, re.I)
        if m_ft: pub_raw = clean_publisher_name(m_ft.group(1))

    if not pub_raw:
        for pat_s in [r'"(?:sellerName|contactName|agencyName|companyName)"\s*:\s*"([^"]{2,50})"', r'"(?:seller|user|agency|owner)"\s*:\s*\{[^{}]{0,300}?"name"\s*:\s*"([^"]{2,50})"']:
            m_s = re.search(pat_s, unescaped_blob, re.I)
            if m_s:
                cand = clean_publisher_name(m_s.group(1))
                if cand != "مالك مباشر":
                    pub_raw = cand
                    break

    if not profile_url:
        m_p2 = re.search(r'/(?:ar/|en/)?profile/([a-zA-Z0-9_\-]{5,})', unescaped_blob)
        if m_p2:
            seller_id = seller_id or f"prof_{m_p2.group(1)[:35]}"
            profile_url = f"https://www.dubizzle.com.eg/profile/{m_p2.group(1)}"
        m_c2 = re.search(r'/(?:ar/|en/)?companies/([a-zA-Z0-9_\-]{3,})', unescaped_blob)
        if m_c2 and m_c2.group(1).lower() not in ("new-cairo", "cairo", "egypt"):
            seller_id = seller_id or f"comp_{m_c2.group(1)[:35]}"
            profile_url = f"https://www.dubizzle.com.eg/companies/{m_c2.group(1)}"
            is_agency = True

    if not seller_id:
        m_uid = re.search(r'"(?:sellerId|userId)"\s*:\s*"?([a-zA-Z0-9_\-]{4,})"?', unescaped_blob)
        if m_uid: seller_id = f"seller_{m_uid.group(1)}"

    return clean_publisher_name(pub_raw), profile_url, seller_id, is_agency

def extract_direct_ad_info(full_html, deal, blacklist, hint_age="منذ ساعة", hint_ts=0):
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
    for d_lbl in ["Description", "الوصف"]:
        desc_el = soup.find(attrs={"aria-label": d_lbl}) or full_soup.find(attrs={"aria-label": d_lbl})
        if desc_el:
            desc = desc_el.get_text(" ", strip=True)
            break
    if not desc:
        desc_el = soup.find("div", {"data-testid": "description"}) or full_soup.find("div", {"data-testid": "description"})
        if desc_el: desc = desc_el.get_text(" ", strip=True)
    if not desc:
        og_d = full_soup.find("meta", {"property": "og:description"}) or full_soup.find("meta", {"name": "description"})
        if og_d and og_d.get("content"): desc = og_d["content"].strip()

    main_text = soup.get_text(" ", strip=True)
    full_text = full_soup.get_text(" ", strip=True)
    norm_full_text = normalize_ar(full_text)

    if deal == "AUTO":
        if re.search(r'(?:غرض\s*العقار\s*[:\-]?\s*للايجار|للايجار|for\s*rent)', normalize_ar(f"{title} {main_text[:1500]}"), re.I):
            deal = FRONTEND_SCHEMA["deal_map"]["rent"]
        else:
            deal = FRONTEND_SCHEMA["deal_map"]["sale"]

    unescaped_blob = full_html.replace(ESC_QUOTE, '"').translate(HINDI_MAP)

    creation_el = full_soup.find(attrs={"aria-label": "Creation date"}) or full_soup.find(attrs={"aria-label": "تاريخ النشر"})
    age_badge_text = creation_el.get_text(" ", strip=True) if creation_el else ""
    if not age_badge_text:
        m_badge = re.search(r'(\d{1,2}\s*(?:دقيقه|دقائق|دقايق|ساعه|ساعات|يوم|ايام)\s*مضت|\d{1,2}\s*قبل\s*(?:دقيقه|دقائق|دقايق|ساعه|ساعات|يوم)|(?:منذ|قبل)\s*\d{1,2}\s*(?:دقيقه|دقائق|دقايق|ساعه|ساعات|يوم|ايام)|(?:ساعه|ساعتين|دقيقه|دقيقتين|يوم|يومين)\s*مضت|\bامس\b)', normalize_ar(full_text[:1800]))
        if m_badge:
            age_badge_text = m_badge.group(1)

    is_fresh, detected_age, _, detected_ts, matched_exact = parse_dubizzle_age_info(age_badge_text, unescaped_json=unescaped_blob)
    if not is_fresh: return None, detected_age, None
    final_age = detected_age if matched_exact else hint_age
    final_ts = detected_ts if matched_exact else (hint_ts or int(time.time()) - 3600)

    if "طريقه الدفع تقسيط" in norm_full_text or "الدفعه المقدمه" in norm_full_text:
        if "ايجار" not in normalize_ar(deal): return None, "Installment Ad (Payment Badge)", None

    price_num = extract_best_price(full_soup, soup, main_html, unescaped_blob, deal)

    is_bad, bad_reason = is_forbidden_or_installment(title, desc, deal, price_num)
    if is_bad: return None, bad_reason, None

    publisher_clean, profile_url, seller_id, is_agency = extract_seller_card_details(full_soup, unescaped_blob)
    company_name_key = f"compname_{normalize_ar(publisher_clean)}" if is_company_like_name(publisher_clean) else ""
    safe_bl_key = seller_id or company_name_key or None

    with STATE_LOCK:
        in_bl = (seller_id and seller_id in blacklist) or (company_name_key and company_name_key in blacklist)
    if in_bl: return None, f"Blacklisted Broker ({publisher_clean})", None

    if is_agency or is_company_like_name(publisher_clean) or re.search(r'(?:company\s*profile|verified\s*business|share\s*agency\s*profile|شركة\s*موثقة|مكتب\s*عقاري)', norm_full_text, re.I):
        return None, f"Company/Agency Account ({publisher_clean})", safe_bl_key

    active_count, count_source = 0, ""
    for el in full_soup.find_all(string=re.compile(r'الإعلانات\s*النشطة|الاعلانات\s*النشطه|إعلانات\s*نشطة|اعلانات\s*نشطه|Active\s*ads', re.I)):
        for candidate_box in ([el.parent, el.parent.parent, el.parent.parent.parent] if (el.parent and el.parent.parent) else [el.parent]):
            if not candidate_box: continue
            box_txt = normalize_ar(candidate_box.get_text(" ", strip=True))
            box_txt = re.sub(r'(?:عضو\s*منذ|member\s*since)\s*\d{4}', ' ', box_txt)
            nums = [int(x) for x in re.findall(r'\b(\d{1,5})\b', box_txt) if int(x) >= 1 and not (1990 <= int(x) <= 2035)]
            if nums:
                active_count = nums[0]
                count_source = f"DOM Box ({active_count} active ads)"
                break
        if active_count > 0: break

    if active_count == 0:
        m_after = re.search(r'(?:الاعلانات\s*النشطه|اعلانات\s*نشطه|active\s*ads)\s*[:\-]?\s*(\d{1,5})\b', norm_full_text, re.I)
        if m_after and int(m_after.group(1)) >= 1:
            active_count = int(m_after.group(1))
            count_source = f"Ad Page Badge ({active_count} active ads)"

    if active_count == 0:
        no_year_text = re.sub(r'(?:عضو\s*منذ|member\s*since)\s*\d{4}', ' ', norm_full_text, flags=re.I)
        m_before = re.search(r'\b(\d{1,4})\s*(?:الاعلانات\s*النشطه|اعلانات\s*نشطه|اعلان\s*نشط|active\s*ads)', no_year_text, re.I)
        if m_before and int(m_before.group(1)) >= 1:
            active_count = int(m_before.group(1))
            count_source = f"Ad Page Text ({active_count} active ads)"

    if active_count == 0:
        for pat in [r'"activeAdsCount"\s*:\s*(\d+)', r'"active_ads_count"\s*:\s*(\d+)', r'"activeAds"\s*:\s*(\d+)', r'"listedAdsCount"\s*:\s*(\d+)', r'"userAdsCount"\s*:\s*(\d+)', r'"adsCount"\s*:\s*(\d+)', r'"totalAds"\s*:\s*(\d+)']:
            m_j = re.search(pat, unescaped_blob)
            if m_j and int(m_j.group(1)) >= 1:
                active_count = int(m_j.group(1))
                count_source = f"JSON ({active_count} active ads)"
                break

    if active_count >= 5:
        return None, f"Broker Count ({publisher_clean}: {active_count} active ads > 4)", safe_bl_key
    if not (1 <= active_count <= 4):
        return None, "Unverified active ads count (0 found on ad page)", None

    local_area, local_rooms = extract_local_specs(main_text, unescaped_blob)
    return {
        "title": title, "desc": desc, "price_num": price_num, "deal": deal,
        "publisher_clean": publisher_clean, "active_count": active_count,
        "count_source": count_source, "local_area": local_area, "local_rooms": local_rooms,
        "age": final_age, "real_ts": final_ts, "profile_url": profile_url, "safe_bl_key": safe_bl_key
    }, "OK", None

def inspect_ad_worker(item, engine, blacklist):
    url, cat, deal, en_label = item["url"], item["cat"], item["deal"], item["en"]
    hint_age, hint_ts = item.get("age", "منذ ساعة"), item.get("real_ts", int(time.time()) - 3600)
    html = engine.fetch_html(url, is_warmup=False)
    if not html:
        return {"url": url, "ad": None, "reason": "Failed to fetch ad HTML", "bl_key": None, "loaded": False}
    info, reason, bl_key = extract_direct_ad_info(html, deal, blacklist, hint_age=hint_age, hint_ts=hint_ts)
    if not info:
        return {"url": url, "ad": None, "reason": reason, "bl_key": bl_key, "loaded": True}

    prof_url = info.get("profile_url")
    if prof_url:
        prof_pub_count, prof_name = engine.verify_profile_published_count(prof_url)
        if prof_name and (info["publisher_clean"] == "مالك مباشر" or is_company_like_name(prof_name)):
            info["publisher_clean"] = prof_name
        if is_company_like_name(info["publisher_clean"]):
            return {"url": url, "ad": None, "reason": f"Profile Company Name ({info['publisher_clean']})", "bl_key": info.get("safe_bl_key"), "loaded": True}
        if prof_pub_count >= 5:
            return {"url": url, "ad": None, "reason": f"Profile Published Ads ({info['publisher_clean']}: {prof_pub_count} > 4)", "bl_key": info.get("safe_bl_key"), "loaded": True}
        if 1 <= prof_pub_count <= 4 and prof_pub_count > info["active_count"]:
            info["active_count"] = prof_pub_count

    if info["publisher_clean"] == "مالك مباشر" and not prof_url:
        return {"url": url, "ad": None, "reason": "Unverified Seller Identity (No Name or Profile)", "bl_key": None, "loaded": True}

    title, desc, price_num, resolved_deal = info["title"], info["desc"], info["price_num"], info["deal"]
    publisher_clean, active_count, count_source = info["publisher_clean"], info["active_count"], info["count_source"]
    ai_area, ai_rooms = info["local_area"], info["local_rooms"]

    try:
        r = requests.post(
            f"{AI_SERVER_URL}/analyze",
            json={"title": title, "description": desc, "publisher": publisher_clean, "deal": resolved_deal, "cat": cat, "price_num": price_num, "source": "دوبيزل", "active_ads_count": active_count},
            timeout=6
        )
        if r.status_code == 200:
            res = r.json()
            if res.get("decision") == "مرفوض":
                return {"url": url, "ad": None, "reason": f"AI Rejected ({publisher_clean})", "bl_key": info.get("safe_bl_key"), "loaded": True}
            if not ai_area and res.get("area"):
                m_a = re.search(r'\d+', str(res.get("area")).translate(HINDI_MAP))
                if m_a: ai_area = m_a.group(0)
            if not ai_rooms and res.get("rooms"):
                m_r = re.search(r'\d+', str(res.get("rooms")).translate(HINDI_MAP))
                if m_r: ai_rooms = m_r.group(0)
    except Exception:
        pass

    sub_zone = detect_sub_zone(f"{title} {desc}")
    price_str = f"{price_num:,} ج.م" if price_num > 0 else "السعر بالتفاصيل"
    num_id = get_numeric_ad_id(url, html)
    real_post_ts = int(info.get("real_ts") or time.time())
    ad_obj = {
        "ad_id": num_id, "id": f"dub_{num_id}", "title": title, "url": url, "link": url,
        "price": price_str, "price_num": price_num, "cat": cat, "category": cat,
        "deal": resolved_deal, "type": resolved_deal, "zone": sub_zone, "location": sub_zone,
        "source": "دوبيزل", "publisher": publisher_clean,
        "pub_ads": active_count, "active_ads_count": active_count,
        "area": ai_area, "rooms": ai_rooms, "age": info["age"], "description": desc[:500],
        "first_seen_ts": real_post_ts, "timestamp": real_post_ts,
        "date": datetime.fromtimestamp(real_post_ts).strftime("%Y-%m-%d %H:%M")
    }
    return {"url": url, "ad": ad_obj, "reason": f"Owner Verified ({count_source})", "bl_key": None, "loaded": True, "en": en_label}

def load_json_list(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, list): return d
                if isinstance(d, dict) and isinstance(d.get("ads"), list): return d["ads"]
        except Exception:
            pass
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
        except Exception:
            time.sleep(0.2)
    return False

def save_state(current_ads, seen_links_dict, blacklist_dict, push_to_github=False):
    with STATE_LOCK:
        current_ads.sort(key=lambda x: int(x.get("first_seen_ts") or 0), reverse=True)
        final_ads = current_ads[:MAX_ADS_STORED]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        payload_to_write = {"updated_at": now_str, "total": len(final_ads), "ads": final_ads}
        safe_write_json(DATA_FILE, payload_to_write)
        safe_write_json(SEEN_FILE, list(seen_links_dict.keys())[-12000:])
        safe_write_json(BLACKLIST_FILE, list(blacklist_dict.keys())[-8000:])
    if push_to_github:
        try:
            fix_git_identity_for_vercel()
            add_res = subprocess.run(["git", "add", "-f", "ads.json"], cwd=BASE_DIR, capture_output=True, text=True, timeout=15)
            if add_res.returncode != 0:
                clear_git_locks()
                subprocess.run(["git", "add", "-f", "ads.json"], cwd=BASE_DIR, capture_output=True, text=True, timeout=15)
            c_res = subprocess.run(["git", "commit", "-m", f"Live Radar Sync ({len(final_ads)} Owners at {now_str})"], cwd=BASE_DIR, capture_output=True, text=True, timeout=15)
            p_res = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=BASE_DIR, capture_output=True, text=True, timeout=30)
            if p_res.returncode != 0:
                clear_git_locks()
                subprocess.run(["git", "pull", "--rebase", "--autostash", "-X", "ours", "origin", "main"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
                p_res = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=BASE_DIR, capture_output=True, text=True, timeout=30)
            if p_res.returncode == 0:
                print(f"    --> [LIVE SYNC] Pushed {len(final_ads)} verified owners to GitHub & Vercel!")
            else:
                err_msg = (p_res.stderr or c_res.stderr or "").strip()[:140]
                print(f"    --> [GIT WARNING] Saved locally ({len(final_ads)} owners), Git message: {err_msg}")
        except Exception as e:
            print(f"    --> [LOCAL SAVE] Saved ads.json locally! (Total Owners: {len(final_ads)}) | {e}")

def normalize_cat_to_schema(raw_cat):
    nc = normalize_ar(raw_cat)
    if "شقق" in nc: return FRONTEND_SCHEMA["cat_map"]["apt"]
    if "فلل" in nc or "فيلات" in nc: return FRONTEND_SCHEMA["cat_map"]["villa"]
    if "تجار" in nc: return FRONTEND_SCHEMA["cat_map"]["comm"]
    if "اراض" in nc or "مبان" in nc: return FRONTEND_SCHEMA["cat_map"]["land"]
    return FRONTEND_SCHEMA["cat_map"]["apt"]

def normalize_deal_to_schema(raw_deal):
    nd = normalize_ar(raw_deal)
    if "ايجار" in nd: return FRONTEND_SCHEMA["deal_map"]["rent"]
    return FRONTEND_SCHEMA["deal_map"]["sale"]

def clean_and_reverify_existing_db(ads_list, engine, blacklist_dict, is_first_cycle=False):
    cleaned, seen_u = [], set()
    for ad in ads_list:
        if not isinstance(ad, dict) or ad.get("source") != "دوبيزل": continue
        u = ad.get("url") or ad.get("link") or ""
        if not u or u in seen_u or "dubizzle.com.eg" not in u: continue
        num_id = get_numeric_ad_id(u)
        if num_id in BANNED_AD_IDS or int(ad.get("ad_id") or 0) in BANNED_AD_IDS: continue
        cnt = int(ad.get("active_ads_count") or ad.get("pub_ads") or 0)
        if not (1 <= cnt <= 4): continue
        deal = normalize_deal_to_schema(ad.get("deal") or ad.get("type") or "تمليك")
        cat = normalize_cat_to_schema(ad.get("cat") or ad.get("category") or "شقق")
        p_num = parse_price_strict(ad.get("price_num") or ad.get("price"), deal)
        bad, _ = is_forbidden_or_installment(ad.get("title", ""), ad.get("description", ""), deal, p_num)
        if bad: continue
        pub_clean = clean_publisher_name(re.sub(r'\(\d+.*?\)$', '', str(ad.get("publisher", ""))).strip())
        if is_company_like_name(pub_clean): continue

        if is_first_cycle and (pub_clean == "مالك مباشر" or ad.get("age") in ("منذ ساعات", "منذ ساعة", "حديث", None)):
            print(f"[Startup Deep Audit] Re-verifying existing ad ID {num_id} (Publisher & Profile check)...")
            res = inspect_ad_worker({"url": u, "cat": cat, "deal": deal, "en": cat, "age": "منذ ساعة", "real_ts": int(ad.get("first_seen_ts") or time.time())}, engine, blacklist_dict)
            if res.get("bl_key"): blacklist_dict[res["bl_key"]] = True
            if not res.get("ad"):
                print(f"    -> [REMOVED HIDDEN BROKER] ID {num_id} rejected: {res.get('reason')}")
                continue
            ad = res["ad"]
            print(f"    -> [VERIFIED OWNER] ID {num_id} | {ad['publisher']} ({ad['pub_ads']} ads) | {ad['age']}")

        seen_u.add(u)
        cleaned.append(ad)
    return cleaned

def run_single_cycle(engine, cycle_num=1):
    inspect_local_frontend_schema()
    fix_git_identity_for_vercel()
    engine.warmup()

    raw_existing = load_json_list(DATA_FILE)
    seen_links_dict = {k: True for k in load_json_list(SEEN_FILE) if k}
    blacklist_dict = {k: True for k in load_json_list(BLACKLIST_FILE) if k and not str(k).startswith("name_")}
    current_ads = clean_and_reverify_existing_db(raw_existing, engine, blacklist_dict, is_first_cycle=(cycle_num == 1))

    existing_urls = {(a.get("url") or a.get("link")) for a in current_ads}
    for u_ex in existing_urls:
        seen_links_dict[u_ex] = True
        seen_links_dict[f"id_{get_numeric_ad_id(u_ex)}"] = True

    if cycle_num == 1:
        save_state(current_ads, seen_links_dict, blacklist_dict, push_to_github=True)

    candidate_urls = set()
    all_raw_candidates = []
    pages_to_scan = 2 if (cycle_num == 1 or len(current_ads) < 25) else 1

    for page_num in range(1, pages_to_scan + 1):
        for src in DUBIZZLE_SOURCES:
            page_url = src["url"] if page_num == 1 else f"{src['url']}?page={page_num}"
            fresh_tuples = engine.get_category_links(page_url, label=f"{src['en']} p.{page_num}", is_land=(src["cat_key"] == "land"))
            for lnk, age_lbl, age_mins, real_ts in fresh_tuples:
                ad_id_key = f"id_{get_numeric_ad_id(lnk)}"
                if lnk not in existing_urls and lnk not in seen_links_dict and ad_id_key not in seen_links_dict and lnk not in candidate_urls:
                    candidate_urls.add(lnk)
                    all_raw_candidates.append({"url": lnk, "cat": src["cat"], "deal": src["deal"], "en": src["en"], "age": age_lbl, "age_mins": age_mins, "real_ts": real_ts})

    all_raw_candidates.sort(key=lambda x: x["age_mins"])
    candidates = all_raw_candidates[:MAX_CANDIDATES_PER_RUN]
    total_cand = len(candidates)

    if total_cand == 0:
        print("\n[Up-to-Date] All current fresh ads have already been inspected! Waiting for newly posted ads...")
        return

    print(f"\n[Parallel Inspector] Launching ThreadPoolExecutor (max_workers={MAX_WORKERS}) for {total_cand} NEW unseen ads (Sorted newest first)...")
    total_added, completed_idx = 0, 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(inspect_ad_worker, item, engine, blacklist_dict) for item in candidates]
        for fut in as_completed(futures):
            completed_idx += 1
            try: res = fut.result()
            except Exception as e:
                print(f"  [{completed_idx}/{total_cand}] [ERROR] Worker exception: {e}")
                continue
            u = res["url"]
            if res.get("loaded"):
                with STATE_LOCK:
                    seen_links_dict[u] = True
                    seen_links_dict[f"id_{get_numeric_ad_id(u)}"] = True
            if res.get("bl_key"):
                with STATE_LOCK: blacklist_dict[res["bl_key"]] = True
            ad_obj = res.get("ad")
            if ad_obj:
                with STATE_LOCK:
                    current_ads.insert(0, ad_obj)
                    existing_urls.add(u)
                    total_added += 1
                print(f"  [{completed_idx}/{total_cand}] [+ ACCEPTED OWNER] {res.get('en')} ({ad_obj['age']}) | {ad_obj['publisher']} ({ad_obj['pub_ads']} ads) | Price: {ad_obj['price']}")
                save_state(current_ads, seen_links_dict, blacklist_dict, push_to_github=False)
            else:
                print(f"  [{completed_idx}/{total_cand}] [- REJECTED] {res.get('reason')}")
                if completed_idx % 15 == 0:
                    save_state(current_ads, seen_links_dict, blacklist_dict, push_to_github=False)

    save_state(current_ads, seen_links_dict, blacklist_dict, push_to_github=(total_added > 0))
    print(f"\n=== Cycle Complete: Added ({total_added}) New Owners | Total Owners in DB: ({len(current_ads)}) | Blacklisted Brokers: ({len(blacklist_dict)}) ===")

def main():
    print("=== Starting 24/7 Dubizzle Owner Radar (45m Cycle | Exact Real Age | 4-Stage Profile & Name Verification) ===")
    engine = SmartHybridEngine()
    cycle_num = 1
    while True:
        print(f"\n>>> Starting Radar Cycle #{cycle_num} at {datetime.now().strftime('%H:%M:%S')} <<<")
        try:
            run_single_cycle(engine, cycle_num=cycle_num)
        except Exception as e:
            print(f"[Cycle Error] {e}")
        cycle_num += 1
        print(f"[Auto-Loop] Sleeping for {AUTO_LOOP_MINUTES} minutes before next automatic scan (Keep window open)...")
        for _ in range(AUTO_LOOP_MINUTES * 2):
            time.sleep(30)

if __name__ == "__main__":
    main()
