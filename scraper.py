import os, sys, re, json, time, random, stat, subprocess
from datetime import datetime
import requests

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from DrissionPage import ChromiumPage, ChromiumOptions

AI_SERVER_URL = "https://gamal216.pythonanywhere.com"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ads.json")
SEEN_FILE = os.path.join(BASE_DIR, "seen_links_local.json")
PROFILE_DIR = os.path.join(BASE_DIR, "chrome_clean_profile")
MAX_ADS_STORED = 450
MAX_ADS_PER_PAGE = 25

DUBIZZLE_SOURCES = [
    {"cat": "شقق", "deal": "إيجار", "en": "Apartments (Rent)", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/"},
    {"cat": "شقق", "deal": "تمليك", "en": "Apartments (Sale)", "url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/"},
    {"cat": "فلل", "deal": "إيجار", "en": "Villas (Rent)", "url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/"},
    {"cat": "فلل", "deal": "تمليك", "en": "Villas (Sale)", "url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/"},
    {"cat": "تجاري", "deal": "إيجار", "en": "Commercial (Rent)", "url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/"},
    {"cat": "تجاري", "deal": "تمليك", "en": "Commercial (Sale)", "url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/"}
]

ZONE_MAPPING = {
    "النرجس": "النرجس", "نرجس": "النرجس", "الياسمين": "الياسمين", "ياسمين": "الياسمين",
    "البنفسج": "البنفسج", "بنفسج": "البنفسج", "اللوتس": "اللوتس", "لوتس": "اللوتس",
    "الأندلس": "الأندلس", "الاندلس": "الأندلس", "اندلس": "الأندلس", "القرنفل": "القرنفل",
    "قرنفل": "القرنفل", "تمر حنة": "التمر حنة", "التمر حنة": "التمر حنة", "جاردينيا": "جاردينيا",
    "جنوب الأكاديمية": "جنوب الأكاديمية", "جنوب الاكاديمية": "جنوب الأكاديمية",
    "شرق الأكاديمية": "شرق الأكاديمية", "شرق الاكاديمية": "شرق الأكاديمية",
    "المستثمرين": "المستثمرين", "الشويفات": "الشويفات", "شويفات": "الشويفات",
    "أبو الهول": "أبو الهول", "ابو الهول": "أبو الهول", "دار مصر": "دار مصر",
    "سكن مصر": "سكن مصر", "جنة": "جنة مصر", "القطامية": "القطامية", "قطامية": "القطامية",
    "التسعين": "شارع التسعين", "شارع التسعين": "شارع التسعين", "ميفيدا": "ميفيدا",
    "هايد بارك": "هايد بارك", "ماونتن فيو": "ماونتن فيو", "التجمع الأول": "التجمع الأول",
    "التجمع الاول": "التجمع الأول", "التجمع الثالث": "التجمع الثالث", "التجمع الخامس": "التجمع الخامس"
}

FORBIDDEN_ZONES = [
    "الرحاب", "رحاب", "rehab", "مدينتي", "مدينتى", "madinaty", "المستقبل", "mostakbal", "سمات",
    "بيت الوطن", "بيت وطن", "beit al watan", "beit el watan", "bayt al watan", "النورث هاوس", "شمال الرحاب",
    "العبور", "الشروق", "مدينة بدر", "مدينه بدر", "هليوبوليس الجديدة", "العاصمة الإدارية", "العاصمه الاداريه",
    "العاشر من رمضان", "6 أكتوبر", "أكتوبر", "الشيخ زايد", "زايد", "المعادي", "زهراء المعادي", "المقطم",
    "الهضبة الوسطى", "مدينة نصر", "مصر الجديدة", "شيراتون", "النزهة", "عين شمس", "السلام", "جسر السويس",
    "حدائق القبة", "المرج", "شبرا", "حلوان", "15 مايو", "الزمالك", "المهندسين", "الدقي", "العجوزة",
    "الهرم", "فيصل", "حدائق الأهرام", "حدائق الاهرام", "حدائق أكتوبر", "الساحل الشمالي", "العين السخنة"
]

INSTALLMENT_KEYWORDS = ["قسط", "تقسيط", "بالتقسيط", "أقساط", "اقساط", "تسهيلات", "فترة سداد", "سنوات سداد", "بمقدم", "مقدم", "دفعة", "دفعات", "متبقي", "المتبقي", "أوفر", "اوفر", "أوفر برايس", "down payment", "downpayment", "installment", "installments", "payment plan"]
CASH_NEGATIONS = ["بدون تقسيط", "لا يوجد تقسيط", "ممنوع التقسيط", "وليس تقسيط", "مش تقسيط", "بدون أقساط", "بدون اقساط", "خالص الثمن", "خالصة الثمن", "خالصه الثمن", "ليس عليها أقساط", "ليس عليها اقساط", "لا يوجد أقساط", "لا يوجد اقساط", "مسدد بالكامل", "مسددة بالكامل", "مسدده بالكامل", "غير متاح تقسيط", "البيع كاش فقط", "كاش فقط", "كاش ولا تقبل التمويل", "كاش نهائي"]
HINDI_MAP = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def normalize_ar(text):
    if not text: return ""
    t = str(text).translate(HINDI_MAP).lower()
    t = re.sub(r'[\u0640\u064B-\u065F]', '', t)
    t = re.sub(r'[إأآا]', 'ا', t)
    t = re.sub(r'ة', 'ه', t)
    t = re.sub(r'ى', 'ي', t)
    return re.sub(r'\s+', ' ', t).strip()

def clean_publisher_name(name):
    if not name: return "مالك مباشر (دوبيزل)"
    s = re.sub(r'<[^>]+>', ' ', str(name))
    s = re.sub(r'(?:path\s+d=|M\d+\.\d+|viewBox|xmlns|svg|fill=)', ' ', s, flags=re.I)
    s = re.sub(r'[\r\n\t]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip(" -_|:,.")
    if not s or len(s) < 2 or len(s) > 55 or re.search(r'[<>{}\[\]=/\\]', s):
        return "مالك مباشر (دوبيزل)"
    return s

def detect_sub_zone(full_text):
    for key, official in ZONE_MAPPING.items():
        if normalize_ar(key) in normalize_ar(full_text):
            return official
    return "القاهرة الجديدة"

def is_forbidden_or_installment(title, desc, deal, price_num):
    raw_combined = re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', f"{title} {desc}")
    norm_text = normalize_ar(raw_combined)
    for idx, bad in enumerate(FORBIDDEN_ZONES):
        if normalize_ar(bad) in norm_text:
            return True, f"Forbidden Zone (#{idx+1})"
    if deal == "تمليك":
        if int(price_num or 0) < 1500000:
            return True, f"Invalid/Downpayment Price ({price_num})"
        temp = norm_text
        for neg in CASH_NEGATIONS:
            temp = temp.replace(normalize_ar(neg), " ")
        for inst in INSTALLMENT_KEYWORDS:
            if normalize_ar(inst) in temp:
                return True, "Installment Ad"
        if re.search(r'\b\d+\s*%\s*(مقدم|تعاقد|دفعه|down)', temp):
            return True, "Installment % Downpayment"
    return False, "OK"

def parse_price_strict(raw_val, deal="تمليك"):
    if not raw_val: return 0
    s = str(raw_val).translate(HINDI_MAP)
    for m in re.findall(r'\d[\d,]*', s):
        val = int(m.replace(',', ''))
        if deal == "إيجار" and 3000 <= val <= 1500000: return val
        if deal == "تمليك" and 1500000 <= val <= 600000000: return val
    return 0

class HybridTurboEngine:
    def __init__(self):
        self.page = None

    def find_clean_browser(self):
        for c in [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]:
            if os.path.exists(c): return c
        return None

    def start_browser(self):
        if self.page is not None: return True
        try:
            os.makedirs(PROFILE_DIR, exist_ok=True)
            co = ChromiumOptions()
            b_path = self.find_clean_browser()
            if b_path:
                co.set_browser_path(b_path)
                print(f"[Browser] Using Clean Profile: {b_path}")
            co.set_paths(local_port=9555, user_data_path=PROFILE_DIR)
            co.set_load_mode("none")
            co.no_imgs(True)
            co.mute(True)
            co.set_argument("--disable-blink-features=AutomationControlled")
            co.set_argument("--disable-extensions")
            co.set_argument("--disable-popup-blocking")
            self.page = ChromiumPage(addr_or_opts=co)
            return True
        except Exception as e:
            print(f"[Browser Start Error] {e}")
            return False

    def kill_vpn_tabs(self):
        if not self.page: return
        try:
            for tid in self.page.tab_ids:
                t = self.page.get_tab(tid)
                u = (t.url or "").lower()
                if "setupvpn" in u or "extension://" in u:
                    if len(self.page.tab_ids) > 1: t.close()
        except Exception:
            pass

    def get_category_links(self, url, label=""):
        if not self.start_browser(): return []
        try:
            self.kill_vpn_tabs()
            self.page.get(url, timeout=8)
            js_links = """
            window.scrollTo(0, 500);
            return Array.from(new Set(
                Array.from(document.querySelectorAll('a[href*="/ad/"]'))
                     .map(a => a.href.split('?')[0].split('#')[0])
                     .filter(h => h.length > 25)
            ));
            """
            for _ in range(12):
                time.sleep(0.9)
                try:
                    res = self.page.run_js(js_links)
                    if isinstance(res, list) and len(res) >= 5:
                        print(f"[Dubizzle Browser] {label} -> JS 200 OK (Extracted {len(res)} ads)")
                        return res
                except Exception:
                    pass
        except Exception:
            pass
        print(f"[Dubizzle Local] {label} -> Extracted 0 ads")
        return []

    def fetch_ad_or_profile_fast(self, url):
        if not self.start_browser(): return None
        try:
            self.kill_vpn_tabs()
            self.page.get(url, timeout=8)
            js_extract = """
            window.scrollTo(0, 650);
            const h1 = document.querySelector('h1');
            const bodyText = document.body ? document.body.innerText : '';
            if ((!h1 || !h1.innerText) && bodyText.length < 300) return null;
            const title = h1 ? h1.innerText.trim() : (document.title || '');
            const ogTitle = document.querySelector('meta[property="og:title"]')?.content || '';
            const ogDesc = document.querySelector('meta[property="og:description"]')?.content || '';
            const metaPrice = document.querySelector('meta[property="product:price:amount"], meta[property="og:price:amount"]')?.content || '';
            const priceEl = document.querySelector('[aria-label="Price"]');
            const priceText = priceEl ? priceEl.innerText.trim() : '';
            const descEl = document.querySelector('[aria-label="Description"], [data-testid="description"]');
            const desc = descEl ? descEl.innerText.trim() : ogDesc;
            const scriptsText = Array.from(document.querySelectorAll('script')).map(s => s.textContent || '').filter(t => t.includes('profile') || t.includes('activeAds') || t.includes('seller') || t.includes('price')).join(' ');
            let mainText = bodyText;
            for (const marker of ['إعلانات مشابهة', 'إعلانات ذات صلة', 'Related ads', 'Similar ads']) {
                const idx = mainText.indexOf(marker);
                if (idx > 250) mainText = mainText.slice(0, idx);
            }
            let cutoffY = 999999;
            for (const el of Array.from(document.querySelectorAll('h2, h3, div, span'))) {
                const tx = (el.innerText || '').trim();
                if (tx === 'إعلانات مشابهة' || tx === 'إعلانات ذات صلة' || tx === 'Related ads') {
                    const r = el.getBoundingClientRect();
                    if (r.top + window.scrollY > 300) { cutoffY = r.top + window.scrollY; break; }
                }
            }
            const mainHrefs = [];
            for (const a of Array.from(document.querySelectorAll('a[href]'))) {
                const r = a.getBoundingClientRect();
                const absY = r.top + window.scrollY;
                if (absY > 110 && absY < cutoffY) mainHrefs.push(a.href);
            }
            const adLinks = Array.from(new Set(
                Array.from(document.querySelectorAll('a[href*="/ad/"]'))
                     .map(a => a.href.split('?')[0])
                     .filter(h => h.length > 25)
            ));
            return {
                title: title, ogTitle: ogTitle, desc: desc, metaPrice: metaPrice, priceText: priceText,
                scriptsText: scriptsText.slice(0, 150000), mainText: mainText.slice(0, 12000),
                allHrefs: mainHrefs, adCount: adLinks.length
            };
            """
            for step in range(10):
                time.sleep(0.9)
                try:
                    res = self.page.run_js(js_extract)
                    if isinstance(res, dict) and (res.get("title") or res.get("adCount", 0) > 0):
                        if step < 3 and not any("/profile/" in h or "/companies/" in h for h in res.get("allHrefs", [])):
                            continue
                        return res
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def close(self):
        try:
            if self.page: self.page.quit()
        except Exception:
            pass

def find_seller_profile_url(hrefs_list, text_blob):
    for h in hrefs_list:
        h_clean = str(h).split("?")[0].strip()
        if re.search(r'/(?:ar/|en/)?profile/[a-zA-Z0-9_-]{5,}', h_clean):
            return (h_clean if h_clean.startswith("http") else f"https://www.dubizzle.com.eg{h_clean}"), False
    m_prof = re.search(r'(https?://(?:www\.)?dubizzle\.com\.eg/(?:ar/|en/)?profile/[a-zA-Z0-9_-]{5,})', text_blob)
    if m_prof: return m_prof.group(1), False
    m_prof2 = re.search(r'"(\/(?:ar\/|en\/)?profile\/[a-zA-Z0-9_-]{5,})"', text_blob)
    if m_prof2: return f"https://www.dubizzle.com.eg{m_prof2.group(1)}", False
    for h in hrefs_list:
        h_clean = str(h).split("?")[0].rstrip("/").strip()
        if re.search(r'/(?:ar/|en/)?companies/[a-zA-Z0-9_-]{3,}', h_clean) and not h_clean.endswith("/companies"):
            return h_clean.split("/")[-1][:25], True
    return "", False

def count_seller_active_ads(payload, engine):
    raw_text = str(payload.get("mainText", "")).translate(HINDI_MAP)
    raw_blob = f"{payload.get('scriptsText', '')} {raw_text}".translate(HINDI_MAP)
    prof_url, is_company = find_seller_profile_url(payload.get("allHrefs", []), raw_blob)
    if is_company: return 99, f"Agency ({prof_url})"
    for pat in [r'"activeAdsCount"\s*:\s*(\d+)', r'"totalAds"\s*:\s*(\d+)', r'"adsCount"\s*:\s*(\d+)', r'"listedAdsCount"\s*:\s*(\d+)']:
        m = re.search(pat, raw_blob)
        if m and int(m.group(1)) >= 1:
            return int(m.group(1)), f"Ad JSON ({m.group(1)} active ads)"
    m_txt = re.search(r'(?:Active\s*Ads\s*:?\s*(\d+)|(\d+)\s*(?:إعلانات\s*نشطة|إعلان\s*نشط|اعلانات\s*نشطه|اعلان\s*نشط|active\s*ads|published\s*ads|ads\s*posted))', raw_text, re.I)
    if m_txt:
        c = int(m_txt.group(1) or m_txt.group(2))
        if c >= 1: return c, f"Seller Badge ({c} active ads)"
    if not prof_url:
        if re.search(r'(?:company\s*profile|verified\s*business|share\s*agency\s*profile|شركة\s*موثقة|مكتب\s*عقاري)', raw_text, re.I):
            return 99, "Agency Account"
        return 0, "No seller profile link"
    prof_payload = engine.fetch_ad_or_profile_fast(prof_url)
    if not prof_payload: return 0, "Could not load seller profile"
    p_blob = f"{prof_payload.get('scriptsText', '')} {prof_payload.get('mainText', '')}".translate(HINDI_MAP)
    for pat in [r'"activeAdsCount"\s*:\s*(\d+)', r'"totalAds"\s*:\s*(\d+)', r'"adsCount"\s*:\s*(\d+)', r'"total"\s*:\s*(\d+)']:
        m = re.search(pat, p_blob)
        if m and int(m.group(1)) >= 1:
            return int(m.group(1)), f"Profile JSON ({m.group(1)} active ads)"
    m_p = re.search(r'(?:Showing|عرض)?\s*(?:\d+\s*[-–]\s*\d+\s*(?:of|من)\s*)?(\d+)\s*(?:إعلانات|إعلان|اعلانات|اعلان|Ads|ad|results|نتيجة)', p_blob, re.I)
    if m_p and int(m_p.group(1)) >= 1:
        return int(m_p.group(1)), f"Profile Counter ({m_p.group(1)} active ads)"
    card_c = int(prof_payload.get("adCount", 0))
    if card_c >= 1: return card_c, f"Profile Cards ({card_c} active ads)"
    return 0, "Unverified ad count"

def parse_dubizzle_ad(url, cat, deal, engine):
    payload = engine.fetch_ad_or_profile_fast(url)
    if not payload: return None, "Failed to load ad page"
    title = re.sub(r'\s*\|\s*(?:دوبيزل|dubizzle).*$', '', str(payload.get("title", "")), flags=re.I).strip()
    if not title or len(title) < 4: return None, "Empty title"
    desc = str(payload.get("desc", "")).strip()
    price_num = parse_price_strict(payload.get("metaPrice", ""), deal) or parse_price_strict(payload.get("priceText", ""), deal)
    if price_num == 0:
        blob = f"{payload.get('ogTitle', '')} {payload.get('mainText', '')} {payload.get('scriptsText', '')}".translate(HINDI_MAP)
        for pat in [r'"price"\s*:\s*"?(\d[\d,]*)"?', r'(?:EGP|ج\.?م|جنيه|LE)\s*(\d[\d,]{3,11})', r'(\d[\d,]{3,11})\s*(?:ج\.?م|جنيه|EGP|LE)']:
            m = re.search(pat, blob, re.I)
            if m:
                price_num = parse_price_strict(m.group(1), deal)
                if price_num > 0: break
    is_bad, bad_reason = is_forbidden_or_installment(title, desc, deal, price_num)
    if is_bad: return None, bad_reason
    active_count, count_info = count_seller_active_ads(payload, engine)
    if not (1 <= active_count <= 4):
        return None, f"Broker/Count Rule (1-4): {count_info}"
    pub_raw = "مالك مباشر (دوبيزل)"
    raw_scripts = str(payload.get("scriptsText", ""))
    m_seller = re.search(r'"sellerName"\s*:\s*"([^"]+)"', raw_scripts) or re.search(r'"user"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', raw_scripts)
    if m_seller: pub_raw = m_seller.group(1).strip()
    publisher_clean = clean_publisher_name(pub_raw)
    ai_area, ai_rooms = None, None
    try:
        r = requests.post(
            f"{AI_SERVER_URL}/analyze",
            json={"title": title, "description": desc, "publisher": publisher_clean, "deal": deal, "cat": cat, "price_num": price_num, "source": "دوبيزل", "active_ads_count": active_count, "dubizzle_strict_count_only": True},
            timeout=10
        )
        if r.status_code == 200:
            res = r.json()
            if res.get("decision") == "مرفوض": return None, "AI Rejected (Broker Pattern)"
            ai_area, ai_rooms = res.get("area"), res.get("rooms")
    except Exception:
        pass
    sub_zone = detect_sub_zone(f"{title} {desc}")
    return {
        "id": f"dub_{abs(hash(url)) % 1000000000}",
        "title": title, "link": url, "url": url,
        "price": f"{price_num:,} ج.م", "price_num": price_num,
        "cat": cat, "category": cat, "deal": deal, "type": deal,
        "zone": sub_zone, "location": sub_zone, "source": "دوبيزل",
        "publisher": f"{publisher_clean} ({active_count} إعلان نشط)",
        "active_ads_count": active_count, "area": ai_area, "rooms": ai_rooms,
        "description": desc[:500], "timestamp": int(time.time()),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    }, f"Owner Verified ({count_info})"

def load_json_list(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, list): return d
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
            time.sleep(0.3)
    return False

def save_and_push_immediately(current_ads, seen_links, push_to_github=True):
    final_ads = current_ads[:MAX_ADS_STORED]
    safe_write_json(DATA_FILE, final_ads)
    safe_write_json(SEEN_FILE, list(seen_links)[-4000:])
    if push_to_github:
        try:
            subprocess.run(["git", "add", "ads.json"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            subprocess.run(["git", "commit", "-m", "Instant Owner Update (Dubizzle 1-4 Active Ads)"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            res = subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            if res.returncode == 0:
                print(f"    --> [LIVE SYNC] Saved to ads.json & pushed to Website! (Total Owners: {len(final_ads)})")
            else:
                print(f"    --> [LOCAL SAVE] Saved to ads.json locally! (Total Owners: {len(final_ads)})")
        except Exception:
            print(f"    --> [LOCAL SAVE] Saved to ads.json locally! (Total Owners: {len(final_ads)})")

def clean_existing_dubizzle_only_db(ads_list):
    cleaned, seen_u = [], set()
    for ad in ads_list:
        if not isinstance(ad, dict) or ad.get("source") != "دوبيزل": continue
        u = ad.get("link") or ad.get("url") or ""
        if not u or u in seen_u or "dubizzle.com.eg" not in u: continue
        cnt = int(ad.get("active_ads_count", 0) or 0)
        if not (1 <= cnt <= 4):
            m_c = re.search(r'\((\d+)\s*(?:إعلان|اعلان|عقار)', str(ad.get("publisher", "")))
            cnt = int(m_c.group(1)) if m_c else 0
            if not (1 <= cnt <= 4): continue
            ad["active_ads_count"] = cnt
        deal = ad.get("deal") or ad.get("type") or "تمليك"
        p_num = parse_price_strict(ad.get("price_num") or ad.get("price"), deal)
        bad, _ = is_forbidden_or_installment(ad.get("title", ""), ad.get("description", ""), deal, p_num)
        if bad: continue
        raw_p = re.sub(r'\(\d+.*?\)$', '', str(ad.get("publisher", ""))).strip()
        ad["publisher"] = f"{clean_publisher_name(raw_p)} ({cnt} إعلان نشط)"
        ad["price_num"], ad["price"] = p_num, f"{p_num:,} ج.م"
        seen_u.add(u)
        cleaned.append(ad)
    return cleaned

def main():
    print("=== Starting Hybrid Turbo Dubizzle Radar (1 to 4 Active Ads Only) ===")
    raw_existing = load_json_list(DATA_FILE)
    current_ads = clean_existing_dubizzle_only_db(raw_existing)
    seen_links = set(load_json_list(SEEN_FILE))
    if len(raw_existing) - len(current_ads) > 0:
        print(f"[Purge] Removed {len(raw_existing) - len(current_ads)} polluted/non-Dubizzle ads from ads.json")
        save_and_push_immediately(current_ads, seen_links, push_to_github=True)
    existing_urls = {(a.get("link") or a.get("url")) for a in current_ads}
    engine = HybridTurboEngine()
    total_added = 0
    for page_num in (1, 2):
        for src in DUBIZZLE_SOURCES:
            page_url = src["url"] if page_num == 1 else f"{src['url']}?page={page_num}"
            label = f"{src['en']} p.{page_num}"
            links = engine.get_category_links(page_url, label=label)
            new_links = [lnk for lnk in links if lnk not in existing_urls and lnk not in seen_links]
            batch = new_links[:MAX_ADS_PER_PAGE]
            print(f"  -> Inspecting {len(batch)} new ads from {label} immediately...")
            for idx, u in enumerate(batch, 1):
                ad_obj, status_msg = parse_dubizzle_ad(u, src["cat"], src["deal"], engine)
                if status_msg != "Failed to load ad page":
                    seen_links.add(u)
                if ad_obj:
                    current_ads.insert(0, ad_obj)
                    existing_urls.add(u)
                    total_added += 1
                    print(f"  [{idx}/{len(batch)}] [+ ACCEPTED OWNER] {src['en']} | Active Ads: {ad_obj['active_ads_count']} | Price: {ad_obj['price_num']:,} EGP")
                    save_and_push_immediately(current_ads, seen_links, push_to_github=True)
                else:
                    print(f"  [{idx}/{len(batch)}] [- REJECTED] {status_msg}")
                time.sleep(random.uniform(0.3, 0.7))
            save_and_push_immediately(current_ads, seen_links, push_to_github=False)
    engine.close()
    print(f"=== Run Complete: Added ({total_added}) New Owners | Total Verified Owners in DB: ({len(current_ads)}) ===")

if __name__ == "__main__":
    main()
