import json
import random
import re
import time
import urllib.parse
from difflib import SequenceMatcher
from html import unescape
from datetime import datetime, timezone, timedelta
import requests as std_requests
from curl_cffi import requests as cffi_requests

CAIRO_TZ = timezone(timedelta(hours=2))
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
BASE_URL = "https://www.dubizzle.com.eg"

SEARCH_URLS = {
    "sale": [
        "https://www.dubizzle.com.eg/en/properties/apartments-duplex-for-sale/5th-settlement/",
        "https://www.dubizzle.com.eg/en/properties/villas-for-sale/5th-settlement/",
        "https://www.dubizzle.com.eg/en/properties/commercial-for-sale/5th-settlement/",
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    ],
    "rent": [
        "https://www.dubizzle.com.eg/en/properties/apartments-duplex-for-rent/5th-settlement/",
        "https://www.dubizzle.com.eg/en/properties/villas-for-rent/5th-settlement/",
        "https://www.dubizzle.com.eg/en/properties/commercial-for-rent/5th-settlement/",
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
    ],
}

MAX_PAGES_PER_CATEGORY = 4
MAX_HOURS_FRESHNESS = 30
BROKER_ACTIVE_ADS_THRESHOLD = 5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

BROKER_CODE_PATTERN = re.compile(
    r"(?:\bكود\s*[:\-]?\s*[A-Za-z0-9\u0660-\u0669]{2,10}\b|\bcode\s*[:\-]?\s*[A-Za-z0-9]{2,10}\b)",
    re.IGNORECASE,
)

VACATION_PROPERTY_PATTERN = re.compile(
    r"(?:عقارات\s*مصايف|مصايف|\b(?:vacation|holiday|chalet|chalets)\b)",
    re.IGNORECASE,
)

 STRICT_FORBIDDEN_LOCATIONS = [
    "مصر الجديدة", "مصر الجديده", "heliopolis", "مدينة نصر", "مدينه نصر", "nasr city",
    "زهراء مدينة نصر", "الكوربة", "أرض الجولف", "ارض الجولف", "روكسي", "الماظة",
    "ألماظة", "شيراتون", "النزهة", "عباس العقاد", "مكرم عبيد", "مصطفى النحاس",
    "جاردينيا سيتي", "تاج سيتي", "taj city", "الرحاب", "مدينة الرحاب", "rehab city",
    "al rehab", "مدينتي", "مدينتى", "madinaty", "الشروق", "مدينة الشروق", "shorouk",
    "مدينة المستقبل", "المستقبل سيتي", "mostakbal", "future city", "بدر", "مدينة بدر",
    "العبور", "العاصمة الإدارية", "new capital", "المعادي", "الشيخ زايد", "6 أكتوبر",
    "المقطم"
]

BROKER_NAME_WORDS = [
    "real estate", "realestate", "properties", "property", "investment", "investments",
    "development", "developments", "group", "agency", "consultancy", "consulting",
    "broker", "brokers", "marketing", "hospitality", "capital", "avenue", "hills",
    "lounge", "hub", "insider", "coldwell", "remax", "houseology", "westfield",
    "conquer", "sadan", "retaj", "colombus", "aspire", "privilege", "signature",
    "imkan", "closer", "el rabeh", "green home", "home group", "4 c", "egy property",
    "gate real estate", "al hayah", "elnemr", "scouts", "falcon", "redefine",
    "elviro", "wall street", "deal", "prime location", "choice", "damas", "ebtkar",
    "home hub", "lotus flower", "black code", "diamant", "maqam", "mavista",
    "horizon", "brand real estate", "alofok", "new home", "fekra re", "almaz",
    "nch", "apex", "el nemr", "make money", "the landmark", "owner 59", "ghp",
    "backyard", "irtkaz", "strive", "landmax", "aqarpedia", "circle realestate",
    "estimate", "global stay", "views real estate", "egypt best",
    "للتسويق", "للاستثمار", "للتطوير", "للمقاولات", "للعقارات", "التسويق العقاري",
    "الاستثمار العقاري", "التطوير العقاري", "شركة موثقة", "الالمانية للتنمية",
    "وايت هوم", "بيتي للمقاولات", "النمر للتطوير", "ثقة العقارية", "شيلد للاسكان"
]

_AD_HREF_RE = re.compile(
    r"(?:https?://(?:www\.)?dubizzle\.com\.eg)?"
    r"(?P<path>/+(?:en/)?ad/[^\"'<>\s]+?ID\d+\.html)",
    re.IGNORECASE,
)


def is_broker_seller_name(name_str):
    if not name_str:
        return False
    low = name_str.lower().strip()
    for w in BROKER_NAME_WORDS:
        if w in low:
            return True
    return False


class AntiBlockClient:
    def __init__(self):
        self.req_sess = std_requests.Session()
        self.cffi_sessions = []
        for imp in ("chrome120", "chrome119", "safari17_0"):
            try:
                s = cffi_requests.Session(impersonate=imp)
                s.headers.update(HEADERS)
                self.cffi_sessions.append(s)
            except Exception:
                pass

    def get_html(self, url, need_window_state=True, timeout_sec=28):
        time.sleep(random.uniform(1.2, 2.4))

        for s in self.cffi_sessions:
            try:
                r = s.get(url, timeout=timeout_sec, allow_redirects=True)
                if r.status_code == 200 and len(r.text) > 1500:
                    if not need_window_state or "window.state" in r.text:
                        return r.text
            except Exception:
                pass

        j_url = "https://r.jina.ai/" + url
        j_headers = dict(HEADERS)
        j_headers["X-Return-Format"] = "html"
        for s in self.cffi_sessions + [self.req_sess]:
            try:
                r = s.get(j_url, headers=j_headers, timeout=timeout_sec)
                if r.status_code == 200 and len(r.text) > 1500:
                    if "Too Many Requests" not in r.text and "RateLimitExceeded" not in r.text:
                        return r.text
            except Exception:
                pass

        return ""

    def get_jina_markdown(self, url, timeout_sec=25):
        j_url = "https://r.jina.ai/" + url
        for s in self.cffi_sessions + [self.req_sess]:
            try:
                r = s.get(j_url, headers=HEADERS, timeout=timeout_sec)
                if r.status_code == 200 and len(r.text) > 500:
                    if "Too Many Requests" not in r.text and "RateLimitExceeded" not in r.text:
                        return r.text
            except Exception:
                pass
        return ""


def extract_window_state(html):
    if not html:
        return None
    match = re.search(r"window\.state\s*=\s*", html)
    if not match:
        return None

    start = match.end()
    depth = 0
    in_string = False
    string_char = ""
    escaped = False
    end = None

    for index in range(start, len(html)):
        ch = html[index]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == string_char:
                in_string = False
            continue
        if ch in ('"', "'"):
            in_string = True
            string_char = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break

    if end is None:
        return None
    try:
        return json.loads(html[start:end])
    except Exception:
        return None


def get_formatted_field(hit, attribute):
    for field in hit.get("formattedExtraFields", []):
        if field.get("attribute") == attribute:
            return field.get("formattedValue_l1") or field.get("formattedValue")
    return None


def _normalize_match_text(value):
    if value is None:
        return ""
    text = unescape(urllib.parse.unquote(str(value)))
    text = text.replace("\u0640", "")
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    text = text.translate(AR_DIGITS)
    text = re.sub(r"[^\w\u0600-\u06FF]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip().lower()


def _text_tokens(value):
    text = _normalize_match_text(value)
    return [t for t in text.split() if len(t) >= 2]


def _extract_number(value):
    if value is None:
        return None
    raw = _normalize_match_text(value).replace(",", "")
    m = re.search(r"\d+(?:\.\d+)?", raw)
    if not m:
        return None
    try:
        return int(float(m.group()))
    except Exception:
        return None


def _strip_html(value):
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return unescape(value)


def normalize_dubizzle_url(raw_u):
    if not raw_u:
        return None, None
    u = urllib.parse.unquote(urllib.parse.unquote(str(raw_u))).strip()
    u = re.sub(r"^https?://(?:www\.)?dubizzle\.com\.eg/+en/ad/", "https://www.dubizzle.com.eg/ad/", u)
    u = re.sub(r"^/+en/ad/", "/ad/", u)
    if u.startswith("/ad/"):
        u = BASE_URL + u
    m = re.search(r"(https?://(?:www\.)?dubizzle\.com\.eg/ad/[^\s\"'<>)\]]+?-ID(\d+)\.html)", u, re.I)
    if not m:
        return None, None
    full_u = m.group(1)
    ad_id = int(m.group(2))
    p = urllib.parse.urlsplit(full_u)
    clean_path = urllib.parse.quote(p.path, safe="/-._~")
    return f"https://www.dubizzle.com.eg{clean_path}", ad_id


def extract_dom_ad_links(html):
    results = []
    seen = set()
    for match in _AD_HREF_RE.finditer(html):
        raw_path = match.group("path")
        raw_href = urllib.parse.urljoin(BASE_URL, raw_path)
        clean_href, pub_id = normalize_dubizzle_url(raw_href)
        if not clean_href or clean_href in seen:
            continue
        seen.add(clean_href)

        w_start = max(0, match.start() - 3500)
        w_end = min(len(html), match.end() + 3500)
        context = _strip_html(html[w_start:w_end])

        href_unquoted = urllib.parse.unquote(clean_href)
        path = urllib.parse.urlparse(href_unquoted).path
        slug_m = re.search(r"/ad/(.+?)-ID\d+\.html$", path, re.I)
        slug_text = slug_m.group(1).replace("-", " ") if slug_m else ""

        results.append({
            "href": clean_href,
            "slug_text": _normalize_match_text(slug_text),
            "context": _normalize_match_text(context),
            "internal_id": str(pub_id) if pub_id else None,
        })
    return results


def _hit_match_fields(hit):
    price = hit.get("extraFields", {}).get("price") or get_formatted_field(hit, "price")
    return {
        "title": hit.get("title_l1") or hit.get("title") or "",
        "title_en": hit.get("title") or "",
        "title_tokens": _text_tokens((hit.get("title_l1") or "") + " " + (hit.get("title") or "")),
        "price": _extract_number(price),
        "area": _extract_number(get_formatted_field(hit, "ft")),
        "bedrooms": _extract_number(get_formatted_field(hit, "rooms")),
        "bathrooms": _extract_number(get_formatted_field(hit, "bathrooms")),
        "location": (hit.get("location.lvl3") or {}).get("name_l1") or "",
        "compound": get_formatted_field(hit, "compound") or hit.get("compound") or "",
    }


def _candidate_score(fields, candidate):
    candidate_text = candidate.get("context", "")
    candidate_slug = candidate.get("slug_text", "")
    title_tokens = fields["title_tokens"]
    if not title_tokens:
        return 0.0, {}

    title_matches = sum(1 for token in title_tokens if token in candidate_slug or token in candidate_text)
    title_coverage = title_matches / max(len(title_tokens), 1)

    slug_ratio = max(
        SequenceMatcher(None, _normalize_match_text(fields["title"]), candidate_slug).ratio(),
        SequenceMatcher(None, _normalize_match_text(fields["title_en"]), candidate_slug).ratio(),
    )

    score = 0.55 * title_coverage + 0.20 * slug_ratio
    evidence = {"title_coverage": round(title_coverage, 4), "slug_ratio": round(slug_ratio, 4)}

    for field_name, weight in [("price", 0.12), ("area", 0.06), ("bedrooms", 0.03), ("bathrooms", 0.03)]:
        expected = fields.get(field_name)
        if expected is not None and re.search(rf"\b{re.escape(str(expected))}\b", candidate_text):
            score += weight
            evidence[field_name] = True

    return score, evidence


def resolve_dom_ad_urls(hits, html):
    dom_links = extract_dom_ad_links(html)
    by_id = {c["internal_id"]: c["href"] for c in dom_links if c.get("internal_id")}
    resolved = {}
    used_hrefs = set()

    for hit in hits:
        hit_id = str(hit.get("id") or hit.get("objectID") or "").strip()
        ext_id = str(hit.get("externalID") or "").strip()
        if not hit_id:
            continue

        for cand_id in (ext_id, hit_id):
            if cand_id and cand_id in by_id and by_id[cand_id] not in used_hrefs:
                resolved[hit_id] = by_id[cand_id]
                used_hrefs.add(by_id[cand_id])
                break
        if hit_id in resolved:
            continue

        slug = hit.get("slug") or hit.get("slug_l1")
        if slug and (ext_id.isdigit() or hit_id.isdigit()):
            pub_num = ext_id if ext_id.isdigit() else hit_id
            u_cand, _ = normalize_dubizzle_url(f"https://www.dubizzle.com.eg/ad/{slug}-ID{pub_num}.html")
            if u_cand:
                resolved[hit_id] = u_cand
                used_hrefs.add(u_cand)
                continue

        if not dom_links:
            continue

        fields = _hit_match_fields(hit)
        ranked = []
        for candidate in dom_links:
            if candidate["href"] in used_hrefs:
                continue
            score, evidence = _candidate_score(fields, candidate)
            ranked.append((score, candidate, evidence))

        ranked.sort(key=lambda item: item[0], reverse=True)
        if not ranked:
            continue

        best_score, best_candidate, best_evidence = ranked[0]
        second_score = ranked[1][0] if len(ranked) > 1 else 0.0
        margin = best_score - second_score
        title_ok = best_evidence.get("title_coverage", 0.0) >= 0.45 or best_evidence.get("slug_ratio", 0.0) >= 0.65

        if best_score >= 0.55 and title_ok and (margin >= 0.04 or best_score >= 0.80):
            resolved[hit_id] = best_candidate["href"]
            used_hrefs.add(best_candidate["href"])

    return resolved


def _find_seller_profile_in_state(obj, seller_id):
    if isinstance(obj, dict):
        seller_profile = obj.get("sellerProfile")
        if isinstance(seller_profile, dict):
            data = seller_profile.get("data") if isinstance(seller_profile.get("data"), dict) else None
            if data and "adsCount" in data and data.get("adsCount") is not None:
                try:
                    return int(data.get("adsCount"))
                except Exception:
                    pass
            for key in ("activeAdsCount", "adsCount", "activeAds"):
                if key in seller_profile and seller_profile.get(key) is not None:
                    try:
                        return int(seller_profile.get(key))
                    except Exception:
                        pass
        for value in obj.values():
            found = _find_seller_profile_in_state(value, seller_id)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_seller_profile_in_state(item, seller_id)
            if found is not None:
                return found
    return None


def clean_markdown_to_text(md):
    txt = (md or "").translate(AR_DIGITS)
    txt = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"\bImage\s*\d+:?\b", " ", txt, flags=re.I)
    txt = re.sub(r"[*#_`~>|]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def extract_cnt_and_seller_from_text(text_src):
    if not text_src:
        return None, ""
    has_agency_carousel = "شاهد المزيد من إعلانات" in text_src
    for marker in ["شاهد المزيد من إعلانات", "الإبلاغ عن هذا الإعلان", "قم بالإبلاغ عن هذا الإعلان", "سلامتك تهمنا"]:
        if marker in text_src:
            text_src = text_src.split(marker)[0]

    clean_all = clean_markdown_to_text(_strip_html(text_src))
    seller = ""
    if "عضو منذ" in clean_all:
        before_member = clean_all.split("عضو منذ")[-2]
        if "تم النشر بواسطة" in before_member:
            cand = before_member.split("تم النشر بواسطة")[-1].strip(" .-:|")
            if 1 <= len(cand) <= 55:
                seller = cand

    clean_no_year = re.sub(r"عضو\s*منذ\s*\d{4}", " ", clean_all)
    clean_no_year = re.sub(r"\b20[0-2]\d\b", " ", clean_no_year)

    counts = []
    for m in re.finditer(r"\b(\d{1,4})[\s:|\-•.]{0,6}(?:ال)?(?:إ|ا)علان(?:ات)?\s*(?:ال)?نشط", clean_no_year):
        val = int(m.group(1))
        if 1 <= val <= 1500:
            counts.append(val)
    for m in re.finditer(r"(?:ال)?(?:إ|ا)علان(?:ات)?\s*(?:ال)?نشط(?:ة|ه)?[\s:|\-•.]{0,6}(\d{1,4})\b", clean_no_year):
        val = int(m.group(1))
        if 1 <= val <= 1500:
            counts.append(val)
    for m in re.finditer(r"\b(\d{1,4})\s*active\s*ads?\b", clean_no_year, re.I):
        val = int(m.group(1))
        if 1 <= val <= 1500:
            counts.append(val)
    for m in re.finditer(r"published\s*ads?\s*\(?(\d{1,4})\)?", clean_no_year, re.I):
        val = int(m.group(1))
        if 1 <= val <= 1500:
            counts.append(val)

    cnt = max(counts) if counts else None
    if has_agency_carousel or "شركة موثقة" in clean_all or is_broker_seller_name(seller):
        cnt = max(cnt or 0, 99)

    return cnt, seller


def get_verified_seller_ads_count(client, seller_id, ad_url, seller_name, sellers_cache):
    if is_broker_seller_name(seller_name):
        return 99, seller_name

    if seller_id and seller_id in sellers_cache:
        cached = sellers_cache[seller_id]
        try:
            c_cnt = int(cached.get("active_ads_count", 0))
            if c_cnt > 0:
                return c_cnt, cached.get("seller_name") or seller_name
        except Exception:
            pass

    cnt = None
    if seller_id:
        prof_url = f"{BASE_URL}/en/profile/{seller_id}/"
        prof_html = client.get_html(prof_url, need_window_state=True, timeout_sec=22)
        if prof_html:
            state = extract_window_state(prof_html)
            if state:
                cnt = _find_seller_profile_in_state(state, seller_id)
            if cnt is None:
                cnt, _ = extract_cnt_and_seller_from_text(prof_html)

    if cnt is None and ad_url:
        ad_html = client.get_html(ad_url, need_window_state=True, timeout_sec=22)
        if ad_html:
            state = extract_window_state(ad_html)
            if state:
                cnt = _find_seller_profile_in_state(state, seller_id)
            if cnt is None:
                cnt, s_name2 = extract_cnt_and_seller_from_text(ad_html)
                if not seller_name and s_name2:
                    seller_name = s_name2

    if cnt is None and ad_url:
        md = client.get_jina_markdown(ad_url, timeout_sec=22)
        if md:
            cnt, s_name2 = extract_cnt_and_seller_from_text(md)
            if not seller_name and s_name2:
                seller_name = s_name2
        if cnt is None:
            md2 = client.get_jina_markdown(ad_url + "?abs=1", timeout_sec=22)
            if md2:
                cnt, s_name2 = extract_cnt_and_seller_from_text(md2)
                if not seller_name and s_name2:
                    seller_name = s_name2

    if cnt is not None and cnt > 0 and seller_id:
        sellers_cache[seller_id] = {
            "seller_id": seller_id,
            "seller_name": seller_name or "مالك",
            "active_ads_count": cnt,
            "classification": "broker" if cnt >= BROKER_ACTIVE_ADS_THRESHOLD else "owner",
            "checked_at": datetime.now(CAIRO_TZ).isoformat(),
        }

    return cnt, seller_name or "مالك"


def classify_deal_category_subtype(listing_type, prop_type_str, url, title_clean, desc_clean, price_num):
    deal = "إيجار" if listing_type == "rent" else "بيع"
    u_dec = urllib.parse.unquote(url or "").lower()
    t_and_d = f"{title_clean} {desc_clean[:180]} {prop_type_str}".lower()

    if any(w in u_dec for w in ["rent", "إيجار", "ايجار", "للايجار", "للإيجار"]) or any(
        w in t_and_d for w in ["للإيجار", "للايجار", "إيجار", "ايجار", "for rent", "monthly"]
    ):
        deal = "إيجار"
    elif 0 < price_num < 150000:
        deal = "إيجار"

    subtype = "شقة"
    if any(w in t_and_d for w in ["دوبلكس", "دوبليكس", "duplex"]):
        subtype = "دوبلكس"
    elif any(w in t_and_d for w in ["بنتهاوس", "penthouse"]):
        subtype = "بنتهاوس"
    elif any(w in t_and_d for w in ["تاون هاوس", "توين هاوس", "فيلا", "ڤيلا", "ستاند الون", "villa", "townhouse", "twin house", "ivilla", "stand alone"]):
        subtype = "فيلا"
    elif any(w in t_and_d for w in ["سطح", "رووف", "روف", "roof"]):
        subtype = "سطح"
    elif any(w in t_and_d for w in ["شقة فندقية", "شقه فندقيه", "فندقية", "serviced", "hotel apartment"]):
        subtype = "شقة فندقية"
    elif any(w in t_and_d for w in ["ستوديو", "استوديو", "studio"]):
        subtype = "ستوديو"
    elif any(w in t_and_d for w in ["غرفة", "غرفه", "room"]):
        subtype = "غرفة"
    elif any(w in f"{title_clean} {u_dec} {prop_type_str}".lower() for w in ["مكتب", "إداري", "اداري", "عيادة", "عياده", "محل", "تجاري", "تجارى", "معرض", "صيدلية", "commercial", "office", "clinic", "retail", "shop", "medical"]):
        subtype = "عقار تجاري"

    if subtype == "فيلا":
        category = "فلل للإيجار" if deal == "إيجار" else "فلل للبيع"
    elif subtype == "عقار تجاري":
        category = "عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"
    else:
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"

    return deal, category, subtype


def load_existing():
    kept = {}
    sellers_cache = {}
    checked_ids = {504371289, 504371232, 504371218, 504371178, 209365202}
    now_dt = datetime.now(CAIRO_TZ)

    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            sellers_cache = data.get("sellers_cache_v1", {})
            checked_ids |= set(data.get("checked_ids_v1", []))
            for a in data.get("ads", []):
                aid = int(a.get("ad_id", 0))
                if not aid or aid in checked_ids:
                    continue
                if a.get("verified_v11") is True or a.get("verified_v12") is True:
                    kept[aid] = a
    except Exception:
        pass

    return kept, sellers_cache, checked_ids


def format_age_from_ts(updated_ts, now_utc):
    if not updated_ts:
        return 2, "منذ ساعات"
    diff_sec = max(60, (now_utc - datetime.fromtimestamp(updated_ts, tz=timezone.utc)).total_seconds())
    hours = diff_sec / 3600.0
    if hours > MAX_HOURS_FRESHNESS:
        return 0, f"منذ {int(hours // 24)} أيام"
    if hours < 1.0:
        mins = max(1, int(diff_sec // 60))
        return 3, f"منذ {mins} دقائق"
    if hours < 24.0:
        return 3, f"منذ {int(hours)} ساعات"
    return 2, "منذ 1 يوم"


def scrape_all():
    kept_ads, sellers_cache, checked_ids = load_existing()
    client = AntiBlockClient()
    now_utc = datetime.now(timezone.utc)
    now_cairo = datetime.now(CAIRO_TZ)

    print(f"Loaded {len(kept_ads)} existing verified owners | Cached sellers: {len(sellers_cache)}")

    candidate_hits = []
    seen_hit_ids = set()

    for listing_type, urls in SEARCH_URLS.items():
        for base_url in urls:
            for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
                sep = "&" if "?" in base_url else "?"
                page_url = base_url if page == 1 else f"{base_url}{sep}page={page}"
                html = client.get_html(page_url, need_window_state=True, timeout_sec=28)
                if not html:
                    continue

                state = extract_window_state(html)
                if state:
                    content = state.get("algolia", {}).get("content", {})
                    hits = content.get("hits", [])
                    if not hits:
                        break
                    resolved_urls = resolve_dom_ad_urls(hits, html)
                    print(f"[{listing_type.upper()}] Page {page}: {len(hits)} hits in window.state ({len(resolved_urls)} URLs resolved)")

                    for hit in hits:
                        if hit.get("state") and hit.get("state") != "active":
                            continue
                        if hit.get("agency") is not None or bool(hit.get("isSellerVerified", False)):
                            continue

                        updated_ts = hit.get("updatedAt") or hit.get("createdAt")
                        tier, age_label = format_age_from_ts(updated_ts, now_utc)
                        if tier == 0:
                            continue

                        hit_id = str(hit.get("id") or hit.get("objectID") or "").strip()
                        ad_url = resolved_urls.get(hit_id)
                        clean_u, pub_ad_id = normalize_dubizzle_url(ad_url)
                        if not clean_u or not pub_ad_id:
                            continue
                        if pub_ad_id in kept_ads or pub_ad_id in checked_ids or pub_ad_id in seen_hit_ids:
                            continue

                        title_str = hit.get("title_l1") or hit.get("title") or ""
                        desc_str = hit.get("description_l1") or hit.get("description") or ""
                        loc_str = (hit.get("location.lvl3") or {}).get("name_l1") or (hit.get("location.lvl3") or {}).get("name") or ""
                        comp_str = get_formatted_field(hit, "compound") or hit.get("compound") or ""

                        if BROKER_CODE_PATTERN.search(desc_str) or BROKER_CODE_PATTERN.search(title_str):
                            checked_ids.add(pub_ad_id)
                            continue

                        check_loc_text = f"{title_str} {loc_str} {comp_str}".lower()
                        if any(bad in check_loc_text for bad in STRICT_FORBIDDEN_LOCATIONS):
                            checked_ids.add(pub_ad_id)
                            continue

                        seller_id = str(hit.get("userExternalID") or "").strip()
                        seller_name = ((hit.get("contactInfo") or {}).get("name") or "").strip()
                        if is_broker_seller_name(seller_name):
                            checked_ids.add(pub_ad_id)
                            continue

                        seen_hit_ids.add(pub_ad_id)
                        candidate_hits.append({
                            "ad_id": pub_ad_id,
                            "url": clean_u,
                            "listing_type": listing_type,
                            "title": title_str,
                            "description": desc_str,
                            "price_raw": hit.get("extraFields", {}).get("price") or get_formatted_field(hit, "price"),
                            "area_raw": get_formatted_field(hit, "ft"),
                            "beds_raw": get_formatted_field(hit, "rooms"),
                            "baths_raw": get_formatted_field(hit, "bathrooms"),
                            "prop_type": get_formatted_field(hit, "type") or "",
                            "seller_id": seller_id,
                            "seller_name": seller_name,
                            "tier": tier,
                            "age_label": age_label,
                        })
                else:
                    dom_links = extract_dom_ad_links(html)
                    print(f"[{listing_type.upper()}] Page {page} (DOM fallback): {len(dom_links)} links")
                    for c in dom_links:
                        clean_u, pub_ad_id = normalize_dubizzle_url(c["href"])
                        if not clean_u or not pub_ad_id or pub_ad_id in kept_ads or pub_ad_id in checked_ids or pub_ad_id in seen_hit_ids:
                            continue
                        ctx = c.get("context", "")
                        if any(bad in ctx for bad in STRICT_FORBIDDEN_LOCATIONS) or is_broker_seller_name(ctx):
                            continue
                        seen_hit_ids.add(pub_ad_id)
                        candidate_hits.append({
                            "ad_id": pub_ad_id,
                            "url": clean_u,
                            "listing_type": listing_type,
                            "title": c.get("slug_text", ""),
                            "description": "",
                            "price_raw": None,
                            "area_raw": None,
                            "beds_raw": None,
                            "baths_raw": None,
                            "prop_type": "",
                            "seller_id": "",
                            "seller_name": "",
                            "tier": 2,
                            "age_label": "منذ ساعات",
                        })

    seller_batch_counts = {}
    for ch in candidate_hits:
        sid = ch["seller_id"]
        if sid:
            seller_batch_counts[sid] = seller_batch_counts.get(sid, 0) + 1

    print(f"Total non-agency fresh candidates to verify: {len(candidate_hits)}")

    inspected = 0
    stats = {}

    for ch in candidate_hits:
        if inspected >= 60:
            break
        ad_id = ch["ad_id"]
        sid = ch["seller_id"]

        if sid and seller_batch_counts.get(sid, 0) >= BROKER_ACTIVE_ADS_THRESHOLD:
            checked_ids.add(ad_id)
            stats["BATCH_BROKER"] = stats.get("BATCH_BROKER", 0) + 1
            continue

        inspected += 1
        cnt, seller_name = get_verified_seller_ads_count(
            client, sid, ch["url"], ch["seller_name"], sellers_cache
        )

        if cnt is None or cnt == 0:
            stats["NO_CNT"] = stats.get("NO_CNT", 0) + 1
            continue

        checked_ids.add(ad_id)
        print(f"[{inspected}] Verified Ad {ad_id} ({ch['age_label']}): Active_Ads={cnt} | Seller={seller_name}")

        if cnt not in (1, 2, 3, 4):
            stats[f"BROKER_{cnt}_ADS"] = stats.get(f"BROKER_{cnt}_ADS", 0) + 1
            continue

        title_clean = clean_markdown_to_text(ch["title"])
        desc_clean = clean_markdown_to_text(ch["description"])

        if not desc_clean or not ch["price_raw"]:
            md = client.get_jina_markdown(ch["url"], timeout_sec=22)
            if md:
                if "لم يعد هذا الإعلان متاح" in md or "هذا الإعلان غير متاح" in md:
                    stats["EXPIRED"] = stats.get("EXPIRED", 0) + 1
                    continue
                if "الوصف" in md:
                    after_d = md.split("الوصف")[-1]
                    for sw in ["تم النشر بواسطة", "الموقع", "معرّف الإعلان", "معرف الإعلان", "رقم الإعلان"]:
                        if sw in after_d:
                            after_d = after_d.split(sw)[0]
                    desc_clean = clean_markdown_to_text(after_d)
                m_h1 = re.search(r"^#\s+(.+)$", md, flags=re.M)
                if m_h1:
                    title_clean = clean_markdown_to_text(m_h1.group(1))

        if any(bad in f"{title_clean} {desc_clean}".lower() for bad in ["مصر الجديدة", "مدينة نصر", "مدينه نصر", "زهراء مدينة نصر", "الكوربة", "أرض الجولف", "روكسي", "الماظة", "شيراتون", "النزهة", "عباس العقاد", "مكرم عبيد"]):
            stats["EXCLUDED_AREA"] = stats.get("EXCLUDED_AREA", 0) + 1
            continue

        price_num = _extract_number(ch["price_raw"]) or 0
        if price_num == 0:
            for pm in re.finditer(r"(\d[\d,]{3,11})\s*(?:ج\.م|جنيه|جم|EGP)", f"{title_clean} {desc_clean}"):
                val = int(pm.group(1).replace(",", ""))
                if val >= 2000:
                    price_num = val
                    break
        price_text = f"{price_num:,} ج.م" if price_num > 0 else "مدرج بالإعلان"

        area_num = _extract_number(ch["area_raw"])
        area = f"{area_num} م²" if area_num else "مدرج بالإعلان"

        beds_num = _extract_number(ch["beds_raw"])
        beds = f"{beds_num} غرف" if beds_num and 1 <= beds_num <= 12 else ""

        baths_num = _extract_number(ch["baths_raw"])
        baths = f"{baths_num} حمام" if baths_num and 1 <= baths_num <= 10 else ""

        deal, category, subtype = classify_deal_category_subtype(
            ch["listing_type"], ch["prop_type"], ch["url"], title_clean, desc_clean, price_num
        )

        kept_ads[ad_id] = {
            "ad_id": ad_id,
            "title": title_clean[:130] if title_clean else "وحدة بالقاهرة الجديدة",
            "price_num": price_num,
            "price_text": price_text,
            "area": area,
            "beds": beds,
            "baths": baths,
            "deal": deal,
            "category": category,
            "subtype": subtype,
            "seller_name": seller_name,
            "seller_ads_count": cnt,
            "fresh_tier": ch["tier"],
            "description": f"[{ch['age_label']}] " + (desc_clean[:680] if desc_clean else title_clean),
            "url": ch["url"],
            "today_verified": True,
            "verified_v12": True,
            "scraped_at": now_cairo.isoformat(),
        }
        stats[f"ADDED_OWNER_{cnt}"] = stats.get(f"ADDED_OWNER_{cnt}", 0) + 1
        print(f"   >>> ADDED OWNER: {ad_id} | {category} ({subtype}) | {price_text} | {seller_name} (Ads: {cnt})")

    print(f"Inspection Summary: {stats}")

    final_ads = list(kept_ads.values())
    final_ads.sort(key=lambda x: (x.get("fresh_tier", 2), x.get("ad_id", 0)), reverse=True)

    out = {
        "last_scrape": now_cairo.strftime("%Y/%m/%d, %I:%M %p"),
        "total_ads": len(final_ads),
        "checked_ids_v1": sorted(list(checked_ids))[-5000:],
        "sellers_cache_v1": sellers_cache,
        "ads": final_ads,
    }
    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(final_ads)} verified fresh New Cairo owner ads.")


if __name__ == "__main__":
    scrape_all()
