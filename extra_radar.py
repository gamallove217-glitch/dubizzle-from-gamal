import json, re, time, random, os, base64, socket, urllib.parse
from datetime import datetime, timezone, timedelta
import requests as std_requests
from curl_cffi import requests

CAIRO_TZ = timezone(timedelta(hours=2))
DATA_FILE = "ads.json"
TG_CONFIG_TOPIC = "gamal_vip_tg_9941_sec"
WARP_PROXY = "socks5h://127.0.0.1:40000"
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
    {"cat": "شقق", "deal": "إيجار", "url": "https://aqarmap.com.eg/ar/for-rent/apartment/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "فلل", "deal": "إيجار", "url": "https://aqarmap.com.eg/ar/for-rent/villa/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "تجاري", "deal": "إيجار", "url": "https://aqarmap.com.eg/ar/for-rent/commercial/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "شقق", "deal": "تمليك", "url": "https://aqarmap.com.eg/ar/for-sale/apartment/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "فلل", "deal": "تمليك", "url": "https://aqarmap.com.eg/ar/for-sale/villa/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "تجاري", "deal": "تمليك", "url": "https://aqarmap.com.eg/ar/for-sale/commercial/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
    {"cat": "أراضي", "deal": "تمليك", "url": "https://aqarmap.com.eg/ar/for-sale/land/cairo/new-cairo/?seller_type=1&sort=publishedAt"},
]

OPENSOOQ_SOURCES = [
    {"cat": "شقق", "deal": "إيجار", "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للإيجار/شقق-للايجار"},
    {"cat": "شقق", "deal": "إيجار", "url": "https://eg.opensooq.com/ar/القاهرة/التجمع-الخامس/عقارات-للإيجار/شقق-للايجار"},
    {"cat": "فلل", "deal": "إيجار", "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للإيجار"},
    {"cat": "شقق", "deal": "تمليك", "url": "https://eg.opensooq.com/ar/القاهرة/التجمع-الخامس/عقارات-للبيع/شقق-للبيع"},
    {"cat": "فلل", "deal": "تمليك", "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للبيع/فلل-قصور-للبيع"},
    {"cat": "تجاري", "deal": "تمليك", "url": "https://eg.opensooq.com/ar/القاهرة/القاهرة-الجديدة/عقارات-للبيع"},
]

def is_warp_up():
    try:
        with socket.create_connection(("127.0.0.1", 40000), timeout=1):
            return True
    except Exception:
        return False

class SmartFetcher:
    def __init__(self):
        self.warp_active = is_warp_up()
        self.warp_sess = requests.Session(impersonate="chrome120", proxies={"http": WARP_PROXY, "https": WARP_PROXY})
        self.warp_sess.headers.update({"Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8", "Referer": "https://www.google.com/"})
        self.direct_sess = requests.Session(impersonate="chrome120")
        self.direct_sess.headers.update({"Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8", "Referer": "https://www.google.com/"})
        self.pw = None
        self.browser = None
        self.context = None

    def _ensure_pw(self):
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
                viewport={"width": 1366, "height": 768}
            )
            self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            return True
        except Exception as e:
            print(f"[PW Init] {e}")
            return False

    def _is_valid_html(self, html):
        if not html or len(html) < 1500:
            return False
        if "Pardon Our Interruption" in html or "Just a moment..." in html or "<title>Attention Required!" in html:
            return False
        return True

    def get_html(self, raw_url):
        url = urllib.parse.quote(raw_url, safe=":/?&=#%")
        statuses = []
        if self.warp_active:
            try:
                r = self.warp_sess.get(url, timeout=18)
                statuses.append(f"WARP:{r.status_code}")
                if r.status_code == 200 and self._is_valid_html(r.text):
                    return r.text, "200 (WARP)"
            except Exception:
                statuses.append("WARP:ERR")

        try:
            r = self.direct_sess.get(url, timeout=18)
            statuses.append(f"Direct:{r.status_code}")
            if r.status_code == 200 and self._is_valid_html(r.text):
                return r.text, "200 (Direct)"
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
                statuses.append(f"PW:{code}")
                if self._is_valid_html(html):
                    return html, "200 (Playwright)"
            except Exception:
                if page:
                    try: page.close()
                    except Exception: pass
                statuses.append("PW:ERR")

        try:
            enc = urllib.parse.quote(url, safe="")
            r = std_requests.get(f"https://api.codetabs.com/v1/proxy?quest={enc}", timeout=20)
            statuses.append(f"Proxy:{r.status_code}")
            if r.status_code == 200 and self._is_valid_html(r.text):
                return r.text, "200 (Proxy)"
        except Exception:
            statuses.append("Proxy:ERR")

        return "", " | ".join(statuses)

    def close(self):
        try:
            if self.browser: self.browser.close()
            if self.pw: self.pw.stop()
        except Exception:
            pass

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
    if any(w in norm_text for w in ["اسبوع", "أسبوع", "شهر", "أشهر", "اشهر", "سنة", "سنه"]):
        return ("قديم", 0, False)
    m = re.search(r'منذ\s+(\d+)\s*(يوم|أيام|ايام)', norm_text)
    if m:
        days = int(m.group(1))
        if days > 5: return (f"منذ {days} أيام", 0, False)
        if days <= 1: return ("منذ يوم", 2, True)
        return (f"منذ {days} أيام", 1, True)
    if "أمس" in norm_text or "امس" in norm_text or "منذ يوم" in norm_text:
        return ("منذ يوم", 2, True)
    return ("حديث", 3, True)

def is_strict_cash_sale(title, visible_text, price_num):
    full_text = normalize_ar(title + " " + visible_text[:4500])
    for neg in SAFE_CASH_NEGATIONS:
        full_text = full_text.replace(normalize_ar(neg), " ")
    for kw in INSTALLMENT_PATTERNS:
        kw_norm = normalize_ar(kw)
        if re.search(r'(^|\s|،|\.|/|-|\(|\*)' + re.escape(kw_norm) + r'(\s|$|،|\.|/|-|\)|\*|:)', full_text):
            return False
    if re.search(r'\b\d+\s*%\s*(مقدم|تعاقد|دفعة|دفعه|down)', full_text):
        return False
    if price_num > 0 and price_num < MIN_CASH_SALE_PRICE:
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
        payload = {
            "chat_id": cid,
            "text": text_msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        r = std_requests.post(url, json=payload, timeout=12)
        return r.status_code == 200
    except Exception:
        return False

def analyze_with_ai(title, visible_text, pub_name, deal, cat, price_num, source):
    url = "https://gamal216.pythonanywhere.com/analyze"
    payload = {
        "text": f"{title} {visible_text[:3500]}",
        "title": title,
        "description": visible_text[:3500],
        "publisher": pub_name,
        "deal": deal,
        "cat": cat,
        "price_num": price_num,
        "source": source,
        "active_ads_count": 1
    }
    try:
        response = std_requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                if result.get("decision") == "مرفوض":
                    return False
                analysis = result.get("analysis", "")
                if "سمسار" in analysis and "مالك حقيقي" not in analysis:
                    return False
                return True
    except Exception as e:
        print(f"[AI Server Error in Extra Radar] {e}")
    if deal == "تمليك":
        return is_strict_cash_sale(title, visible_text, price_num)
    return True

def monitor_system_with_ai(stats_dict):
    url = "https://gamal216.pythonanywhere.com/monitor"
    try:
        response = std_requests.post(url, json=stats_dict, timeout=20)
        if response.status_code == 200:
            res = response.json()
            if res.get("status") == "success":
                return res.get("ai_advice", "النظام يعمل بشكل طبيعي"), res.get("health", "جيد")
    except Exception as e:
        print(f"[AI Monitor Error] {e}")
    return "تعذر الاتصال بعقل المراقبة، الفحص التقليدي سليم.", "غير معروف"

def run_extra_radar():
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    existing_ads = data.get("ads", [])
    extra_checked = set(data.get("extra_checked_ids", []))
    banned_pubs = set(data.get("banned_publishers", []))
    banned_ids = set(data.get("banned_ad_ids", []))
    notified_ids = set(data.get("telegram_notified_ids", []))
    tg_cfg = sync_telegram_config(data.get("telegram_config", {}))
    run_report = data.get("last_run_report", {})

    seen_ids = {a.get("ad_id") for a in existing_ads if a.get("ad_id")}
    fetcher = SmartFetcher()
    new_extra_ads = []

    aq_candidates = []
    for src in AQARMAP_SOURCES:
        for page in range(1, 3):
            page_url = src["url"] if page == 1 else f"{src['url']}&page={page}"
            html, status_info = fetcher.get_html(page_url)
            print(f"[Aqarmap] {src['cat']} ({src['deal']}) p.{page} -> {status_info}")
            time.sleep(random.uniform(1.0, 1.8))
            if not html:
                continue
            links = re.findall(r'href="(/ar/listing/(\d+)[^"]*)"', html)
            for path, num_str in links:
                uid = int("91" + num_str)
                if uid in seen_ids or uid in extra_checked or uid in banned_ids:
                    continue
                aq_candidates.append({
                    "ad_id": uid,
                    "source": "عقارماب",
                    "url": "https://aqarmap.com.eg" + path,
                    "cat": src["cat"],
                    "deal": src["deal"]
                })
                seen_ids.add(uid)

    os_candidates = []
    for src in OPENSOOQ_SOURCES:
        for page in range(1, 3):
            page_url = src["url"] if page == 1 else f"{src['url']}?page={page}"
            html, status_info = fetcher.get_html(page_url)
            print(f"[OpenSooq] {src['cat']} ({src['deal']}) p.{page} -> {status_info}")
            time.sleep(random.uniform(1.0, 1.8))
            if not html:
                continue
            links = re.findall(r'href="(/ar/search/(\d+)[^"]*)"', html)
            for path, num_str in links:
                uid = int("92" + num_str)
                if uid in seen_ids or uid in extra_checked or uid in banned_ids:
                    continue
                os_candidates.append({
                    "ad_id": uid,
                    "source": "السوق المفتوح",
                    "url": "https://eg.opensooq.com" + path,
                    "cat": src["cat"],
                    "deal": src["deal"]
                })
                seen_ids.add(uid)

    all_candidates = aq_candidates[:30] + os_candidates[:30]
    print(f"[Extra Radar] Candidates -> Aqarmap: {len(aq_candidates)} | OpenSooq: {len(os_candidates)}")

    aq_added = 0
    os_added = 0

    for item in all_candidates:
        uid = item["ad_id"]
        extra_checked.add(uid)
        try:
            html, _ = fetcher.get_html(item["url"])
            if not html:
                continue
            t_m = re.search(r'<title>([^<]+)</title>', html)
            title = t_m.group(1).split("|")[0].split("-")[0].strip() if t_m else ""
            if not title or len(title) < 5:
                continue
            visible_text = extract_visible_text(html)
            zone = detect_zone(title + " " + visible_text[:4500])
            if not zone:
                continue
            age_label, fresh_tier, is_recent = parse_age_and_tier(visible_text)
            if not is_recent:
                continue

            p_m = re.search(r'([\d,]{4,15})\s*(?:جنيه|ج\.م|EGP)', html, re.I)
            if p_m:
                price_num = int(p_m.group(1).replace(",", ""))
                price_str = f"{p_m.group(1)} ج.م"
            else:
                price_num = 0
                price_str = "السعر بالتفاصيل"

            pub_name = f"مالك ({item['source']})"
            is_owner = analyze_with_ai(title, visible_text, pub_name, item["deal"], item["cat"], price_num, item["source"])
            if not is_owner:
                print(f"[Rejected by AI Extra] {item['source']} | {title[:30]}")
                continue

            area_m = re.search(r'(\d{2,4})\s*(?:متر|م²|sqm|m²)', visible_text, re.I)
            area_val = int(area_m.group(1)) if area_m else None
            rooms_m = re.search(r'(\d)\s*(?:غرف|غرفة|نوم)', visible_text)
            rooms_val = int(rooms_m.group(1)) if rooms_m else None

            now_ts = int(time.time())
            now_cairo = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
            new_extra_ads.append({
                "ad_id": uid,
                "source": item["source"],
                "title": title,
                "price": price_str,
                "price_num": price_num,
                "zone": zone,
                "cat": item["cat"],
                "deal": item["deal"],
                "area": area_val,
                "rooms": rooms_val,
                "publisher": pub_name,
                "pub_ads": 1,
                "age": age_label,
                "fresh_tier": fresh_tier,
                "first_seen_ts": now_ts,
                "desc_verified_v2": True,
                "url": item["url"],
                "verified_v12": True,
                "scraped_at": now_cairo
            })
            if item["source"] == "عقارماب":
                aq_added += 1
            else:
                os_added += 1
            print(f"[+ Extra Approved by AI] {item['source']} | {item['deal']} | {zone} | {title[:35]}")
            time.sleep(random.uniform(0.9, 1.5))
        except Exception:
            continue

    fetcher.close()
    merged_ads = new_extra_ads + existing_ads
    merged_ads.sort(key=lambda x: (x.get("first_seen_ts", 0), x.get("ad_id", 0)), reverse=True)

    dub_total = sum(1 for a in merged_ads if (a.get("source") or "دوبيزل") == "دوبيزل")
    aq_total = sum(1 for a in merged_ads if a.get("source") == "عقارماب")
    os_total = sum(1 for a in merged_ads if a.get("source") == "السوق المفتوح")
    rent_total = sum(1 for a in merged_ads if a.get("deal") == "إيجار")
    sale_total = sum(1 for a in merged_ads if a.get("deal") != "إيجار")

    dub_added = run_report.get("dub_added", 0)
    dub_insp = run_report.get("dub_inspected", 0)
    ai_stats_payload = {
        "total_ads": len(merged_ads),
        "rent_total": rent_total,
        "sale_total": sale_total,
        "dub_inspected": dub_insp,
        "dub_added": dub_added,
        "aq_checked": len(aq_candidates),
        "aq_added": aq_added,
        "os_checked": len(os_candidates),
        "os_added": os_added
    }
    ai_advice, sys_health = monitor_system_with_ai(ai_stats_payload)
    print(f"[AI Monitor] Health: {sys_health} | Advice: {ai_advice}")

    now_str = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
    run_report.update({
        "last_run_at": now_str,
        "aq_candidates": len(aq_candidates),
        "aq_added": aq_added,
        "os_candidates": len(os_candidates),
        "os_added": os_added,
        "total_live": len(merged_ads),
        "dub_total": dub_total,
        "aq_total": aq_total,
        "os_total": os_total,
        "rent_total": rent_total,
        "sale_total": sale_total,
        "ai_health": sys_health,
        "ai_advice": ai_advice
    })

    tok = os.environ.get("TELEGRAM_BOT_TOKEN") or tg_cfg.get("tok", "")
    cid = os.environ.get("TELEGRAM_CHAT_ID") or tg_cfg.get("cid", "")

    if tok and cid:
        new_Alert_ads = [a for a in merged_ads if a.get("fresh_tier") == 3 and a.get("ad_id") not in notified_ids]
        for ad in new_Alert_ads[:10]:
            msg = (
                f"<b>صيد جديد مفحوص بالذكاء الاصطناعي ({ad.get('deal')}) من {ad.get('source', 'دوبيزل')}</b>\n"
                f"المنطقة: <b>{ad.get('zone')}</b> ({ad.get('cat')})\n"
                f"السعر: <b>{ad.get('price')}</b>\n"
                f"المساحة: {ad.get('area') or 'غير محدد'} م2 | الغرف: {ad.get('rooms') or 'غير محدد'}\n"
                f"العنوان: {ad.get('title')}\n"
                f"الناشر: {ad.get('publisher')}\n"
                f"<a href=\"{ad.get('url')}\">اضغط هنا لفتح الإعلان الأصلي</a>"
            )
            if send_telegram_msg(tok, cid, msg):
                notified_ids.add(ad.get("ad_id"))
            time.sleep(0.5)

        summary_msg = (
            f"<b>التقرير الشامل وعقل المراقبة الذكي ({now_str})</b>\n"
            f"حالة النظام: <b>{sys_health}</b>\n"
            f"تشخيص الذكاء الاصطناعي:\n"
            f"<i>{ai_advice}</i>\n"
            f"إجمالي الإعلانات الحية بالموقع: <b>{len(merged_ads)} إعلان</b>\n"
            f"إيجار: <b>{rent_total}</b> | تمليك كاش: <b>{sale_total}</b>\n"
            f"دوبيزل: <b>{dub_total}</b> (جديد بالرن: +{dub_added} من {dub_insp} مفحوص)\n"
            f"عقارماب: <b>{aq_total}</b> (جديد بالرن: +{aq_added} من {len(aq_candidates)} مرشح)\n"
            f"السوق المفتوح: <b>{os_total}</b> (جديد بالرن: +{os_added} من {len(os_candidates)} مرشح)"
        )
        send_telegram_msg(tok, cid, summary_msg)
    else:
        for a in merged_ads[:30]:
            if a.get("ad_id"):
                notified_ids.add(a.get("ad_id"))

    data["updated_at"] = now_str
    data["total"] = len(merged_ads)
    data["last_run_report"] = run_report
    data["ads"] = merged_ads
    data["extra_checked_ids"] = list(extra_checked)[-10000:]
    data["telegram_config"] = tg_cfg
    data["telegram_notified_ids"] = list(notified_ids)[-5000:]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_extra_radar()
