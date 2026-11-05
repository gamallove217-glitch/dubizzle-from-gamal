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
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/q-%D8%A8%D8%AF%D9%88%D9%86-%D9%88%D8%B3%D9%8A%D8%B7/",
        "https://www.dubizzle.com.eg/en/properties/apartments-duplex-for-sale/5th-settlement/",
        "https://www.dubizzle.com.eg/en/properties/villas-for-sale/5th-settlement/",
        "https://www.dubizzle.com.eg/en/properties/commercial-for-sale/5th-settlement/",
    ],
    "rent": [
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/q-%D9%85%D9%86-%D8%A7%D9%84%D9%85%D8%A7%D9%84%D9%83/",
        "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/q-%D8%A8%D8%AF%D9%88%D9%86-%D9%88%D8%B3%D9%8A%D8%B7/",
        "https://www.dubizzle.com.eg/en/properties/apartments-duplex-for-rent/5th-settlement/",
        "https://www.dubizzle.com.eg/en/properties/villas-for-rent/5th-settlement/",
        "https://www.dubizzle.com.eg/en/properties/commercial-for-rent/5th-settlement/",
    ],
}

MAX_PAGES_PER_CATEGORY = 2
MAX_HOURS_FRESHNESS = 30
BROKER_ACTIVE_ADS_THRESHOLD = 5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
}

BROKER_CODE_PATTERN = re.compile(
    r"(?:\bكود\s*[:\-]?\s*[A-Za-z0-9\u0660-\u0669]{2,10}\b|\bcode\s*[:\-]?\s*[A-Za-z0-9]{2,10}\b)",
    re.IGNORECASE,
)

STRICT_FORBIDDEN_EVERYWHERE = [
    "مصر الجديدة", "مصر الجديده", "heliopolis", "مدينة نصر", "مدينه نصر", "nasr city",
    "زهراء مدينة نصر", "الكوربة", "أرض الجولف", "ارض الجولف", "روكسي", "الماظة",
    "ألماظة", "شيراتون", "النزهة", "عباس العقاد", "مكرم عبيد", "مصطفى النحاس",
    "جاردينيا سيتي", "جسر السويس", "عين شمس", "حدائق القبة", "شبرا", "حلوان",
    "المعادي", "الشيخ زايد", "6 أكتوبر", "المقطم"
]

STRICT_FORBIDDEN_LOCATIONS = STRICT_FORBIDDEN_EVERYWHERE + [
    "تاج سيتي", "taj city", "الرحاب", "مدينة الرحاب", "rehab city",
    "al rehab", "مدينتي", "مدينتى", "madinaty", "الشروق", "مدينة الشروق", "shorouk",
    "مدينة المستقبل", "المستقبل سيتي", "mostakbal", "future city", "بدر", "مدينة بدر",
    "العبور", "العاصمة الإدارية", "new capital"
]

STRICT_NEW_CAIRO_HEADER = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "القطامية", "القطاميه", "5th settlement",
    "new cairo", "1st settlement", "3rd settlement", "katameya"
]

BROKER_NAME_WORDS = [
    "verified badge", "real estate", "realestate", "properties", "property", "investment",
    "investments", "development", "developments", "group", "agency", "consultancy",
    "consulting", "broker", "brokers", "marketing", "hospitality", "capital", "avenue",
    "hills", "lounge", "hub", "insider", "coldwell", "remax", "houseology", "westfield",
    "conquer", "sadan", "retaj", "colombus", "aspire", "privilege", "signature",
    "imkan", "closer", "el rabeh", "green home", "home group", "4 c", "egy property",
    "gate real estate", "al hayah", "elnemr", "scouts", "falcon", "redefine",
    "elviro", "wall street", "deal", "prime location", "choice", "damas", "ebtkar",
    "home hub", "lotus flower", "black code", "diamant", "maqam", "mavista",
    "horizon", "brand real estate", "alofok", "new home", "fekra re", "almaz",
    "nch", "apex", "el nemr", "make money", "the landmark", "owner 59", "ghp",
    "backyard", "irtkaz", "strive", "landmax", "aqarpedia", "circle realestate",
    "estimate", "global stay", "views real estate", "egypt best", "roy real estate",
    "alfa development", "tawabek", "spade", "heritage", "platinum", "el shazly",
    "maak real estate", "tarek mamdouh", "mustafa ghanima", "ahmed essam ahmed",
    "للتسويق", "للاستثمار", "للتطوير", "للمقاولات", "للعقارات", "التسويق العقاري",
    "الاستثمار العقاري", "التطوير العقاري", "شركة موثقة", "الالمانية للتنمية",
    "وايت هوم", "بيتي للمقاولات", "النمر للتطوير", "ثقة العقارية", "شيلد للاسكان"
]

_AD_HREF_RE = re.compile(
    r"(?:https?://(?:www\.)?dubizzle\.com\.eg)?"
    r"(?P<path>/+(?:en/)?ad/[^\"'<>\s\)]+?ID\d+\.html)",
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

    def get_direct_html(self, url, timeout_sec=22):
        time.sleep(random.uniform(1.0, 1.8))
        for s in self.cffi_sessions:
            try:
                r = s.get(url, timeout=timeout_sec, allow_redirects=True)
                if r.status_code == 200 and len(r.text) > 1500 and "window.state" in r.text:
                    return r.text
            except Exception:
                pass
        return ""

    def get_jina_markdown(self, url, with_links=False, timeout_sec=26):
        j_url = "https://r.jina.ai/" + url
        j_headers = dict(HEADERS)
        if with_links:
            j_headers["X-With-Links-Summary"] = "true"
        for s in self.cffi_sessions + [self.req_sess]:
            try:
                r = s.get(j_url, headers=j_headers, timeout=timeout_sec)
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
    if ad_id < 208500000:
        return None, None
    p = urllib.parse.urlsplit(full_u)
    clean_path = urllib.parse.quote(p.path, safe="/-._~")
    return f"https://www.dubizzle.com.eg{clean_path}", ad_id


def clean_markdown_to_text(md):
    txt = (md or "").translate(AR_DIGITS)
    txt = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"\bImage\s*\d+:?\b", " ", txt, flags=re.I)
    txt = re.sub(r"[*#_`~>|]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def get_card_tier_and_label(card_text):
    t = card_text.translate(AR_DIGITS)
    if re.search(r"منذ\s*(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة)", t) or re.search(r"\b(week|weeks|month|months|year)\s*ago\b", t, re.I):
        return 0, "OLD"
    m_d = re.search(r"منذ\s*(\d+)\s*(?:أيام|ايام|يوم)", t)
    if m_d:
        d = int(m_d.group(1))
        if d >= 2:
            return 0, m_d.group(0)
        return 2, m_d.group(0)
    m_d_en = re.search(r"\b(\d+)\s*days?\s*ago\b", t, re.I)
    if m_d_en:
        d = int(m_d_en.group(1))
        if d >= 2:
            return 0, f"منذ {d} أيام"
        return 2, "منذ 1 يوم"
    m_h = re.search(r"منذ\s*(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)", t)
    if m_h:
        return 3, m_h.group(0)
    m_h_en = re.search(r"\b(\d+)\s*(mins?|minutes?|hours?)\s*ago\b", t, re.I)
    if m_h_en:
        unit = "دقائق" if "min" in m_h_en.group(2).lower() else "ساعات"
        return 3, f"منذ {m_h_en.group(1)} {unit}"
    return 1, "منذ ساعات"


def extract_cards_from_jina_page(raw_md):
    results = {}
    if not raw_md:
        return results

    body_part = raw_md.split("Links/Buttons:")[0] if "Links/Buttons:" in raw_md else raw_md
    links_part = raw_md.split("Links/Buttons:")[1] if "Links/Buttons:" in raw_md else ""

    last_end = 0
    for m in re.finditer(r"(?:https?://(?:www\.)?dubizzle\.com\.eg)?/+(?:en/)?ad/[^\s\"'<>)\]]+?-ID(\d+)\.html", body_part):
        clean_u, ad_id = normalize_dubizzle_url(m.group(0))
        if not clean_u or not ad_id:
            continue
        bullet_pos = body_part.rfind("* [", max(last_end, m.start() - 650), m.start())
        start_pos = bullet_pos if bullet_pos != -1 else max(last_end, m.start() - 350)
        close_paren = body_part.find(")", m.end(), min(len(body_part), m.end() + 220))
        end_pos = close_paren + 1 if close_paren != -1 else min(len(body_part), m.end() + 120)
        last_end = end_pos

        card_raw = body_part[start_pos:end_pos]
        if "-200x150." in card_raw or "Verified Badge" in card_raw:
            continue
        card_snip = clean_markdown_to_text(card_raw)
        tier, age_lbl = get_card_tier_and_label(card_snip)
        if tier == 0:
            continue
        if any(bad in card_snip.lower() for bad in STRICT_FORBIDDEN_LOCATIONS) or is_broker_seller_name(card_snip):
            continue
        results[ad_id] = (clean_u, card_snip, tier, age_lbl)

    if links_part:
        for m in re.finditer(r"\[([^\]]+)\]\((https?://(?:www\.)?dubizzle\.com\.eg/+(?:en/)?ad/[^\s\"'<>)\]]+?-ID(\d+)\.html)\)", links_part):
            link_title = m.group(1).strip()
            clean_u, ad_id = normalize_dubizzle_url(m.group(2))
            if not clean_u or not ad_id or ad_id in results:
                continue

            search_key = link_title[:40].strip()
            pos = body_part.find(search_key) if len(search_key) >= 8 else -1
            if pos != -1:
                c_start = max(0, pos - 260)
                c_end = min(len(body_part), pos + len(link_title) + 260)
                card_raw = body_part[c_start:c_end]
            else:
                card_raw = link_title

            if "-200x150." in card_raw or "Verified Badge" in card_raw:
                continue
            card_snip = clean_markdown_to_text(card_raw)
            tier, age_lbl = get_card_tier_and_label(card_snip)
            if tier == 0:
                continue
            if any(bad in card_snip.lower() for bad in STRICT_FORBIDDEN_LOCATIONS) or is_broker_seller_name(card_snip):
                continue
            results[ad_id] = (clean_u, link_title + " " + card_snip, tier, age_lbl)

    return results


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


def trim_before_footer_markers(text_src):
    if not text_src:
        return ""
    for marker in ["الإبلاغ عن هذا الإعلان", "قم بالإبلاغ عن هذا الإعلان", "سلامتك تهمنا"]:
        if marker in text_src:
            text_src = text_src.split(marker)[0]
    return text_src


def extract_cnt_and_seller_from_text(text_src):
    if not text_src:
        return None, ""
    has_agency_carousel = "شاهد المزيد من إعلانات" in text_src
    ad_sec = trim_before_footer_markers(text_src)
    clean_all = clean_markdown_to_text(_strip_html(ad_sec))

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
    elif any(w in t_and_d for w in ["غرفة للإيجار", "غرفه للايجار", "غرفة مفروشة", "room for rent"]):
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

    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            sellers_cache = data.get("sellers_cache_v1", {})
            checked_ids |= (
                set(data.get("checked_ids_v1", []))
                | set(data.get("checked_ids_today_v11", []))
                | set(data.get("checked_ids_today_v10", []))
            )
            for a in data.get("ads", []):
                aid = int(a.get("ad_id", 0))
                if not aid or aid in checked_ids:
                    continue
                if a.get("verified_v11") is True or a.get("verified_v12") is True:
                    kept[aid] = a
    except Exception:
        pass

    checked_ids.discard(208757422)
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


def inspect_candidate(client, ch, sellers_cache):
    ad_id = ch["ad_id"]
    url = ch["url"]
    sid = ch.get("seller_id", "")
    seller_name = ch.get("seller_name", "")

    if is_broker_seller_name(seller_name):
        return None, True, "BROKER_NAME", {}

    cnt = None
    if sid and sid in sellers_cache:
        try:
            cnt = int(sellers_cache[sid].get("active_ads_count", 0))
            seller_name = sellers_cache[sid].get("seller_name") or seller_name
        except Exception:
            cnt = None

    if cnt is None and sid:
        prof_html = client.get_direct_html(f"{BASE_URL}/en/profile/{sid}/", timeout_sec=18)
        if prof_html:
            st = extract_window_state(prof_html)
            if st:
                cnt = _find_seller_profile_in_state(st, sid)

    raw_md = client.get_jina_markdown(url, with_links=False, timeout_sec=25)
    fallback_md = ""
    related_cards = {}

    if raw_md:
        if "لم يعد هذا الإعلان متاح" in raw_md or "هذا الإعلان لم يعد متاح" in raw_md or "هذا الإعلان غير متاح" in raw_md:
            return None, True, "EXPIRED", {}
        if "شاهد المزيد من إعلانات" not in raw_md:
            related_cards.update(extract_cards_from_jina_page(raw_md))
        c1, s1 = extract_cnt_and_seller_from_text(raw_md)
        if c1 is not None and (cnt is None or c1 > cnt):
            cnt = c1
        if not seller_name and s1:
            seller_name = s1

    if cnt is None or cnt <= 4:
        fallback_md = client.get_jina_markdown(url + "?abs=1", with_links=False, timeout_sec=25)
        if fallback_md:
            if "لم يعد هذا الإعلان متاح" in fallback_md or "هذا الإعلان لم يعد متاح" in fallback_md:
                return None, True, "EXPIRED", {}
            if "شاهد المزيد من إعلانات" not in fallback_md:
                related_cards.update(extract_cards_from_jina_page(fallback_md))
            c2, s2 = extract_cnt_and_seller_from_text(fallback_md)
            if c2 is not None and (cnt is None or c2 > cnt):
                cnt = c2
            if not seller_name and s2:
                seller_name = s2

    combined_md = (raw_md or "") + "\n" + (fallback_md or "")
    ad_sec = trim_before_footer_markers(combined_md)
    before_desc = ad_sec.split("الوصف")[0] if "الوصف" in ad_sec else ad_sec[:2200]
    page_tier, page_age = get_card_tier_and_label(clean_markdown_to_text(before_desc))

    if page_tier == 0:
        print(f"Skipped Old Ad {ad_id}: Age={page_age}")
        return None, True, "OLD_AD", related_cards

    tier = page_tier if page_tier in (2, 3) else ch.get("tier", 2)
    age_label = page_age if page_tier in (2, 3) else ch.get("age_label", "منذ ساعات")

    if not cnt:
        return None, False, "NO_CNT", related_cards

    seller_name = seller_name or "مالك"
    if sid:
        sellers_cache[sid] = {
            "seller_id": sid,
            "seller_name": seller_name,
            "active_ads_count": cnt,
            "classification": "broker" if cnt >= BROKER_ACTIVE_ADS_THRESHOLD else "owner",
        }

    print(f"Checked Fresh Ad {ad_id} ({age_label}): Active_Ads={cnt} | Seller={seller_name}")

    if cnt not in (1, 2, 3, 4):
        return None, True, f"BROKER_{cnt}_ADS", {}

    title_clean = clean_markdown_to_text(ch.get("title") or "")
    desc_clean = clean_markdown_to_text(ch.get("description") or "")

    for src in [trim_before_footer_markers(raw_md), trim_before_footer_markers(fallback_md)]:
        if src and "الوصف" in src:
            after_d = src.split("الوصف")[-1]
            for sw in ["تم النشر بواسطة", "الموقع", "معرّف الإعلان", "معرف الإعلان", "رقم الإعلان", "اقرأ المزيد في التطبيق", "الكماليات"]:
                if sw in after_d:
                    after_d = after_d.split(sw)[0]
            cand_d = clean_markdown_to_text(after_d)
            if len(cand_d) > len(desc_clean):
                desc_clean = cand_d

    if not title_clean or len(title_clean) < 10:
        m_h1 = re.search(r"^#\s+(.+)$", ad_sec, flags=re.M)
        if m_h1:
            title_clean = clean_markdown_to_text(m_h1.group(1))
        if not title_clean:
            m_t = re.search(r"Title:\s*(.+?)(?:\n|\|)", combined_md)
            if m_t:
                title_clean = clean_markdown_to_text(m_t.group(1))

    if BROKER_CODE_PATTERN.search(desc_clean) or BROKER_CODE_PATTERN.search(title_clean):
        return None, True, "BROKER_CODE", {}

    before_desc_clean = clean_markdown_to_text(before_desc)
    loc_box_clean = clean_markdown_to_text(ad_sec.split("الموقع")[-1][:220]) if "الموقع" in ad_sec else ""
    official_loc_and_title = f"{title_clean} {before_desc_clean} {loc_box_clean}".lower()
    entire_ad_text = f"{official_loc_and_title} {desc_clean}".lower()

    for bad_city in STRICT_FORBIDDEN_EVERYWHERE:
        if bad_city in entire_ad_text:
            print(f"Skipped Excluded Area ({bad_city}) in Ad {ad_id}")
            return None, True, "EXCLUDED_AREA", {}

    for bad_sat in STRICT_FORBIDDEN_LOCATIONS:
        if bad_sat in official_loc_and_title:
            print(f"Skipped Excluded Location ({bad_sat}) in Ad {ad_id}")
            return None, True, "EXCLUDED_AREA", {}

    if combined_md and not any(w in official_loc_and_title for w in STRICT_NEW_CAIRO_HEADER):
        print(f"Skipped Non-New-Cairo Location in Ad {ad_id}")
        return None, True, "NOT_NEW_CAIRO", {}

    top_sec = clean_markdown_to_text(ad_sec)
    all_price_text = f"{top_sec} {desc_clean}"
    price_num = _extract_number(ch.get("price_raw")) or 0
    if price_num == 0:
        for pm in re.finditer(r"(\d[\d,]{3,11})\s*(?:ج\.م|جنيه|جم|EGP)", all_price_text):
            val = int(pm.group(1).replace(",", ""))
            if val >= 2000:
                price_num = val
                break
    if price_num == 0:
        m_mil = re.search(r"(\d+(?:\.\d+)?)\s*مليون", all_price_text)
        if m_mil:
            price_num = int(float(m_mil.group(1)) * 1000000)

    price_text = f"{price_num:,} ج.م" if price_num > 0 else "مدرج بالإعلان"

    area_num = _extract_number(ch.get("area_raw"))
    if not area_num:
        m_area = re.search(r"(?:المساحة|مساحة|المساحه)[^\d]{0,12}(\d{2,4})", all_price_text)
        if not m_area:
            m_area = re.search(r"\b(\d{2,4})\s*(?:متر|م2|م²|sqm)\b", all_price_text, re.I)
        if m_area:
            area_num = int(m_area.group(1))
    area = f"{area_num} م²" if area_num else "مدرج بالإعلان"

    beds_num = _extract_number(ch.get("beds_raw"))
    if not beds_num:
        m_beds = re.search(r"(?:غرف نوم|غرف|غرفة)[^\d]{0,8}(\d{1,2})", all_price_text)
        if m_beds:
            beds_num = int(m_beds.group(1))
    beds = f"{beds_num} غرف" if beds_num and 1 <= beds_num <= 12 else ""

    baths_num = _extract_number(ch.get("baths_raw"))
    if not baths_num:
        m_baths = re.search(r"(?:الحمامات|حمامات|حمام)[^\d]{0,8}(\d{1,2})", all_price_text)
        if m_baths:
            baths_num = int(m_baths.group(1))
    baths = f"{baths_num} حمام" if baths_num and 1 <= baths_num <= 10 else ""

    deal, category, subtype = classify_deal_category_subtype(
        ch.get("listing_type", "sale"), ch.get("prop_type", ""), url, title_clean, desc_clean, price_num
    )

    return {
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
        "fresh_tier": tier,
        "description": f"[{age_label}] " + (desc_clean[:680] if desc_clean else title_clean),
        "url": url,
        "today_verified": True,
        "verified_v12": True,
        "scraped_at": datetime.now(CAIRO_TZ).isoformat(),
    }, True, f"ADDED_OWNER_{cnt}", related_cards


def candidate_priority(ch):
    uid = ch["ad_id"]
    tier = ch.get("tier", 2)
    txt = f"{ch.get('title', '')} {urllib.parse.unquote(ch.get('url', ''))}"
    score = tier * 30000000000
    if any(w in txt for w in ["من المالك", "بدون وسيط", "المالك مباشر", "من-المالك", "بدون-وسيط", "owner"]):
        score += 10000000000
    if 209340000 <= uid < 300000000:
        score += 5000000000
    score += uid
    return score


def scrape_all():
    kept_ads, sellers_cache, checked_ids = load_existing()
    client = AntiBlockClient()
    now_utc = datetime.now(timezone.utc)
    now_cairo = datetime.now(CAIRO_TZ)

    print(f"Kept existing owners: {len(kept_ads)} | Cached sellers: {len(sellers_cache)}")

    candidate_map = {}

    if 208757422 not in kept_ads and 208757422 not in checked_ids:
        candidate_map[208757422] = {
            "ad_id": 208757422,
            "url": "https://www.dubizzle.com.eg/ad/%D8%B4%D9%82%D8%A9-%D8%A3%D8%B1%D8%B6%D9%8A-180%D9%85-%D9%84%D9%84%D8%A8%D9%8A%D8%B9-%D8%A8%D8%A7%D9%84%D8%AA%D8%AC%D9%85%D8%B9-%D8%A7%D9%84%D8%AE%D8%A7%D9%85%D8%B3-%D8%A7%D9%84%D8%AD%D9%8A-%D8%A7%D9%84%D8%AB%D8%A7%D9%84%D8%AB-%D9%85%D9%88%D9%82%D8%B9-%D9%85%D9%85%D9%8A%D8%B2-ID208757422.html",
            "listing_type": "sale",
            "title": "شقة أرضي 180م للبيع بالتجمع الخامس الحي الثالث",
            "description": "",
            "price_raw": None,
            "area_raw": None,
            "beds_raw": None,
            "baths_raw": None,
            "prop_type": "",
            "seller_id": "",
            "seller_name": "",
            "tier": 3,
            "age_label": "منذ ساعات",
        }

    for listing_type, urls in SEARCH_URLS.items():
        for base_url in urls:
            for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
                sep = "&" if "?" in base_url else "?"
                page_url = base_url if page == 1 else f"{base_url}{sep}page={page}"

                html = client.get_direct_html(page_url, timeout_sec=18)
                state = extract_window_state(html) if html else None

                if state:
                    content = state.get("algolia", {}).get("content", {})
                    hits = content.get("hits", [])
                    if not hits:
                        break
                    resolved_urls = resolve_dom_ad_urls(hits, html)
                    print(f"[{listing_type.upper()}] Direct window.state Page {page}: {len(hits)} hits ({len(resolved_urls)} URLs)")

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
                        if not clean_u or not pub_ad_id or pub_ad_id in kept_ads or pub_ad_id in checked_ids:
                            continue

                        title_str = hit.get("title_l1") or hit.get("title") or ""
                        desc_str = hit.get("description_l1") or hit.get("description") or ""
                        loc_str = (hit.get("location.lvl3") or {}).get("name_l1") or (hit.get("location.lvl3") or {}).get("name") or ""
                        comp_str = get_formatted_field(hit, "compound") or hit.get("compound") or ""

                        if BROKER_CODE_PATTERN.search(desc_str) or BROKER_CODE_PATTERN.search(title_str):
                            checked_ids.add(pub_ad_id)
                            continue
                        if any(bad in f"{title_str} {loc_str} {comp_str}".lower() for bad in STRICT_FORBIDDEN_LOCATIONS):
                            checked_ids.add(pub_ad_id)
                            continue

                        seller_id = str(hit.get("userExternalID") or "").strip()
                        seller_name = ((hit.get("contactInfo") or {}).get("name") or "").strip()
                        if is_broker_seller_name(seller_name):
                            checked_ids.add(pub_ad_id)
                            continue

                        candidate_map[pub_ad_id] = {
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
                        }
                else:
                    raw_md = client.get_jina_markdown(page_url, with_links=True, timeout_sec=26)
                    extracted = extract_cards_from_jina_page(raw_md)
                    print(f"[{listing_type.upper()}] Proxy Page {page}: extracted {len(extracted)} fresh non-broker cards")
                    for pub_ad_id, (clean_u, card_snip, tier, age_lbl) in extracted.items():
                        if pub_ad_id in kept_ads or pub_ad_id in checked_ids:
                            continue
                        if pub_ad_id not in candidate_map or tier > candidate_map[pub_ad_id]["tier"]:
                            candidate_map[pub_ad_id] = {
                                "ad_id": pub_ad_id,
                                "url": clean_u,
                                "listing_type": listing_type,
                                "title": card_snip[:120],
                                "description": "",
                                "price_raw": None,
                                "area_raw": None,
                                "beds_raw": None,
                                "baths_raw": None,
                                "prop_type": "",
                                "seller_id": "",
                                "seller_name": "",
                                "tier": tier,
                                "age_label": age_lbl,
                            }

    for a in list(kept_ads.values()):
        try:
            seed_md = client.get_jina_markdown(a["url"], with_links=False, timeout_sec=22)
            for rid, (ru, rsnip, rtier, rage) in extract_cards_from_jina_page(seed_md).items():
                if rid not in kept_ads and rid not in checked_ids and rid not in candidate_map:
                    candidate_map[rid] = {
                        "ad_id": rid,
                        "url": ru,
                        "listing_type": "rent" if a.get("deal") == "إيجار" else "sale",
                        "title": rsnip[:120],
                        "description": "",
                        "price_raw": None,
                        "area_raw": None,
                        "beds_raw": None,
                        "baths_raw": None,
                        "prop_type": "",
                        "seller_id": "",
                        "seller_name": "",
                        "tier": rtier,
                        "age_label": rage,
                    }
        except Exception:
            pass

    queue = sorted(candidate_map.values(), key=candidate_priority, reverse=True)
    queued_ids = {c["ad_id"] for c in queue}

    print(f"Total fresh non-agency candidates queued: {len(queue)}")

    inspected = 0
    stats = {}

    while queue and inspected < 60:
        ch = queue.pop(0)
        ad_id = ch["ad_id"]
        if ad_id in kept_ads or ad_id in checked_ids:
            continue

        inspected += 1
        try:
            item, mark_checked, reason, new_related = inspect_candidate(client, ch, sellers_cache)
            stats[reason] = stats.get(reason, 0) + 1
            if mark_checked:
                checked_ids.add(ad_id)
            if item:
                kept_ads[ad_id] = item
                print(
                    f"[{inspected}] >>> ADDED OWNER: {ad_id} | {item['category']} ({item['subtype']}) | "
                    f"{item['price_text']} | {item['seller_name']} (Active Ads: {item['seller_ads_count']})"
                )
            added_q = False
            for rid, (ru, rsnip, rtier, rage) in new_related.items():
                if rid not in kept_ads and rid not in checked_ids and rid not in queued_ids:
                    queue.append({
                        "ad_id": rid,
                        "url": ru,
                        "listing_type": ch.get("listing_type", "sale"),
                        "title": rsnip[:120],
                        "description": "",
                        "price_raw": None,
                        "area_raw": None,
                        "beds_raw": None,
                        "baths_raw": None,
                        "prop_type": "",
                        "seller_id": "",
                        "seller_name": "",
                        "tier": rtier,
                        "age_label": rage,
                    })
                    queued_ids.add(rid)
                    added_q = True
            if added_q:
                queue.sort(key=candidate_priority, reverse=True)
        except Exception as e:
            print(f"[{inspected}] Error {ad_id}: {e}")

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
