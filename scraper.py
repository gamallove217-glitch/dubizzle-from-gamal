import json
import time
import re
import os
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import requests as std_requests

try:
    from curl_cffi import requests as cffi_requests
    USE_CFFI = True
except ImportError:
    import cloudscraper
    USE_CFFI = False

URLS = [
    {"url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/", "deal": "بيع", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/", "deal": "إيجار", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/rooms-for-rent/new-cairo/", "deal": "إيجار", "category": "شقق"},
    {"url": "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/", "deal": "بيع", "category": "فيلا"},
    {"url": "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/", "deal": "إيجار", "category": "فيلا"},
    {"url": "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/", "deal": "بيع", "category": "تجاري وإداري"},
    {"url": "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/", "deal": "إيجار", "category": "تجاري وإداري"}
]

BROKER_KEYWORDS = [
    "شركة", "للعقارات", "التسويق العقاري", "بروكر", "سمسار", "عمولة", "مكتب عقارات",
    "real estate", "property", "properties", "agency", "broker", "consultancy", "investment"
]

SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

def fetch_page(session, url):
    headers = {
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
        "Referer": "https://www.dubizzle.com.eg/"
    }
    try:
        if USE_CFFI:
            res = session.get(url, headers=headers, impersonate="chrome120", timeout=25)
        else:
            res = session.get(url, headers=headers, timeout=25)
        if res.status_code == 200 and ("/ad/" in res.text or "dubizzle" in res.text):
            return res.text
    except Exception:
        pass

    try:
        jina_url = "https://r.jina.ai/" + url
        jina_headers = {"X-Return-Format": "html", "Accept-Language": "ar"}
        res2 = std_requests.get(jina_url, headers=jina_headers, timeout=30)
        if res2.status_code == 200:
            return res2.text
    except Exception:
        pass
    return ""

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

def get_user_ads_count(session, profile_url):
    if not profile_url:
        return 1
    try:
        time.sleep(1.0)
        html = fetch_page(session, profile_url)
        if not html:
            return 1
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        match = re.search(r"(\d+)\s*(?:إعلان|إعلانات|اعلان|Ads|ad)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        ad_links = {a["href"] for a in soup.find_all("a", href=True) if "/ad/" in a["href"]}
        if ad_links:
            return len(ad_links)
        return 1
    except Exception:
        return 1

def parse_ad_details(session, ad_url, blocked_users):
    try:
        time.sleep(1.0)
        html = fetch_page(session, ad_url)
        if not html:
            return None
        soup = BeautifulSoup(html, "html.parser")

        seller_name = "مالك"
        profile_url = None
        for a in soup.find_all("a", href=True):
            if "/profile/" in a["href"]:
                profile_url = "https://www.dubizzle.com.eg" + a["href"] if a["href"].startswith("/") else a["href"]
                seller_name = a.get_text(strip=True) or "مالك"
                break

        if profile_url and profile_url in blocked_users:
            return None

        for a in soup.find_all("a", href=True):
            if "/companies/" in a["href"] or "/agencies/" in a["href"]:
                if profile_url:
                    blocked_users.add(profile_url)
                return None

        description = ""
        desc_el = soup.find("div", {"aria-label": "Description"}) or soup.find("div", class_=re.compile(r"description", re.I))
        if desc_el:
            description = desc_el.get_text("\n", strip=True)
        if not description:
            meta_desc = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
            if meta_desc and meta_desc.get("content"):
                description = meta_desc["content"].strip()

        title = ""
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
        if not title:
            meta_title = soup.find("meta", {"property": "og:title"})
            if meta_title and meta_title.get("content"):
                title = meta_title["content"].strip()

        price_text = "غير محدد"
        price_num = 0
        price_el = soup.find("span", {"aria-label": "Price"}) or soup.find(string=re.compile(r"ج\.م|EGP"))
        if price_el:
            price_text = price_el.strip() if isinstance(price_el, str) else price_el.get_text(strip=True)
            nums = re.findall(r"\d+", price_text.replace(",", ""))
            if nums:
                price_num = int(nums[0])

        page_text = soup.get_text(" ", strip=True)
        area_match = re.search(r"(\d+)\s*(?:م²|متر|sqm|m²)", page_text, re.I)
        beds_match = re.search(r"(\d+)\s*(?:غرف|غرفة|beds|bed)", page_text, re.I)
        baths_match = re.search(r"(\d+)\s*(?:حمام|حمامات|baths|bath)", page_text, re.I)

        combined_check = (seller_name + " " + title + " " + description[:200]).lower()
        for kw in BROKER_KEYWORDS:
            if kw in combined_check:
                if profile_url:
                    blocked_users.add(profile_url)
                return None

        ads_count = get_user_ads_count(session, profile_url)
        if ads_count > 7:
            if profile_url:
                blocked_users.add(profile_url)
            return None

        if ads_count < 1 or ads_count > 4:
            return None

        return {
            "title": title or "عقار بالقاهرة الجديدة",
            "price_text": price_text,
            "price_num": price_num,
            "area": area_match.group(1) + " م²" if area_match else "غير محدد",
            "beds": beds_match.group(1) + " غرف" if beds_match else "",
            "baths": baths_match.group(1) + " حمام" if baths_match else "",
            "description": description if description else "اضغط على فتح الإعلان لقراءة كافة التفاصيل على دوبيزل.",
            "seller_name": seller_name,
            "seller_profile": profile_url or "",
            "seller_ads_count": ads_count
        }
    except Exception:
        return None

def scrape_all():
    session = cffi_requests.Session() if USE_CFFI else cloudscraper.create_scraper()
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
    new_ads = []

    for cat in URLS:
        try:
            html = fetch_page(session, cat["url"])
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")

            ad_urls = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/ad/" in href and "-ID" in href:
                    full_url = "https://www.dubizzle.com.eg" + href if href.startswith("/") else href
                    if full_url not in seen_urls and full_url not in ad_urls:
                        ad_urls.append(full_url)

            for ad_url in ad_urls[:10]:
                seen_urls.add(ad_url)
                details = parse_ad_details(session, ad_url, blocked_users)
                if not details:
                    continue

                subtype = detect_subtype(details["title"], details["description"], cat["category"])
                new_ads.append({
                    "title": details["title"],
                    "url": ad_url,
                    "price_text": details["price_text"],
                    "price_num": details["price_num"],
                    "deal": cat["deal"],
                    "category": cat["category"],
                    "subtype": subtype,
                    "location": "القاهرة الجديدة",
                    "area": details["area"],
                    "beds": details["beds"],
                    "baths": details["baths"],
                    "description": details["description"],
                    "seller_name": details["seller_name"],
                    "seller_profile": details["seller_profile"],
                    "seller_ads_count": details["seller_ads_count"],
                    "scraped_timestamp": now_ts,
                    "scraped_date": now_cairo
                })
        except Exception:
            continue

    final_ads = new_ads + valid_existing_ads

    payload = {
        "last_scrape": now_cairo,
        "total": len(final_ads),
        "blocked_count": len(blocked_users),
        "blocked_users": list(blocked_users),
        "ads": final_ads
    }

    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    scrape_all()
