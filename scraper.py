import json, re, time, random, os
from datetime import datetime, timezone, timedelta
from curl_cffi import requests

CAIRO_TZ = timezone(timedelta(hours=2))
DATA_FILE = "ads.json"
NTFY_BAN_TOPIC = "gamal_vip_ban_9941_sec"

PAGES_PER_CATEGORY = int(os.environ.get("PAGES_PER_CATEGORY", "5"))
MAX_RUNTIME_SECONDS = int(os.environ.get("MAX_RUNTIME_SECONDS", "600"))
MAX_AD_AGE_SECONDS = 7 * 86400

CATEGORIES = [
    {"name": "شقق", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo-fifth-settlement/"},
    {"name": "شقق", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo-fifth-settlement/"},
    {"name": "فلل", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo-fifth-settlement/"},
    {"name": "فلل", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo-fifth-settlement/"},
    {"name": "تجاري", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo-fifth-settlement/"},
    {"name": "تجاري", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo-fifth-settlement/"},
    {"name": "أراضي", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/vacation-homes-and-land-for-sale/new-cairo-fifth-settlement/"},
]

ZONES = [
    ("التجمع الخامس", ["التجمع الخامس", "fifth settlement", "5th settlement"]),
    ("التجمع الأول", ["التجمع الأول", "التجمع الاول", "first settlement", "1st settlement"]),
    ("التجمع الثالث", ["التجمع الثالث", "third settlement", "3rd settlement"]),
    ("التجمع السادس", ["التجمع السادس", "sixth settlement"]),
    ("بيت الوطن", ["بيت الوطن", "beit al watan", "bayt al watan"]),
    ("اللوتس", ["اللوتس", "lotus"]),
    ("النرجس", ["النرجس", "narges", "narjis"]),
    ("الياسمين", ["الياسمين", "yasmeen", "jasmine"]),
    ("البنفسج", ["البنفسج", "banafseg"]),
    ("الأندلس", ["الأندلس", "الاندلس", "andalus"]),
    ("جنوب الأكاديمية", ["جنوب الأكاديمية", "جنوب الاكاديمية"]),
    ("شرق الأكاديمية", ["شرق الأكاديمية", "شرق الاكاديمية"]),
    ("المستثمرين", ["المستثمرين", "investors"]),
    ("الرحاب", ["الرحاب", "rehab"]),
    ("مدينتي", ["مدينتي", "madinaty"]),
    ("الشويفات", ["الشويفات", "choueifat"]),
    ("القرنفل", ["القرنفل", "koronfel"]),
    ("التمر حنة", ["التمر حنة", "تمر حنة", "tamr hena"]),
    ("أبو الهول", ["أبو الهول", "ابو الهول", "جاردينيا هايتس", "جاردينيا"]),
    ("دار مصر", ["دار مصر", "سكن مصر", "جنة مصر", "فرجينيا"]),
    ("القطامية", ["القطامية", "القطاميه", "katameya"]),
    ("شارع التسعين", ["التسعين", "90th"]),
    ("المستقبل سيتي", ["المستقبل", "mostakbal"]),
]

EXCLUDED_CITIES = [
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
    "development", "group", "homes", "house", "capital", "egypt", "new cairo"
]

INSTALLMENT_PATTERNS = [
    "تقسيط", "بالتقسيط", "أقساط", "اقساط", "قسط", "مقدم", "دفعة", "دفعه", "دفعات",
    "تسهيلات", "سداد", "سنوات", "سنين", "على اطول فترة", "فترة سداد", "بدون فوائد",
    "استلام فوري بمقدم", "بمقدم", "ادفع", "تعاقد ب", "تعاقد بمقدم", "متبقي", "المتبقي",
    "أوفر", "اوفر", "أوفر برايس", "اوفر برايس", "شامل الأوفر", "شامل الاوفر"
]

SAFE_CASH_NEGATIONS = [
    "كاش فقط", "الكاش فقط", "البيع كاش فقط", "بدون تقسيط", "لا يوجد تقسيط", "ممنوع التقسيط",
    "وليس تقسيط", "بدون أقساط", "بدون اقساط", "خالص الثمن", "خالصة الثمن", "خالصه الثمن",
    "ليس عليها أقساط", "ليس عليها اقساط", "لا يوجد أقساط", "لا يوجد اقساط", "مسدد بالكامل", "مسددة بالكامل"
]

def is_clean_direct_ad(title, desc_text="", deal="تمليك"):
    full = f"{title} {desc_text}".lower()
    full_clean = re.sub(r'\s+', ' ', full)
    if re.search(r'(بيت\s*الوطن|beit\s*al\s*watan|bayt\s*al\s*watan)', full_clean):
        if not re.search(r'(امام|أمام|قريب\s*من|بجوار|فيو|تطل\s*على|خطوات\s*من)\s*بيت\s*الوطن', full_clean):
            return False
    if deal == "تمليك":
        cleaned_for_check = full_clean
        for neg in SAFE_CASH_NEGATIONS:
            cleaned_for_check = cleaned_for_check.replace(neg, " ")
        for pat in INSTALLMENT_PATTERNS:
            if re.search(r'(^|\s|،|\.|/|-|\()' + re.escape(pat) + r'(\s|$|،|\.|/|-|\))', cleaned_for_check):
                return False
        if re.search(r'\b\d+\s*%\s*(مقدم|تعاقد|دفعة|دفعه)', cleaned_for_check):
            return False
    return True

def detect_zone(text):
    t = text.lower()
    for city in EXCLUDED_CITIES:
        if city.lower() in t:
            return None
    for z_name, keywords in ZONES:
        for kw in keywords:
            if kw in t:
                if z_name == "بيت الوطن":
                    return None
                return z_name
    if any(k in t for k in ["القاهرة الجديدة", "القاهره الجديده", "تجمع", "new cairo", "settlement"]):
        return "القاهرة الجديدة"
    return None

def is_broker_text(name, text=""):
    n = (name or "").lower().strip()
    for w in BROKER_WORDS:
        if w in n:
            return True
    t = (text or "").lower()
    if any(p in t for p in ["شركة عقارات", "مكتب عقارات", "للتسويق العقاري", "للاستشارات العقارية", "عمولة المكتب", "عموله المكتب", "متاح لدينا وحدات", "متوفر لدينا شقق"]):
        return True
    return False

def parse_age_and_tier(page_text):
    norm_text = re.sub(r'[\u064B-\u065F\u0640]', '', page_text)
    m = re.search(r'منذ\s+(\d+|دقيقة|دقيقتين|ساعة|ساعتين|يوم|يومين)\s*(دقيقة|دقائق|ساعة|ساعات|يوم|أيام|ايام|يوما|اسبوع|أسبوع|اشهر|أشهر|شهر)?', norm_text)
    if not m:
        if "اليوم" in norm_text or "منذ لحظات" in norm_text or "الآن" in norm_text:
            return ("اليوم", 3, True)
        if "أمس" in norm_text or "امس" in norm_text:
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

    kept = []
    seen_ids = set()
    for a in existing_ads:
        aid = a.get("ad_id")
        pub = a.get("publisher", "")
        if not aid or aid in banned_ids or pub in banned_pubs:
            continue
        if not is_clean_direct_ad(a.get("title", ""), "", a.get("deal", "تمليك")):
            continue
        first_ts = a.get("first_seen_ts") or now_ts
        if (now_ts - first_ts) > MAX_AD_AGE_SECONDS:
            continue
        a["first_seen_ts"] = first_ts
        a["fresh_tier"] = compute_tier_from_ts(first_ts)
        if a.get("verified_v12") is True and aid not in seen_ids:
            kept.append(a)
            seen_ids.add(aid)

    session = requests.Session(impersonate="chrome120")
    candidates = []

    for cat in CATEGORIES:
        if time.time() - start_ts > MAX_RUNTIME_SECONDS * 0.45:
            break
        for page in range(1, PAGES_PER_CATEGORY + 1):
            url = cat["url"] if page == 1 else f"{cat['url']}?page={page}"
            try:
                resp = session.get(url, timeout=20)
                if resp.status_code != 200:
                    break
                matches = re.findall(r'href="(/ad/[^"]+-ID(\d+)\.html)"', resp.text)
                for rel_url, id_str in matches:
                    ad_id = int(id_str)
                    if ad_id in seen_ids or ad_id in checked_ids or ad_id in banned_ids:
                        continue
                    candidates.append({
                        "ad_id": ad_id,
                        "url": "https://www.dubizzle.com.eg" + rel_url,
                        "cat": cat["name"],
                        "deal": cat["deal"]
                    })
                    seen_ids.add(ad_id)
                time.sleep(random.uniform(1.0, 1.8))
            except Exception:
                break

    new_verified = []
    for item in candidates:
        if time.time() - start_ts > MAX_RUNTIME_SECONDS:
            break
        ad_id = item["ad_id"]
        checked_ids.add(ad_id)
        try:
            r = session.get(item["url"], timeout=20)
            if r.status_code != 200:
                continue
            html = r.text

            t_m = re.search(r'<title>([^<]+)</title>', html)
            title = t_m.group(1).split("|")[0].split("-")[0].strip() if t_m else ""
            if not title:
                continue

            zone = detect_zone(title + " " + html[:4000])
            if not zone:
                continue

            age_label, _, is_recent = parse_age_and_tier(html)
            if not is_recent:
                continue

            pub_m = re.search(r'"/profile/([a-zA-Z0-9_-]+)"[^>]*>([^<]+)<', html)
            if not pub_m:
                pub_m = re.search(r'href="(/profile/[^"]+)"', html)
                pub_id = pub_m.group(1) if pub_m else None
                pub_name = "مالك"
            else:
                pub_id = "/profile/" + pub_m.group(1)
                pub_name = pub_m.group(2).strip()

            if pub_name in banned_pubs or is_broker_text(pub_name, title):
                banned_pubs.add(pub_name)
                continue

            if not is_clean_direct_ad(title, html[:12000], item["deal"]):
                continue

            pub_ads_count = 1
            if pub_id:
                try:
                    pr = session.get("https://www.dubizzle.com.eg" + pub_id, timeout=15)
                    if pr.status_code == 200:
                        counts = [int(x) for x in re.findall(r'(\d+)\s+(?:إعلان|اعلان|إعلانات|اعلانات|ads|Ads)', pr.text)]
                        profile_cards = len(set(re.findall(r'-ID(\d+)\.html', pr.text)))
                        pub_ads_count = max(counts + [profile_cards, 1])
                except Exception:
                    pub_ads_count = 99

            if pub_ads_count < 1 or pub_ads_count > 4:
                if pub_name != "مالك":
                    banned_pubs.add(pub_name)
                continue

            p_m = re.search(r'([\d,]+)\s*ج\.م', html)
            price_str = p_m.group(0) if p_m else "السعر بالداخل"
            price_num = int(p_m.group(1).replace(",", "")) if p_m else 0

            area_m = re.search(r'(\d{2,4})\s*(?:متر|م²|sqm)', html)
            area_val = int(area_m.group(1)) if area_m else None

            rooms_m = re.search(r'(\d)\s*(?:غرف|غرفة|نوم)', html)
            rooms_val = int(rooms_m.group(1)) if rooms_m else None

            ad_ts = int(time.time())
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
                "url": item["url"],
                "verified_v12": True,
                "scraped_at": datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %H:%M")
            })
            time.sleep(random.uniform(1.2, 2.2))
        except Exception:
            continue

    final_ads = [a for a in (new_verified + kept) if a.get("publisher") not in banned_pubs and a.get("ad_id") not in banned_ids]
    final_ads.sort(key=lambda x: (x.get("fresh_tier", 1), x.get("first_seen_ts", 0)), reverse=True)

    now_str = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
    out = {
        "updated_at": now_str,
        "total": len(final_ads),
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
