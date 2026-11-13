import json, re, time, random, os, base64
from datetime import datetime, timezone, timedelta
import requests as std_requests
from curl_cffi import requests

CAIRO_TZ = timezone(timedelta(hours=2))
DATA_FILE = "ads.json"
TG_CONFIG_TOPIC = "gamal_vip_tg_9941_sec"
AI_ANALYZE_URL = "https://gamal216.pythonanywhere.com/analyze"
AI_MONITOR_URL = "https://gamal216.pythonanywhere.com/monitor"

MAX_AD_AGE_SECONDS = 7 * 86400
MIN_CASH_SALE_PRICE = 1400000

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

AQARMAP_SOURCES = [
    {"cat": "شقق", "deal": "إيجار", "pages": 3, "url": "https://aqarmap.com.eg/ar/for-rent/apartment/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "فلل", "deal": "إيجار", "pages": 2, "url": "https://aqarmap.com.eg/ar/for-rent/villa/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "تجاري", "deal": "إيجار", "pages": 2, "url": "https://aqarmap.com.eg/ar/for-rent/commercial/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "شقق", "deal": "تمليك", "pages": 2, "url": "https://aqarmap.com.eg/ar/for-sale/apartment/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "فلل", "deal": "تمليك", "pages": 2, "url": "https://aqarmap.com.eg/ar/for-sale/villa/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "تجاري", "deal": "تمليك", "pages": 1, "url": "https://aqarmap.com.eg/ar/for-sale/commercial/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "أراضي", "deal": "تمليك", "pages": 1, "url": "https://aqarmap.com.eg/ar/for-sale/land/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
]

OPENSOOQ_SOURCES = [
    {"cat": "شقق", "deal": "إيجار", "pages": 3, "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للايجار/شقق-للايجار"},
    {"cat": "فلل", "deal": "إيجار", "pages": 2, "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للايجار/فلل-قصور-للايجار"},
    {"cat": "تجاري", "deal": "إيجار", "pages": 2, "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للايجار/محلات-وتجاري-للايجار"},
    {"cat": "شقق", "deal": "تمليك", "pages": 2, "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للبيع/شقق-للبيع"},
    {"cat": "فلل", "deal": "تمليك", "pages": 2, "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للبيع/فلل-قصور-للبيع"},
    {"cat": "تجاري", "deal": "تمليك", "pages": 1, "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للبيع/محلات-وتجاري-للبيع"},
]

def normalize_ar(text):
    t = (text or "").lower()
    t = re.sub(r'[\u0640\u064B-\u065F]', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def extract_ad_core_text(html):
    cleaned = re.sub(r'<(script|style|svg|noscript|header|footer|nav)[^>]*>.*?</\1>', ' ', html, flags=re.S | re.I)
    tags_stripped = re.sub(r'<[^>]+>', ' ', cleaned)
    tags_stripped = re.sub(r'\s+', ' ', tags_stripped)
    for cutoff in ["عقارات مشابهة", "إعلانات مشابهة", "اعلانات مشابهة", "عقارات مقترحة", "Related ads"]:
        idx = tags_stripped.find(cutoff)
        if idx != -1 and idx > 150:
            tags_stripped = tags_stripped[:idx]
    desc_matches = re.findall(r'"description"\s*:\s*"([^"]+)"', html)
    return (" ".join(desc_matches) + " " + tags_stripped).strip()

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
    if any(p in t for p in ["شركة عقارات", "مكتب عقارات", "للتسويق العقاري", "للاستشارات العقارية", "عمولة المكتب", "عموله المكتب", "متاح لدينا وحدات", "متوفر لدينا شقق"]):
        return True
    return False

def verify_with_external_ai(title, core_text, publisher, deal, cat, price_num, source, stats):
    try:
        payload = {
            "title": title,
            "description": core_text[:1800],
            "publisher": publisher,
            "deal": deal,
            "cat": cat,
            "price_num": price_num,
            "source": source
        }
        r = std_requests.post(AI_ANALYZE_URL, json=payload, timeout=10)
        if r.status_code == 200:
            res = r.json()
            dec = str(res.get("decision", "")).strip()
            if any(w in dec for w in ["مرفوض", "سمسار", "تقسيط", "شركة", "بيت الوطن"]):
                stats["ai_rejected"] += 1
                return False, None, None
            return True, res.get("area"), res.get("rooms")
    except Exception:
        pass
    return True, None, None

def compute_tier_from_ts(ts):
    age_sec = int(time.time()) - int(ts)
    if age_sec <= 12 * 3600:
        return 3
    if age_sec <= 36 * 3600:
        return 2
    return 1

def parse_aqarmap_ad(session, url, ad_id, cat, deal, stats):
    try:
        r = session.get(url, timeout=18)
        if r.status_code != 200:
            return None
        html = r.text
        stats["aq_checked"] += 1

        t_m = re.search(r'<title>([^<]+)</title>', html)
        title = t_m.group(1).split("|")[0].split("-")[0].strip() if t_m else ""
        if not title or len(title) < 5:
            return None

        core_text = extract_ad_core_text(html)
        if any(x in core_text[:3000] for x in ["مطور عقاري", "شركة عقارية", "وسيط عقاري", "وكيل عقاري"]):
            if "المالك" not in core_text[:3000]:
                stats["aq_rejected_broker"] += 1
                return None

        zone = detect_zone(title, core_text)
        if not zone:
            stats["aq_rejected_zone"] += 1
            return None

        p_m = re.search(r'([\d,]{4,15})\s*(?:جنيه|ج\.م|EGP)', html)
        price_str = f"{p_m.group(1)} ج.م" if p_m else "السعر بالتفاصيل"
        price_num = int(p_m.group(1).replace(",", "")) if p_m else 0

        if not is_clean_direct_ad(title, core_text, deal, price_num):
            stats["aq_rejected_installments"] += 1
            return None

        if is_broker_text("", core_text):
            stats["aq_rejected_broker"] += 1
            return None

        area_m = re.search(r'(\d{2,4})\s*(?:متر|م²|م2)', core_text)
        area_val = int(area_m.group(1)) if area_m else None

        rooms_m = re.search(r'(\d)\s*(?:غرف|غرفة|نوم)', core_text)
        rooms_val = int(rooms_m.group(1)) if rooms_m else None

        ai_ok, ai_area, ai_rooms = verify_with_external_ai(title, core_text, "مالك (عقارماب)", deal, cat, price_num, "عقارماب", stats)
        if not ai_ok:
            return None
        if not area_val and isinstance(ai_area, int):
            area_val = ai_area
        if not rooms_val and isinstance(ai_rooms, int):
            rooms_val = ai_rooms

        now_cairo = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
        return {
            "ad_id": ad_id,
            "source": "عقارماب",
            "title": title,
            "price": price_str,
            "price_num": price_num,
            "zone": zone,
            "cat": cat,
            "deal": deal,
            "area": area_val,
            "rooms": rooms_val,
            "publisher": "مالك (عقارماب)",
            "pub_ads": 1,
            "age": "اليوم",
            "fresh_tier": 3,
            "first_seen_ts": int(time.time()),
            "desc_verified_v2": True,
            "url": url,
            "verified_v12": True,
            "scraped_at": now_cairo
        }
    except Exception:
        return None

def parse_opensooq_ad(session, url, ad_id, cat, deal, stats):
    try:
        r = session.get(url, timeout=18)
        if r.status_code != 200:
            return None
        html = r.text
        stats["os_checked"] += 1

        t_m = re.search(r'<title>([^<]+)</title>', html)
        title = t_m.group(1).split("|")[0].split("-")[0].strip() if t_m else ""
        if not title or len(title) < 5:
            return None

        core_text = extract_ad_core_text(html)
        if any(x in core_text[:4000] for x in ["الوسيط", "مكتب عقاري", "شركة عقارية"]):
            stats["os_rejected_broker"] += 1
            return None

        zone = detect_zone(title, core_text)
        if not zone:
            stats["os_rejected_zone"] += 1
            return None

        p_m = re.search(r'([\d,]{4,15})\s*(?:جنيه|ج\.م|EGP)', html)
        price_str = f"{p_m.group(1)} ج.م" if p_m else "السعر بالتفاصيل"
        price_num = int(p_m.group(1).replace(",", "")) if p_m else 0

        if not is_clean_direct_ad(title, core_text, deal, price_num):
            stats["os_rejected_installments"] += 1
            return None

        if is_broker_text("", core_text):
            stats["os_rejected_broker"] += 1
            return None

        area_m = re.search(r'(\d{2,4})\s*(?:متر|م²|م2)', core_text)
        area_val = int(area_m.group(1)) if area_m else None

        rooms_m = re.search(r'(\d)\s*(?:غرف|غرفة|نوم)', core_text)
        rooms_val = int(rooms_m.group(1)) if rooms_m else None

        ai_ok, ai_area, ai_rooms = verify_with_external_ai(title, core_text, "مالك (السوق المفتوح)", deal, cat, price_num, "السوق المفتوح", stats)
        if not ai_ok:
            return None
        if not area_val and isinstance(ai_area, int):
            area_val = ai_area
        if not rooms_val and isinstance(ai_rooms, int):
            rooms_val = ai_rooms

        now_cairo = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
        return {
            "ad_id": ad_id,
            "source": "السوق المفتوح",
            "title": title,
            "price": price_str,
            "price_num": price_num,
            "zone": zone,
            "cat": cat,
            "deal": deal,
            "area": area_val,
            "rooms": rooms_val,
            "publisher": "مالك (السوق المفتوح)",
            "pub_ads": 1,
            "age": "اليوم",
            "fresh_tier": 3,
            "first_seen_ts": int(time.time()),
            "desc_verified_v2": True,
            "url": url,
            "verified_v12": True,
            "scraped_at": now_cairo
        }
    except Exception:
        return None

def send_admin_telegram_reports(data, final_ads, stats):
    tg_cfg = data.get("telegram_config") or {}
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN") or tg_cfg.get("tok", "")
    admin_cid = os.environ.get("TELEGRAM_CHAT_ID") or tg_cfg.get("cid", "")

    try:
        r = std_requests.get(f"https://ntfy.sh/{TG_CONFIG_TOPIC}/json?poll=1&since=all", timeout=8)
        if r.status_code == 200 and r.text.strip():
            lines = [ln for ln in r.text.strip().splitlines() if ln.strip()]
            if lines:
                last_msg = json.loads(lines[-1]).get("message", "")
                if last_msg:
                    decoded = json.loads(base64.b64decode(last_msg).decode("utf-8"))
                    if decoded.get("tok"):
                        tg_token = decoded["tok"].strip()
                    if decoded.get("cid"):
                        admin_cid = str(decoded["cid"]).strip()
                    data["telegram_config"] = {"tok": tg_token, "cid": admin_cid}
    except Exception:
        pass

    notified_ids = set(data.get("telegram_notified_ids", []))
    is_first_notify = len(notified_ids) == 0

    new_cards_to_send = []
    for ad in final_ads:
        aid = ad.get("ad_id")
        if aid not in notified_ids:
            new_cards_to_send.append(ad)
            notified_ids.add(aid)

    new_cards_to_send = new_cards_to_send[:5] if is_first_notify else new_cards_to_send[:15]

    dub_total = sum(1 for a in final_ads if a.get("source", "دوبيزل") == "دوبيزل")
    aq_total = sum(1 for a in final_ads if a.get("source") == "عقارماب")
    os_total = sum(1 for a in final_ads if a.get("source") == "السوق المفتوح")
    rent_total = sum(1 for a in final_ads if a.get("deal") == "إيجار")
    sale_total = sum(1 for a in final_ads if a.get("deal") == "تمليك")
    dub_rep = data.get("last_run_report") or {}
    now_str = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")

    ai_advice = "جميع المنصات تعمل بكفاءة عالية."
    try:
        m_res = std_requests.post(AI_MONITOR_URL, json={
            "total_ads": len(final_ads),
            "rent_total": rent_total,
            "sale_total": sale_total,
            "dub_added": dub_rep.get("dub_added", 0),
            "aq_checked": stats["aq_checked"],
            "os_checked": stats["os_checked"]
        }, timeout=8)
        if m_res.status_code == 200:
            ai_advice = m_res.json().get("ai_advice", ai_advice)
    except Exception:
        pass

    if not tg_token or not admin_cid:
        data["telegram_notified_ids"] = list(notified_ids)[-5000:]
        return

    summary_text = (
        f"تقرير القيادة الذكي (AI Master) | مصيدة الملاك\n"
        f"التوقيت: {now_str}\n"
        f"--------------------------------\n"
        f"الإجمالي الحي بالموقع: {len(final_ads)} إعلان مالك\n"
        f"- إيجار مباشر: {rent_total} إعلان | تمليك كاش: {sale_total} إعلان\n"
        f"- دوبيزل: {dub_total} | عقارماب: {aq_total} | السوق المفتوح: {os_total}\n"
        f"--------------------------------\n"
        f"نتائج الفحص في هذه الجولة:\n"
        f"- دوبيزل: فحص ({dub_rep.get('dub_inspected', 0)}) | قبول ملاك جدد ({dub_rep.get('dub_added', 0)})\n"
        f"- عقارماب: فحص ({stats['aq_checked']}) | استبعاد سمسار/تقسيط ({stats['aq_rejected_broker'] + stats['aq_rejected_installments']})\n"
        f"- السوق المفتوح: فحص ({stats['os_checked']}) | استبعاد سمسار/تقسيط ({stats['os_rejected_broker'] + stats['os_rejected_installments']})\n"
        f"- استبعاد إضافي بالذكاء الاصطناعي: {stats['ai_rejected']} إعلان\n"
        f"- تشخيص المراقب الذكي: {ai_advice}"
    )

    try:
        std_requests.post(
            f"https://api.telegram.org/bot{tg_token}/sendMessage",
            json={"chat_id": admin_cid, "text": summary_text},
            timeout=10
        )
    except Exception:
        pass

    for ad in new_cards_to_send:
        msg_text = (
            f"إعلان مالك جديد ({ad.get('deal')} | {ad.get('source', 'دوبيزل')})\n"
            f"العنوان: {ad.get('title')}\n"
            f"السعر: {ad.get('price')}\n"
            f"المنطقة: {ad.get('zone')} | {ad.get('cat')}\n"
            f"المساحة: {ad.get('area') or '-'} م² | الغرف: {ad.get('rooms') or '-'}\n"
            f"الرابط: {ad.get('url')}"
        )
        try:
            std_requests.post(
                f"https://api.telegram.org/bot{tg_token}/sendMessage",
                json={"chat_id": admin_cid, "text": msg_text, "disable_web_page_preview": True},
                timeout=10
            )
            time.sleep(0.3)
        except Exception:
            pass

    data["telegram_notified_ids"] = list(notified_ids)[-5000:]

def run_extra_radar():
    if not os.path.exists(DATA_FILE):
        return
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    now_ts = int(time.time())
    existing_ads = data.get("ads", [])
    extra_checked = set(data.get("extra_checked_ids", []))
    banned_ids = set(data.get("banned_ad_ids", []))
    banned_pubs = set(data.get("banned_publishers", []))

    session = requests.Session(impersonate="chrome120")
    session.headers.update({"Accept-Language": "ar-EG,ar;q=0.9"})

    kept_map = {}
    for a in existing_ads:
        aid = a.get("ad_id")
        if not aid:
            continue
        if a.get("source") in ("عقارماب", "السوق المفتوح"):
            extra_checked.add(aid)
        pub = a.get("publisher", "")
        if aid in banned_ids or pub in banned_pubs:
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

        a.pop("_extra_meta", None)
        a["desc_verified_v2"] = True
        a["first_seen_ts"] = orig_ts
        a["fresh_tier"] = compute_tier_from_ts(orig_ts)
        kept_map[aid] = a

    stats = {
        "aq_checked": 0, "aq_rejected_broker": 0, "aq_rejected_zone": 0, "aq_rejected_installments": 0,
        "os_checked": 0, "os_rejected_broker": 0, "os_rejected_zone": 0, "os_rejected_installments": 0,
        "ai_rejected": 0
    }

    new_extra = []

    for src in AQARMAP_SOURCES:
        max_p = src.get("pages", 2)
        for page in range(1, max_p + 1):
            page_url = src["url"] if page == 1 else f"{src['url']}&page={page}"
            try:
                r = session.get(page_url, timeout=18)
                print(f"[Aqarmap] {src['cat']} ({src['deal']}) p.{page} -> HTTP {r.status_code}")
                if r.status_code != 200:
                    break
                matches = re.findall(r'((?:https?://aqarmap\.com\.eg)?/ar/listing/(\d+)[^"\'\s<>\\]*)', r.text)
                unseen_batch = []
                seen_in_page = set()
                for raw_path, lid in matches:
                    ad_id = 700000000 + int(lid)
                    if ad_id in seen_in_page or ad_id in kept_map or ad_id in extra_checked or ad_id in banned_ids:
                        continue
                    seen_in_page.add(ad_id)
                    clean_path = re.sub(r'^https?://aqarmap\.com\.eg', '', raw_path)
                    unseen_batch.append((ad_id, "https://aqarmap.com.eg" + clean_path))

                limit_cnt = 14 if src["deal"] == "إيجار" else 8
                for ad_id, full_url in unseen_batch[:limit_cnt]:
                    extra_checked.add(ad_id)
                    ad_obj = parse_aqarmap_ad(session, full_url, ad_id, src["cat"], src["deal"], stats)
                    if ad_obj:
                        new_extra.append(ad_obj)
                        kept_map[ad_id] = ad_obj
                    time.sleep(random.uniform(0.7, 1.2))
            except Exception as e:
                print(f"[Aqarmap Error] {e}")
                break

    for src in OPENSOOQ_SOURCES:
        max_p = src.get("pages", 2)
        for page in range(1, max_p + 1):
            page_url = src["url"] if page == 1 else f"{src['url']}?page={page}"
            try:
                r = session.get(page_url, timeout=18)
                print(f"[OpenSooq] {src['cat']} ({src['deal']}) p.{page} -> HTTP {r.status_code}")
                if r.status_code != 200:
                    break
                matches = re.findall(r'((?:https?://eg\.opensooq\.com)?/ar/search/(\d{8,10})(?:/[^"\'\s<>\\]*)?)', r.text)
                unseen_batch = []
                seen_in_page = set()
                for raw_path, lid in matches:
                    ad_id = 800000000 + int(lid[-8:])
                    if ad_id in seen_in_page or ad_id in kept_map or ad_id in extra_checked or ad_id in banned_ids:
                        continue
                    seen_in_page.add(ad_id)
                    clean_path = re.sub(r'^https?://eg\.opensooq\.com', '', raw_path)
                    unseen_batch.append((ad_id, "https://eg.opensooq.com" + clean_path))

                limit_cnt = 14 if src["deal"] == "إيجار" else 8
                for ad_id, full_url in unseen_batch[:limit_cnt]:
                    extra_checked.add(ad_id)
                    ad_obj = parse_opensooq_ad(session, full_url, ad_id, src["cat"], src["deal"], stats)
                    if ad_obj:
                        new_extra.append(ad_obj)
                        kept_map[ad_id] = ad_obj
                    time.sleep(random.uniform(0.7, 1.2))
            except Exception as e:
                print(f"[OpenSooq Error] {e}")
                break

    final_ads = sorted(
        list(kept_map.values()),
        key=lambda x: (x.get("first_seen_ts", 0), x.get("ad_id", 0)),
        reverse=True
    )

    send_admin_telegram_reports(data, final_ads, stats)

    now_str = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
    rep = data.get("last_run_report") or {}
    rep.update({
        "last_run_at": now_str,
        "aq_checked": stats["aq_checked"],
        "os_checked": stats["os_checked"],
        "extra_added": len(new_extra),
        "ai_rejected": stats["ai_rejected"]
    })

    data["updated_at"] = now_str
    data["total"] = len(final_ads)
    data["last_run_report"] = rep
    data["ads"] = final_ads
    data["extra_checked_ids"] = list(extra_checked)[-6000:]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_extra_radar()
