import json
import time
import re
import os
from urllib.parse import unquote, urlparse, parse_qs
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

API_KEY = "1fbcb4ca0bad271b0780c0a848e8c05b"

SEARCH_QUERIES = [
    {"q": 'site:dubizzle.com.eg/ad/ ("القاهرة الجديدة" OR "التجمع" OR "الرحاب" OR "مدينتي") ("للايجار" OR "للإيجار" OR "ايجار") ("شقة" OR "شقه" OR "دوبلكس" OR "بنتهاوس" OR "استوديو" OR "روف" OR "غرفة")', "deal": "إيجار", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ ("القاهرة الجديدة" OR "التجمع" OR "الرحاب" OR "مدينتي") ("للبيع" OR "بيع") ("شقة" OR "شقه" OR "دوبلكس" OR "بنتهاوس" OR "استوديو" OR "روف")', "deal": "بيع", "category": "شقق"},
    {"q": 'site:dubizzle.com.eg/ad/ ("القاهرة الجديدة" OR "التجمع") ("للايجار" OR "للإيجار") ("فيلا" OR "تاون هاوس" OR "توين هاوس" OR "villa")', "deal": "إيجار", "category": "فيلا"},
    {"q": 'site:dubizzle.com.eg/ad/ ("القاهرة الجديدة" OR "التجمع") ("للبيع") ("فيلا" OR "تاون هاوس" OR "توين هاوس" OR "villa")', "deal": "بيع", "category": "فيلا"},
    {"q": 'site:dubizzle.com.eg/ad/ ("القاهرة الجديدة" OR "التجمع") ("للايجار" OR "للإيجار") ("مكتب" OR "محل" OR "عيادة" OR "إداري" OR "اداري" OR "تجاري" OR "مقر")', "deal": "إيجار", "category": "تجاري وإداري"},
    {"q": 'site:dubizzle.com.eg/ad/ ("القاهرة الجديدة" OR "التجمع") ("للبيع") ("مكتب" OR "محل" OR "عيادة" OR "إداري" OR "اداري" OR "تجاري")', "deal": "بيع", "category": "تجاري وإداري"}
]

DIRECT_URLS = [
    {"url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/", "deal": "إيجار", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/", "deal": "بيع", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/", "deal": "إيجار", "category": "فيلا"},
    {"url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/", "deal": "بيع", "category": "فيلا"},
    {"url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/", "deal": "إيجار", "category": "تجاري وإداري"},
    {"url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/", "deal": "بيع", "category": "تجاري وإداري"}
]

BROKER_KEYWORDS = [
    "شركة", "للعقارات", "التسويق العقاري", "بروكر", "سمسار", "عمولة", "مكتب عقارات",
    "real estate", "property", "properties", "agency", "broker", "consultancy", "investment",
    "verified business", "featured business", "فرصة استثمارية من شركة"
]

SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

def detect_subtype(title, description, category):
    if category != "شقق":
        return category
    text = (title + " " + description).lower()
    if any(w in text for w in ["بنتهاوس", "بنت هاوس", "penthouse"]):
        return "بنتهاوس"
    if any(w in text for w in ["دوبلكس", "دوبليكس", "duplex"]):
        return "دوبلكس"
    if any(w in text for w in ["استوديو", "ستوديو", "studio"]):
        return "استوديو"
    if any(w in text for w in ["روف", "رووف", "roof"]):
        return "روف"
    if any(w in text for w in ["غرفة", "غرفه", "room"]):
        return "غرفة"
    return "شقة"

def is_broker_text(text):
    low = text.lower()
    return any(kw in low for kw in BROKER_KEYWORDS)

def extract_specs(text):
    price_text = "السعر داخل الإعلان"
    price_num = 0
    p_match = re.search(r"([\d,]{4,12})\s*(?:ج\.م|جنيه|EGP)", text, re.I) or re.search(r"(?:ج\.م|EGP)\s*([\d,]{4,12})", text, re.I)
    if p_match:
        raw_p = p_match.group(1).replace(",", "")
        if raw_p.isdigit():
            price_num = int(raw_p)
            price_text = f"{price_num:,} ج.م"

    area_match = re.search(r"(\d{2,4})\s*(?:م²|متر|sqm|m²|م٢|م\b)", text, re.I)
    beds_match = re.search(r"(\d)\s*(?:غرف|غرفة|نوم|beds|bed)", text, re.I)
    baths_match = re.search(r"(\d)\s*(?:حمام|حمامات|baths|bath)", text, re.I)

    area = area_match.group(1) + " م²" if area_match else "مدرج بالإعلان"
    beds = beds_match.group(1) + " غرف" if beds_match else ""
    baths = baths_match.group(1) + " حمام" if baths_match else ""
    return price_text, price_num, area, beds, baths

def clean_dubizzle_url(raw_href):
    if not raw_href:
        return ""
    if "/url?" in raw_href or "uddg=" in raw_href:
        parsed = urlparse(raw_href)
        qs = parse_qs(parsed.query)
        for key in ["q", "url", "uddg"]:
            if key in qs and qs[key]:
                raw_href = unquote(qs[key][0])
                break
    if raw_href.startswith("/"):
        raw_href = "https://www.dubizzle.com.eg" + raw_href
    raw_href = raw_href.split("?")[0].split("#")[0]
    if "dubizzle.com.eg" in raw_href and "/ad/" in raw_href:
        return raw_href
    return ""

def scrape_from_search_index(seen_urls, blocked_users, seller_counts, now_ts, now_cairo):
    collected = []
    for item in SEARCH_QUERIES:
        google_url = f"https://www.google.com/search?q={requests.utils.quote(item['q'])}&num=25&hl=ar"
        try:
            params = {"api_key": API_KEY, "url": google_url}
            res = requests.get("http://api.scraperapi.com", params=params, timeout=30)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, "html.parser")

            for a in soup.find_all("a", href=True):
                ad_url = clean_dubizzle_url(a["href"])
                if not ad_url or ad_url in seen_urls:
                    continue

                parent = a.find_parent("div", class_=True)
                container = parent.find_parent("div", class_=True) if parent else a
                block_text = container.get_text(" | ", strip=True) if container else a.get_text(" ", strip=True)

                h3 = a.find("h3")
                title = h3.get_text(strip=True) if h3 else a.get_text(strip=True)
                title = re.sub(r"\s*[-|]\s*(?:دوبيزل|dubizzle|اوليكس|olx).*$", "", title, flags=re.I).strip()
                if len(title) < 5:
                    continue

                full_text = f"{title} | {block_text}"
                if is_broker_text(full_text):
                    blocked_users.add(ad_url)
                    continue

                seller_key = title[:25]
                seller_counts[seller_key] = seller_counts.get(seller_key, 0) + 1
                if seller_counts[seller_key] > 7:
                    blocked_users.add(seller_key)
                    continue

                price_text, price_num, area, beds, baths = extract_specs(full_text)
                clean_desc = block_text.replace(title, "").strip(" |")
                if len(clean_desc) < 15:
                    clean_desc = title

                subtype = detect_subtype(title, clean_desc, item["category"])
                seen_urls.add(ad_url)
                collected.append({
                    "title": title,
                    "url": ad_url,
                    "price_text": price_text,
                    "price_num": price_num,
                    "deal": item["deal"],
                    "category": item["category"],
                    "subtype": subtype,
                    "location": "القاهرة الجديدة",
                    "area": area,
                    "beds": beds,
                    "baths": baths,
                    "description": clean_desc,
                    "seller_name": "مالك مباشر",
                    "seller_profile": seller_key,
                    "seller_ads_count": seller_counts[seller_key],
                    "scraped_timestamp": now_ts,
                    "scraped_date": now_cairo
                })
        except Exception as e:
            print(f"Search index error: {e}")
    return collected

def scrape_from_direct(seen_urls, blocked_users, seller_counts, now_ts, now_cairo):
    collected = []
    for cat in DIRECT_URLS[:2]:
        try:
            params = {"api_key": API_KEY, "url": cat["url"], "premium": "true", "country_code": "eg"}
            res = requests.get("http://api.scraperapi.com", params=params, timeout=45)
            if res.status_code != 200:
                continue
            soup = BeautifulSoup(res.text, "html.parser")
            for card in soup.find_all("article"):
                card_html = str(card)
                if "/companies/" in card_html or "/agencies/" in card_html:
                    blocked_users.add(cat["url"] + "#company")
                    continue
                link_el = card.find("a", href=re.compile(r"/ad/"))
                if not link_el:
                    continue
                ad_url = clean_dubizzle_url(link_el["href"])
                if not ad_url or ad_url in seen_urls:
                    continue
                card_text = card.get_text(" | ", strip=True)
                if is_broker_text(card_text):
                    blocked_users.add(ad_url)
                    continue
                title_el = card.find("h2") or link_el
                title = title_el.get_text(strip=True) if title_el else "عقار بالقاهرة الجديدة"
                price_text, price_num, area, beds, baths = extract_specs(card_text)
                subtype = detect_subtype(title, card_text, cat["category"])
                seen_urls.add(ad_url)
                collected.append({
                    "title": title,
                    "url": ad_url,
                    "price_text": price_text,
                    "price_num": price_num,
                    "deal": cat["deal"],
                    "category": cat["category"],
                    "subtype": subtype,
                    "location": "القاهرة الجديدة",
                    "area": area,
                    "beds": beds,
                    "baths": baths,
                    "description": card_text,
                    "seller_name": "مالك مباشر",
                    "seller_profile": ad_url,
                    "seller_ads_count": 1,
                    "scraped_timestamp": now_ts,
                    "scraped_date": now_cairo
                })
        except Exception:
            pass
    return collected

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
        ad_ts = ad.get("scraped_timestamp", now_ts)
        seller_prof = ad.get("seller_profile", "")
        if (now_ts - ad_ts) < SEVEN_DAYS_SECONDS and (not seller_prof or seller_prof not in blocked_users):
            valid_existing_ads.append(ad)

    seen_urls = {ad.get("url") for ad in valid_existing_ads if ad.get("url")}
    seller_counts = {}

    indexed_ads = scrape_from_search_index(seen_urls, blocked_users, seller_counts, now_ts, now_cairo)
    direct_ads = scrape_from_direct(seen_urls, blocked_users, seller_counts, now_ts, now_cairo)

    all_candidates = indexed_ads + direct_ads
    filtered_new = [
        ad for ad in all_candidates
        if ad["seller_profile"] not in blocked_users and 1 <= ad["seller_ads_count"] <= 4
    ]

    final_ads = filtered_new + valid_existing_ads

    payload = {
        "last_scrape": now_cairo,
        "total": len(final_ads),
        "blocked_count": len(blocked_users),
        "blocked_users": list(blocked_users),
        "ads": final_ads
    }

    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Success: {len(final_ads)} owner ads, {len(blocked_users)} blocked.")

if __name__ == "__main__":
    scrape_all()
