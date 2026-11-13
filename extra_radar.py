import json, re, time, random, os, base64
from datetime import datetime, timezone, timedelta
import requests as std_requests
from curl_cffi import requests

CAIRO_TZ = timezone(timedelta(hours=2))
DATA_FILE = "ads.json"
TG_CONFIG_TOPIC = "gamal_vip_tg_9941_sec"
MAX_AD_AGE_SECONDS = 7 * 86400

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
    "development", "group", "homes", "house", "capital"
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

AQARMAP_SOURCES = [
    {"cat": "شقق", "deal": "تمليك", "url": "https://aqarmap.com.eg/ar/for-sale/apartment/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "شقق", "deal": "إيجار", "url": "https://aqarmap.com.eg/ar/for-rent/apartment/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "فلل", "deal": "تمليك", "url": "https://aqarmap.com.eg/ar/for-sale/villa/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "فلل", "deal": "إيجار", "url": "https://aqarmap.com.eg/ar/for-rent/villa/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "تجاري", "deal": "تمليك", "url": "https://aqarmap.com.eg/ar/for-sale/commercial/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "تجاري", "deal": "إيجار", "url": "https://aqarmap.com.eg/ar/for-rent/commercial/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "أراضي", "deal": "تمليك", "url": "https://aqarmap.com.eg/ar/for-sale/land/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
]

OPENSOOQ_SOURCES = [
    {"cat": "شقق", "deal": "تمليك", "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للبيع/شقق-للبيع"},
    {"cat": "شقق", "deal": "إيجار", "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للايجار/شقق-للايجار"},
    {"cat": "فلل", "deal": "تمليك", "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للبيع/فلل-قصور-للبيع"},
    {"cat": "فلل", "deal": "إيجار", "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للايجار/فلل-قصور-للايجار"},
    {"cat": "تجاري", "deal": "تمليك", "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للبيع/محلات-وتجاري-للبيع"},
    {"cat": "تجاري", "deal": "إيجار", "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للايجار/محلات-وتجاري-للايجار"},
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

        if any(x in html for x in ["مطور عقاري", "شركة عقارية", "وسيط عقاري", "وكيل عقاري"]):
            if "المالك" not in html[:6000]:
                stats["aq_rejected_broker"] += 1
                return None

        zone = detect_zone(title + " " + html[:6000])
        if not zone:
            stats["aq_rejected_zone"] += 1
            return None

        if not is_clean_direct_ad(title, html[:12000], deal):
            stats["aq_rejected_installments"] += 1
            return None

        if is_broker_text("", title):
            stats["aq_rejected_broker"] += 1
            return None

        p_m = re.search(r'([\d,]{4,15})\s*(?:جنيه|ج\.م|EGP)', html)
        price_str = f"{p_m.group(1)} ج.م" if p_m else "السعر بالداخل"
        price_num = int(p_m.group(1).replace(",", "")) if p_m else 0

        area_m = re.search(r'(\d{2,4})\s*(?:متر|م²|م2)', html)
        area_val = int(area_m.group(1)) if area_m else None

        rooms_m = re.search(r'(\d)\s*(?:غرف|غرفة|نوم)', html)
        rooms_val = int(rooms_m.group(1)) if rooms_m else None

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
            "age": "حديث",
            "fresh_tier": 3,
            "first_seen_ts": int(time.time()),
            "url": url,
            "verified_v12": True,
            "scraped_at": datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %H:%M")
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

        if any(x in html[:8000] for x in ["الوسيط", "مكتب عقاري", "شركة عقارية"]):
            stats["os_rejected_broker"] += 1
            return None

        zone = detect_zone(title + " " + html[:6000])
        if not zone:
            stats["os_rejected_zone"] += 1
            return None

        if not is_clean_direct_ad(title, html[:12000], deal):
            stats["os_rejected_installments"] += 1
            return None

        if is_broker_text("", title):
            stats["os_rejected_broker"] += 1
            return None

        p_m = re.search(r'([\d,]{4,15})\s*(?:جنيه|ج\.م|EGP)', html)
        price_str = f"{p_m.group(1)} ج.م" if p_m else "السعر بالداخل"
        price_num = int(p_m.group(1).replace(",", "")) if p_m else 0

        area_m = re.search(r'(\d{2,4})\s*(?:متر|م²|م2)', html)
        area_val = int(area_m.group(1)) if area_m else None

        rooms_m = re.search(r'(\d)\s*(?:غرف|غرفة|نوم)', html)
        rooms_val = int(rooms_m.group(1)) if rooms_m else None

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
            "age": "حديث",
            "fresh_tier": 3,
            "first_seen_ts": int(time.time()),
            "url": url,
            "verified_v12": True,
            "scraped_at": datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %H:%M")
        }
    except Exception:
        return None

def send_admin_telegram_reports(data, final_ads, stats, run_new_extra_count):
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

    if not tg_token or not admin_cid:
        return

    notified_ids = set(data.get("telegram_notified_ids", []))
    is_first_notify = len(notified_ids) == 0

    new_cards_to_send = []
    for ad in final_ads:
        aid = ad.get("ad_id")
        if aid not in notified_ids:
            new_cards_to_send.append(ad)
            notified_ids.add(aid)

    if is_first_notify:
        new_cards_to_send = new_cards_to_send[:5]
    else:
        new_cards_to_send = new_cards_to_send[:15]

    dub_total = sum(1 for a in final_ads if a.get("source", "دوبيزل") == "دوبيزل")
    aq_total = sum(1 for a in final_ads if a.get("source") == "عقارماب")
    os_total = sum(1 for a in final_ads if a.get("source") == "السوق المفتوح")
    now_str = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")

    summary_text = (
        f"تقرير الرن التفصيلي الكامل | مصيدة الملاك\n"
        f"التوقيت: {now_str}\n"
        f"--------------------------------\n"
        f"الإجمالي الحي بالموقع الآن: {len(final_ads)} إعلان مالك\n"
        f"- دوبيزل: {dub_total} إعلان\n"
        f"- عقارماب: {aq_total} إعلان\n"
        f"- السوق المفتوح: {os_total} إعلان\n"
        f"--------------------------------\n"
        f"تفاصيل الفحص في هذه الجولة:\n"
        f"- عقارماب: فحص ({stats['aq_checked']}) | استبعاد سمسار ({stats['aq_rejected_broker']}) | استبعاد تقسيط/بيت وطن ({stats['aq_rejected_installments']})\n"
        f"- السوق المفتوح: فحص ({stats['os_checked']}) | استبعاد سمسار ({stats['os_rejected_broker']}) | استبعاد تقسيط/بيت وطن ({stats['os_rejected_installments']})\n"
        f"- صافي الملاك الجدد المضافين الآن: {len(new_cards_to_send)} إعلان"
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
            f"إعلان مالك جديد ({ad.get('source', 'دوبيزل')})\n"
            f"العنوان: {ad.get('title')}\n"
            f"السعر: {ad.get('price')}\n"
            f"المنطقة: {ad.get('zone')} | {ad.get('cat')} ({ad.get('deal')})\n"
            f"المساحة: {ad.get('area') or '-'} م²\n"
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

    kept_map = {}
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
        a.pop("_extra_meta", None)
        a["first_seen_ts"] = first_ts
        a["fresh_tier"] = compute_tier_from_ts(first_ts)
        kept_map[aid] = a

    stats = {
        "aq_checked": 0, "aq_rejected_broker": 0, "aq_rejected_zone": 0, "aq_rejected_installments": 0,
        "os_checked": 0, "os_rejected_broker": 0, "os_rejected_zone": 0, "os_rejected_installments": 0
    }

    session = requests.Session(impersonate="chrome120")
    new_extra = []

    for src in AQARMAP_SOURCES:
        try:
            r = session.get(src["url"], timeout=18)
            if r.status_code == 200:
                links = list(set(re.findall(r'href="(/ar/listing/(\d+)[^"]*)"', r.text)))
                for rel, lid in links[:8]:
                    ad_id = 700000000 + int(lid)
                    if ad_id in kept_map or ad_id in extra_checked or ad_id in banned_ids:
                        continue
                    extra_checked.add(ad_id)
                    full_url = "https://aqarmap.com.eg" + rel
                    ad_obj = parse_aqarmap_ad(session, full_url, ad_id, src["cat"], src["deal"], stats)
                    if ad_obj:
                        new_extra.append(ad_obj)
                        kept_map[ad_id] = ad_obj
                    time.sleep(random.uniform(0.8, 1.4))
        except Exception:
            continue

    for src in OPENSOOQ_SOURCES:
        try:
            r = session.get(src["url"], timeout=18)
            if r.status_code == 200:
                links = list(set(re.findall(r'href="(/ar/search/(\d+)/[^"]*)"', r.text)))
                for rel, lid in links[:8]:
                    ad_id = 800000000 + int(lid[-8:])
                    if ad_id in kept_map or ad_id in extra_checked or ad_id in banned_ids:
                        continue
                    extra_checked.add(ad_id)
                    full_url = "https://eg.opensooq.com" + rel
                    ad_obj = parse_opensooq_ad(session, full_url, ad_id, src["cat"], src["deal"], stats)
                    if ad_obj:
                        new_extra.append(ad_obj)
                        kept_map[ad_id] = ad_obj
                    time.sleep(random.uniform(0.8, 1.4))
        except Exception:
            continue

    final_ads = sorted(
        list(kept_map.values()),
        key=lambda x: (x.get("fresh_tier", 1), x.get("first_seen_ts", 0)),
        reverse=True
    )

    send_admin_telegram_reports(data, final_ads, stats, len(new_extra))

    now_str = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
    data["updated_at"] = now_str
    data["total"] = len(final_ads)
    data["ads"] = final_ads
    data["extra_checked_ids"] = list(extra_checked)[-5000:]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_extra_radar()
