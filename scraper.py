import json
import time
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

API_KEY = "1fbcb4ca0bad271b0780c0a848e8c05b"
SCHEMA_VERSION = 4
MIN_FRESH_AD_ID = 204800000
SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

LIVE_CATEGORY_URLS = [
    {"url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/", "deal": "إيجار", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/", "deal": "بيع", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/rooms-for-rent/new-cairo/", "deal": "إيجار", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/", "deal": "إيجار", "category": "فيلا"},
    {"url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/", "deal": "بيع", "category": "فيلا"},
    {"url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/", "deal": "إيجار", "category": "تجاري وإداري"},
    {"url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/", "deal": "بيع", "category": "تجاري وإداري"}
]

SEARCH_QUERIES = [
    {"q": 'site:dubizzle.com.eg/ad/ ("ID2049" OR "ID205") ("التجمع" OR "القاهرة الجديدة" OR "الرحاب" OR "مدينتي") ("للايجار" OR "للإيجار")', "deal": "إيجار", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ ("ID2049" OR "ID205") ("التجمع" OR "القاهرة الجديدة" OR "الرحاب" OR "مدينتي") ("للبيع")', "deal": "بيع", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ ("ID2049" OR "ID205") ("التجمع" OR "القاهرة الجديدة") ("فيلا" OR "تاون هاوس" OR "توين هاوس")', "deal": "بيع", "category": "فيلا"},
    {"q": 'site:dubizzle.com.eg/ad/ ("ID2049" OR "ID205") ("التجمع" OR "القاهرة الجديدة") ("مكتب" OR "محل" OR "اداري" OR "إداري" OR "تجاري" OR "عيادة")', "deal": "إيجار", "category": "تجاري وإداري"},
    {"q": 'site:dubizzle.com.eg/en/ad/ ("ID2049" OR "ID205") "New Cairo" ("Rent" OR "Sale")', "deal": "إيجار", "category": "شقق"}
]

DELETED_VISIBLE_PHRASES = [
    "لم يتم العثور على تطابقات",
    "قد تم بيعه أو إزالته",
    "تم بيعه أو إزالته",
    "we couldn't find any matches",
    "no longer available"
]

def detect_category_and_subtype(title, description, default_cat):
    text = (title + " " + description).lower()
    if any(w in text for w in ["مكتب", "محل", "عيادة", "عياده", "إداري", "اداري", "تجاري", "مول", "مقر", "office", "clinic", "retail", "commercial"]):
        return "تجاري وإداري", "تجاري وإداري"
    if any(w in text for w in ["فيلا", "تاون هاوس", "توين هاوس", "ستاند الون", "villa", "townhouse", "twinhouse", "standalone"]):
        return "فيلا", "فيلا"
    if any(w in text for w in ["بنتهاوس", "بنت هاوس", "penthouse"]):
        return "شقق", "بنتهاوس"
    if any(w in text for w in ["دوبلكس", "دوبليكس", "duplex"]):
        return "شقق", "دوبلكس"
    if any(w in text for w in ["استوديو", "ستوديو", "studio"]):
        return "شقق", "استوديو"
    if any(w in text for w in ["روف", "رووف", "roof"]):
        return "شقق", "روف"
    if any(w in text for w in ["غرفة", "غرفه", "room"]):
        return "شقق", "غرفة"
    return default_cat, ("شقة" if default_cat == "شقق" else default_cat)

def detect_deal(title, description, default_deal):
    text = (title + " " + description).lower()
    if any(w in text for w in ["للايجار", "للإيجار", "ايجار", "إيجار", "for rent", "monthly", "شهري"]):
        return "إيجار"
    if any(w in text for w in ["للبيع", "بيع", "for sale"]):
        return "بيع"
    return default_deal

def is_fresh_ad_url(ad_url):
    m = re.search(r"-ID(\d+)", ad_url, re.I)
    if m:
        try:
            return int(m.group(1)) >= MIN_FRESH_AD_ID
        except Exception:
            return True
    return True

def extract_specs(text):
    price_text = ""
    price_num = 0
    patterns = [
        r"([\d,]{4,12})\s*(?:ج\.م|جنيه|جنية|EGP)",
        r"(?:ج\.م|ج\.م\.|EGP)\s*([\d,]{4,12})"
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            raw_p = m.group(1).replace(",", "")
            if raw_p.isdigit() and int(raw_p) >= 1000:
                price_num = int(raw_p)
                price_text = f"{price_num:,} ج.م"
                break

    area_match = re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢)", text, re.I)
    beds_match = re.search(r"(\d)\s*(?:غرف|غرفة|نوم|beds|bed|bedrooms)", text, re.I)
    baths_match = re.search(r"(\d)\s*(?:حمام|حمامات|baths|bath|bathrooms)", text, re.I)

    area = area_match.group(1) + " م²" if area_match else "مدرج بالإعلان"
    beds = beds_match.group(1) + " غرف" if beds_match else ""
    baths = baths_match.group(1) + " حمام" if baths_match else ""
    return price_text, price_num, area, beds, baths

def fetch_html(url, timeout=40):
    for mode in [{"premium": "true"}, {"render": "true"}, {}]:
        try:
            params = {"api_key": API_KEY, "url": url}
            params.update(mode)
            res = requests.get("http://api.scraperapi.com", params=params, timeout=timeout)
            if res.status_code == 200 and len(res.text) > 1000:
                return res.text
            if res.status_code in [404, 410]:
                return "NOT_FOUND"
        except Exception:
            pass
    return ""

def get_user_ads_count(profile_url):
    if not profile_url:
        return 1
    html = fetch_html(profile_url, timeout=30)
    if not html or html == "NOT_FOUND":
        return 1
    soup = BeautifulSoup(html, "html.parser")
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    vis_text = soup.get_text(" ", strip=True)
    m = re.search(r"(\d+)\s*(?:إعلان|إعلانات|اعلان|Ads|ad|Showing)", vis_text, re.I)
    if m:
        return int(m.group(1))
    ad_links = {a["href"].split("?")[0] for a in soup.find_all("a", href=True) if "/ad/" in a["href"]}
    if ad_links:
        return len(ad_links)
    return 1

def find_card_container(a_tag):
    curr = a_tag
    for _ in range(6):
        if not curr or not curr.parent:
            break
        curr = curr.parent
        txt = curr.get_text(" ", strip=True)
        if ("ج.م" in txt or "EGP" in txt) and len(txt) < 1500:
            return curr
    return a_tag.parent or a_tag

def fetch_single_category(cat):
    html = fetch_html(cat["url"], timeout=45)
    if not html or html == "NOT_FOUND":
        return []
    soup = BeautifulSoup(html, "html.parser")
    for s in soup(["script", "style", "noscript"]):
        s.decompose()

    cards = soup.find_all("article")
    if not cards:
        cards = soup.find_all("li", {"aria-label": "Listing"})
    if not cards:
        ad_anchors = soup.find_all("a", href=re.compile(r"/ad/.*-ID\d+"))
        seen_c = set()
        cards = []
        for a in ad_anchors:
            c = find_card_container(a)
            if id(c) not in seen_c:
                seen_c.add(id(c))
                cards.append(c)

    items = []
    for card in cards:
        card_html = str(card)
        if "/companies/" in card_html or "/agencies/" in card_html:
            comp_urls = [a["href"] for a in card.find_all("a", href=True) if "/companies/" in a["href"] or "/agencies/" in a["href"]]
            items.append({"blocked_company": comp_urls})
            continue

        link_el = card.find("a", href=re.compile(r"/ad/")) if card.name != "a" else card
        if not link_el or not link_el.get("href"):
            continue

        href = link_el["href"].split("?")[0]
        ad_url = "https://www.dubizzle.com.eg" + href if href.startswith("/") else href
        if "/ad/" not in ad_url or not is_fresh_ad_url(ad_url):
            continue

        card_text = card.get_text(" | ", strip=True)
        if any(dp in card_text.lower() for dp in DELETED_VISIBLE_PHRASES):
            continue

        price_text, price_num, area, beds, baths = extract_specs(card_text)
        if price_num == 0:
            continue

        title = ""
        h2 = card.find(["h2", "h3"])
        if h2:
            title = h2.get_text(strip=True)
        if not title and link_el.get("title"):
            title = link_el["title"].strip()
        if len(title) < 5:
            parts = [p.strip() for p in card_text.split("|") if len(p.strip()) > 10 and "ج.م" not in p and "EGP" not in p]
            title = parts[0] if parts else "عقار بالقاهرة الجديدة"

        seller_name = "مالك"
        profile_url = ""
        for a in card.find_all("a", href=True):
            if "/profile/" in a["href"]:
                profile_url = "https://www.dubizzle.com.eg" + a["href"] if a["href"].startswith("/") else a["href"]
                seller_name = a.get_text(strip=True) or "مالك"
                break

        lines = [p.strip() for p in card_text.split("|") if len(p.strip()) > 2]
        clean_desc = "\n".join(lines)
        cat_name, subtype = detect_category_and_subtype(title, clean_desc, cat["category"])
        deal_name = detect_deal(title, clean_desc, cat["deal"])

        items.append({
            "title": title,
            "url": ad_url,
            "price_text": price_text,
            "price_num": price_num,
            "deal": deal_name,
            "category": cat_name,
            "subtype": subtype,
            "area": area,
            "beds": beds,
            "baths": baths,
            "description": clean_desc,
            "seller_name": seller_name,
            "seller_profile": profile_url
        })
    return items

def verify_live_ad_page(cand, blocked_users):
    ad_url = cand["url"]
    html = fetch_html(ad_url, timeout=35)
    if html == "NOT_FOUND":
        return None
    if not html:
        return cand if cand.get("price_num", 0) > 0 else None

    soup = BeautifulSoup(html, "html.parser")
    meta_desc = ""
    md = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
    if md and md.get("content"):
        meta_desc = md["content"].strip()

    for s in soup(["script", "style", "noscript"]):
        s.decompose()

    vis_text = soup.get_text(" | ", strip=True)
    if any(dp in vis_text.lower() for dp in DELETED_VISIBLE_PHRASES):
        return None

    for a in soup.find_all("a", href=True):
        if "/companies/" in a["href"] or "/agencies/" in a["href"]:
            blocked_users.add(a["href"])
            return None

    profile_url = cand.get("seller_profile", "")
    seller_name = cand.get("seller_name", "مالك")
    for a in soup.find_all("a", href=True):
        if "/profile/" in a["href"]:
            profile_url = "https://www.dubizzle.com.eg" + a["href"] if a["href"].startswith("/") else a["href"]
            seller_name = a.get_text(strip=True) or seller_name
            break

    if profile_url and profile_url in blocked_users:
        return None

    price_text, price_num, area, beds, baths = extract_specs(vis_text + " " + cand.get("title", "") + " " + cand.get("description", ""))
    if price_num == 0:
        price_num = cand.get("price_num", 0)
        price_text = cand.get("price_text", "")
    if price_num == 0:
        return None

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 and h1.get_text(strip=True) else cand["title"]

    desc_el = soup.find("div", {"aria-label": "Description"}) or soup.find("div", class_=re.compile(r"description", re.I))
    description = desc_el.get_text("\n", strip=True) if desc_el else (meta_desc or cand["description"])

    ads_count = 1
    if profile_url:
        ads_count = get_user_ads_count(profile_url)
        if ads_count > 7:
            blocked_users.add(profile_url)
            return None
        if ads_count > 4:
            return None

    cat_name, subtype = detect_category_and_subtype(title, description, cand["category"])
    deal_name = detect_deal(title, description, cand["deal"])

    return {
        "title": title,
        "url": ad_url,
        "price_text": price_text,
        "price_num": price_num,
        "deal": deal_name,
        "category": cat_name,
        "subtype": subtype,
        "area": area if area != "مدرج بالإعلان" else cand.get("area", "مدرج بالإعلان"),
        "beds": beds or cand.get("beds", ""),
        "baths": baths or cand.get("baths", ""),
        "description": description,
        "seller_name": seller_name,
        "seller_profile": profile_url or seller_name,
        "seller_ads_count": ads_count
    }

def fetch_google_query(item):
    found = []
    for tbs_val in ["qdr:d", "qdr:w"]:
        try:
            params = {
                "api_key": API_KEY,
                "query": item["q"],
                "hl": "ar",
                "gl": "eg",
                "tbs": tbs_val,
                "num": "20"
            }
            res = requests.get("https://api.scraperapi.com/structured/google/search", params=params, timeout=35)
            if res.status_code != 200:
                continue
            data = res.json()
            for r in data.get("organic_results", []):
                ad_url = r.get("link", "").split("?")[0]
                if "dubizzle.com.eg" not in ad_url or "/ad/" not in ad_url or not is_fresh_ad_url(ad_url):
                    continue
                title = re.sub(r"\s*[-|]\s*(?:دوبيزل|dubizzle).*$", "", r.get("title", ""), flags=re.I).strip()
                snippet = r.get("snippet", "").strip()
                if any(dp in (title + " " + snippet).lower() for dp in DELETED_VISIBLE_PHRASES):
                    continue
                price_text, price_num, area, beds, baths = extract_specs(title + " " + snippet)
                cat_name, subtype = detect_category_and_subtype(title, snippet, item["category"])
                deal_name = detect_deal(title, snippet, item["deal"])
                found.append({
                    "title": title or "عقار بالقاهرة الجديدة",
                    "url": ad_url,
                    "price_text": price_text,
                    "price_num": price_num,
                    "deal": deal_name,
                    "category": cat_name,
                    "subtype": subtype,
                    "area": area,
                    "beds": beds,
                    "baths": baths,
                    "description": snippet or title,
                    "seller_name": "مالك",
                    "seller_profile": ""
                })
        except Exception:
            pass
    return found

def scrape_all():
    now_ts = int(time.time())
    cairo_tz = timezone(timedelta(hours=2))
    now_cairo = datetime.now(cairo_tz).strftime("%Y/%m/%d، %I:%M %p")

    existing_ads = []
    blocked_users = set()

    if os.path.exists("ads.json"):
        try:
            with open("ads.json", "r", encoding="utf-8") as f:
                old_data = json.load(f)
                existing_ads = old_data.get("ads", [])
                blocked_users = set(old_data.get("blocked_users", []))
        except Exception:
            pass

    valid_existing_ads = []
    for ad in existing_ads:
        if ad.get("schema_version") != SCHEMA_VERSION:
            continue
        ad_ts = ad.get("scraped_timestamp", now_ts)
        seller_prof = ad.get("seller_profile", "")
        if ad.get("price_num", 0) > 0 and (now_ts - ad_ts) < SEVEN_DAYS_SECONDS and (not seller_prof or seller_prof not in blocked_users):
            valid_existing_ads.append(ad)

    seen_urls = {ad.get("url") for ad in valid_existing_ads if ad.get("url")}
    raw_candidates = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        cat_futures = [executor.submit(fetch_single_category, cat) for cat in LIVE_CATEGORY_URLS]
        for fut in as_completed(cat_futures):
            for item in fut.result():
                if "blocked_company" in item:
                    for cu in item["blocked_company"]:
                        blocked_users.add(cu)
                elif item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    raw_candidates.append(item)

        g_futures = [executor.submit(fetch_google_query, q) for q in SEARCH_QUERIES]
        for fut in as_completed(g_futures):
            for item in fut.result():
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    raw_candidates.append(item)

    print(f"Total fresh candidates to verify: {len(raw_candidates)}")

    verified_ads = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        v_futures = [executor.submit(verify_live_ad_page, cand, blocked_users) for cand in raw_candidates[:35]]
        for fut in as_completed(v_futures):
            res = fut.result()
            if res and res.get("price_num", 0) > 0:
                verified_ads.append(res)

    seller_counts = {}
    for ad in verified_ads + valid_existing_ads:
        sk = ad.get("seller_profile") or ad.get("seller_name") or ad.get("url")
        seller_counts[sk] = max(seller_counts.get(sk, 0), ad.get("seller_ads_count", 1))

    final_ads = []
    for ad in verified_ads:
        sk = ad.get("seller_profile") or ad.get("seller_name") or ad.get("url")
        count = max(seller_counts.get(sk, 1), ad.get("seller_ads_count", 1))
        if count > 7:
            blocked_users.add(sk)
            continue
        if sk in blocked_users or count < 1 or count > 4:
            continue
        ad["Schema"] = SCHEMA_VERSION
        ad["schema_version"] = SCHEMA_VERSION
        ad["location"] = "القاهرة الجديدة"
        ad["seller_ads_count"] = count
        ad["scraped_timestamp"] = now_ts
        ad["scraped_date"] = now_cairo
        final_ads.append(ad)

    final_ads.extend(valid_existing_ads)
    unique_owners = len({ad.get("seller_profile") or ad.get("url") for ad in final_ads})

    payload = {
        "last_scrape": now_cairo,
        "total": len(final_ads),
        "owners_count": unique_owners,
        "blocked_count": len(blocked_users),
        "blocked_users": list(blocked_users),
        "ads": final_ads
    }

    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Success: {len(final_ads)} active owner ads saved.")

if __name__ == "__main__":
    scrape_all()
