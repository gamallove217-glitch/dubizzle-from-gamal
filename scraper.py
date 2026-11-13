import json, re, time, random, os
from datetime import datetime, timezone, timedelta
import requests as std_requests
from curl_cffi import requests

CAIRO_TZ = timezone(timedelta(hours=2))
DATA_FILE = "ads.json"
NTFY_BAN_TOPIC = "gamal_vip_ban_9941_sec"
AI_ANALYZE_URL = "https://gamal216.pythonanywhere.com/analyze"

PAGES_PER_CATEGORY = int(os.environ.get("PAGES_PER_CATEGORY", "4"))
MAX_RUNTIME_SECONDS = int(os.environ.get("MAX_RUNTIME_SECONDS", "600"))
MAX_AD_AGE_SECONDS = 7 * 86400
MIN_CASH_SALE_PRICE = 1400000

CATEGORIES = [
    {"name": "شقق", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo-fifth-settlement/"},
    {"name": "شقق", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/"},
    {"name": "فلل", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo-fifth-settlement/"},
    {"name": "فلل", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/"},
    {"name": "تجاري", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo-fifth-settlement/"},
    {"name": "تجاري", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/"},
    {"name": "شقق", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo-fifth-settlement/"},
    {"name": "شقق", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/"},
    {"name": "فلل", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo-fifth-settlement/"},
    {"name": "تجاري", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo-fifth-settlement/"},
    {"name": "أراضي", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/vacation-homes-and-land-for-sale/new-cairo-fifth-settlement/"},
]

ZONES = [
    ("التجمع الخامس", ["التجمع الخامس", "fifth settlement", "5th settlement"]),
    ("التجمع الأول", ["التجمع الأول", "التجمع الاول", "first settlement", "1st settlement"]),
    ("التجمع الثالث", ["التجمع الثالث", "third settlement", "3rd settlement"]),
    ("التجمع السادس", ["التجمع السادس", "sixth settlement"]),
    ("اللوتس", ["اللوتس", "lotus"]),
    ("النرجس", ["النرجس", "narges", "narjis"]),
    ("الياسمين", ["الياسمين", "yasmeen", "jasmine"]),
    ("البنفسج", ["البنفسج", "banafseg"]),
    ("الأندلس", ["الأندلس", "الاندلس", "andalus"]),
    ("جنوب الأكاديمية", ["جنوب الأكاديمية", "جنوب الاكاديمية", "south academy"]),
    ("شرق الأكاديمية", ["شرق الأكاديمية", "شرق الاكاديمية"]),
    ("المستثمرين", ["المستثمرين", "investors"]),
    ("الرحاب", ["الرحاب", "rehab"]),
    ("مدينتي", ["مدينتي", "madinaty"]),
    ("الشويفات", ["الشويفات", "choueifat", "shouyfat"]),
    ("القرنفل", ["القرنفل", "koronfel"]),
    ("التمر حنة", ["التمر حنة", "تمر حنة", "tamr hena"]),
    ("أبو الهول", ["أبو الهول", "ابو الهول", "جاردينيا هايتس", "جاردينيا"]),
    ("دار مصر", ["دار مصر", "سكن مصر", "جنة مصر", "فرجينيا"]),
    ("القطامية", ["القطامية", "القطاميه", "katameya"]),
    ("شارع التسعين", ["التسعين", "90th"]),
    ("المستقبل سيتي", ["المستقبل", "mostakbal"]),
]

EXCLUDED_CITIES = [
    "بيت الوطن", "بيت وطن", "beit al watan", "beit el watan", "bayt al watan", "النورث هاوس", "شمال الرحاب",
    "العبور", "الشروق", "بدر", "هليوبوليس الجديدة", "العاصمة الإدارية", "العاصمه الاداريه",
    "العاشر من رمضان", "6 أكتوبر", "أكتوبر", "الشيخ زايد", "زايد", "المعادي", "زهراء المعادي",
    "المقطم", "الهضبة الوسطى", "مدينة نصر", "مصر الجديدة", "شيراتون", "النزهة", "عين شمس",
    "السلام", "جسر السويس", "قباء", "حدائق القبة", "المرج", "شبرا", "حلوان", "15 مايو",
    "حدائق حلوان", "دار السلام", "الزمالك", "المهندسين", "الدقي", "العجوزة", "الهرم", "فيصل",
    "حدائق الأهرام", "حدائق الاهرام", "حدائق أكتوبر", "الساحل الشمالي", "العين السخنة", "الجونة",
    "الغردقة", "شرم الشيخ", "الإسكندرية", "الاسكندرية", "المنصورة", "طنطا", "دمياط", "بورسعيد"
]

BROKER_WORDS = [
    "شركة", "شركه", "مكتب", "للعقارات", "للاستثمار", "للتسويق", "للتطوير", "بروكر", "سمسار",
    "وسيط", "عمولة", "عموله", "أوفر", "اوفر", "تاجر", "استشاري عقاري", "مستشار عقاري",
    "real estate", "property", "properties", "broker", "agency", "consultancy", "investment",
    "development", "group", "homes", "house", "capital"
]

INSTALLMENT_PATTERNS = [
    "تقسيط", "بالتقسيط", "لتقسيط", "أقساط", "اقساط", "باقساط", "بأقساط", "قسط", "مقدم", "بمقدم",
    "دفعة", "دفعه", "دفعات", "تسهيلات", "سداد", "فترة سداد", "سنوات سداد", "بدون فوائد",
    "ادفع", "تعاقد", "متبقي", "المتبقي", "أوفر", "اوفر", "أوفر برايس", "اوفر برايس", "امكانية التقسيط",
    "متاح تقسيط", "ويوجد تقسيط", "استلام فوري بمقدم",
    "down payment", "downpayment", "installment", "installments", "payment plan"
]

SAFE_CASH_NEGATIONS = [
    "بدون تقسيط", "لا يوجد تقسيط", "ممنوع التقسيط", "وليس تقسيط",
    "بدون أقساط", "بدون اقساط", "خالص الثمن", "خالصة الثمن", "خالصه الثمن",
    "ليس عليها أقساط", "ليس عليها اقساط", "لا يوجد أقساط", "لا يوجد اقساط",
    "مسدد بالكامل", "مسددة بالكامل", "غير متاح تقسيط"
]

def normalize_ar(text):
    t = (text or "").lower()
    t = re.sub(r'[\u0640\u064B-\u065F]', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def extract_ad_core_text(html):
    cleaned = re.sub(r'<(script|style|svg|noscript)[^>]*>.*?</\1>', ' ', html, flags=re.S | re.I)
    tags_stripped = re.sub(r'<[^>]+>', ' ', cleaned)
    tags_stripped = re.sub(r'\s+', ' ', tags_stripped)
    for cutoff in ["Related ads", "إعلانات ذات صلة", "إعلانات مشابهة", "See More Ads by", "Your safety matters to us"]:
        idx = tags_stripped.find(cutoff)
        if idx != -1 and idx > 150:
            tags_stripped = tags_stripped[:idx]
    desc_matches = re.findall(r'"description"\s*:\s*"([^"]+)"', html)
    return (tags_stripped + " " + " ".join(desc_matches)).strip()

def parse_scraped_at_ts(s, fallback_ts):
    if not s or not isinstance(s, str):
        return fallback_ts
    for fmt in ("%Y-%m-%d %I:%M %p", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(s.strip(), fmt).replace(tzinfo=CAIRO_TZ)
            return int(dt.timestamp())
        except Exception:
            pass
    return fallback_ts

def is_clean_direct_ad(title, desc_text="", deal="تمليك", price_num=0):
    full_clean = normalize_ar(f"{title} {desc_text}")
    for bad_loc in ["بيت الوطن", "بيت وطن", "beit al watan", "beit el watan", "bayt al watan", "النورث هاوس", "شمال الرحاب"]:
        if bad_loc in full_clean:
            return False

    if deal == "تمليك":
        if 0 < price_num < MIN_CASH_SALE_PRICE:
            return False
        cleaned_for_check = full_clean
        for neg in SAFE_CASH_NEGATIONS:
            cleaned_for_check = cleaned_for_check.replace(normalize_ar(neg), " ")
        for pat in INSTALLMENT_PATTERNS:
            p_norm = normalize_ar(pat)
            if re.search(r'(^|\s|،|\.|/|-|\(|\[|\*)' + re.escape(p_norm) + r'(\s|$|،|\.|/|-|\)|\]|\*)', cleaned_for_check):
                return False
        if re.search(r'\b\d+\s*%\s*(مقدم|تعاقد|دفعة|دفعه|down)', cleaned_for_check):
            return False
    return True

def detect_zone(title, core_text=""):
    t_title = normalize_ar(title)
    for city in EXCLUDED_CITIES:
        if normalize_ar(city) in t_title:
            return None
    for z_name, keywords in ZONES:
        for kw in keywords:
            if normalize_ar(kw) in t_title:
                return z_name

    t_full = normalize_ar(title + " " + core_text[:2500])
    for city in EXCLUDED_CITIES:
        if normalize_ar(city) in t_full:
            return None
    for z_name, keywords in ZONES:
        for kw in keywords:
            if normalize_ar(kw) in t_full:
                return z_name
    if any(k in t_full for k in ["القاهرة الجديدة", "القاهره الجديده", "تجمع", "new cairo", "settlement"]):
        return "القاهرة الجديدة"
    return None

def is_broker_text(name, text=""):
    n = normalize_ar(name)
    for w in BROKER_WORDS:
        if normalize_ar(w) in n:
            return True
    t = normalize_ar(text)
    if any(p in t for p in ["شركة عقارات", "مكتب عقارات", "للتسويق العقاري", "للاستشارات العقارية", "عمولة المكتب", "عموله المكتب", "متاح لدينا وحدات", "متوفر لدينا شقق", "company profile", "verified business", "share agency profile"]):
        return True
    return False

def verify_with_external_ai(title, core_text, publisher, deal, cat, price_num):
    try:
        payload = {
            "title": title,
            "description": core_text[:1800],
            "publisher": publisher,
            "deal": deal,
            "cat": cat,
            "price_num": price_num,
            "source": "دوبيزل"
        }
        r = std_requests.post(AI_ANALYZE_URL, json=payload, timeout=10)
        if r.status_code == 200:
            res = r.json()
            dec = str(res.get("decision", "")).strip()
            if any(w in dec for w in ["مرفوض", "سمسار", "تقسيط", "شركة", "بيت الوطن"]):
                return False, None, None
            return True, res.get("area"), res.get("rooms")
    except Exception:
        pass
    return True, None, None

def parse_age_and_tier(page_text):
    norm_text = normalize_ar(page_text)
    en_m = re.search(r'(\d+)\s*(minute|minutes|hour|hours|day|days|week|weeks|month|months)\s+ago', norm_text, re.I)
    if en_m:
        num = int(en_m.group(1))
        unit = en_m.group(2).lower()
        if "min" in unit or "hour" in unit:
            return (f"منذ {num} ساعة" if "hour" in unit else f"منذ {num} دقيقة", 3, True)
        if "day" in unit:
            if num <= 1: return ("منذ يوم", 2, True)
            if num <= 5: return (f"منذ {num} أيام", 1, True)
            return (f"منذ {num} أيام", 0, False)
        return ("قديم", 0, False)

    m = re.search(r'منذ\s+(\d+|دقيقة|دقيقتين|ساعة|ساعتين|يوم|يومين)\s*(دقيقة|دقائق|ساعة|ساعات|يوم|أيام|ايام|يوما|اسبوع|أسبوع|اشهر|أشهر|شهر)?', norm_text)
    if not m:
        if "اليوم" in norm_text or "منذ لحظات" in norm_text or "الآن" in norm_text:
            return ("اليوم", 3, True)
        if "أمس" in norm_text or "امس" in norm_text or "yesterday" in norm_text:
            return ("منذ يوم", 2, True)
        return ("حديث", 2, True)

    val_str = m.group(1)
    unit = m.group(2) or ""
    if val_str in ["دقيقة", "دقيقتين"] or "دقيق" in unit:
        return (f"منذ {val_str} {unit}".strip(), 3, True)
    if val_str in ["ساعة", "ساعتين"] or "ساع" in unit:
        return (f"منذ {val_str} {unit}".strip(), 3, True)
    if val_str == "يوم":
        return ("منذ يوم", 2, True)
    if val_str == "يومين":
        return ("منذ يومين", 1, True)
    if val_str.isdigit():
        num = int(val_str)
        if "يوم" in unit or "أيام" in unit or "ايام" in unit:
            if num <= 1: return ("منذ يوم", 2, True)
            if num <= 5: return (f"منذ {num} أيام", 1, True)
            return (f"منذ {num} أيام", 0, False)
        if any(x in unit for x in ["اسبوع", "أسبوع", "شهر", "أشهر", "اشهر"]):
            return ("قديم", 0, False)
    return ("حديث", 2, True)

def compute_tier_from_ts(ts):
    age_sec = int(time.time()) - int(ts)
    if age_sec <= 12 * 3600:
        return 3
    if age_sec <= 36 * 3600:
        return 2
    return 1

def create_healing_session(profile_idx=0):
    profiles = ["chrome120", "chrome110", "safari15_5"]
    imp = profiles[profile_idx % len(profiles)]
    s = requests.Session(impersonate=imp)
    s.headers.update({
        "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.dubizzle.com.eg/"
    })
    return s

def sync_ntfy_bans(banned_pubs, banned_ids):
    try:
        r = requests.get(f"https://ntfy.sh/{NTFY_BAN_TOPIC}/json?poll=1&since=48h", timeout=10)
        if r.status_code == 200:
            for line in r.text.strip().splitlines():
                if not line: continue
                msg = json.loads(line).get("message", "")
                if msg.startswith("BAN_AD:"):
                    parts = msg.replace("BAN_AD:", "").split("|")
                    if parts[0].isdigit():
                        banned_ids.add(int(parts[0]))
                    if len(parts) > 1 and parts[1].strip():
                        banned_pubs.add(parts[1].strip())
    except Exception:
        pass

def load_existing():
    if not os.path.exists(DATA_FILE):
        return {}, [], set(), set(), set()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return (
            data,
            data.get("ads", []),
            set(data.get("checked_ids", [])),
            set(data.get("banned_publishers", [])),
            set(data.get("banned_ad_ids", []))
        )
    except Exception:
        return {}, [], set(), set(), set()

def run_scraper():
    start_ts = time.time()
    now_ts = int(start_ts)
    raw_data, existing_ads, checked_ids, banned_pubs, banned_ids = load_existing()
    sync_ntfy_bans(banned_pubs, banned_ids)

    session = create_healing_session(0)

    kept = []
    seen_ids = set()
    for a in existing_ads:
        aid = a.get("ad_id")
        if not aid:
            continue
        checked_ids.add(aid)
        pub = a.get("publisher", "")
        if aid in banned_ids or pub in banned_pubs or aid in seen_ids:
            continue

        p_num = a.get("price_num", 0)
        deal_type = a.get("deal", "تمليك")
        if not is_clean_direct_ad(a.get("title", ""), "", deal_type, p_num):
            continue
        if not detect_zone(a.get("title", ""), a.get("zone", "")):
            continue

        orig_ts = a.get("first_seen_ts")
        if not orig_ts:
            orig_ts = parse_scraped_at_ts(a.get("scraped_at"), now_ts - 86400)
        if (now_ts - orig_ts) > MAX_AD_AGE_SECONDS:
            continue

        a["desc_verified_v2"] = True
        a["first_seen_ts"] = orig_ts
        a["fresh_tier"] = compute_tier_from_ts(orig_ts)
        kept.append(a)
        seen_ids.add(aid)

    rent_candidates = []
    sale_candidates = []
    pages_fetched = 0

    for page in range(1, PAGES_PER_CATEGORY + 1):
        if time.time() - start_ts > MAX_RUNTIME_SECONDS * 0.40:
            break
        for idx, cat in enumerate(CATEGORIES):
            url = cat["url"] if page == 1 else f"{cat['url']}?page={page}"
            try:
                resp = session.get(url, timeout=20)
                if resp.status_code != 200:
                    session = create_healing_session(idx + page)
                    resp = session.get(url, timeout=20)
                pages_fetched += 1
                print(f"[Dubizzle] {cat['name']} ({cat['deal']}) p.{page} -> HTTP {resp.status_code}")
                if resp.status_code != 200:
                    continue
                matches = re.findall(r'((?:https?://www\.dubizzle\.com\.eg)?(?:/ar|/en)?/ad/[^"\'\s<>\\]+-ID(\d+)\.html)', resp.text)
                for raw_path, id_str in matches:
                    ad_id = int(id_str)
                    if ad_id in seen_ids or ad_id in checked_ids or ad_id in banned_ids:
                        continue
                    clean_path = re.sub(r'^https?://www\.dubizzle\.com\.eg', '', raw_path)
                    clean_path = re.sub(r'^/(?:ar|en)/', '/', clean_path)
                    item_obj = {
                        "ad_id": ad_id,
                        "url": "https://www.dubizzle.com.eg" + clean_path,
                        "cat": cat["name"],
                        "deal": cat["deal"]
                    }
                    if cat["deal"] == "إيجار":
                        rent_candidates.append(item_obj)
                    else:
                        sale_candidates.append(item_obj)
                    seen_ids.add(ad_id)
                time.sleep(random.uniform(0.6, 1.1))
            except Exception as e:
                print(f"[Dubizzle Error] {e}")
                continue

    candidates = []
    r_idx, s_idx = 0, 0
    while r_idx < len(rent_candidates) or s_idx < len(sale_candidates):
        for _ in range(2):
            if r_idx < len(rent_candidates):
                candidates.append(rent_candidates[r_idx])
                r_idx += 1
        if s_idx < len(sale_candidates):
            candidates.append(sale_candidates[s_idx])
            s_idx += 1

    print(f"[Dubizzle] Candidates ready -> Rent: {len(rent_candidates)} | Sale: {len(sale_candidates)}")
    new_verified = []
    inspected_cnt = 0

    for item in candidates:
        if time.time() - start_ts > MAX_RUNTIME_SECONDS:
            break
        ad_id = item["ad_id"]
        checked_ids.add(ad_id)
        inspected_cnt += 1
        try:
            r = session.get(item["url"], timeout=20)
            if r.status_code != 200:
                continue
            html = r.text

            t_m = re.search(r'<title>([^<]+)</title>', html)
            title = t_m.group(1).split("|")[0].split("-")[0].strip() if t_m else ""
            if not title:
                continue

            core_text = extract_ad_core_text(html)
            if any(x in core_text for x in ["Company Profile", "Verified Business", "Share agency profile"]):
                continue
            if "/companies/" in html[:90000]:
                continue

            zone = detect_zone(title, core_text)
            if not zone:
                continue

            age_label, _, is_recent = parse_age_and_tier(core_text)
            if not is_recent:
                continue

            pub_name = "مالك مباشر"
            pub_id = None
            pub_m = re.search(r'"((?:/ar|/en)?/profile/[a-zA-Z0-9_-]+)"[^>]*>([^<]+)<', html)
            if pub_m:
                pub_id = pub_m.group(1)
                pub_name = pub_m.group(2).strip()
            else:
                pub_m2 = re.search(r'href="((?:/ar|/en)?/profile/[a-zA-Z0-9_-]+)"', html)
                if pub_m2:
                    pub_id = pub_m2.group(1)
                posted_m = re.search(r'Posted by\s*([^\.\n<]{2,40})', core_text) or re.search(r'"sellerName"\s*:\s*"([^"]+)"', html)
                if posted_m:
                    pub_name = posted_m.group(1).strip()

            if pub_name in banned_pubs or is_broker_text(pub_name, core_text):
                if pub_name not in ("مالك", "مالك مباشر"):
                    banned_pubs.add(pub_name)
                continue

            p_m = re.search(r'([\d,]{4,15})\s*ج\.م', html) or re.search(r'EGP\s*([\d,]{4,15})', html)
            if p_m:
                price_num = int(p_m.group(1).replace(",", ""))
                price_str = f"{p_m.group(1)} ج.م"
            else:
                price_num = 0
                price_str = "السعر بالتفاصيل"

            if not is_clean_direct_ad(title, core_text, item["deal"], price_num):
                continue

            pub_ads_count = 1
            active_m = re.search(r'Active Ads\s*(\d+)', core_text, re.I) or re.search(r'(?:الإعلانات النشطة|الاعلانات النشطة)\s*(\d+)', core_text)
            if active_m:
                pub_ads_count = int(active_m.group(1))
            elif pub_id:
                try:
                    clean_prof = re.sub(r'^/(?:ar|en)/', '/', pub_id)
                    pr = session.get("https://www.dubizzle.com.eg" + clean_prof, timeout=12)
                    if pr.status_code == 200:
                        profile_cards = len(set(re.findall(r'-ID(\d+)\.html', pr.text)))
                        pub_ads_count = max(profile_cards, 1)
                except Exception:
                    pub_ads_count = 1

            if pub_ads_count < 1 or pub_ads_count > 4:
                if pub_name not in ("مالك", "مالك مباشر"):
                    banned_pubs.add(pub_name)
                continue

            area_m = re.search(r'(\d{2,4})\s*(?:متر|م²|sqm|m²)', core_text, re.I)
            area_val = int(area_m.group(1)) if area_m else None

            rooms_m = re.search(r'(\d)\s*(?:غرف|غرفة|نوم|beds|bed|bedrooms)', core_text, re.I)
            rooms_val = int(rooms_m.group(1)) if rooms_m else None

            ai_ok, ai_area, ai_rooms = verify_with_external_ai(title, core_text, pub_name, item["deal"], item["cat"], price_num)
            if not ai_ok:
                print(f"[- AI Rejected Dubizzle] {title[:40]}")
                continue
            if not area_val and isinstance(ai_area, int):
                area_val = ai_area
            if not rooms_val and isinstance(ai_rooms, int):
                rooms_val = ai_rooms

            ad_ts = int(time.time())
            now_cairo = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
            new_verified.append({
                "ad_id": ad_id,
                "source": "دوبيزل",
                "title": title,
                "price": price_str,
                "price_num": price_num,
                "zone": zone,
                "cat": item["cat"],
                "deal": item["deal"],
                "area": area_val,
                "rooms": rooms_val,
                "publisher": pub_name,
                "pub_ads": pub_ads_count,
                "age": age_label,
                "fresh_tier": 3,
                "first_seen_ts": ad_ts,
                "desc_verified_v2": True,
                "url": item["url"],
                "verified_v12": True,
                "scraped_at": now_cairo
            })
            print(f"[+ Dubizzle {item['deal']}] {zone} | {title[:40]} (Ads: {pub_ads_count})")
            time.sleep(random.uniform(0.7, 1.2))
        except Exception:
            continue

    print(f"[Dubizzle] New verified direct owners added: {len(new_verified)}")
    final_ads = [a for a in (new_verified + kept) if a.get("publisher") not in banned_pubs and a.get("ad_id") not in banned_ids]
    final_ads.sort(key=lambda x: (x.get("first_seen_ts", 0), x.get("ad_id", 0)), reverse=True)

    now_str = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
    run_report = {
        "last_run_at": now_str,
        "dub_pages": pages_fetched,
        "dub_candidates": len(candidates),
        "dub_inspected": inspected_cnt,
        "dub_added": len(new_verified)
    }

    out = {
        "updated_at": now_str,
        "total": len(final_ads),
        "last_run_report": run_report,
        "ads": final_ads,
        "checked_ids": list(checked_ids)[-12000:],
        "extra_checked_ids": raw_data.get("extra_checked_ids", []),
        "banned_publishers": list(banned_pubs),
        "banned_ad_ids": list(banned_ids),
        "telegram_config": raw_data.get("telegram_config", {}),
        "telegram_notified_ids": raw_data.get("telegram_notified_ids", [])
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_scraper()
