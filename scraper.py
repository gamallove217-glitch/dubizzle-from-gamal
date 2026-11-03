"""Dubizzle Egypt New Cairo owner ads scraper.

Flow: listing pages (discovery) -> full live ad page (truth) -> strict owner filter.
All pages are fetched through ScraperAPI with a tier ladder (plain, render, premium)
and a hard credit budget. A run_report is written inside ads.json for diagnostics.
"""
import json
import os
import re
import threading
import time
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import quote

import requests

# Prefer a GitHub secret named SCRAPERAPI_KEY. The fallback keeps the old behavior.
API_KEY = os.environ.get("SCRAPERAPI_KEY") or "1fbcb4ca0bad271b0780c0a848e8c05b"
SCHEMA_VERSION = 11
SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

SITE = "https://www.dubizzle.com.eg"
SCRAPER_ENDPOINT = "https://api.scraperapi.com/"
ACCOUNT_ENDPOINT = "https://api.scraperapi.com/account"
SEARCH_ENDPOINT = "https://api.scraperapi.com/structured/google/search"

CREDIT_BUDGET = int(os.environ.get("CREDIT_BUDGET", "300"))
CREDIT_RESERVE = int(os.environ.get("CREDIT_RESERVE", "30"))
LISTING_SHARE = float(os.environ.get("LISTING_SHARE", "0.35"))
MIN_HOURS_BETWEEN_SCHEDULED = float(os.environ.get("MIN_HOURS", "20"))
MAX_RUNTIME_SEC = int(os.environ.get("MAX_RUNTIME_SEC", "1500"))
TARGET_NEW_ADS = int(os.environ.get("TARGET_NEW_ADS", "45"))
PAGES_PER_SOURCE = int(os.environ.get("PAGES_PER_SOURCE", "2"))
GOOGLE_FALLBACK_QUERIES = int(os.environ.get("GOOGLE_FALLBACK_QUERIES", "3"))
MIN_CANDIDATES = int(os.environ.get("MIN_CANDIDATES", "30"))
SKIP_VERIFIED_BUSINESS = os.environ.get("SKIP_VERIFIED_BUSINESS", "1") == "1"
MAX_WORKERS = 5

MAX_OWNER_ADS = 4
BLOCK_ABOVE = 7

# (credits per request on ScraperAPI) plain=1, render=10, premium=10, premium+render=25
TIERS = [
    {"name": "plain", "extra": {}, "cost": 1},
    {"name": "render", "extra": {"render": "true"}, "cost": 10},
    {"name": "premium", "extra": {"premium": "true"}, "cost": 10},
    {"name": "premium_render", "extra": {"premium": "true", "render": "true"}, "cost": 25},
]

# Slugs verified from public search results: apartments-duplex-for-rent/5th-settlement
# and the q-<keyword> pages. The other slugs are assumed; run_report shows which worked.
RENT, SALE = "apartments-duplex-for-rent", "apartments-duplex-for-sale"
LISTING_SOURCES = [
    (f"{RENT}/5th-settlement/", "إيجار", "شقق"),
    (f"{SALE}/5th-settlement/", "بيع", "شقق"),
    ("villas-for-sale/5th-settlement/", "بيع", "فيلا"),
    ("villas-for-rent/5th-settlement/", "إيجار", "فيلا"),
    ("commercial-for-rent/5th-settlement/", "إيجار", "تجاري وإداري"),
    ("commercial-for-sale/5th-settlement/", "بيع", "تجاري وإداري"),
    (f"{RENT}/new-cairo/", "إيجار", "شقق"),
    (f"{SALE}/new-cairo/", "بيع", "شقق"),
    (f"{RENT}/q-الرحاب/", "إيجار", "شقق"),
    (f"{SALE}/q-الرحاب/", "بيع", "شقق"),
    (f"{RENT}/q-مدينتي/", "إيجار", "شقق"),
    (f"{SALE}/q-مدينتي/", "بيع", "شقق"),
]
for _kw in ("المالك", "دوبلكس", "بنتهاوس", "استوديو", "روف"):
    LISTING_SOURCES.append((f"{RENT}/5th-settlement/q-{_kw}/", "إيجار", "شقق"))
    LISTING_SOURCES.append((f"{SALE}/5th-settlement/q-{_kw}/", "بيع", "شقق"))

# Used only as a fallback feeder when listing discovery returns too few ads (25 credits each).
SEARCH_QUERIES = [
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار التجمع الخامس ج.م", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع التجمع الخامس ج.م", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ فيلا للبيع التجمع الخامس ج.م", "deal": "بيع", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار القاهرة الجديدة ج.م", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للبيع القاهرة الجديدة ج.م", "deal": "بيع", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ فيلا للايجار التجمع الخامس ج.م", "deal": "إيجار", "category": "فيلا"},
    {"q": "site:dubizzle.com.eg/ad/ مكتب اداري للايجار التجمع الخامس ج.م", "deal": "إيجار", "category": "تجاري وإداري"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار الرحاب ج.م", "deal": "إيجار", "category": "شقق"},
    {"q": "site:dubizzle.com.eg/ad/ شقة للايجار مدينتي ج.م", "deal": "إيجار", "category": "شقق"},
]

NEW_CAIRO_PLACES = [
    "التجمع", "القاهرة الجديدة", "القاهره الجديده", "الرحاب", "مدينتي", "مدينتى",
    "النرجس", "اللوتس", "الياسمين", "البنفسج", "الشويفات", "الأندلس", "الاندلس",
    "بيت الوطن", "الأكاديمية", "الاكاديمية", "المستثمرين", "القطامية", "ميفيدا",
    "هايد بارك", "ماونتن فيو", "بالم هيلز", "سراي", "التسعين", "القرنفل",
    "تاج سيتي", "ابو الهول", "جاردينيا", "دار مصر", "سكن مصر", "جنة", "الباتيو",
    "new cairo", "5th settlement", "rehab", "madinaty", "mivida", "hyde park"
]

EXCLUDED_CITIES = [
    "العبور", "لوران", "سموحة", "سموحه", "الإسكندرية", "الاسكندرية", "اسكندرية",
    "أكتوبر", "اكتوبر", "زايد", "الشيخ زايد", "الشروق", "بدر", "المعادي", "المعادى",
    "مدينة نصر", "مدينه نصر", "مصر الجديدة", "مصر الجديده", "المقطم", "الهرم",
    "فيصل", "الدقي", "المهندسين", "حلوان", "شبرا", "عين شمس", "الساحل", "السخنة",
    "الغردقة", "ميامي", "سيدي بشر", "المنتزه", "العجمي", "طنطا", "المنصورة", "الزقازيق"
]

# Checked only against visible text (scripts removed first), never against raw HTML.
DELETED_PHRASES = [
    "لم يتم العثور على تطابقات", "قد تم بيعه أو إزالته", "تم بيعه أو إزالته",
    "حاول البحث عن إعلانات مشابهة", "we couldn't find any matches", "no longer available",
]

BLOCK_MARKERS = (
    "just a moment", "attention required", "enable javascript and cookies",
    "checking your browser", "verify you are human", "error 1020",
    "access denied", "you have been blocked",
)
CUT_MARKERS = (
    "إعلانات مشابهة", "اعلانات مشابهة", "الإعلانات المشابهة", "الاعلانات المشابهة",
    "إعلانات ذات صلة", "اتجاهات الأسعار", "الاتجاهات والمؤشرات",
    "similar ads", "related ads", "price trends",
)
SELLER_LABELS = ("تم النشر بواسطة", "نشر بواسطة", "نُشر بواسطة", "posted by", "published by")
BIZ_RE = re.compile(r"صاحب عمل موثق|verified business", re.I)

# ---------------------------------------------------------------- run state
T0 = time.time()
LOCK = threading.Lock()
STOP = threading.Event()
STATS = Counter()
EXAMPLES = {"blocked": [], "no_count": [], "no_price": [], "invalid": [], "listing_empty": []}
TIER_STATE = {}
BUDGET = None


class BudgetStop(Exception):
    pass


class Budget:
    def __init__(self, limit):
        self.limit = limit
        self.phase_limit = limit
        self.used = 0
        self.lock = threading.Lock()

    def spend(self, n):
        with self.lock:
            if self.used + n > self.phase_limit:
                raise BudgetStop("credits")
            self.used += n


def bump(key, n=1):
    with LOCK:
        STATS[key] += n


def add_example(kind, url, tier, lines, extra=""):
    with LOCK:
        if len(EXAMPLES[kind]) >= 3:
            return
        EXAMPLES[kind].append({
            "url": url, "tier": tier, "extra": extra,
            "head": " | ".join(lines[:12])[:500],
            "seller_window": seller_window_text(lines),
        })


# ---------------------------------------------------------------- text helpers
DIGITS = {**{0x660 + i: 48 + i for i in range(10)}, **{0x6F0 + i: 48 + i for i in range(10)}}
AR = "\u0621-\u064A"


def norm(text):
    text = text.translate(DIGITS)
    text = text.replace("\u066c", ",").replace("\u066b", ".").replace("\u00a0", " ")
    return re.sub(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", text)


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "template", "svg", "head"}
    BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
             "tr", "table", "section", "article", "header", "footer", "main", "nav",
             "aside", "form", "dl", "dt", "dd", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif not self.skip:
            self.parts.append("\n" if tag in self.BLOCK else " ")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif not self.skip:
            self.parts.append("\n" if tag in self.BLOCK else " ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_lines(html):
    p = _TextExtractor()
    try:
        p.feed(html)
        p.close()
    except Exception:
        pass
    lines = []
    for ln in norm("".join(p.parts)).split("\n"):
        ln = re.sub(r"\s+", " ", ln).strip()
        if ln:
            lines.append(ln)
    return lines


def to_int(s):
    s = s.replace(",", "").strip()
    return int(s) if s.isdigit() else 0


def extract_title(html):
    t = ""
    m = (re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*)["\']', html, re.I)
         or re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']og:title["\']', html, re.I))
    if m:
        t = m.group(1)
    if not t.strip():
        m = re.search(r"<h1\b[^>]*>(.*?)</h1>", html, re.S | re.I)
        if m:
            t = re.sub(r"<[^>]+>", " ", m.group(1))
    if not t.strip():
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        t = m.group(1) if m else ""
    t = re.sub(r"\s+", " ", norm(unescape(t))).strip()
    return re.sub(r"\s*[-|]\s*(?:دوبيزل|dubizzle).*$", "", t, flags=re.I).strip()


def main_segment(lines):
    out = []
    for ln in lines:
        low = ln.lower()
        if len(out) >= 8 and any(m in low for m in CUT_MARKERS):
            break
        out.append(ln)
    return out


def field_value(lines, labels):
    for i, ln in enumerate(lines):
        low = ln.lower()
        for lab in labels:
            if low.startswith(lab):
                rest = ln[len(lab):].strip(" :：")
                if rest:
                    return rest[:40]
                if i + 1 < len(lines):
                    return lines[i + 1][:40]
    return ""


CUR = r"(?:EGP|(?<![" + AR + r"])ج\.?\s?م\.?(?![" + AR + r"])|جنيه|جنية)"
NUM = r"(\d{1,3}(?:,\d{3})+|\d{4,12})"
PRICE_RES = [re.compile(CUR + r"\s*" + NUM, re.I), re.compile(NUM + r"\s*" + CUR, re.I)]
UNIT = r"(?:\(\s*(?:م\s?[²2]?|m\s?[²2]?|sqm|متر(?:\s*مربع)?)\s*\))?"
AREA_RE = re.compile(r"(?:المساحة|Area)\s*" + UNIT + r"\s*[:：]?\s*(\d{2,5})", re.I)
AREA_FALLBACK_RE = re.compile(r"(?<![\d,])(\d{2,4})\s*(?:م²|م2|متر(?:\s*مربع)?|sqm|m²|m2)", re.I)
BEDS_RE = re.compile(r"(?:غرف(?:ة)?\s*(?:ال)?نوم|Bedrooms?|Beds?)\s*[:：]?\s*(\d{1,2})", re.I)
BEDS2_RE = re.compile(r"(?<![\d,])(\d{1,2})\s*(?:غرف نوم|غرف|غرفة|bedrooms?|beds?)", re.I)
BATHS_RE = re.compile(r"(?:(?:ال)?حمامات|حمام|Bathrooms?|Baths?)\s*[:：]?\s*(\d{1,2})", re.I)
BATHS2_RE = re.compile(r"(?<![\d,])(\d{1,2})\s*(?:حمامات|حمام|bathrooms?|baths?)", re.I)
PERIOD_RE = re.compile(r"(شهري[اً]?|سنوي[اً]?|يومي[اً]?|monthly|yearly|daily)", re.I)

ACT = r"(?:ال)?[إأآا]علان(?:ات)?\s*(?:ال)?نشط(?:ة|ه|ين)?"
ACTIVE_PATS = [
    re.compile(r"(?<![\d,.])(\d{1,3})(?![\d,])\s*" + ACT),
    re.compile(ACT + r"\s*[:：]?\s*(?<![\d,.])(\d{1,3})(?![\d,])"),
    re.compile(r"(?<![\d,.])(\d{1,3})(?![\d,])\s*active\s*(?:ads?|listings?)", re.I),
    re.compile(r"active\s*(?:ads?|listings?)\s*[:：]?\s*(\d{1,3})(?![\d,])", re.I),
]
NAME_CUT_RE = re.compile(
    r"\s+(?:عضو منذ|member since)|\s+\d{1,3}\s+(?:ال)?[إأآا]علان|\s+(?:ال)?[إأآا]علان|\s+\d{1,3}\s+active",
    re.I)


def first_price(text):
    best = None
    for rx in PRICE_RES:
        for m in rx.finditer(text):
            val = to_int(m.group(1))
            if val >= 1000 and (best is None or m.start() < best[0]):
                best = (m.start(), val)
                break
    return best[1] if best else 0


def seller_index(lines):
    for i, ln in enumerate(lines):
        low = ln.lower()
        for lab in SELLER_LABELS:
            if lab in low:
                return i, lab
    return None, None


def seller_window_text(lines):
    idx, _ = seller_index(lines)
    if idx is None:
        return "no seller label found"
    return " | ".join(lines[idx: idx + 10])[:400]


def extract_seller(lines):
    idx, lab = seller_index(lines)
    name, window, biz = None, "", False
    if idx is not None:
        ln = lines[idx]
        after = ln[ln.lower().index(lab) + len(lab):].strip(" :：-")
        if not after and idx + 1 < len(lines):
            after = lines[idx + 1]
        cand = NAME_CUT_RE.split(after)[0].strip()
        if 2 <= len(cand) <= 40:
            name = cand
        window = " ".join(lines[idx: idx + 12])
        biz = bool(BIZ_RE.search(window))
    count, src = None, ""
    for scope, label in ((window, "seller_box"), ("\n".join(lines), "page_text")):
        if not scope:
            continue
        for rx in ACTIVE_PATS:
            m = rx.search(scope)
            if m:
                count, src = int(m.group(1)), label
                break
        if count is not None:
            break
    return name, count, src, biz


def parse_ad_page(html):
    """Return (result, complete). complete=True means no need to escalate to a stronger tier."""
    lines = html_to_lines(html)
    out = {"state": "invalid"}
    head = " ".join(lines[:15]).lower()
    if len(lines) < 80 and any(m in head for m in BLOCK_MARKERS):
        out["state"] = "blocked"
        out["lines"] = lines
        return out, False
    low_full = "\n".join(lines).lower()
    if any(dp in low_full for dp in DELETED_PHRASES):
        return {"state": "gone"}, True
    title = extract_title(html)
    main = main_segment(lines)
    main_text = "\n".join(main)
    price_lines = [ln for ln in main[:30] if not (title and ln.startswith(title[:25]))]
    price = first_price("\n".join(price_lines[:25])) or first_price("\n".join(price_lines))
    if not price:
        m = re.search(r'"price"\s*:\s*"?(\d[\d.]*)', html)
        if m and m.group(1).replace(".", "").isdigit() and float(m.group(1)) >= 1000:
            price = int(float(m.group(1)))
    if not title and not price:
        out["lines"] = lines
        return out, False
    period = ""
    for ln in main[:25]:
        if str(price) in ln.replace(",", "") or f"{price:,}" in ln:
            pm = PERIOD_RE.search(" ".join(main[max(0, main.index(ln) - 1): main.index(ln) + 3]))
            period = pm.group(1) if pm else ""
            break
    m_area = AREA_RE.search(main_text) or AREA_FALLBACK_RE.search(title + "\n" + main_text)
    m_beds = BEDS_RE.search(main_text) or BEDS2_RE.search(title + "\n" + main_text)
    m_baths = BATHS_RE.search(main_text) or BATHS2_RE.search(title + "\n" + main_text)
    loc_line = ""
    for ln in main[:30]:
        if len(ln) < 90 and re.search(r"[،,]", ln) and (
                any(p in ln.lower() for p in NEW_CAIRO_PLACES + EXCLUDED_CITIES)
                or "القاهرة" in ln or "cairo" in ln.lower()):
            loc_line = ln
            break
    start = 0
    for i, ln in enumerate(main):
        if ln.lower().strip(": ") in ("التفاصيل", "الوصف", "details", "description"):
            start = i + 1
            break
    else:
        for i, ln in enumerate(main):
            if title and ln.startswith(title[:25]):
                start = i + 1
                break
    desc_parts = []
    for ln in main[start:]:
        low = ln.lower()
        if any(low.startswith(s) for s in ("الموقع", "location", "سلامتك", "your safety", "تم النشر", "posted by")):
            break
        if len(ln) >= 30:
            desc_parts.append(ln)
    name, count, count_src, biz = extract_seller(lines)
    if count is None:
        mj = re.search(r'"(?:activeAdsCount|active_ads_count|activeAds|active_ads)"\s*:\s*(\d{1,4})', html)
        if mj:
            count, count_src = int(mj.group(1)), "embedded_json"
    out.update({
        "state": "ok", "title": title, "price_num": price, "price_period": period,
        "area": (m_area.group(1) + " م²") if m_area else "مدرج بالإعلان",
        "beds": (m_beds.group(1) + " غرف") if m_beds else "",
        "baths": (m_baths.group(1) + " حمام") if m_baths else "",
        "loc_line": loc_line,
        "type_field": field_value(main, ("النوع", "type")),
        "purpose": field_value(main, ("الغرض", "purpose")),
        "description": "\n".join(desc_parts)[:1500],
        "seller_name": name, "count": count, "count_src": count_src, "biz": biz,
        "lines": lines,
    })
    return out, count is not None


# ---------------------------------------------------------------- classification
def detect_category_and_subtype(title, type_field, default_cat):
    t = title.lower()
    tf = type_field.lower()
    both = t + " " + tf
    if any(w in tf for w in ["فيلا", "تاون", "توين", "villa", "townhouse", "twin"]):
        cat = "فيلا"
    elif any(w in tf for w in ["مكتب", "محل", "عيادة", "عياده", "تجاري", "اداري", "إداري", "commercial", "office", "shop", "clinic", "retail"]):
        cat = "تجاري وإداري"
    elif any(w in tf for w in ["شقة", "شقه", "apartment", "duplex", "دوبلكس", "penthouse", "بنتهاوس", "studio", "استوديو", "غرفة", "room", "roof", "روف"]):
        cat = "شقق"
    elif any(w in t for w in ["مكتب", "محل", "عيادة", "عياده", "office", "clinic", "retail"]):
        cat = "تجاري وإداري"
    elif any(w in t for w in ["فيلا", "تاون هاوس", "توين هاوس", "ستاند الون", "villa", "townhouse", "twinhouse", "standalone"]):
        cat = "فيلا"
    else:
        cat = default_cat
    if cat == "فيلا":
        return cat, "فيلا"
    if cat == "تجاري وإداري":
        return cat, "تجاري وإداري"
    if any(w in both for w in ["بنتهاوس", "بنت هاوس", "penthouse"]):
        return "شقق", "بنتهاوس"
    if any(w in both for w in ["دوبلكس", "دوبليكس", "duplex"]):
        return "شقق", "دوبلكس"
    if any(w in both for w in ["استوديو", "ستوديو", "studio"]):
        return "شقق", "استوديو"
    if re.match(r"^\s*(?:روف|رووف|roof)", t) or any(w in tf for w in ["روف", "roof"]):
        return "شقق", "روف"
    if re.match(r"^\s*(?:غرفة|غرفه|room)", t) or any(w in tf for w in ["غرفة", "room"]):
        return "شقق", "غرفة"
    return cat, ("شقة" if cat == "شقق" else cat)


def detect_deal(purpose, default_deal):
    p = purpose.lower()
    if any(w in p for w in ["ايجار", "إيجار", "rent"]):
        return "إيجار"
    if any(w in p for w in ["بيع", "sale"]):
        return "بيع"
    return default_deal


def in_new_cairo(title, loc_line, from_nc_source):
    loc = loc_line.lower()
    if loc:
        if any(ex in loc for ex in EXCLUDED_CITIES):
            return False
        if any(nc in loc for nc in NEW_CAIRO_PLACES):
            return True
    t = title.lower()
    if any(ex in t for ex in EXCLUDED_CITIES):
        return False
    if any(nc in t for nc in NEW_CAIRO_PLACES):
        return True
    return from_nc_source


def extract_ad_id(ad_url):
    m = re.search(r"-ID(\d+)", ad_url, re.I)
    return int(m.group(1)) if m and m.group(1).isdigit() else 0


def normalize_ad_url(href):
    href = unescape(href).split("?")[0].split("#")[0]
    if href.startswith("//"):
        href = "https:" + href
    if href.startswith("/"):
        href = SITE + href
    href = re.sub(r"^(https?://[^/]+)/(?:en|ar)/ad/", r"\1/ad/", href)
    return quote(href, safe=":/%-._~")


# ---------------------------------------------------------------- fetching
def scraper_get(url, tier):
    BUDGET.spend(tier["cost"])
    params = {"api_key": API_KEY, "url": url}
    params.update(tier["extra"])
    for attempt in range(3):
        if time.time() - T0 > MAX_RUNTIME_SEC:
            raise BudgetStop("time")
        try:
            r = requests.get(SCRAPER_ENDPOINT, params=params, timeout=80)
        except requests.RequestException:
            time.sleep(3)
            continue
        if r.status_code == 429:
            time.sleep(6 * (attempt + 1))
            continue
        return
