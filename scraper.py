import sentry_sdk
sentry_sdk.init(
    dsn="https://3b5256edded0be9600bd289dcf4b66c6@o4512424824799232.ingest.de.sentry.io/4512425074425936",
    traces_sample_rate=1.0,
)
import json, re, time, random, os
from datetime import datetime, timezone, timedelta
from curl_cffi import requests

CAIRO_TZ = timezone(timedelta(hours=2))
DATA_FILE = "ads.json"
NTFY_BAN_TOPIC = "gamal_vip_ban_9941_sec"

PAGES_PER_CATEGORY = int(os.environ.get("PAGES_PER_CATEGORY", "3"))
MAX_RUNTIME_SECONDS = int(os.environ.get("MAX_RUNTIME_SECONDS", "600"))
MAX_AD_AGE_SECONDS = 7 * 86400
MIN_CASH_SALE_PRICE = 1400000

CATEGORIES = [
    {"name": "شقق", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo-fifth-settlement/"},
    {"name": "شقق", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo-fifth-settlement/"},
    {"name": "شقق", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/"},
    {"name": "شقق", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/"},
    {"name": "فلل", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo-fifth-settlement/"},
    {"name": "فلل", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo-fifth-settlement/"},
    {"name": "فلل", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/"},
    {"name": "تجاري", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo-fifth-settlement/"},
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

def normalize_ar(text):
    t = (text or "").lower()
    t = re.sub(r'[\u0640\u064B-\u065F]', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def extract_visible_text(html):
    cleaned = re.sub(r'<(script|style|svg|noscript)[^>]*>.*?</\1>', ' ', html, flags=re.S | re.I)
    desc_matches = re.findall(r'"description"\s*:\s*"([^"]+)"', html)
    tags_stripped = re.sub(r'<[^>]+>', ' ', cleaned)
    return tags_stripped + " " + " ".join(desc_matches)

def detect_zone(text):
    t = normalize_ar(text)
    for city in EXCLUDED_CITIES:
        if normalize_ar(city) in t:
            return None
    for z_name, keywords in ZONES:
        for kw in keywords:
            if normalize_ar(kw) in t:
                return z_name
    if any(k in t for k in ["القاهرة الجديدة", "القاهره الجديده", "تجمع", "new cairo", "settlement"]):
        return "القاهرة الجديدة"
    return None

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

# --- دالة الذكاء الاصطناعي الجديدة للاتصال بخادم PythonAnywhere ---
def analyze_with_ai(ad_text, active_ads_count):
    url = "https://gamal216.pythonanywhere.com/analyze"
    payload = {
        "text": ad_text,
        "active_ads_count": active_ads_count
    }
    try:
        # استخدام requests القياسي للاتصال بالـ API
        import requests as std_requests 
        response = std_requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                analysis = result.get("analysis", "")
                if "سمسار" in analysis and "مالك حقيقي" not in analysis:
                    return False # سمسار
                return True # مالك
    except Exception as e:
        print(f"[AI Server Error] {e}")
        # في حالة فشل الخادم لأي سبب، نعتمد على الفلتر الآمن (من 1 لـ 4 إعلانات)
        if 1 <= active_ads_count <= 4:
            return True
        return False
    return False

def run_scraper():
    start_ts = time.time()
    now_ts = int(start_ts)
    raw_data, existing_ads, checked_ids, banned_pubs, banned_ids = load_existing()
    sync_ntfy_bans(banned_pubs, banned_ids)

    session = requests.Session(impersonate="chrome120")
    session.headers.update({
        "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.dubizzle.com.eg/"
    })

    kept = []
    seen_ids = set()
    
    # تنظيف الإعلانات القديمة والاحتفاظ بالصالحة
    for a in existing_ads:
        aid = a.get("ad_id")
        if not aid:
            continue
        checked_ids.add(aid)
        pub = a.get("publisher", "")
        if aid in banned_ids or pub in banned_pubs or aid in seen_ids:
            continue

        orig_ts = a.get("first_seen_ts") or (now_ts - 86400)
        if (now_ts - orig_ts) > MAX_AD_AGE_SECONDS:
            continue

        a["first_seen_ts"] = orig_ts
        a["fresh_tier"] = compute_tier_from_ts(orig_ts)
        kept.append(a)
        seen_ids.add(aid)

    candidates = []
    pages_fetched = 0

    # مرحلة سحب الروابط
    for page in range(1, PAGES_PER_CATEGORY + 1):
        if time.time() - start_ts > MAX_RUNTIME_SECONDS * 0.40:
            break
        for cat in CATEGORIES:
            url = cat["url"] if page == 1 else f"{cat['url']}?page={page}"
            try:
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
                    candidates.append({
                        "ad_id": ad_id,
                        "url": "https://www.dubizzle.com.eg" + clean_path,
                        "cat": cat["name"],
                        "deal": cat["deal"]
                    })
                    seen_ids.add(ad_id)
                time.sleep(random.uniform(0.7, 1.2))
            except Exception as e:
                print(f"[Dubizzle Error] {e}")
                continue

    print(f"[Dubizzle] Total new candidates to inspect: {len(candidates)}")
    new_verified = []
    inspected_cnt = 0

    # مرحلة الفحص العميق بالذكاء الاصطناعي
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

            if "/companies/" in html or "featured_agency" in html:
                continue

            t_m = re.search(r'<title>([^<]+)</title>', html)
            title = t_m.group(1).split("|")[0].split("-")[0].strip() if t_m else ""
            if not title:
                continue

            visible_text = extract_visible_text(html)
            zone = detect_zone(title + " " + visible_text[:5000])
            if not zone:
                continue

            age_label, _, is_recent = parse_age_and_tier(visible_text)
            if not is_recent:
                continue

            pub_m = re.search(r'"((?:/ar|/en)?/profile/[a-zA-Z0-9_-]+)"[^>]*>([^<]+)<', html)
            if not pub_m:
                pub_m2 = re.search(r'href="((?:/ar|/en)?/profile/[a-zA-Z0-9_-]+)"', html)
                if not pub_m2:
                    continue
                pub_id = pub_m2.group(1)
                name_m = re.search(r'"sellerName"\s*:\s*"([^"]+)"', html) or re.search(r'"name"\s*:\s*"([^"]+)"', html)
                pub_name = name_m.group(1).strip() if name_m else "مالك مباشر"
            else:
                pub_id = pub_m.group(1)
                pub_name = pub_m.group(2).strip()

            p_m = re.search(r'([\d,]{4,15})\s*ج\.م', html) or re.search(r'EGP\s*([\d,]{4,15})', html)
            if p_m:
                price_num = int(p_m.group(1).replace(",", ""))
                price_str = f"{p_m.group(1)} ج.م"
            else:
                price_num = 0
                price_str = "السعر بالتفاصيل"

            pub_ads_count = 1
            try:
                clean_prof = re.sub(r'^/(?:ar|en)/', '/', pub_id)
                pr = session.get("https://www.dubizzle.com.eg" + clean_prof, timeout=15)
                if pr.status_code == 200:
                    profile_cards = len(set(re.findall(r'-ID(\d+)\.html', pr.text)))
                    exact_counts = [int(x) for x in re.findall(r'(\d+)\s+(?:إعلان\b|اعلان\b|إعلانات\b|اعلانات\b|published ads\b|active ads\b)', pr.text, re.I) if int(x) < 300]
                    pub_ads_count = max(exact_counts + [profile_cards, 1])
            except Exception:
                pub_ads_count = 1

            # إرسال البيانات لخادم الذكاء الاصطناعي للفحص القاطع
            is_direct_owner = analyze_with_ai(title + " " + visible_text, pub_ads_count)
            
            if not is_direct_owner:
                banned_pubs.add(pub_name)
                print(f"[Rejected by AI] {pub_name} | Ads: {pub_ads_count}")
                continue

            area_m = re.search(r'(\d{2,4})\s*(?:متر|م²|sqm|m²)', visible_text, re.I)
            area_val = int(area_m.group(1)) if area_m else None

            rooms_m = re.search(r'(\d)\s*(?:غرف|غرفة|نوم|beds|bed|bedrooms)', visible_text, re.I)
            rooms_val = int(rooms_m.group(1)) if rooms_m else None

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
            print(f"[+ Approved by AI] {item['deal']} | {zone} | {title[:40]}")
            time.sleep(random.uniform(0.9, 1.5))
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
        
