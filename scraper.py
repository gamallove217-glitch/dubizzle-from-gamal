import json, re, time, random, os, socket, urllib.parse
from datetime import datetime, timezone, timedelta
import requests as std_requests
from curl_cffi import requests

CAIRO_TZ = timezone(timedelta(hours=2))
DATA_FILE = "ads.json"
NTFY_BAN_TOPIC = "gamal_vip_ban_9941_sec"
WARP_PROXY = "socks5h://127.0.0.1:40000"
HINDI_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

PAGES_PER_CATEGORY = int(os.environ.get("PAGES_PER_CATEGORY", "2"))
MAX_RUNTIME_SECONDS = int(os.environ.get("MAX_RUNTIME_SECONDS", "600"))
MAX_AD_AGE_SECONDS = 7 * 86400
MIN_CASH_SALE_PRICE = 1500000

CATEGORIES = [
    {"name": "شقق", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo-fifth-settlement/"},
    {"name": "شقق", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/"},
    {"name": "فلل", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo-fifth-settlement/"},
    {"name": "فلل", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/"},
    {"name": "تجاري", "deal": "إيجار", "url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo-fifth-settlement/"},
    {"name": "شقق", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo-fifth-settlement/"},
    {"name": "شقق", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/"},
    {"name": "فلل", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo-fifth-settlement/"},
    {"name": "تجاري", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo-fifth-settlement/"},
    {"name": "أراضي", "deal": "تمليك", "url": "https://www.dubizzle.com.eg/properties/vacation-homes-and-land-for-sale/new-cairo-fifth-settlement/"},
]

ZONES = [
    ("التجمع الخامس", ["التجمع الخامس", "fifth settlement", "5th settlement", "ميفيدا", "mivida", "هايد بارك", "ماونتن فيو", "كايرو فيستفال", "الباتيو", "فيلت", "سوديك"]),
    ("التجمع الأول", ["التجمع الأول", "التجمع الاول", "first settlement", "1st settlement"]),
    ("التجمع الثالث", ["التجمع الثالث", "third settlement", "3rd settlement", "أربيلا", "اربيلا"]),
    ("التجمع السادس", ["التجمع السادس", "sixth settlement"]),
    ("اللوتس", ["اللوتس", "lotus"]),
    ("النرجس", ["النرجس", "narges", "narjis"]),
    ("الياسمين", ["الياسمين", "yasmeen", "jasmine"]),
    ("البنفسج", ["البنفسج", "banafseg"]),
    ("الأندلس", ["الأندلس", "الاندلس", "andalus"]),
    ("جنوب الأكاديمية", ["جنوب الأكاديمية", "جنوب الاكاديمية", "south academy"]),
    ("شرق الأكاديمية", ["شرق الأكاديمية", "شرق الاكاديمية"]),
    ("المستثمرين", ["المستثمرين", "investors"]),
    ("الشويفات", ["الشويفات", "choueifat", "shouyfat"]),
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
    "العاشر من رمضان", "6 أكتوبر", "أكتوبر", "الشيخ زايد", "زايد", "المعادي", "زهراء المعادي",
    "المقطم", "الهضبة الوسطى", "مدينة نصر", "مصر الجديدة", "شيراتون", "النزهة", "عين شمس",
    "السلام", "جسر السويس", "قباء", "حدائق القبة", "المرج", "شبرا", "حلوان", "15 مايو",
    "حدائق حلوان", "دار السلام", "الزمالك", "المهندسين", "الدقي", "العجوزة", "الهرم", "فيصل",
    "حدائق الأهرام", "حدائق الاهرام", "حدائق أكتوبر", "الساحل الشمالي", "العين السخنة", "الجونة",
    "الغردقة", "شرم الشيخ", "الإسكندرية", "الاسكندرية", "المنصورة", "طنطا", "دمياط", "بورسعيد",
    "المستقبل", "mostakbal", "سمات"
]

INSTALLMENT_SUBSTRINGS = [
    "قسط", "تقسيط", "بالتقسيط", "لتقسيط", "اقساط", "أقساط", "باقساط", "بأقساط",
    "مقدم", "بمقدم", "دفعة", "دفعه", "دفعات", "تسهيلات", "سداد", "فترة سداد", "سنوات سداد",
    "بدون فوائد", "متبقي", "المتبقي", "أوفر", "اوفر", "امكانية التقسيط", "متاح تقسيط", "ويوجد تقسيط",
    "down payment", "downpayment", "installment", "installments", "payment plan"
]

SAFE_CASH_NEGATIONS = [
    "بدون تقسيط", "لا يوجد تقسيط", "ممنوع التقسيط", "وليس تقسيط", "مش تقسيط",
    "بدون أقساط", "بدون اقساط", "خالص الثمن", "خالصة الثمن", "خالصه الثمن",
    "ليس عليها أقساط", "ليس عليها اقساط", "لا يوجد أقساط", "لا يوجد اقساط",
    "مسدد بالكامل", "مسددة بالكامل", "غير متاح تقسيط", "كاش فقط"
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
        base_headers = {
            "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site"
        }
        self.warp_sess = requests.Session(impersonate="chrome120", proxies={"http": WARP_PROXY, "https": WARP_PROXY})
        self.warp_sess.headers.update(base_headers)
        self.direct_sess = requests.Session(impersonate="chrome120")
        self.direct_sess.headers.update(base_headers)
        self.pw = None
        self.browser = None
        self.context = None
        self.pw_warmed = False

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
                viewport={"width": 1366, "height": 768},
                extra_http_headers={"Referer": "https://www.google.com/"}
            )
            self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            return True
        except Exception as e:
            print(f"[PW Init] {e}")
            return False

    def _sync_cookies_from_pw(self):
        try:
            for c in self.context.cookies():
                name, val, dom = c.get("name"), c.get("value"), c.get("domain", "")
                if name and val and "dubizzle" in dom:
                    self.warp_sess.cookies.set(name, val, domain=dom)
                    self.direct_sess.cookies.set(name, val, domain=dom)
        except Exception:
            pass

    def _is_valid_html(self, html, req_regex=None):
        if not html or len(html) < 1500:
            return False
        if "Pardon Our Interruption" in html or "Just a moment..." in html or "<title>Attention Required!" in html:
            return False
        if req_regex and not re.search(req_regex, html):
            return False
        return True

    def get_html(self, url, req_regex=None):
        statuses = []
        if self.warp_active:
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
        except Exception:
            statuses.append("Direct:ERR")

        if self._ensure_pw():
            page = None
            try:
                page = self.context.new_page()
                if not self.pw_warmed:
                    try:
                        page.goto("https://www.dubizzle.com.eg/", wait_until="domcontentloaded", timeout=20000)
                        page.wait_for_timeout(4000)
                        self.pw_warmed = True
                    except Exception:
                        pass
                resp = page.goto(url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(4500)
                html = page.content()
                if not self._is_valid_html(html, req_regex):
                    page.reload(wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(3500)
                    html = page.content()
                code = resp.status if resp else 0
                page.close()
                if self._is_valid_html(html, req_regex):
                    self._sync_cookies_from_pw()
                    return html, "200 (Playwright)"
                statuses.append(f"PW:{code}")
            except Exception:
                if page:
                    try: page.close()
                    except Exception: pass
                statuses.append("PW:ERR")

        try:
            r = std_requests.get(f"https://r.jina.ai/{url}", headers={"X-Return-Format": "html", "User-Agent": "Mozilla/5.0"}, timeout=22)
            if r.status_code == 200 and self._is_valid_html(r.text, req_regex):
                return r.text, "200 (Jina)"
            statuses.append(f"Jina:{r.status_code}")
        except Exception:
            statuses.append("Jina:ERR")

        return "", " | ".join(statuses)

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

def extract_ad_body(html):
    meta_desc = " ".join(re.findall(r'<meta[^>]+(?:name="description"|property="og:description")[^>]+content="([^"]+)"', html, flags=re.I))
    json_desc = " ".join(re.findall(r'"description"\s*:\s*"([^"]+)"', html))
    pure_desc = f"{meta_desc} {json_desc}".strip()
    if len(pure_desc) < 40:
        body_cleaned = re.sub(r'<(script|style|svg|noscript|header|nav|footer|aside|ul|ol)[^>]*>.*?</\1>', ' ', html, flags=re.S | re.I)
        tags_stripped = re.sub(r'<[^>]+>', ' ', body_cleaned)
        pure_desc = re.sub(r'\s+', ' ', tags_stripped).strip()[:1200]
    pure_desc = re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', pure_desc)
    return pure_desc[:2500]

def detect_zone(title, body_text):
    core = normalize_ar(f"{title} {body_text[:1000]}")
    for city in EXCLUDED_CITIES:
        if normalize_ar(city) in core:
            return None
    for z_name, keywords in ZONES:
        for kw in keywords:
            if normalize_ar(kw) in core:
                return z_name
    return "القاهرة الجديدة"

def is_strict_cash_sale(title, body_text, price_num, raw_html=""):
    if int(price_num or 0) < MIN_CASH_SALE_PRICE:
        return False
    norm_html_check = normalize_ar(raw_html[:15000])
    if "طريقه الدفع تقسيط" in norm_html_check or "طريقه الدفعتقسيط" in norm_html_check:
        return False
    full_text = normalize_ar(f"{title} {body_text[:2000]}")
    for neg in SAFE_CASH_NEGATIONS:
        full_text = full_text.replace(normalize_ar(neg), " ")
    for kw in INSTALLMENT_SUBSTRINGS:
        if normalize_ar(kw) in full_text:
            return False
    return True

def is_valid_existing_ad(ad, banned_pubs, banned_ids):
    aid = ad.get("ad_id")
    pub = ad.get("publisher", "")
    if not aid or aid in banned_ids or pub in banned_pubs:
        return False
    source = ad.get("source", "دوبيزل")
    pub_ads = int(ad.get("pub_ads", 1) or 1)
    if source == "دوبيزل":
        if not (1 <= pub_ads <= 4):
            return False
    else:
        if pub in ("مالك (عقارماب)", "مالك (السوق المفتوح)", "مالك") or pub_ads > 2:
            return False
    title = ad.get("title", "")
    zone = ad.get("zone", "")
    deal = ad.get("deal", "تمليك")
    price_num = int(ad.get("price_num", 0) or 0)
    norm_all = normalize_ar(f"{title} {zone}")
    for city in EXCLUDED_CITIES:
        if normalize_ar(city) in norm_all:
            return False
    if deal != "إيجار":
        if not is_strict_cash_sale(title, "", price_num):
            return False
    return True

def parse_age_and_tier(page_text):
    norm_text = normalize_ar(page_text)
    if re.search(r'منذ\s+(\d+\s*)?(اسبوع|اسابيع|شهر|اشهر|سنه|سنوات)', norm_text):
        return ("قديم", 0, False)
    m = re.search(r'منذ\s+(\d+)\s*(يوم|ايام)', norm_text)
    if m:
        num = int(m.group(1))
        if num <= 1: return ("منذ يوم", 2, True)
        if num <= 5: return (f"منذ {num} أيام", 1, True)
        return (f"منذ {num} أيام", 0, False)
    return ("حديث", 3, True)

def compute_tier_from_ts(ts):
    age_sec = int(time.time()) - int(ts)
    if age_sec <= 12 * 3600:
        return 3
    if age_sec <= 36 * 3600:
        return 2
    return 1

def sync_ntfy_bans(banned_pubs, banned_ids):
    try:
        r = std_requests.get(f"https://ntfy.sh/{NTFY_BAN_TOPIC}/json?poll=1&since=48h", timeout=10)
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

def get_real_dubizzle_active_ads(fetcher, ad_html, pub_id):
    h_ad = ad_html.translate(HINDI_MAP)
    json_counts = [int(x) for x in re.findall(r'"(?:activeAdsCount|publishedAdsCount|totalAds|adsCount)"\s*:\s*(\d+)', h_ad) if int(x) > 0]
    clean_prof = re.sub(r'^https?://www\.dubizzle\.com\.eg', '', pub_id)
    if not clean_prof.startswith("/"):
        clean_prof = "/" + clean_prof
    pr_html, _ = fetcher.get_html("https://www.dubizzle.com.eg" + clean_prof)
    if not pr_html and not json_counts:
        return 0
    pr_clean = (pr_html or "").translate(HINDI_MAP)
    profile_cards = len(set(re.findall(r'-ID(\d+)\.html', pr_clean)))
    text_counts = [
        int(x) for x in re.findall(r'(\d+)\s+(?:إعلان\b|اعلان\b|إعلانات\b|اعلانات\b|published ads\b|active ads\b)', pr_clean, re.I)
        if 0 < int(x) < 500
    ]
    all_found = json_counts + text_counts + ([profile_cards] if profile_cards > 0 else [])
    return max(all_found) if all_found else 0

def notify_ai_server_dubizzle(title, body_text, pub_name, deal, cat, price_num, pub_ads_count):
    if not (1 <= pub_ads_count <= 4):
        return False
    url = "https://gamal216.pythonanywhere.com/analyze"
    payload = {
        "text": f"{title} {body_text[:2000]}",
        "title": title,
        "description": body_text[:2000],
        "publisher": "مالك مباشر",
        "deal": deal,
        "cat": cat,
        "price_num": price_num,
        "source": "دوبيزل",
        "active_ads_count": pub_ads_count,
        "dubizzle_strict_count_only": True
    }
    try:
        std_requests.post(url, json=payload, timeout=10)
    except Exception:
        pass
    return True

def run_scraper():
    start_ts = time.time()
    now_ts = int(start_ts)
    raw_data, existing_ads, checked_ids, banned_pubs, banned_ids = load_existing()
    sync_ntfy_bans(banned_pubs, banned_ids)

    fetcher = SmartFetcher()
    kept = []
    seen_ids = set()

    for a in existing_ads:
        aid = a.get("ad_id")
        if not aid or aid in seen_ids:
            continue
        checked_ids.add(aid)
        if not is_valid_existing_ad(a, banned_pubs, banned_ids):
            print(f"[Purged Old Invalid Ad] {a.get('zone')} | {a.get('publisher')} | {a.get('title', '')[:35]}")
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

    for page in range(1, PAGES_PER_CATEGORY + 1):
        if time.time() - start_ts > MAX_RUNTIME_SECONDS * 0.45:
            break
        for cat in CATEGORIES:
            url = cat["url"] if page == 1 else f"{cat['url']}?page={page}"
            html, status_info = fetcher.get_html(url, req_regex=r'-ID\d+\.html')
            pages_fetched += 1
            print(f"[Dubizzle] {cat['name']} ({cat['deal']}) p.{page} -> {status_info}")
            time.sleep(random.uniform(1.0, 1.8))
            if not html:
                continue
            matches = re.findall(r'((?:https?://www\.dubizzle\.com\.eg)?(?:/ar|/en)?/ad/[^"\'\s<>\\]+-ID(\d+)\.html)', html)
            for raw_path, id_str in matches:
                ad_id = int(id_str)
                if ad_id in seen_ids or ad_id in checked_ids or ad_id in banned_ids:
                    continue
                clean_path = re.sub(r'^https?://www\.dubizzle\.com\.eg', '', raw_path)
                clean_path = re.sub(r'^/(?:ar|en)/', '/', clean_path)
                if not clean_path.startswith("/"):
                    clean_path = "/" + clean_path
                candidates.append({
                    "ad_id": ad_id,
                    "url": "https://www.dubizzle.com.eg" + clean_path,
                    "cat": cat["name"],
                    "deal": cat["deal"]
                })
                seen_ids.add(ad_id)

    print(f"[Dubizzle] Total new candidates to inspect: {len(candidates)}")
    new_verified = []
    inspected_cnt = 0

    for item in candidates:
        if time.time() - start_ts > MAX_RUNTIME_SECONDS:
            break
        ad_id = item["ad_id"]
        checked_ids.add(ad_id)
        inspected_cnt += 1
        try:
            html, _ = fetcher.get_html(item["url"])
            if not html:
                continue
            if "/companies/" in html or "featured_agency" in html:
                print(f"[Rejected Dubizzle Agency] ID:{ad_id} (Corporate Account)")
                continue
            t_m = re.search(r'<title>([^<]+)</title>', html)
            title = t_m.group(1).split("|")[0].split("-")[0].strip() if t_m else ""
            if not title:
                continue
            body_text = extract_ad_body(html)
            zone = detect_zone(title, body_text)
            if not zone:
                print(f"[Rejected Dubizzle Forbidden Zone] {title[:35]}")
                continue
            age_label, _, is_recent = parse_age_and_tier(body_text)
            if not is_recent:
                continue

            p_m = re.search(r'([\d,]{4,15})\s*ج\.م', html) or re.search(r'EGP\s*([\d,]{4,15})', html)
            if p_m:
                price_num = int(p_m.group(1).replace(",", ""))
                price_str = f"{p_m.group(1)} ج.م"
            else:
                price_num = 0
                price_str = "السعر بالتفاصيل"

            if item["deal"] != "إيجار" and not is_strict_cash_sale(title, body_text, price_num, html):
                print(f"[Rejected Dubizzle Installment/Price] {price_str} | {title[:35]}")
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

            if pub_name in banned_pubs:
                continue

            pub_ads_count = get_real_dubizzle_active_ads(fetcher, html, pub_id)
            if not (1 <= pub_ads_count <= 4):
                if pub_ads_count > 4:
                    banned_pubs.add(pub_name)
                print(f"[Rejected Dubizzle Active Ads Count] {pub_name} | Active Ads: {pub_ads_count}")
                continue

            notify_ai_server_dubizzle(title, body_text, pub_name, item["deal"], item["cat"], price_num, pub_ads_count)

            area_m = re.search(r'(\d{2,4})\s*(?:متر|م²|sqm|m²)', body_text, re.I)
            area_val = int(area_m.group(1)) if area_m else None
            rooms_m = re.search(r'(\d)\s*(?:غرف|غرفة|نوم|beds|bed|bedrooms)', body_text, re.I)
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
            print(f"[+ Dubizzle Owner 1-4 Ads Approved] {item['deal']} | {zone} | {pub_name} ({pub_ads_count} إعلان) | {title[:35]}")
            time.sleep(random.uniform(1.0, 1.6))
        except Exception:
            continue

    fetcher.close()
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
