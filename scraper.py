import os, sys, re, json, time, random, stat, subprocess, threading, hashlib, ctypes
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from DrissionPage import ChromiumPage, ChromiumOptions

def disable_cmd_quickedit_and_sleep():
    if not sys.platform.startswith("win"): return
    try:
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

AI_SERVER_URL = "https://gamal216.pythonanywhere.com"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ads.json")
SEEN_FILE = os.path.join(BASE_DIR, "seen_links_local.json")
BLACKLIST_FILE = os.path.join(BASE_DIR, "blacklist.json")
RESET_FLAG_FILE = os.path.join(BASE_DIR, "clean_reset_v8.flag")
PROFILE_DIR = os.path.join(BASE_DIR, "chrome_clean_profile")

MAX_ADS_STORED = 450
MAX_CANDIDATES_PER_RUN = 800
AUTO_LOOP_MINUTES = 45
STATE_LOCK = threading.Lock()
BROWSER_LOCK = threading.Lock()
TURNSTILE_LOCK = threading.Lock()
PROFILE_CACHE = {}
ESC_QUOTE = chr(92) + '"'

DUBIZZLE_SOURCES = [
    {"cat_key": "apt", "cat": "شقق", "deal": "إيجار", "en": "Apartments (Rent)", "max_pages": 5, "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/"},
    {"cat_key": "apt", "cat": "شقق", "deal": "تمليك", "en": "Apartments (Sale)", "max_pages": 5, "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/"},
    {"cat_key": "villa", "cat": "فلل", "deal": "إيجار", "en": "Villas (Rent)", "max_pages": 3, "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/"},
    {"cat_key": "villa", "cat": "فلل", "deal": "تمليك", "en": "Villas (Sale)", "max_pages": 3, "url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/"},
    {"cat_key": "comm", "cat": "تجاري", "deal": "إيجار", "en": "Commercial (Rent)", "max_pages": 3, "url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/"},
    {"cat_key": "comm", "cat": "تجاري", "deal": "تمليك", "en": "Commercial (Sale)", "max_pages": 3, "url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/"},
    {"cat_key": "land", "cat": "أراضي", "deal": "AUTO", "en": "Buildings & Lands (Sale/Rent)", "max_pages": 3, "url": "https://www.dubizzle.com.eg/properties/buildings-lands-for-sale/new-cairo/"}
]

ZONE_MAPPING = {"النرجس": "النرجس", "نرجس": "النرجس", "الياسمين": "الياسمين", "ياسمين": "الياسمين", "البنفسج": "البنفسج", "بنفسج": "البنفسج", "اللوتس": "اللوتس", "لوتس": "اللوتس", "الأندلس": "الأندلس", "الاندلس": "الأندلس", "اندلس": "الأندلس", "القرنفل": "القرنفل", "قرنفل": "القرنفل", "تمر حنة": "التمر حنة", "التمر حنة": "التمر حنة", "جاردينيا": "جاردينيا", "جنوب الأكاديمية": "جنوب الأكاديمية", "جنوب الاكاديمية": "جنوب الأكاديمية", "شرق الأكاديمية": "شرق الأكاديمية", "شرق الاكاديمية": "شرق الأكاديمية", "المستثمرين": "المستثمرين", "الشويفات": "الشويفات", "شويفات": "الشويفات", "أبو الهول": "أبو الهول", "ابو الهول": "أبو الهول", "دار مصر": "دار مصر", "سكن مصر": "سكن مصر", "جنة": "جنة مصر", "القطامية": "القطامية", "قطامية": "القطامية", "التسعين": "شارع التسعين", "شارع التسعين": "شارع التسعين", "ميفيدا": "ميفيدا", "هايد بارك": "هايد بارك", "ماونتن فيو": "ماونتن فيو", "التجمع الأول": "التجمع الأول", "التجمع الاول": "التجمع الأول", "التجمع الثالث": "التجمع الثالث", "التجمع الخامس": "التجمع الخامس"}
FORBIDDEN_ZONES = ["الرحاب", "رحاب", "rehab", "مدينتي", "مدينتى", "madinaty", "المستقبل", "mostakbal", "سمات", "بيت الوطن", "بيت وطن", "beit al watan", "beit el watan", "bayt al watan", "النورث هاوس", "شمال الرحاب", "العبور", "الشروق", "مدينة بدر", "مدينه بدر", "هليوبوليس الجديدة", "العاصمة الإدارية", "العاصمه الاداريه", "العاشر من رمضان", "6 أكتوبر", "أكتوبر", "الشيخ زايد", "زايد", "المعادي", "زهراء المعادي", "المقطم", "الهضبة الوسطى", "مدينة نصر", "مصر الجديدة", "شيراتون", "النزهة", "عين شمس", "السلام", "جسر السويس", "حدائق القبة", "المرج", "شبرا", "حلوان", "15 مايو", "الزمالك", "المهندسين", "الدقي", "العجوزة", "الهرم", "فيصل", "حدائق الأهرام", "حدائق الاهرام", "حدائق أكتوبر", "الساحل الشمالي", "العين السخنة", "مقبرة", "مقابر", "مدفن", "مدافن", "جبانة", "طريق السخنة"]
INSTALLMENT_KEYWORDS = ["قسط", "تقسيط", "بالتقسيط", "أقساط", "اقساط", "تسهيلات", "فترة سداد", "سنوات سداد", "بمقدم", "مقدم", "دفعة", "دفعات", "الدفعة المقدمة", "متبقي", "المتبقي", "أوفر", "اوفر", "أوفر برايس", "down payment", "downpayment", "installment", "installments", "payment plan"]
CASH_NEGATIONS = ["بدون تقسيط", "لا يوجد تقسيط", "ممنوع التقسيط", "وليس تقسيط", "مش تقسيط", "بدون أقساط", "بدون اقساط", "خالص الثمن", "خالصة الثمن", "خالصه الثمن", "ليس عليها أقساط", "ليس عليها اقساط", "لا يوجد أقساط", "لا يوجد اقساط", "مسدد بالكامل", "مسددة بالكامل", "مسدده بالكامل", "غير متاح تقسيط", "البيع كاش فقط", "كاش فقط", "كاش ولا تقبل التمويل", "كاش نهائي"]
COMPANY_NAME_KEYWORDS = ["شركه", "شركة", "عقارات", "للعقارات", "تسويق", "للتسويق", "ماركتنج", "مكتب", "استثمار", "تطوير", "جروب", "هوم", "هاوس", "بروكر", "ريال استيت", "استيت", "فيرتكس", "روي", "ايكو", "إيكو", "كابيتال", "كونسلت", "للاستشارات", "إعمار", "معمار", "ريديفاين", "ارتكاز", "إرتكاز", "ابتكار", "إبتكار", "إمكان", "امكان", "نيو أفينيو", "فالكون", "جلوبال", "جرين هوم", "فيوز", "أورا", "اورا", "انسبيريشن", "برايم", "ديل", "redefine", "vertex", "echo", "roy real", "real estate", "realestate", "estate", "estates", "realty", "properties", "property", "broker", "brokers", "brokerage", "agency", "agencies", "group", "developments", "development", "investment", "investments", "marketing", "lounge", "scouts", "hub", "home", "homes", "house", "egypt", "capital", "consultant", "consultancy", "consulting", "prime", "elite", "empire", "avenue", "landmark", "residence", "living", "towers", "tower", "irtkaz", "ebtkar", "imkan", "falcon", "views", "aura", "inspairtion", "inspiration", "insider", "meer", "deal", "ghp"]
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
            for fid in ("catFilter", "dealFilter"):
                sel = soup.find("select", {"id": fid})
                if not sel: continue
                for opt in sel.find_all("option"):
                    val = (opt.get("value") or "").strip()
                    if not val or val == "ALL": continue
                    txt = normalize_ar(opt.get_text(" ", strip=True) + " " + val)
                    if fid == "catFilter":
                        if "شقق" in txt: FRONTEND_SCHEMA["cat_map"]["apt"] = val
                        elif "فلل" in txt or "فيلات" in txt: FRONTEND_SCHEMA["cat_map"]["villa"] = val
                        elif "تجار" in txt: FRONTEND_SCHEMA["cat_map"]["comm"] = val
                        elif "اراض" in txt or "مبان" in txt: FRONTEND_SCHEMA["cat_map"]["land"] = val
                    else:
                        if "ايجار" in txt: FRONTEND_SCHEMA["deal_map"]["rent"] = val
                        elif "تمليك" in txt or "بيع" in txt or "كاش" in txt: FRONTEND_SCHEMA["deal_map"]["sale"] = val
        except Exception: pass
    for src in DUBIZZLE_SOURCES:
        if src["cat_key"] in FRONTEND_SCHEMA["cat_map"]: src["cat"] = FRONTEND_SCHEMA["cat_map"][src["cat_key"]]
        if src["deal"] in ("إيجار", "ايجار"): src["deal"] = FRONTEND_SCHEMA["deal_map"]["rent"]
        elif src["deal"] in ("تمليك", "بيع"): src["deal"] = FRONTEND_SCHEMA["deal_map"]["sale"]

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

def parse_dubizzle_age_info(text):
    now_ts = int(time.time())
    if text:
        norm = normalize_ar(text)
        if re.search(r'(?:(\d+)\s*(?:اسبوع|اسابيع|شهر|شهور|اشهر|سنه|سنوات)\s*مضت|(?:منذ|قبل)\s*(?:\d+\s*)?(?:اسبوع|اسابيع|اسبوعين|شهر|شهور|اشهر|سنه|سنوات)|\b(?:\d+|a|an)\s*(?:weeks?|months?|years?)\s*ago\b)', norm, re.I):
            return False, "Old Ad (>1w)", 99999, now_ts - 604800, True
        if re.search(r'(?:([2-9]|\d{2,})\s*(?:ايام|يوم)\s*مضت|يومين\s*مضت|(?:منذ|قبل)\s*([2-9]|\d{2,})\s*(?:ايام|يوم)|(?:منذ|قبل)\s*يومين|\b([2-9]|\d{2,})\s*days?\s*ago\b)', norm, re.I):
            return False, "Old Ad (>1d)", 99999, now_ts - 172800, True
        m_hr = re.search(r'(?:(\d{1,2})\s*(?:ساعه|ساعات)\s*مضت|(\d{1,2})\s*قبل\s*(?:ساعه|ساعات)|(?:منذ|قبل)\s*(\d{1,2})\s*(?:ساعه|ساعات)|\b(\d{1,2})\s*(?:hours?|hrs?)\s*ago\b)', norm, re.I)
        if m_hr:
            val = int(next(g for g in m_hr.groups() if g is not None))
            if val > 24: return False, f"Old Ad ({val}h)", val * 60, now_ts - (val * 3600), True
            return True, f"منذ {val} ساعة", val * 60, now_ts - (val * 3600), True
        if re.search(r'(?:ساعتين\s*مضت|(?:منذ|قبل)\s*ساعتين)', norm): return True, "منذ 2 ساعة", 120, now_ts - 7200, True
        if re.search(r'(?:ساعه\s*مضت|(?:منذ|قبل)\s*ساعه\b|\b(?:an|1)\s*hour\s*ago\b)', norm): return True, "منذ 1 ساعة", 60, now_ts - 3600, True
        m_min = re.search(r'(?:(\d{1,3})\s*(?:دقيقه|دقائق|دقايق)\s*مضت|(\d{1,3})\s*قبل\s*(?:دقيقه|دقائق|دقايق)|(?:منذ|قبل)\s*(\d{1,3})\s*(?:دقيقه|دقائق|دقايق)|\b(\d{1,3})\s*(?:minutes?|mins?)\s*ago\b)', norm, re.I)
        if m_min:
            val = int(next(g for g in m_min.groups() if g is not None))
            return True, f"منذ {val} دقيقة", max(1, val), now_ts - (val * 60), True
        if re.search(r'(?:دقيقتين\s*مضت|(?:منذ|قبل)\s*دقيقتين)', norm): return True, "منذ 2 دقيقة", 2, now_ts - 120, True
        if re.search(r'(?:دقيقه\s*مضت|(?:منذ|قبل)\s*دقيقه\b|\bالان\b|\bحالا\b)', norm): return True, "منذ 1 دقيقة", 1, now_ts - 60, True
        if re.search(r'(?:1\s*يوم\s*مضت|يوم\s*مضت|1\s*قبل\s*يوم|(?:منذ|قبل)\s*(?:1\s*يوم|يوم\s*واحد|يوم\b)|\bامس\b|\byesterday\b)', norm, re.I):
            return True, "منذ 24 ساعة", 1440, now_ts - 86400, True
    return True, "منذ ساعة", 60, now_ts - 3600, False

def is_company_like_name(name):
    norm = normalize_ar(name)
    if not norm or norm in (normalize_ar("مالك مباشر"), "owner"): return False
    for k in COMPANY_NAME_KEYWORDS:
        nk = normalize_ar(k)
        if len(nk) <= 3:
            if re.search(rf'\b{re.escape(nk)}\b', norm): return True
        elif nk in norm: return True
    return bool(re.search(r'\b(?:real|estate|properties|property|broker|agency|agencies|group|developments|investment|marketing|lounge|scouts|homes|house|capital|consultant|prime|elite|empire|echo|roy|vertex|redefine|irtkaz|ebtkar|imkan|falcon|views|aura|insider|meer|deal|ghp)\b', norm, re.I))

def extract_visible_dubizzle_ad_id(text):
    if not text: return ""
    m_vis = re.search(r'(?:معرّف\s*الإعلان|معرف\s*الإعلان|معرف\s*الاعلان|رقم\s*الإعلان|Ad\s*ID)\s*[:\-]?\s*([25]\d{7,10})\b', text.translate(HINDI_MAP), re.I)
    return m_vis.group(1) if m_vis else ""

def get_numeric_ad_id(url, html=""):
    m_url = re.search(r'ID(\d{6,12})', str(url), re.I)
    if m_url: return int(m_url.group(1))
    vis_id = extract_visible_dubizzle_ad_id(html)
    if vis_id: return int(vis_id)
    return int(hashlib.md5(str(url).encode("utf-8")).hexdigest()[:8], 16)

def clean_publisher_name(name):
    if not name: return "مالك مباشر"
    s = re.sub(r'<[^>]+>', ' ', str(name))
    s = re.sub(r'(?:path\s+d=|M\d+\.\d+|viewBox|xmlns|svg|fill=|رؤية\s*ملف|View\s*profile|تم\s*النشر\s*بواسطة|تم\s*النشر\s*بواسطه|الناشر|المعلن|عضو\s*منذ.*|الإعلانات\s*النشطة.*|الاعلانات\s*النشطه.*|إعلانات\s*نشطة.*|اعلانات\s*نشطه.*|\(\d+.*?\)|\(دوبيزل\))', ' ', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip(" -_|:,><.")
    words = s.split()
    half = len(words) // 2
    if half >= 1 and len(words) % 2 == 0 and [w.lower() for w in words[:half]] == [w.lower() for w in words[half:]]:
        s = " ".join(words[:half])
    if not s or len(s) < 2 or len(s) > 55 or re.search(r'[<>{}\[\]=/\\]', s): return "مالك مباشر"
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
    for pat in [r'(?:EGP|ج\.?م|جنيه|LE)\s*(\d[\d,\.]{3,14})', r'(\d[\d,\.]{3,14})\s*(?:ج\.?م|جنيه|EGP|LE)', r'"(?:price|rawPrice|priceAmount|value)"\s*:\s*"?(\d[\d,]{4,12})"?']:
        for src_t in (clean_main, combined_blob):
            for m in re.findall(pat, src_t, re.I):
                p = parse_price_strict(m, deal)
                if p > 0: return p
    return 0

def is_forbidden_or_installment(title, desc, deal, price_num):
    raw_combined = re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', f"{title} {desc}")
    norm_text = normalize_ar(raw_combined)
    for idx, bad in enumerate(FORBIDDEN_ZONES):
        if normalize_ar(bad) in norm_text: return True, f"Forbidden Zone (#{idx+1})"
    for phrase in BROKER_DESC_PHRASES:
        if normalize_ar(phrase) in norm_text: return True, f"Company Copywriting ({phrase})"
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
        if idx > 15000: return html[:idx]
    return html

def is_turnstile_failed_in_html(html):
    if not html: return False
    norm_h = normalize_ar(html)
    for marker in ("فشل التحقق", "تعذر التحقق من اتصالك", "حدث الصفحه للمحاوله", "refresh the page to try again"):
        if marker in norm_h: return True
    return False

def is_turnstile_in_html(html):
    if not html: return False
    if html.count("/ad/") >= 10: return False
    if is_turnstile_failed_in_html(html): return True
    norm_h = normalize_ar(html)
    for marker in ("التحقق الامني", "زائر حقيقي للمتابعه", "حدد المربع ادناه", "محمي ضد الحركه الاليه", "تاكيد انك انسان"):
        if marker in norm_h: return True
    return "<title>just a moment" in norm_h[:5000]

def extract_dubizzle_links_from_html(html, prefilter_cards=False, blacklist_dict=None):
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
                card_txt = card.get_text(" ", strip=True) if card else ""
                c_date_el = (card.find(attrs={"aria-label": "Creation date"}) or card.find(attrs={"aria-label": "تاريخ النشر"})) if card else None
                age_target_txt = c_date_el.get_text(" ", strip=True) if c_date_el else card_txt
                is_fresh, age_lbl, age_mins, real_ts, _ = parse_dubizzle_age_info(age_target_txt)
                if not is_fresh: continue
                card_age = age_lbl
                if card:
                    skip_company_card = False
                    for a_c in card.find_all("a", href=True):
                        h_c = str(a_c["href"]).lower()
                        if "/companies/" in h_c or "/agencies/" in h_c:
                            skip_company_card = True; break
                    if not skip_company_card:
                        if card.find(attrs={"aria-label": re.compile(r'agency|company|شركة|وكيل', re.I)}):
                            skip_company_card = True
                    if skip_company_card: continue
                norm_c = normalize_ar(re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', card_txt))
                if "الدفعه المقدمه" in norm_c or "طريقه الدفع تقسيط" in norm_c or "down payment" in norm_c: continue
                if any(normalize_ar(bz) in norm_c for bz in FORBIDDEN_ZONES): continue
            seen_u.add(full)
            results.append((full, card_age, age_mins, real_ts))
    return results

class SmartHybridEngine:
    def __init__(self):
        self.page = None
        self.land_url_resolved = False
        self.last_refresh_ts = 0

    def get_live_dom(self):
        if not self.page: return ""
        try:
            with BROWSER_LOCK:
                return self.page.run_js("return document.documentElement ? document.documentElement.outerHTML : '';") or ""
        except Exception: return ""

    def minimize_chrome_safely(self):
        if not self.page: return
        try:
            with BROWSER_LOCK:
                try: self.page.run_cdp("Emulation.setFocusEmulationEnabled", enabled=True)
                except Exception: pass
                try: self.page.set.window.mini()
                except Exception: pass
        except Exception: pass

    def hard_refresh_anchor(self, target_url=None):
        if not self.page: return
        u = target_url or DUBIZZLE_SOURCES[0]["url"]
        try:
            with BROWSER_LOCK:
                try: self.page.set.load_mode.normal()
                except Exception: pass
                try: self.page.run_cdp("Emulation.setFocusEmulationEnabled", enabled=True)
                except Exception: pass
                self.page.get(u, timeout=18)
            self.last_refresh_ts = time.time()
            time.sleep(3.5)
        except Exception: pass

    def cdp_press_key(self, key_name, vk_code, code_str, char_txt=""):
        try:
            self.page.run_cdp("Input.dispatchKeyEvent", type="rawKeyDown", windowsVirtualKeyCode=vk_code, nativeVirtualKeyCode=vk_code, key=key_name, code=code_str)
            time.sleep(0.05)
            if char_txt:
                self.page.run_cdp("Input.dispatchKeyEvent", type="char", windowsVirtualKeyCode=vk_code, key=key_name, code=code_str, text=char_txt, unmodifiedText=char_txt)
                time.sleep(0.05)
            self.page.run_cdp("Input.dispatchKeyEvent", type="keyUp", windowsVirtualKeyCode=vk_code, nativeVirtualKeyCode=vk_code, key=key_name, code=code_str)
        except Exception: pass

    def cdp_internal_focus_point(self, vx, vy):
        try:
            x, y = int(vx), int(vy)
            if x <= 10 or y <= 10: return
            self.page.run_cdp("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
            time.sleep(0.03)
            self.page.run_cdp("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button="left", clickCount=1)
            time.sleep(0.05)
            self.page.run_cdp("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button="left", clickCount=1)
        except Exception: pass

    def try_auto_solve_turnstile(self, attempt_idx=0):
        if not self.page: return "no_page"
        try:
            with BROWSER_LOCK:
                try: self.page.run_cdp("Emulation.setFocusEmulationEnabled", enabled=True)
                except Exception: pass
                box = self.page.run_js("""
                    let targetEl = null, topR = null, botR = null;
                    for (const el of document.querySelectorAll('p, div, span, h1, h2')) {
                        const r = el.getBoundingClientRect();
                        if (r.height < 8 || r.height > 280 || r.width < 50) continue;
                        const t = (el.innerText || '').trim();
                        if (t.includes('المربع') || t.includes('زائر حقيقي')) {
                            if (!topR || r.height < topR.height) { topR = r; targetEl = el; }
                        }
                        if (t.includes('لماذا') && (!botR || r.height < botR.height)) botR = r;
                    }
                    if (targetEl) {
                        targetEl.setAttribute('tabindex', '0');
                        targetEl.focus();
                    } else if (document.body) {
                        document.body.setAttribute('tabindex', '0');
                        document.body.focus();
                    }
                    let cx = (window.innerWidth || 640) / 2, ty = ((window.innerHeight || 700) / 2) + 25;
                    if (topR && botR) { cx = (topR.left + topR.right) / 2; ty = (topR.bottom + botR.top) / 2; }
                    else if (topR) { cx = (topR.left + topR.right) / 2; ty = topR.bottom + 52; }
                    return { cx: Math.round(cx), ty: Math.round(ty), hasTarget: Boolean(targetEl) };
                """)
                if box and isinstance(box, dict) and not box.get("hasTarget"):
                    self.cdp_internal_focus_point(box["cx"], max(30, box["ty"] - 65))
                    time.sleep(0.15)
                for step in range(3):
                    self.cdp_press_key("Tab", 9, "Tab")
                    time.sleep(0.28)
                    self.cdp_press_key(" ", 32, "Space", " ")
                    time.sleep(0.28)
                if box and isinstance(box, dict):
                    self.cdp_internal_focus_point(box["cx"] + 120, box["ty"])
                    time.sleep(0.15)
                    self.cdp_press_key(" ", 32, "Space", " ")
                return "Background(Tab+Space)"
        except Exception: pass
        return "Background(Tab+Space)"

    def wait_until_turnstile_cleared(self, max_wait_loops=35, expect_ads=False):
        if not self.page: return False
        with TURNSTILE_LOCK:
            time.sleep(1.0)
            refreshed_once = False
            was_turnstile = False
            for attempt in range(max_wait_loops):
                dom_now = self.get_live_dom()
                if not is_turnstile_in_html(dom_now):
                    if expect_ads:
                        if dom_now.count("/ad/") >= 8:
                            if was_turnstile:
                                print("[Security Solver] Turnstile cleared via Tab+Space! Stabilizing 3.5s...")
                                time.sleep(3.5)
                            self.minimize_chrome_safely()
                            return True
                    else:
                        if "<h1" in dom_now.lower() or dom_now.count("/ad/") >= 8 or len(dom_now) > 35000:
                            if was_turnstile:
                                time.sleep(2.5)
                            self.minimize_chrome_safely()
                            return True
                else:
                    was_turnstile = True
                if is_turnstile_failed_in_html(dom_now) and not refreshed_once:
                    print("[Self-Healing] 'فشل التحقق' detected -> Refreshing tab once...")
                    refreshed_once = True
                    self.hard_refresh_anchor()
                    continue
                if is_turnstile_in_html(dom_now) and attempt in (0, 2, 4, 7, 10, 14, 18, 23, 28):
                    status = self.try_auto_solve_turnstile(attempt_idx=(attempt // 2))
                    if attempt in (0, 4, 10):
                        print(f"[Security Solver] Turnstile detected -> Executed {status} (Zero Mouse / Minimized)...")
                time.sleep(2.2)
            self.minimize_chrome_safely()
            return not is_turnstile_in_html(self.get_live_dom())

    def ensure_anchor_browser(self):
        if self.page is None:
            try:
                os.makedirs(PROFILE_DIR, exist_ok=True)
                co = ChromiumOptions()
                for c in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")]:
                    if os.path.exists(c): co.set_browser_path(c); break
                co.set_paths(local_port=9555, user_data_path=PROFILE_DIR)
                co.set_argument("--disable-background-timer-throttling")
                co.set_argument("--disable-backgrounding-occluded-windows")
                co.set_argument("--disable-renderer-backgrounding")
                co.set_argument("--disable-features=CalculateNativeWinOcclusion")
                co.mute(True)
                self.page = ChromiumPage(addr_or_opts=co)
            except Exception as e:
                print(f"[Browser Port 9555 Info] {e}")
                return False
        try:
            self.minimize_chrome_safely()
            try: self.page.set.load_mode.normal()
            except Exception: pass
            dom_now = self.get_live_dom()
            cur_u = str(self.page.run_js("return location.href || '';") or "").lower()
            if "dubizzle.com.eg" in cur_u and not is_turnstile_in_html(dom_now) and dom_now.count("/ad/") >= 8:
                test_h = self.browser_background_fetch_single(DUBIZZLE_SOURCES[0]["url"], require_ads=True)
                if test_h and test_h.count("/ad/") >= 8:
                    self.minimize_chrome_safely()
                    links_now = extract_dubizzle_links_from_html(test_h, prefilter_cards=False)
                    print(f"[Engine] Existing Live Session Verified & Minimized! ({len(links_now)} ads visible)")
                    return True
            if "dubizzle.com.eg" not in cur_u or "notfound" in cur_u or (not is_turnstile_in_html(dom_now) and dom_now.count("/ad/") < 8):
                self.hard_refresh_anchor(DUBIZZLE_SOURCES[0]["url"])
            self.wait_until_turnstile_cleared(max_wait_loops=40, expect_ads=True)
            links_now = extract_dubizzle_links_from_html(self.get_live_dom(), prefilter_cards=False)
            if len(links_now) == 0:
                self.hard_refresh_anchor(DUBIZZLE_SOURCES[0]["url"])
                self.wait_until_turnstile_cleared(max_wait_loops=35, expect_ads=True)
                links_now = extract_dubizzle_links_from_html(self.get_live_dom(), prefilter_cards=False)
            self.minimize_chrome_safely()
            print(f"[Engine] Live Session Ready & Chrome Parked in Taskbar! ({len(links_now)} ads visible)")
            return True
        except Exception as e:
            print(f"[Engine Init Info] {e}")
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
        self.ensure_anchor_browser()
        self.discover_land_slug_from_html(self.get_live_dom())

    def direct_tab_fetch(self, url, require_h1=False, require_ads=False):
        if not self.page and not self.ensure_anchor_browser(): return ""
        try:
            with BROWSER_LOCK:
                self.page.get(url, timeout=18)
            for _ in range(10):
                time.sleep(0.5)
                dom = self.get_live_dom()
                if is_turnstile_in_html(dom):
                    self.wait_until_turnstile_cleared(max_wait_loops=35, expect_ads=require_ads)
                    dom = self.get_live_dom()
                if dom and not is_turnstile_in_html(dom):
                    if require_ads and dom.count("/ad/") >= 8:
                        return dom
                    if require_h1 and "<h1" in dom.lower() and len(dom) > 20000:
                        return dom
                    if not require_ads and not require_h1 and len(dom) > 12000:
                        return dom
            dom = self.get_live_dom()
            if dom and not is_turnstile_in_html(dom) and len(dom) > 10000:
                return dom
        except Exception: pass
        return ""

    def browser_background_fetch_single(self, url, require_h1=False, require_ads=False):
        time.sleep(random.uniform(0.7, 1.2))
        if not self.page: return ""
        req_id = f"req_{int(time.time()*1000)}_{random.randint(1000,9999)}"
        js_start = """
        window.__fetches = window.__fetches || {};
        const reqId = arguments[0], targetUrl = arguments[1];
        window.__fetches[reqId] = { done: false, status: 0, html: '' };
        (async () => {
            try {
                const r = await fetch(targetUrl, { method: 'GET', credentials: 'include' });
                window.__fetches[reqId].status = r.status;
                window.__fetches[reqId].html = await r.text();
            } catch (e) { window.__fetches[reqId].status = -1; }
            window.__fetches[reqId].done = true;
        })();
        return true;
        """
        try:
            with BROWSER_LOCK: self.page.run_js(js_start, req_id, url)
            for _ in range(32):
                time.sleep(0.22)
                with BROWSER_LOCK:
                    res_state = self.page.run_js(
                        "const f = (window.__fetches && window.__fetches[arguments[0]]); "
                        "if (!f || !f.done) return null; "
                        "const out = {status: f.status, html: f.html}; delete window.__fetches[arguments[0]]; return out;", req_id
                    )
                if res_state and isinstance(res_state, dict):
                    st, h = int(res_state.get("status") or 0), res_state.get("html") or ""
                    if st == 200 and h and not is_turnstile_in_html(h) and len(h) > 5000:
                        if require_ads and h.count("/ad/") < 8: return ""
                        if require_h1 and "<h1" not in h.lower(): return ""
                        return h
                    return ""
        except Exception: pass
        finally:
            try:
                with BROWSER_LOCK: self.page.run_js("if (window.__fetches) delete window.__fetches[arguments[0]];", req_id)
            except Exception: pass
        return ""

    def fetch_html(self, url, require_h1=False, require_ads=False):
        h = self.browser_background_fetch_single(url, require_h1=require_h1, require_ads=require_ads)
        if h and not is_turnstile_in_html(h) and len(h) > 5000:
            if not self.land_url_resolved: self.discover_land_slug_from_html(h)
            return h
        h_nav = self.direct_tab_fetch(url, require_h1=require_h1, require_ads=require_ads)
        if h_nav and not is_turnstile_in_html(h_nav) and len(h_nav) > 5000:
            if not self.land_url_resolved: self.discover_land_slug_from_html(h_nav)
            return h_nav
        return ""

    def get_category_links(self, url, label="", is_land=False, blacklist_dict=None):
        raw_pairs, fresh_pairs = [], []
        urls_to_try = [url]
        if is_land and "?page=" not in url:
            urls_to_try.extend(["https://www.dubizzle.com.eg/properties/buildings-lands/new-cairo/", "https://www.dubizzle.com.eg/properties/land-for-sale/new-cairo/"])
        for u_try in urls_to_try:
            html = self.fetch_html(u_try, require_h1=False, require_ads=True)
            raw_pairs = extract_dubizzle_links_from_html(html, prefilter_cards=False)
            fresh_pairs = extract_dubizzle_links_from_html(html, prefilter_cards=True, blacklist_dict=blacklist_dict)
            if raw_pairs:
                if is_land:
                    for src in DUBIZZLE_SOURCES:
                        if src["cat_key"] == "land": src["url"] = u_try.split("?")[0]
                break
        print(f"[Hybrid-Fetch] {label} -> {'200 OK' if raw_pairs else 'Empty'} (Total: {len(raw_pairs)} | Non-Agency Fresh & Cash: {len(fresh_pairs)})")
        return fresh_pairs

    def verify_profile_published_count(self, profile_url):
        if not profile_url: return 0, ""
        with STATE_LOCK:
            if profile_url in PROFILE_CACHE: return PROFILE_CACHE[profile_url]
        h = self.fetch_html(profile_url, require_h1=False, require_ads=False)
        if not h: return 0, ""
        soup = BeautifulSoup(h, "html.parser")
        prof_name = ""
        for tag_n in ("h1", "h2"):
            el_n = soup.find(tag_n)
            if el_n:
                cand = clean_publisher_name(el_n.get_text(" ", strip=True))
                if cand != "مالك مباشر": prof_name = cand; break
        txt = normalize_ar(soup.get_text(" ", strip=True))
        unesc_h = h.replace(ESC_QUOTE, '"').translate(HINDI_MAP)
        count_val = 0
        for m_p in re.findall(r'(?:الاعلانات\s*المنشوره|اعلانات\s*منشوره|الاعلانات\s*النشطه|اعلانات\s*نشطه|published\s*ads|active\s*ads)\s*[:\-]?\s*(\d{1,5})\b', txt, re.I):
            v = int(m_p)
            if v >= 1 and not (1990 <= v <= 2035): count_val = v; break
        if count_val == 0:
            txt_no_yr = re.sub(r'(?:عضو\s*منذ|member\s*since)\s*\d{4}', ' ', txt)
            for m_b in re.findall(r'\b(\d{1,5})\s*(?:الاعلانات\s*المنشوره|اعلانات\s*منشوره|الاعلانات\s*النشطه|اعلانات\s*نشطه|published\s*ads|active\s*ads)', txt_no_yr, re.I):
                v = int(m_b)
                if v >= 1 and not (1990 <= v <= 2035): count_val = v; break
        if count_val == 0:
            for pat_j in [r'"totalAds"\s*:\s*(\d+)', r'"publishedAdsCount"\s*:\s*(\d+)', r'"activeAdsCount"\s*:\s*(\d+)', r'"adsCount"\s*:\s*(\d+)']:
                m_j = re.search(pat_j, unesc_h)
                if m_j and int(m_j.group(1)) >= 1: count_val = int(m_j.group(1)); break
        if count_val == 0: count_val = len(extract_dubizzle_links_from_html(h, prefilter_cards=False))
        with STATE_LOCK: PROFILE_CACHE[profile_url] = (count_val, prof_name)
        return count_val, prof_name

def extract_seller_card_details(full_soup, unescaped_blob):
    pub_raw, profile_url, seller_id, is_agency = "", "", "", False
    for lbl_el in full_soup.find_all(string=re.compile(r'تم\s*النشر\s*بواسطة|تم\s*النشر\s*بواسطه|Posted\s*by|Listed\s*by', re.I)):
        curr = lbl_el.parent
        for _ in range(6):
            if not curr: break
            c_txt = curr.get_text(" ", strip=True)
            if len(c_txt) > 650: break
            for a_in in curr.find_all("a", href=True):
                hc = str(a_in["href"]).split("?")[0].rstrip("/").strip()
                m_c = re.search(r'/(?:ar/|en/)?(?:companies|agencies)/([a-zA-Z0-9_\-]{3,})', hc, re.I)
                if m_c and not hc.endswith("/companies"):
                    seller_id = f"comp_{m_c.group(1)[:35]}"
                    profile_url = hc if hc.startswith("http") else f"https://www.dubizzle.com.eg{hc}"
                    is_agency = True
                m_p = re.search(r'/(?:ar/|en/)?profile/([a-zA-Z0-9_\-]{4,})', hc, re.I)
                if m_p:
                    seller_id = seller_id or f"prof_{m_p.group(1)[:35]}"
                    profile_url = profile_url or (hc if hc.startswith("http") else f"https://www.dubizzle.com.eg{hc}")
                    a_t = clean_publisher_name(a_in.get_text(" ", strip=True))
                    if a_t != "مالك مباشر": pub_raw = a_t
            if re.search(r'عضو\s*منذ|الإعلانات\s*النشطة|إعلانات\s*نشطة|الاعلانات\s*النشطه|اعلانات\s*نشطه|Member\s*since|Active\s*ads', c_txt, re.I):
                after_lbl = re.split(r'تم\s*النشر\s*بواسطة|تم\s*النشر\s*بواسطه|Posted\s*by|Listed\s*by', c_txt, flags=re.I)[-1]
                before_meta = re.split(r'عضو\s*منذ|الإعلانات\s*النشطة|إعلانات\s*نشطة|الاعلانات\s*النشطه|اعلانات\s*نشطه|رؤية\s*ملف|إظهار\s*الرقم', after_lbl, flags=re.I)[0]
                cand = clean_publisher_name(before_meta)
                if cand != "مالك مباشر": pub_raw = cand; break
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
                if cand != "مالك مباشر": pub_raw = cand; break
    if not profile_url:
        m_p2 = re.search(r'/(?:ar/|en/)?profile/([a-zA-Z0-9_\-]{5,})', unescaped_blob)
        if m_p2:
            seller_id = seller_id or f"prof_{m_p2.group(1)[:35]}"
            profile_url = f"https://www.dubizzle.com.eg/profile/{m_p2.group(1)}"
    return clean_publisher_name(pub_raw), profile_url, seller_id, is_agency

def extract_direct_ad_info(full_html, deal, blacklist, hint_age="منذ ساعة", hint_ts=0):
    main_html = strip_related_ads_section(full_html)
    soup = BeautifulSoup(main_html, "html.parser")
    full_soup = BeautifulSoup(full_html, "html.parser")
    for tag in soup.find_all(["header", "nav", "footer"]): tag.decompose()
    h1 = soup.find("h1") or full_soup.find("h1")
    title = re.sub(r'\s*\|\s*(?:دوبيزل|dubizzle).*$', '', (h1.get_text(" ", strip=True) if h1 else ""), flags=re.I).strip()
    if not title or len(title) < 4: return None, "Empty title", None
    desc_el = soup.find(attrs={"aria-label": "Description"}) or full_soup.find(attrs={"aria-label": "الوصف"}) or soup.find("div", {"data-testid": "description"}) or full_soup.find("div", {"data-testid": "description"})
    desc = desc_el.get_text(" ", strip=True) if desc_el else ""
    main_text = soup.get_text(" ", strip=True)
    full_text = full_soup.get_text(" ", strip=True)
    norm_main_text, norm_full_text = normalize_ar(main_text), normalize_ar(full_text)
    if deal == "AUTO":
        deal = FRONTEND_SCHEMA["deal_map"]["rent"] if re.search(r'(?:للايجار|for\s*rent)', normalize_ar(f"{title} {main_text[:1500]}"), re.I) else FRONTEND_SCHEMA["deal_map"]["sale"]
    unescaped_blob = main_html.replace(ESC_QUOTE, '"').translate(HINDI_MAP)
    full_unescaped = full_html.replace(ESC_QUOTE, '"').translate(HINDI_MAP)
    creation_el = full_soup.find(attrs={"aria-label": "Creation date"}) or full_soup.find(attrs={"aria-label": "تاريخ النشر"})
    age_badge_text = creation_el.get_text(" ", strip=True) if creation_el else ""
    if not age_badge_text:
        m_b = re.search(r'(\d{1,2}\s*(?:دقيقه|دقائق|دقايق|ساعه|ساعات|يوم|ايام)\s*مضت|\d{1,2}\s*قبل\s*(?:دقيقه|دقائق|دقايق|ساعه|ساعات|يوم)|(?:منذ|قبل)\s*\d{1,2}\s*(?:دقيقه|دقائق|دقايق|ساعه|ساعات|يوم|ايام)|(?:ساعه|ساعتين|دقيقه|دقيقتين|يوم|يومين)\s*مضت|\bامس\b)', norm_full_text[:1800])
        if m_b: age_badge_text = m_b.group(1)
    is_fresh, detected_age, _, detected_ts, matched_exact = parse_dubizzle_age_info(age_badge_text)
    if not is_fresh: return None, detected_age, None
    final_age = detected_age if matched_exact else hint_age
    final_ts = detected_ts if matched_exact else (hint_ts or int(time.time()) - 3600)
    if "ايجار" not in normalize_ar(deal) and re.search(r'طريقه\s*الدفع\s*[:\-]?\s*تقسيط\b', norm_main_text[:2500]):
        return None, "Installment Ad (Payment Table)", None
    price_num = extract_best_price(full_soup, soup, main_html, full_unescaped, deal)
    is_bad, bad_reason = is_forbidden_or_installment(title, desc, deal, price_num)
    if is_bad: return None, bad_reason, None
    publisher_clean, profile_url, seller_id, is_agency = extract_seller_card_details(full_soup, unescaped_blob)
    company_name_key = f"compname_{normalize_ar(publisher_clean)}" if is_company_like_name(publisher_clean) else ""
    safe_bl_key = seller_id or company_name_key or None
    with STATE_LOCK:
        in_bl = (seller_id and seller_id in blacklist) or (company_name_key and company_name_key in blacklist)
    if in_bl: return None, f"Blacklisted Broker ({publisher_clean})", None
    if is_agency or is_company_like_name(publisher_clean): return None, f"Company Account ({publisher_clean})", safe_bl_key
    active_count, count_source = 0, ""
    for el in full_soup.find_all(string=re.compile(r'الإعلانات\s*النشطة|الاعلانات\s*النشطه|إعلانات\s*نشطة|اعلانات\s*نشطه|Active\s*ads', re.I)):
        for candidate_box in ([el.parent, el.parent.parent, el.parent.parent.parent] if (el.parent and el.parent.parent) else [el.parent]):
            if not candidate_box: continue
            box_txt = re.sub(r'(?:عضو\s*منذ|member\s*since)\s*\d{4}', ' ', normalize_ar(candidate_box.get_text(" ", strip=True)))
            nums = [int(x) for x in re.findall(r'\b(\d{1,5})\b', box_txt) if int(x) >= 1 and not (1990 <= int(x) <= 2035)]
            if nums: active_count = nums[0]; count_source = f"DOM ({active_count} ads)"; break
        if active_count > 0: break
    if active_count == 0:
        no_yr = re.sub(r'(?:عضو\s*منذ|member\s*since)\s*\d{4}', ' ', norm_full_text)
        m_act = re.search(r'(?:الاعلانات\s*النشطه|اعلانات\s*نشطه|active\s*ads)\s*[:\-]?\s*(\d{1,5})\b', no_yr) or re.search(r'\b(\d{1,4})\s*(?:الاعلانات\s*النشطه|اعلانات\s*نشطه|اعلان\s*نشط|active\s*ads)', no_yr)
        if m_act: active_count = int(m_act.group(1)); count_source = f"Badge ({active_count} ads)"
    if active_count == 0:
        for pat in [r'"activeAdsCount"\s*:\s*(\d+)', r'"active_ads_count"\s*:\s*(\d+)', r'"activeAds"\s*:\s*(\d+)', r'"listedAdsCount"\s*:\s*(\d+)', r'"userAdsCount"\s*:\s*(\d+)', r'"adsCount"\s*:\s*(\d+)', r'"totalAds"\s*:\s*(\d+)']:
            m_j = re.search(pat, full_unescaped)
            if m_j and int(m_j.group(1)) >= 1: active_count = int(m_j.group(1)); count_source = f"JSON ({active_count} ads)"; break
    vis_ad_id = extract_visible_dubizzle_ad_id(full_text)
    if active_count == 0 and vis_ad_id.startswith("2") and not is_agency:
        active_count, count_source = 1, f"AppOwnerID ({vis_ad_id})"
    if active_count >= 5: return None, f"Broker Count ({publisher_clean}: {active_count} > 4)", safe_bl_key
    local_area, local_rooms = extract_local_specs(main_text, unescaped_blob)
    return {"title": title, "desc": desc, "price_num": price_num, "deal": deal, "publisher_clean": publisher_clean, "active_count": active_count, "count_source": count_source, "local_area": local_area, "local_rooms": local_rooms, "age": final_age, "real_ts": final_ts, "profile_url": profile_url, "safe_bl_key": safe_bl_key}, "OK", None

def inspect_ad_worker(item, engine, blacklist):
    url, cat, deal, en_label = item["url"], item["cat"], item["deal"], item["en"]
    html = engine.fetch_html(url, require_h1=True, require_ads=False)
    if not html: return {"url": url, "ad": None, "reason": "Failed to fetch ad HTML", "bl_key": None, "loaded": False}
    info, reason, bl_key = extract_direct_ad_info(html, deal, blacklist, hint_age=item.get("age", "منذ ساعة"), hint_ts=item.get("real_ts", 0))
    if not info:
        is_loaded = (reason != "Empty title")
        return {"url": url, "ad": None, "reason": reason, "bl_key": bl_key, "loaded": is_loaded}
    prof_url = info.get("profile_url")
    if prof_url:
        prof_pub_count, prof_name = engine.verify_profile_published_count(prof_url)
        if prof_name and (info["publisher_clean"] in ("مالك مباشر", "Owner", "owner") or is_company_like_name(prof_name)):
            info["publisher_clean"] = prof_name
        if is_company_like_name(info["publisher_clean"]):
            return {"url": url, "ad": None, "reason": f"Profile Company ({info['publisher_clean']})", "bl_key": info.get("safe_bl_key"), "loaded": True}
        if prof_pub_count >= 5:
            return {"url": url, "ad": None, "reason": f"Profile Published Ads ({info['publisher_clean']}: {prof_pub_count} > 4)", "bl_key": info.get("safe_bl_key"), "loaded": True}
        if 1 <= prof_pub_count <= 4 and prof_pub_count > info["active_count"]:
            info["active_count"] = prof_pub_count
    if info["active_count"] == 0:
        info["active_count"] = 1
    title, desc, price_num, resolved_deal = info["title"], info["desc"], info["price_num"], info["deal"]
    publisher_clean, active_count = info["publisher_clean"], info["active_count"]
    ai_area, ai_rooms = info["local_area"], info["local_rooms"]
    try:
        r = requests.post(f"{AI_SERVER_URL}/analyze", json={"title": title, "description": desc, "publisher": publisher_clean, "deal": resolved_deal, "cat": cat, "price_num": price_num, "source": "دوبيزل", "active_ads_count": active_count}, timeout=6)
        if r.status_code == 200 and r.json().get("decision") == "مرفوض":
            return {"url": url, "ad": None, "reason": f"AI Rejected ({publisher_clean})", "bl_key": info.get("safe_bl_key"), "loaded": True}
    except Exception: pass
    num_id = get_numeric_ad_id(url, html)
    real_post_ts = int(info.get("real_ts") or time.time())
    ad_obj = {
        "ad_id": num_id, "id": f"dub_{num_id}", "title": title, "url": url, "link": url,
        "price": f"{price_num:,} ج.م" if price_num > 0 else "السعر بالتفاصيل", "price_num": price_num,
        "cat": cat, "category": cat, "deal": resolved_deal, "type": resolved_deal,
        "zone": detect_sub_zone(f"{title} {desc}"), "location": detect_sub_zone(f"{title} {desc}"),
        "source": "دوبيزل", "publisher": publisher_clean, "pub_ads": active_count, "active_ads_count": active_count,
        "area": ai_area, "rooms": ai_rooms, "age": info["age"], "description": desc[:500],
        "first_seen_ts": real_post_ts, "timestamp": real_post_ts, "date": datetime.fromtimestamp(real_post_ts).strftime("%Y-%m-%d %H:%M")
    }
    return {"url": url, "ad": ad_obj, "reason": "Owner Verified", "bl_key": None, "loaded": True, "en": en_label}

def load_json_list(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d if isinstance(d, list) else (d.get("ads", []) if isinstance(d, dict) else [])
        except Exception: pass
    return []

def safe_write_json(path, data):
    for _ in range(3):
        try:
            if os.path.exists(path):
                try: os.chmod(path, stat.S_IWRITE)
                except Exception: pass
            with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception: time.sleep(0.2)
    return False

def save_state(current_ads, seen_links_dict, blacklist_dict, push_to_github=False):
    with STATE_LOCK:
        current_ads.sort(key=lambda x: int(x.get("first_seen_ts") or 0), reverse=True)
        final_ads = current_ads[:MAX_ADS_STORED]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        safe_write_json(DATA_FILE, {"updated_at": now_str, "total": len(final_ads), "ads": final_ads})
        safe_write_json(SEEN_FILE, list(seen_links_dict.keys())[-15000:])
        safe_write_json(BLACKLIST_FILE, list(blacklist_dict.keys())[-8000:])
    if push_to_github:
        try:
            fix_git_identity_for_vercel()
            subprocess.run(["git", "add", "-f", "ads.json"], cwd=BASE_DIR, capture_output=True, timeout=15)
            subprocess.run(["git", "commit", "-m", f"Live Radar Sync ({len(final_ads)} Owners at {now_str})"], cwd=BASE_DIR, capture_output=True, timeout=15)
            p_res = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=BASE_DIR, capture_output=True, text=True, timeout=30)
            if p_res.returncode != 0:
                clear_git_locks()
                subprocess.run(["git", "pull", "--rebase", "--autostash", "-X", "ours", "origin", "main"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
                p_res = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=BASE_DIR, capture_output=True, text=True, timeout=30)
            print(f"    --> [LIVE SYNC] Pushed {len(final_ads)} verified owners to GitHub & Vercel!")
        except Exception as e:
            print(f"    --> [LOCAL SAVE] ({len(final_ads)} owners) | {e}")

def run_single_cycle(engine, cycle_num=1):
    inspect_local_frontend_schema()
    fix_git_identity_for_vercel()
    if not os.path.exists(RESET_FLAG_FILE):
        safe_write_json(SEEN_FILE, [])
        with open(RESET_FLAG_FILE, "w") as f: f.write("ok")
        print("[Clean-Retry v8.6] Initialized clean seen links!")
    engine.warmup()
    raw_existing = load_json_list(DATA_FILE)
    current_ads, seen_u = [], set()
    for ad in raw_existing:
        u = ad.get("url") or ad.get("link") or ""
        num_id = get_numeric_ad_id(u)
        pub_n = ad.get("publisher") or ""
        if not u or u in seen_u or num_id in BANNED_AD_IDS or is_company_like_name(pub_n): continue
        seen_u.add(u)
        current_ads.append(ad)
    seen_links_dict = {k: True for k in load_json_list(SEEN_FILE) if k}
    blacklist_dict = {k: True for k in load_json_list(BLACKLIST_FILE) if k}
    existing_urls = {(a.get("url") or a.get("link")) for a in current_ads}
    for u_ex in existing_urls:
        seen_links_dict[u_ex] = True
        seen_links_dict[f"id_{get_numeric_ad_id(u_ex)}"] = True

    candidate_urls, all_raw_candidates = set(), []
    for src in DUBIZZLE_SOURCES:
        max_p = src.get("max_pages", 3) if cycle_num == 1 else 2
        for page_num in range(1, max_p + 1):
            page_url = src["url"] if page_num == 1 else f"{src['url']}?page={page_num}"
            fresh_tuples = engine.get_category_links(page_url, label=f"{src['en']} p.{page_num}", is_land=(src["cat_key"] == "land"), blacklist_dict=blacklist_dict)
            for lnk, age_lbl, age_mins, real_ts in fresh_tuples:
                ad_id_key = f"id_{get_numeric_ad_id(lnk)}"
                if lnk not in existing_urls and lnk not in seen_links_dict and ad_id_key not in seen_links_dict and lnk not in candidate_urls:
                    candidate_urls.add(lnk)
                    all_raw_candidates.append({"url": lnk, "cat": src["cat"], "deal": src["deal"], "en": src["en"], "age": age_lbl, "age_mins": age_mins, "real_ts": real_ts})
            if len(fresh_tuples) < 3: break

    all_raw_candidates.sort(key=lambda x: x["age_mins"])
    candidates = all_raw_candidates[:MAX_CANDIDATES_PER_RUN]
    total_cand = len(candidates)
    if total_cand == 0:
        print("\n[Up-to-Date] All current fresh ads have already been inspected! Waiting for newly posted ads...")
        return

    print(f"\n[Inspector v8.6] Launching 100% Minimized Scan for ({total_cand}) non-agency <=24h ads...")
    total_added, completed_idx = 0, 0
    for batch_start in range(0, total_cand, 40):
        batch = candidates[batch_start:batch_start + 40]
        for item in batch:
            completed_idx += 1
            try: res = inspect_ad_worker(item, engine, blacklist_dict)
            except Exception as e:
                print(f"  [{completed_idx}/{total_cand}] [ERROR] {e}"); continue
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
                save_state(current_ads, seen_links_dict, blacklist_dict, push_to_github=(total_added % 3 == 0))
            else:
                print(f"  [{completed_idx}/{total_cand}] [- REJECTED] {res.get('reason')}")
            if completed_idx % 10 == 0:
                save_state(current_ads, seen_links_dict, blacklist_dict, push_to_github=False)
        save_state(current_ads, seen_links_dict, blacklist_dict, push_to_github=False)
        if batch_start + 40 < total_cand:
            print(f"    [Rate-Guard] Batch of 40 ads done -> Cooling down 12s to keep IP 100% clean...")
            time.sleep(12.0)

    save_state(current_ads, seen_links_dict, blacklist_dict, push_to_github=(total_added > 0))
    print(f"\n=== Cycle Complete: Added ({total_added}) New Owners | Total Owners in DB: ({len(current_ads)}) | Blacklisted Brokers: ({len(blacklist_dict)}) ===")

def main():
    print("=== Starting 24/7 Dubizzle Owner Radar v8.6 (Zero Mouse | Tab+Space Only | Always Minimized) ===")
    engine = SmartHybridEngine()
    cycle_num = 1
    while True:
        print(f"\n>>> Starting Radar Cycle #{cycle_num} at {datetime.now().strftime('%H:%M:%S')} <<<")
        try: run_single_cycle(engine, cycle_num=cycle_num)
        except Exception as e: print(f"[Cycle Error] {e}")
        cycle_num += 1
        print(f"[Auto-Loop] Sleeping for {AUTO_LOOP_MINUTES} minutes before next automatic scan...")
        for _ in range(AUTO_LOOP_MINUTES * 2): time.sleep(30)

if __name__ == "__main__":
    main()
