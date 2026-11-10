import base64
import json
import os
import random
import re
import time
import urllib.parse
import requests as std_requests
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

# ✅ FIX: المنطقة الزمنية الحقيقية بدل +2 ثابتة
CAIRO_TZ = ZoneInfo("Africa/Cairo") if ZoneInfo else timezone(timedelta(hours=2))
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

# PERMANENT FIX: TTL لجميع الإعلانات (7 أيام)
CHECKED_TTL_DAYS = int(os.environ.get("CHECKED_TTL_DAYS", "7") or 7)

# ── FIX(C1): توكن تليجرام كان مكتوب في الكود (base64 = ترميز مش تشفير) ──
# أي حد يفتح الملف ياخد التوكن ويبعت من البوت بتاعك. اتنقل لمتغير بيئة.
# ضيفه في: Settings → Secrets and variables → Actions → TELEGRAM_BOT_TOKEN
TG_TOKEN = (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
TG_B64_LIST = [TG_TOKEN] if TG_TOKEN else []
if not TG_B64_LIST:
    print("⚠️  TELEGRAM_BOT_TOKEN مش موجود في البيئة — إرسال تليجرام متعطّل في الرَن ده.")

# ── FIX(M1): حدود الـ ID كانت "قنابل موقوتة" مكتوبة يدوي في الكود ──
# كل ما المواقع تكبر الأرقام دي بتبقى قديمة. بقيت متغيرات بيئة تتغيّر من غير ما تلمس الكود.
AQARMAP_MIN_ID  = int(os.environ.get("AQARMAP_MIN_ID", "7150000") or 0)
OPENSOOQ_MIN_ID = int(os.environ.get("OPENSOOQ_MIN_ID", "289000000") or 0)
MAX_AD_AGE_DAYS = int(os.environ.get("MAX_AD_AGE_DAYS", "12") or 12)

AR_MONTHS = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "أبريل": 4, "ابريل": 4, "مايو": 5, "يونيو": 6,
    "يوليو": 7, "أغسطس": 8, "اغسطس": 8, "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10,
    "نوفمبر": 11, "ديسمبر": 12,
}

STRICT_NEW_CAIRO_HEADER = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "القطامية", "القطاميه", "new cairo", "5th settlement",
    "fifth settlement", "katameya"
]

NEW_CAIRO_WORDS = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "التجمع", "الحي الأول", "الحي الاول", "الحي الثاني",
    "الحي التاني", "الحي الثالث", "الحي التالت", "الحي الرابع", "الحي الخامس",
    "النرجس", "اللوتس", "الأندلس", "الاندلس", "الياسمين", "البنفسج",
    "جنوب الأكاديمية", "جنوب الاكاديمية", "الاكاديمية", "شرق الأكاديمية", "شرق الاكاديمية",
    "المستثمرين", "النورث هاوس", "القرنفل", "تمر حنة", "اللؤلؤة",
    "ابو الهول", "أبو الهول", "جاردينيا هايتس", "غرب الجولف", "غرب أرابيلا", "غرب ارابيلا",
    "أرابيلا", "ارابيلا", "الشويفات", "الداون تاون", "التسعين", "القطامية", "القطاميه",
    "كايرو فيستيفال", "كايرو فستيفال", "ميفيدا", "ماونتن فيو", "هايد بارك", "بالم هيلز",
    "سوديك", "فيليت", "ايست تاون", "ايستاون", "زيد ايست", "تريو", "ازار", "دار مصر",
    "سكن مصر", "جنة", "الجامعة الأمريكية", "الجامعه الامريكيه", "الجولدن سكوير",
    "الدبلوماسيين", "لافيستا", "الباتيو", "مون فالي", "ذا سكوير", "فيفث سكوير", "سراي",
    "القطاع الأول", "القطاع الثاني", "القطاع الثالث", "القطاع الرابع", "الزهور", "الأشرفية"
]

FORBIDDEN_URL_SLUGS = [
    "el-rehab", "madinaty", "mostakbal-city", "new-heliopolis", "el-shorouk",
    "badr-city", "new-administrative-capital", "el-obour", "nasr-city", "heliopolis",
    "maadi", "mokattam", "sheikh-zayed", "6th-of-october", "chalet", "north-coast",
    "ain-sokhna", "شاليهات-مصايف", "شقق-ومنازل-العطلات", "الرحاب", "مدينتي",
    "الشروق", "العاصمة-الادارية", "المستقبل", "مدينة-نصر", "مصر-الجديدة"
]

STRICT_FORBIDDEN_HEADER = [
    "مصر الجديدة", "مصر الجديده", "مدينة نصر", "مدينه نصر", "زهراء مدينة نصر",
    "الكوربة", "أرض الجولف", "ارض الجولف", "ميدان الحجاز", "روكسي", "الميريلاند",
    "الماظة", "ألماظة", "شيراتون", "النزهة", "النزهه", "عباس العقاد", "مكرم عبيد",
    "مصطفى النحاس", "الحي العاشر", "جاردينيا سيتي", "جسر السويس", "عين شمس",
    "حدائق القبة", "شبرا", "حلوان", "الزمالك", "وسط البلد", "رمسيس", "العباسية",
    "الإسكندرية", "الاسكندرية", "سموحة", "العجمي", "برج العرب", "الساحل الشمالي",
    "العين السخنة", "الغردقة", "شرم الشيخ", "المنصورة", "طنطا", "أسيوط",
    "الشيخ زايد", "6 أكتوبر", "٦ أكتوبر", "حدائق أكتوبر", "الهرم", "حدائق الأهرام",
    "فيصل", "المهندسين", "الدقي", "العجوزة", "المعادي", "زهراء المعادي",
    "العاشر من رمضان", "المقطم", "الهضبة الوسطى",
    "عقارات مصايف", "شاليه للبيع", "شاليه للإيجار", "شاليهات",
    "مدينة الرحاب", "شقق للبيع في الرحاب", "في الرحاب", "بمدينتي", "في مدينتي",
    "مدينة الشروق", "في الشروق", "مدينة المستقبل", "المستقبل سيتي", "مدينة بدر",
    "مدينة العبور", "في العبور", "العاصمة الإدارية", "العاصمه الاداريه", "حدائق العاصمة",
    "تاج سيتي", "هليوبوليس الجديدة", "هليوبوليس الجديده",
    # 🆕 بيت الوطن — ممنوعة زي مدينتي، بحماية من «تبعد عن بيت الوطن»
    "بيت الوطن", "بيت الوطنى", "بيت الوطن الجديد"
]

WORDS_TO_SANITIZE_IN_DESC = [
    "مصر الجديدة", "مصر الجديده", "مدينة نصر", "مدينه نصر", "الرحاب", "مدينة الرحاب",
    "مدينتي", "مدينتى", "الشروق", "مدينة الشروق", "مدينة المستقبل", "المستقبل سيتي",
    "مدينة بدر", "العبور", "العاصمة الإدارية", "العاصمه الاداريه", "تاج سيتي",
    "هليوبوليس الجديدة", "جاردينيا سيتي", "المقطم", "المعادي", "شيراتون", "النزهة",
    "جاردينيا", "عقارات مصايف", "بيت الوطن", "بيت الوطنى"
]

# ==============================================================================
#  🛡️ حماية من اللبس — نفس منطق scraper.py بالظبط (الملف ده مستقل فما ينفعش يستورده)
#    • «تبعد عن بيت الوطن 5 دقايق»  ⇒ مش في بيت الوطن ⇒ تعدي
#    • «بدون أقساط من المالك»        ⇒ كاش ⇒ تعدي
#    • «بدون مقدم وأقساط على 5 سنين» ⇒ الواو فصلت النفي ⇒ تقسيط ⇒ مرفوض
# ==============================================================================
INSTALLMENT_WORDS = [
    "بالتقسيط", "تقسيط", "أقساط", "اقساط", "بالأقساط", "بالاقساط", "قسط",
    "مقدم", "بقدم", "بمقدم", "دفعة", "دفعه", "أقل مقدم", "اقل مقدم",
    "تسهيلات", "تسهيل", "نظام سداد", "أنظمة سداد", "انظمة سداد",
    "خطة سداد", "خطط سداد", "سداد ميسر", "سداد مرن",
    "على سنوات", "علي سنوات", "على سنين", "علي سنين", "لسنوات", "لسنين",
    "خصم الكاش", "سعر الشركة",
    "installment", "installments", "down payment", "payment plan",
]
NEGATION_RE = re.compile(
    r"(?:^|[\s،,;.\-–—(|«»\"])"
    r"(?:بدون|بلا|لا|مش|ليس|غير|من\s+غير|منغير|مفيش|خالي|خالٍ|مبقتش|no|not|without|zero)"
    r"(?=$|[\s،,;.\-–—)|«»\"])"
)
AREA_HINT_RE = re.compile(
    r"(?:يبعد|تبعد|بعاد|بعيد|بعيده|قريب|قريبه|قرب|بجوار|بجانب|جنب|خلف|خلفها|"
    r"أمام|امام|وراء|ورا|مقابل|خارج|ناحية|اتجاه|حوالي|تقريبا|تقريباً|"
    r"على\s+بعد|علي\s+بعد|بعد|لسه\s+موصل|"
    r"(?:^|[\s،,;.\-–—(|])(?:مش|ليس|غير|بدون|بلا|لا)(?=$|[\s،,;.\-–—)|]))"
)
CONJUNCTION_MARKS = (" و", "،", ",", "+", "|", " أو ", " او ", " ثم ", ";", " وكذلك ")
LOOKBACK_CHARS = 26


def _governed_before(text, start, pattern):
    if not text or start <= 0:
        return False
    window = text[max(0, start - LOOKBACK_CHARS):start]
    best = None
    for m in pattern.finditer(window):
        best = m
    if best is None:
        return False
    between = window[best.end():]
    if any(c in between for c in CONJUNCTION_MARKS):
        return False
    return True


def area_is_the_location(text, area):
    t = text or ""
    for m in re.finditer(re.escape(area), t):
        if not _governed_before(t, m.start(), AREA_HINT_RE):
            return True
    return False


def has_installment_offer(text):
    t = (text or "").lower()
    for w in INSTALLMENT_WORDS:
        for m in re.finditer(re.escape(w.lower()), t):
            if not _governed_before(t, m.start(), NEGATION_RE):
                return True
    return False


def forbidden_area_hit(text, forbidden_list):
    for bad in forbidden_list:
        if area_is_the_location(text, bad):
            return bad
    return None


AQARMAP_SETTLEMENT_ZONES = [
    "cairo/new-cairo",
    "cairo/new-cairo/bait-el-watan",
    "cairo/new-cairo/compounds",
    "cairo/new-cairo/el-katameya",
    "cairo/new-cairo/shorouk",
    "cairo/new-cairo/6th-settlement",
    "cairo/new-cairo/first-settlement",
    "cairo/new-cairo/third-settlement"
]

AQARMAP_PROP_TYPES = [
    ("for-sale", "apartment"),
    ("for-rent", "apartment"),
    ("for-rent", "furnished-apartment"),
    ("for-sale", "villa"),
    ("for-rent", "villa"),
    ("for-sale", "land"),
    ("for-sale", "building"),
    ("for-sale", "administrative"),
    ("for-rent", "administrative"),
    ("for-sale", "commercial"),
    ("for-rent", "commercial"),
    ("for-sale", "medical"),
    ("for-rent", "medical")
]

OPENSOOQ_CATEGORY_URLS = [
    "https://eg.opensooq.com/ar/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9/%D8%A7%D9%84%D8%AA%D8%AC%D9%85%D8%B9-%D8%A7%D9%84%D8%AE%D8%A7%D9%85%D8%B3/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D9%84%D8%A8%D9%8A%D8%B9/%D8%B4%D9%82%D9%82-%D9%84%D9%84%D8%A8%D9%8A%D8%B9",
    "https://eg.opensooq.com/ar/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9/%D8%A7%D9%84%D8%AA%D8%AC%D9%85%D8%B9-%D8%A7%D9%84%D8%AE%D8%A7%D9%85%D8%B3/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D9%84%D8%A7%D9%8A%D8%AC%D8%A7%D8%B1/%D8%B4%D9%82%D9%82-%D9%84%D9%84%D8%A7%D9%8A%D8%AC%D8%A7%D8%B1",
    "https://eg.opensooq.com/ar/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9/%D8%A7%D9%84%D8%AA%D8%AC%D9%85%D8%B9-%D8%A7%D9%84%D8%AE%D8%A7%D9%85%D8%B3/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D9%84%D8%A8%D9%8A%D8%B9/%D9%81%D9%84%D9%84-%D9%82%D8%B5%D9%88%D8%B1-%D9%84%D9%84%D8%A8%D9%8A%D8%B9",
    "https://eg.opensooq.com/ar/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9/%D8%A7%D9%84%D8%AA%D8%AC%D9%85%D8%B9-%D8%A7%D9%84%D8%AE%D8%A7%D9%85%D8%B3/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D9%84%D8%A7%D9%8A%D8%AC%D8%A7%D8%B1/%D9%81%D9%84%D9%84-%D9%82%D8%B5%D9%88%D8%B1-%D9%84%D9%84%D8%A7%D9%8A%D8%AC%D8%A7%D8%B1",
    "https://eg.opensooq.com/ar/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9/%D8%A7%D9%84%D8%AA%D8%AC%D9%85%D8%B9-%D8%A7%D9%84%D8%AE%D8%A7%D9%85%D8%B3/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D9%84%D8%A8%D9%8A%D8%B9/%D8%AA%D8%AC%D8%A7%D8%B1%D9%8A-%D9%84%D9%84%D8%A8%D9%8A%D8%B9",
    "https://eg.opensooq.com/ar/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9/%D8%A7%D9%84%D8%AA%D8%AC%D9%85%D8%B9-%D8%A7%D9%84%D8%AE%D8%A7%D9%85%D8%B3/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D9%84%D8%A7%D9%8A%D8%AC%D8%A7%D8%B1/%D8%AA%D8%AC%D8%A7%D8%B1%D9%8A-%D9%84%D9%84%D8%A7%D9%8A%D8%AC%D8%A7%D8%B1",
    "https://eg.opensooq.com/ar/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9/%D8%A7%D9%84%D8%AA%D8%AC%D9%85%D8%B9-%D8%A7%D9%84%D8%AE%D8%A7%D9%85%D8%B3/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D9%84%D8%A8%D9%8A%D8%B9/%D8%A3%D8%B1%D8%A7%D8%B6%D9%8A-%D9%84%D9%84%D8%A8%D9%8A%D8%B9",
    "https://eg.opensooq.com/ar/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9/%D8%A7%D9%84%D8%AA%D8%AC%D9%85%D8%B9-%D8%A7%D9%84%D8%AE%D8%A7%D9%85%D8%B3/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D9%84%D8%A8%D9%8A%D8%B9/%D8%B9%D9%85%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D9%84%D8%A8%D9%8A%D8%B9",
    "https://eg.opensooq.com/ar/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9-%D8%A7%D9%84%D8%AC%D8%AF%D9%8A%D8%AF%D8%A9/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D9%84%D8%A8%D9%8A%D8%B9/%D8%B4%D9%82%D9%82-%D9%84%D9%84%D8%A8%D9%8A%D8%B9",
    "https://eg.opensooq.com/ar/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9/%D8%A7%D9%84%D9%82%D8%A7%D9%87%D8%B1%D8%A9-%D8%A7%D9%84%D8%AC%D8%AF%D9%8A%D8%AF%D8%A9/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA-%D9%84%D9%84%D8%A7%D9%8A%D8%AC%D8%A7%D8%B1/%D8%B4%D9%82%D9%82-%D9%84%D9%84%D8%A7%D9%8A%D8%AC%D8%A7%D8%B1"
]

EXTRA_QUERIES = [
    'site:aqarmap.com.eg/ar/listing "التجمع الخامس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "القاهرة الجديدة" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "التجمع الأول" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "التجمع الثالث" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "القطامية" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "النرجس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "اللوتس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "الياسمين" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "البنفسج" "مالك عقار"',
    # 🆕 اتشال: كان بيدوّر على بيت الوطن بالاسم — المنطقة بقت ممنوعة
    'site:aqarmap.com.eg/ar/listing "جنوب الأكاديمية" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "الأندلس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "القرنفل" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "فيلا للإيجار" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "فلل للبيع" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "أرض" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "إداري" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "تجاري" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "عيادة" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "محل" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "للإيجار" "القاهرة الجديدة" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "شقق للايجار" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "duplex" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "بنتهاوس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "ستوديو" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "إداري" "القاهرة الجديدة" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "عيادة" "القاهرة الجديدة" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "مكتب" "القاهرة الجديدة" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "أرض للإيجار" "القاهرة الجديدة" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "land" "new cairo" "owner"',
    'site:aqarmap.com.eg/ar/listing "commercial" "new cairo" "owner"',
    'site:aqarmap.com.eg/ar/listing "administrative" "new cairo" "owner"',
    'site:aqarmap.com.eg/ar/listing "medical" "new cairo" "owner"',
    'site:eg.opensooq.com/ar "التجمع الخامس" "المالك"',
    'site:eg.opensooq.com/ar "القاهرة الجديدة" "المالك"',
    'site:eg.opensooq.com/ar "التجمع الخامس" "من المالك"',
    'site:eg.opensooq.com/ar "التجمع الأول" "المالك"',
    'site:eg.opensooq.com/ar "التجمع الثالث" "المالك"',
    'site:eg.opensooq.com/ar "النرجس" "المالك"',
    'site:eg.opensooq.com/ar "اللوتس" "المالك"',
    'site:eg.opensooq.com/ar "الياسمين" "المالك"',
    'site:eg.opensooq.com/ar "البنفسج" "المالك"',
    'site:eg.opensooq.com/ar "فلل" "المالك"',
    'site:eg.opensooq.com/ar "أراضي" "المالك"',
    'site:eg.opensooq.com/ar "إيجار" "المالك"',
    'site:eg.opensooq.com/ar "تجاري" "المالك"',
    'site:eg.opensooq.com/ar "إداري" "المالك"',
    'site:eg.opensooq.com/ar "عيادة" "المالك"',
    'site:eg.opensooq.com/ar "مكتب" "المالك"',
    'site:eg.opensooq.com/ar "للايجار" "المالك"'
]


def clean_text(md):
    txt = (md or "")
    txt = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]+", "", txt)
    txt = txt.translate(AR_DIGITS)
    txt = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"(?:aqarmap\.com\.eg|eg\.opensooq\.com)\s*(?:›|>|/)\s*ar\s*(?:›|>|/)?\s*(?:listing)?", " ", txt, flags=re.I)
    txt = re.sub(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+20\d{2}\s*·?", " ", txt, flags=re.I)
    txt = re.sub(r"[*#_`~>|/\\]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def clean_card_title(title_str):
    t = clean_text(title_str)
    t = re.sub(r"^(?:aqarmap\.com\.eg|eg\.opensooq\.com).*?(?:listing|ar)\s*", "", t, flags=re.I)
    t = t.replace(". عقارماب", "").replace("- عقارماب", "").replace("عقارماب", "").strip(" .-:|…")
    return t[:130] if len(t) > 5 else "وحدة من المالك بالقاهرة الجديدة"


def sanitize_for_dubizzle_compatibility(text):
    s = clean_text(text or "")
    for w in WORDS_TO_SANITIZE_IN_DESC:
        s = s.replace(w, " ")
    s = s.replace("أكتشف المزيد من العقارات المشابهة", " ")
    s = s.replace("تواصل مع شركات عقارية موثوقة تعرض عقارات مشابهة لهذا العقار", " ")
    return re.sub(r"\s+", " ", s).strip()


def strip_villa_neighborhood_names(txt):
    s = txt or ""
    for phrase in [
        "البنفسج فيلات", "النرجس فيلات", "الياسمين فيلات", "القرنفل فيلات",
        "جنوب الاكاديمية فيلات", "جنوب الأكاديمية فيلات", "شرق الاكاديمية فيلات",
        "شرق الأكاديمية فيلات", "التجمع الخامس فيلات", "منطقة الفيلات", "حي الفيلات",
        "فيو فيلا", "فيو الفيلات", "داخل فيلا", "في فيلا", "بفيلا"
    ]:
        s = s.replace(phrase, " ")
    return s


def classify_unit(url, title_clean, header_clean, price_num):
    u_dec = urllib.parse.unquote(url).lower()
    t_low = (title_clean or "").lower()
    t_and_u = f"{t_low} {u_dec}".lower()
    header_str = (header_clean or "").lower()
    for ignore_phrase in ["المكاتب يمتنعون", "المكاتب يَمتنعون", "والمكاتب", "و المكاتب", "مكاتب التسويق", "مكاتب العقارات", "مكاتب السمسرة"]:
        header_str = header_str.replace(ignore_phrase, " ")
    all_check = f"{t_and_u} {header_str}"

    deal = "بيع"
    if any(w in t_and_u for w in ["للبيع", "-for-sale", "for-sale", "للبيع "]):
        deal = "بيع"
    elif any(w in all_check for w in [
        "للإيجار", "للايجار", "for-rent", "for rent", "شقق للايجار", "فلل للايجار",
        "تجاري للايجار", "أراضي للايجار", "عمارات للايجار", "غرف ومشاركة",
        "furnished-apartment", "شقة مفروشة", "شقق مفروشة", "إيجار مفروش", "/شهر"
    ]):
        deal = "إيجار"
    elif 0 < price_num < 150000:
        deal = "إيجار"

    is_explicit_apt = any(w in t_low for w in ["شقة", "شقه", "apartment", "flat", "دوبلكس", "دوبليكس", "بنتهاوس", "ستوديو", "استوديو", "studio", "رووف", "روف"])

    if any(w in all_check for w in [
        "/land/", "-land-", "أراضي للبيع", "أراضي للايجار", "اراضي للبيع", "قطعة أرض",
        "قطعه ارض", "أرض للبيع", "ارض للبيع", "أرض سكنية", "أرض تجارية", "أرض مباني",
        "للبيع أرض", "للبيع ارض", "أراض "
    ]) and not is_explicit_apt:
        return deal, "مبانى و أراضى", "أراض"

    if any(w in all_check for w in [
        "/building/", "-building-", "عمارات للبيع", "عمارات للايجار", "عمارة كاملة", "عماره كامله",
        "عمارة للبيع", "عماره للبيع", "مبنى كامل", "مباني للبيع", "مبنى للبيع"
    ]) and not is_explicit_apt:
        return deal, "مبانى و أراضى", "مبنى"

    if any(w in all_check for w in [
        "/medical/", "-medical-", "medical", "clinic", "عيادة", "عياده", "صيدلية", "صيدليه",
        "مركز طبي", "وحدة طبية", "طبي للبيع", "طبي للإيجار", "عيادات"
    ]) and not is_explicit_apt:
        category = "عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"
        return deal, category, "طبي"

    if any(w in all_check for w in [
        "/administrative/", "-administrative-", "office", "business park", "مكتب للبيع", "مكتب للإيجار", "مكتب للايجار",
        "مكتب اداري", "مكتب إداري", "محل ادارى", "محل إداري", "إداري", "اداري", "مقر إداري", "مقر اداري", "وحدة إدارية"
    ]) and not is_explicit_apt:
        if not any(w in all_check for w in ["retail", "shop"]):
            category = "عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"
            return deal, category, "إداري"

    if any(w in all_check for w in [
        "/commercial/", "-commercial-", "retail", "shop", "commercial", "تجاري للبيع", "تجاري للايجار",
        "محل ", "محل للبيع", "محل للإيجار", "محل للايجار", "محلات", "تجاري", "تجارى",
        "معرض", "مخزن", "مصنع", "مطعم", "كافيه"
    ]) and not is_explicit_apt:
        category = "عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"
        return deal, category, "عقار تجاري"

    if any(w in all_check for w in ["furnished-apartment", "شقة مفروشة", "شقه مفروشه", "شقق مفروشة"]):
        return "إيجار", "شقق للإيجار", "شقة مفروشة"

    if any(w in t_and_u for w in ["شقة فندقية", "شقه فندقيه", "فندقية", "فندقيه", "أجنحة فندقية"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "شقة فندقية"

    if any(w in t_and_u for w in ["ستوديو", "استوديو", "studio"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "ستوديو"

    if any(w in t_and_u for w in ["غرف ومشاركة", "غرفة للإيجار", "غرفه للايجار", "غرفة مفروشة"]) and not is_explicit_apt and (0 < price_num < 150000):
        return "إيجار", "شقق للإيجار", "غرفة"

    if any(w in t_and_u for w in ["دوبلكس", "دوبليكس", "duplex", "تريبلكس"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "دوبلكس"

    if any(w in t_and_u for w in ["بنتهاوس", "بينتهاوس", "penthouse"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "بنتهاوس"

    if any(w in t_and_u for w in ["سطح", "رووف", "روف ", "طابق أخير مع روف", "roof"]) or t_and_u.startswith("روف"):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "سطح"

    cleaned_t = strip_villa_neighborhood_names(all_check)
    if any(w in cleaned_t for w in [
        "/villa/", "-villa-", "فلل - قصور", "فلل قصور", "فيلا منفصلة", "فيلا مستقلة",
        "تاون هاوس", "توين هاوس", "ستاند الون", "فيلا للبيع", "فيلا للإيجار",
        "فيلا للايجار", "ڤيلا", "townhouse", "twinhouse", "standalone", "villa"
    ]) and not is_explicit_apt:
        category = "فلل للإيجار" if deal == "إيجار" else "فلل للبيع"
        return deal, category, "فيلا"

    category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
    return deal, category, "شقة"


def has_forbidden_url_slug(url):
    u_dec = urllib.parse.unquote(url).lower()
    return any(slug in u_dec for slug in FORBIDDEN_URL_SLUGS)


def check_aqarmap_freshness(core_text, lid):
    text_no_build_year = re.sub(r"سنة\s*البناء[\s:.•\-]*\d{4}", " ", core_text)
    m_pub = re.search(
        r"\b(\d{1,2})\s+(يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يوليو|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر)\s+(20\d{2})\b",
        text_no_build_year
    )
    if m_pub:
        day_num, month_ar, yr_str = int(m_pub.group(1)), m_pub.group(2), int(m_pub.group(3))
        # ✅ FIX(M1): مقارنة حقيقية بتاريخ النهارده بدل "2026" و"نوفمبر" المكتوبة يدوي
        mm = AR_MONTHS.get(month_ar)
        if mm:
            try:
                pub = datetime(yr_str, mm, day_num, tzinfo=CAIRO_TZ)
                if (datetime.now(CAIRO_TZ) - pub).days <= MAX_AD_AGE_DAYS:
                    return True, f"{day_num} {month_ar} {yr_str}"
            except ValueError:
                pass
        return False, f"OLD_DATE_{day_num}_{month_ar}_{yr_str}"

    if "اليوم" in text_no_build_year[:1200] or "أمس" in text_no_build_year[:1200]:
        return True, "اليوم"
    if lid >= AQARMAP_MIN_ID:
        return True, "حديث (حسب الـ ID)"
    return False, "NO_RECENT_DATE"


def check_opensooq_freshness(core_text, oid):
    m_rel = re.search(r"قبل\s*(\d+)?\s*(دقيقة|دقائق|ساعة|ساعات|ساعه|يوم|يومين|أيام|ايام)", core_text[:3000])
    if m_rel:
        return True, m_rel.group(0)
    if "أمس" in core_text[:3000] or "اليوم" in core_text[:3000]:
        return True, "اليوم/أمس"
    # Check ID threshold first — newer listings have higher oid
    if oid >= OPENSOOQ_MIN_ID:
        return True, "حديث (السوق المفتوح)"
    m_date = re.search(r"\b(\d{2})-(\d{2})-(20\d{2})\b", core_text[:3000])
    if m_date:
        dd, mm, yyyy = int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3))
        if yyyy == 2026 and mm == 11 and dd >= 1:
            return True, m_date.group(0)
        if yyyy == 2026 and mm == 10 and dd >= 10:
            return True, m_date.group(0)
        return False, f"OLD_DATE_{m_date.group(0)}"
    return False, "OLD_OPENSOOQ"


def to_google_translate_proxy(url):
    p = urllib.parse.urlsplit(url)
    host_dash = p.netloc.replace(".", "-")
    q = f"{p.query}&_x_tr_sl=en&_x_tr_tl=ar&_x_tr_hl=ar" if p.query else "_x_tr_sl=en&_x_tr_tl=ar&_x_tr_hl=ar"
    return f"https://{host_dash}.translate.goog{p.path}?{q}"


def fetch_page(req_sess, cffi_sess, url, timeout_sec=22):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com.eg/"
    }
    combined_parts = []
    links_buf = []
    title_line = ""

    for attempt in range(2):
        try:
            r = cffi_sess.get("https://r.jina.ai/" + url, headers=headers, timeout=timeout_sec)
            if r.status_code == 429 or "Too Many Requests" in r.text:
                if attempt == 0:
                    time.sleep(8)
                    continue
            if r.status_code == 200 and len(r.text) > 500 and "Too Many Requests" not in r.text and "Just a moment..." not in r.text:
                txt = r.text
                if "Generated by cloudfront" in txt or "403 ERROR" in txt or "Request blocked" in txt or "403 Forbidden" in txt or "Access Denied" in txt:
                    continue
                if "متر" in txt or "جنيه" in txt or "المعلن" in txt or "/listing/" in txt:
                    m_h1 = re.search(r"^#\s+(.+)$", txt, flags=re.M)
                    if m_h1:
                        title_line = f"# {m_h1.group(1).strip()}\n"
                    combined_parts.append(txt)
                    for m_l in re.finditer(r"https?://(?:aqarmap\.com\.eg/ar/listing/\d{7}-[^\s\"'<>)\]]+|eg\.opensooq\.com/ar/[^\s\"'<>)\]]+?/\d{9,10})", txt):
                        links_buf.append(m_l.group(0))
                    break
        except Exception:
            pass

    if not combined_parts:
        candidate_urls = [url]
        if "aqarmap.com.eg" in url:
            candidate_urls.insert(0, to_google_translate_proxy(url))
        for cand_u in candidate_urls:
            try:
                r2 = cffi_sess.get(cand_u, headers=headers, timeout=16, allow_redirects=True)
                if r2.status_code == 200 and len(r2.text) > 800 and "Just a moment" not in r2.text:
                    soup = BeautifulSoup(r2.text, "lxml")
                    base = "https://aqarmap.com.eg" if "aqarmap" in url else "https://eg.opensooq.com"
                    for a in soup.find_all("a", href=True):
                        raw_href = a["href"]
                        href = urllib.parse.unquote(raw_href)
                        if "/listing/" in href or re.search(r"/\d{9,10}\b", href):
                            full_h = base + raw_href if raw_href.startswith("/") else raw_href
                            links_buf.append(full_h)
                    h1 = soup.find("h1")
                    if h1 and not title_line:
                        title_line = f"# {h1.get_text(' ', strip=True)}\n"
                    for tag in soup.find_all(["head", "title", "script", "style", "nav", "footer", "noscript", "svg", "iframe"]):
                        tag.decompose()
                    body_t = soup.get_text(" ", strip=True)
                    if "متر" in body_t or "جنيه" in body_t or "المعلن" in body_t:
                        combined_parts.append(body_t)
                        break
            except Exception:
                pass

    if not combined_parts and not links_buf:
        return ""
    return title_line + "\n" + "\n".join(combined_parts) + "\n" + "\n".join(links_buf)


def discover_extra_candidates(req_sess, cffi_sess, existing_os_urls=None):
    aqar_cands = {}
    opensooq_cands = {}

    aqar_combos = [
        f"https://aqarmap.com.eg/ar/{deal}/{ptype}/{zone}/?byOwnerOnly=1"
        for zone in AQARMAP_SETTLEMENT_ZONES
        for (deal, ptype) in AQARMAP_PROP_TYPES
    ]
    random.shuffle(aqar_combos)
    for cat_u in aqar_combos[:10]:
        raw_cat = fetch_page(req_sess, cffi_sess, cat_u, timeout_sec=20)
        if raw_cat:
            for m in re.finditer(r"(?:https?://aqarmap\.com\.eg)?(/ar/listing/(\d{7})-[^\s\"'<>)\]?]+)", raw_cat):
                lid = int(m.group(2))
                full_u = "https://aqarmap.com.eg" + m.group(1) if m.group(1).startswith("/") else m.group(1)
                uid = 700000000 + lid
                if lid >= 7050000 and not has_forbidden_url_slug(full_u):
                    aqar_cands[uid] = {"url": full_u}
        time.sleep(2.0)

    os_sample = list(OPENSOOQ_CATEGORY_URLS)
    random.shuffle(os_sample)
    for os_u in os_sample[:3]:
        raw_os = fetch_page(req_sess, cffi_sess, os_u, timeout_sec=20)
        if raw_os:
            for m in re.finditer(r"(?:https?://eg\.opensooq\.com)?(/ar/[^\s\"'<>)\]?]+?/(\d{9,10}))", raw_os):
                oid = int(m.group(2))
                full_u = "https://eg.opensooq.com" + m.group(1) if m.group(1).startswith("/") else m.group(1)
                uid = 800000000 + (oid % 100000000)
                if oid >= OPENSOOQ_MIN_ID and not has_forbidden_url_slug(full_u):
                    opensooq_cands[uid] = {
                        "url": f"https://eg.opensooq.com/ar/search/{oid}",
                        "oid": oid
                    }
        time.sleep(2.0)

    # Crawling existing OpenSooq listing pages to discover related listings
    if existing_os_urls:
        os_urls_sample = list(existing_os_urls)[:3]
        for os_listing_u in os_urls_sample:
            raw_os_listing = fetch_page(req_sess, cffi_sess, os_listing_u, timeout_sec=20)
            if raw_os_listing:
                for m in re.finditer(r"(?:https?://eg\.opensooq\.com)?(/ar/[^\s\"'<>)\]?]+?/(\d{9,10}))", raw_os_listing):
                    oid = int(m.group(2))
                    uid = 800000000 + (oid % 100000000)
                    if oid >= OPENSOOQ_MIN_ID and uid not in opensooq_cands:
                        opensooq_cands[uid] = {
                            "url": f"https://eg.opensooq.com/ar/search/{oid}",
                            "oid": oid
                        }
            time.sleep(2.0)

    q_list = list(EXTRA_QUERIES)
    random.shuffle(q_list)
    for q in q_list[:25]:
        enc = urllib.parse.quote(q)
        for s_url in [
            f"https://search.yahoo.com/search?p={enc}&b=1",
            f"https://www.bing.com/search?q={enc}&first=1"
        ]:
            try:
                r = cffi_sess.get(s_url, timeout=9)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "lxml")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        target = href.split("RU=")[1].split("/RK=")[0] if "RU=" in href else href
                        target = urllib.parse.unquote(target)
                        if has_forbidden_url_slug(target):
                            continue

                        parent_blk = a.find_parent(["div", "li"])
                        if parent_blk and parent_blk.find_parent(["div", "li"]):
                            parent_blk = parent_blk.find_parent(["div", "li"])
                        raw_snip = parent_blk.get_text(" ", strip=True) if parent_blk else ""
                        if re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep)\s+\d{1,2},\s+20\d{2}", raw_snip, flags=re.I):
                            continue

                        m_aq = re.search(r"(https?://aqarmap\.com\.eg/ar/listing/(\d{7})-[^\s\"'<>)\]]+)", target)
                        if m_aq:
                            lid = int(m_aq.group(2))
                            uid = 700000000 + lid
                            if lid >= 7050000 and uid not in aqar_cands:
                                aqar_cands[uid] = {"url": m_aq.group(1)}

                        m_os = re.search(r"eg\.opensooq\.com/ar/[^\s\"'<>)\]]+?/(\d{9,10})", target)
                        if m_os:
                            oid = int(m_os.group(1))
                            uid = 800000000 + (oid % 100000000)
                            if oid >= OPENSOOQ_MIN_ID and uid not in opensooq_cands:
                                opensooq_cands[uid] = {
                                    "url": f"https://eg.opensooq.com/ar/search/{oid}",
                                    "oid": oid
                                }
            except Exception:
                pass
            time.sleep(0.1)

    return aqar_cands, opensooq_cands


def parse_aqarmap_ad(req_sess, cffi_sess, uid, cand_info, banned_accounts):
    url = cand_info["url"]
    if has_forbidden_url_slug(url):
        return None, True, "EXCLUDED_AREA"

    lid = uid - 700000000
    if lid < 7050000:
        return None, True, "OLD_AD"

    raw = fetch_page(req_sess, cffi_sess, url, timeout_sec=22)
    if not raw or len(raw) < 500:
        return None, False, "NO_PAGE"

    clean_full = clean_text(raw)

    if f"EG-{lid}" not in clean_full and "تفاصيل الإعلان" not in clean_full and "نوع المعلن" not in clean_full:
        return None, True, "EXPIRED_OR_REDIRECTED"

    for exp_phrase in ["هذا الإعلان غير متاح", "لم يعد هذا العقار متاح", "تم بيع العقار", "تم تأجير العقار", "انتهت صلاحية الإعلان"]:
        if exp_phrase in clean_full:
            return None, True, "EXPIRED_OR_REDIRECTED"

    pos_spec = clean_full.find("تفاصيل الإعلان")
    if pos_spec == -1:
        pos_spec = clean_full.find("نوع المعلن")
    if pos_spec == -1:
        pos_spec = clean_full.find("مالك عقار")
    if pos_spec == -1:
        return None, True, "BANNED_BROKER_TYPE"

    ad_core = clean_full[max(0, pos_spec - 900): pos_spec + 3000]

    seller_sec = ""
    if "تواصل مع المعلن" in clean_full:
        seller_sec = clean_full.split("تواصل مع المعلن", 1)[1][:280]

    for cut_marker in ["إعلانات ذات صلة", "تواصل مع أصحاب العقارات المماثلة", "أكتشف المزيد من العقارات المشابهة"]:
        if cut_marker in ad_core and ad_core.find(cut_marker) > 400:
            ad_core = ad_core[:ad_core.find(cut_marker)]

    if re.search(r"نوع\s*المعلن[\s:.•\-]*(?:مطور|مسوق|شركة|وسيط|مكتب)", ad_core):
        return None, True, "BANNED_BROKER_TYPE"

    if "مالك عقار" not in ad_core and "مالك العقار" not in ad_core:
        return None, True, "BANNED_BROKER_TYPE"

    is_fresh, age_lbl = check_aqarmap_freshness(ad_core, lid)
    if not is_fresh:
        return None, True, "OLD_AD"

    price_num = 0
    for pm in re.finditer(r"(\d[\d,]{3,11})\s*(?:جنيه|ج\.م|جم|EGP)", ad_core):
        val = int(pm.group(1).replace(",", ""))
        if val >= 2000:
            price_num = val
            break
    if price_num == 0:
        return None, True, "EXPIRED_OR_NO_PRICE"
    price_text = f"{price_num:,} ج.م"

    desc_clean = ad_core
    if "وصف الإعلان" in ad_core:
        desc_clean = ad_core.split("وصف الإعلان", 1)[1]
    elif f"EG-{lid}" in ad_core:
        desc_clean = ad_core.split(f"EG-{lid}", 1)[1]
    elif "مالك عقار" in ad_core:
        desc_clean = ad_core.split("مالك عقار", 1)[1]

    for end_m in ["مزايا العقار", "حفظ ملاحظة", "تواصل مع المعلن", "أظهر المزيد", "وقت الوصول", "تم إضافة الإعلان", "أكتشف المزيد"]:
        if end_m in desc_clean:
            desc_clean = desc_clean.split(end_m, 1)[0]

    title_clean = "وحدة من المالك بالقاهرة الجديدة"
    m_h1 = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    if m_h1 and len(clean_card_title(m_h1.group(1))) > 5:
        title_clean = clean_card_title(m_h1.group(1))[:60]

    header_only = f"{title_clean} {ad_core[:450]}"
    header_and_desc = f"{header_only} {desc_clean}"

    # 🛡️ واعية بالسياق: «قريب من بيت الوطن» تعدي، «في بيت الوطن» تترفض
    _hit = forbidden_area_hit(header_only, STRICT_FORBIDDEN_HEADER)
    if _hit:
        return None, True, "EXCLUDED_AREA"
    if has_installment_offer(header_and_desc):
        return None, True, "INSTALLMENT_AD"

    if not any(w in header_and_desc.lower() for w in [x.lower() for x in STRICT_NEW_CAIRO_HEADER]):
        return None, True, "NOT_NEW_CAIRO"
    if not any(w in header_and_desc.lower() for w in [x.lower() for x in NEW_CAIRO_WORDS]):
        return None, True, "NOT_NEW_CAIRO"

    seller = "مالك عقار"
    # Search in full text for seller name (2 words max to filter out company names)
    for m_s in re.finditer(r"([A-Za-z\u0600-\u06FF]{2,20}(?:\s+[A-Za-z\u0600-\u06FF]{2,20})?)\s*(\d{1,2})\s*(?:عقار|عقارين|إعلان|اعلان)", clean_full):
        cand_s = m_s.group(1).strip(" .-:|")
        cnt_val = int(m_s.group(2))
        if 2 <= len(cand_s) <= 35 and cnt_val <= 20:
            if re.search(r"(?:Real Estate|Consultancy|Company|company|Broker|agency|Agency|شركة|مؤسسة|مكتب|كاتب|وسيط|مسوق|عقارات|استشارات)", cand_s, re.I):
                continue
            if "عقار" in cand_s or "إعلان" in cand_s or "نوع" in cand_s or "تواصل" in cand_s or "سجل" in cand_s or "شركات" in cand_s:
                continue
            seller = cand_s
            break

    for m_cnt in re.finditer(r"\b(\d{1,4})\s*(?:عقار|عقارات|إعلان|اعلان)", clean_full):
        if int(m_cnt.group(1)) > 20:
            return None, True, "BANNED_BROKER_PORTFOLIO"

    acc_key = f"name:{seller.lower().strip()}" if seller not in ("مالك", "مالك عقار", "المالك") else ""
    if acc_key and acc_key in banned_accounts:
        return None, True, "BANNED_ACCOUNT"

    area = "مدرج بالإعلان"
    m_area = re.search(r"(\d{2,4})\s*(?:متر|م²|م2)", f"{title_clean} {ad_core}")
    if m_area:
        area = f"{m_area.group(1)} م²"

    beds = ""
    m_beds = re.search(r"(\d{1,2})\s*(?:غرف|غرفة)", f"{title_clean} {ad_core}")
    if not m_beds:
        m_beds = re.search(r"(?:الغرف|غرف)[^\d]{0,8}(\d{1,2})", ad_core)
    if m_beds and 1 <= int(m_beds.group(1)) <= 12:
        beds = f"{m_beds.group(1)} غرف"

    baths = ""
    m_baths = re.search(r"(\d{1,2})\s*حمام", f"{title_clean} {ad_core}")
    if not m_baths:
        m_baths = re.search(r"(?:الحمامات|حمام)[^\d]{0,8}(\d{1,2})", ad_core)
    if m_baths and 1 <= int(m_baths.group(1)) <= 10:
        baths = f"{m_baths.group(1)} حمام"

    deal, category, subtype = classify_unit(url, title_clean, ad_core[:650], price_num)
    now_iso = datetime.now(CAIRO_TZ).isoformat()
    safe_title = sanitize_for_dubizzle_compatibility(title_clean)
    safe_desc = sanitize_for_dubizzle_compatibility(desc_clean.strip()[:600])

    return {
        "ad_id": uid,
        "source": "عقارماب",
        "title": safe_title,
        "price_num": price_num,
        "price_text": price_text,
        "area": area,
        "beds": beds,
        "baths": baths,
        "deal": deal,
        "category": category,
        "subtype": subtype,
        "seller_name": seller,
        "account_id": acc_key,
        "seller_ads_count": 1,
        "fresh_tier": 3,
        "description": f"[عقارماب • {age_lbl}] {safe_desc}",
        "url": url,
        "today_verified": True,
        "verified_v12": True,
        "scraped_at": now_iso
    }, True, "ADDED_OWNER_AQARMAP"


def parse_opensooq_ad(req_sess, cffi_sess, uid, cand_info, banned_accounts):
    url = cand_info["url"]
    oid = cand_info["oid"]

    if has_forbidden_url_slug(url):
        return None, True, "EXCLUDED_AREA"

    if oid < OPENSOOQ_MIN_ID:
        return None, True, "OLD_AD"

    raw = fetch_page(req_sess, cffi_sess, url, timeout_sec=22)
    if not raw or len(raw) < 400:
        return None, False, "NO_PAGE"

    clean_full = clean_text(raw)

    if "المعلن" in clean_full:
        idx_m = clean_full.find("المعلن")
        clean_full = clean_full[max(0, idx_m - 450):]

    ad_core = clean_full
    for cut_marker in ["إعلانات مشابهة", "إعلانات مقترحة", "الأسئلة الشائعة", "بيع كل شئ على السوق المفتوح"]:
        if cut_marker in ad_core:
            ad_core = ad_core.split(cut_marker)[0]

    if "المعلن" not in ad_core and "الوصف" not in ad_core:
        return None, False, "NO_PAGE"

    if not re.search(r"المعلن[\s:.•\-]*المالك", ad_core):
        return None, True, "BANNED_BROKER_TYPE"

    is_fresh, age_lbl = check_opensooq_freshness(ad_core, oid)
    if not is_fresh:
        return None, True, "OLD_AD"

    desc_clean = ad_core
    if "الوصف" in ad_core:
        desc_clean = ad_core.split("الوصف", 1)[1]
    if "بلغ عن إساءة" in desc_clean:
        desc_clean = desc_clean.split("بلغ عن إساءة", 1)[0]

    title_clean = "وحدة من المالك بالقاهرة الجديدة"
    m_h1 = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    if m_h1 and len(clean_card_title(m_h1.group(1))) > 5:
        title_clean = clean_card_title(m_h1.group(1)).split("|")[0].strip()[:60]

    header_only = f"{title_clean} {ad_core[:400]}"
    header_and_desc = f"{title_clean} {ad_core.split('بلغ عن إساءة')[0]}"

    # 🛡️ واعية بالسياق + رفض التقسيط
    _hit = forbidden_area_hit(title_clean, STRICT_FORBIDDEN_HEADER)
    if _hit:
        return None, True, "EXCLUDED_AREA"
    if has_installment_offer(header_and_desc):
        return None, True, "INSTALLMENT_AD"

    if not any(w in header_and_desc.lower() for w in [x.lower() for x in STRICT_NEW_CAIRO_HEADER]):
        return None, True, "NOT_NEW_CAIRO"
    if not any(w in header_and_desc.lower() for w in [x.lower() for x in NEW_CAIRO_WORDS]):
        return None, True, "NOT_NEW_CAIRO"

    seller = "مالك العقار"
    m_av = re.search(r"Avatar[\s.•\-]*([A-Za-z\u0600-\u06FF0-9_\s]{2,35}?)\s*(?:تابِع|الردّ|التقييم)", ad_core)
    if m_av:
        cand_s = m_av.group(1).strip(" .-:|")
        if 2 <= len(cand_s) <= 35:
            seller = cand_s

    acc_key = f"name:{seller.lower().strip()}" if seller not in ("مالك", "مالك العقار", "المالك") else ""
    if acc_key and acc_key in banned_accounts:
        return None, True, "BANNED_ACCOUNT"

    price_num = 0
    for pm in re.finditer(r"(\d[\d,]{3,11})\s*(?:جنيه|ج\.م|جم|EGP)", header_and_desc):
        val = int(pm.group(1).replace(",", ""))
        if val >= 2000:
            price_num = val
            break
    if price_num == 0:
        m_p2 = re.search(r"\b(\d{1,3}(?:,\d{3}){1,3})\b", title_clean)
        if m_p2:
            price_num = int(m_p2.group(1).replace(",", ""))
    if price_num == 0:
        return None, True, "EXPIRED_OR_NO_PRICE"
    price_text = f"{price_num:,} ج.م"

    area = "مدرج بالإعلان"
    m_area = re.search(r"(?:المساحة|مساحة)[^\d]{0,10}(\d{2,4})", header_and_desc)
    if m_area:
        area = f"{m_area.group(1)} م²"

    beds = ""
    m_beds = re.search(r"(?:عدد الغرف|غرف)[^\d]{0,6}(\d{1,2})", header_and_desc)
    if m_beds and 1 <= int(m_beds.group(1)) <= 12:
        beds = f"{m_beds.group(1)} غرف"

    deal, category, subtype = classify_unit(url, title_clean, header_and_desc[:600], price_num)
    now_iso = datetime.now(CAIRO_TZ).isoformat()
    safe_title = sanitize_for_dubizzle_compatibility(title_clean)
    safe_desc = sanitize_for_dubizzle_compatibility(desc_clean.strip()[:600])

    return {
        "ad_id": uid,
        "source": "السوق المفتوح",
        "title": safe_title,
        "price_num": price_num,
        "price_text": price_text,
        "area": area,
        "beds": beds,
        "baths": "",
        "deal": deal,
        "category": category,
        "subtype": subtype,
        "seller_name": seller,
        "account_id": acc_key,
        "seller_ads_count": 1,
        "fresh_tier": 3,
        "description": f"[السوق المفتوح • {age_lbl}] {safe_desc}",
        "url": url,
        "today_verified": True,
        "verified_v12": True,
        "scraped_at": now_iso
    }, True, "ADDED_OWNER_OPENSOOQ"


def parse_dubizzle_log():
    dub_stats = {
        "inspected": 0,
        "added_owners": 0,
        "banned_brokers": 0,
        "excluded_or_old": 0
    }
    if not os.path.exists("dubizzle_run.log"):
        return dub_stats
    try:
        with open("dubizzle_run.log", "r", encoding="utf-8", errors="ignore") as f:
            log_txt = f.read()
        m_insp = re.search(r"Total inspected this run:\s*(\d+)", log_txt)
        if m_insp:
            dub_stats["inspected"] = int(m_insp.group(1))
        dub_stats["added_owners"] = len(re.findall(r"\] ADDED:", log_txt))
        m_sum = re.search(r"Inspection Summary:\s*(\{[^\}]+\})", log_txt)
        if m_sum:
            raw_dict = m_sum.group(1)
            b_cnt = 0
            ex_cnt = 0
            for k, v in re.findall(r"'([^']+)':\s*(\d+)", raw_dict):
                val = int(v)
                if "BANNED" in k:
                    b_cnt += val
                elif k in ("OLD_AD", "EXCLUDED_AREA", "NOT_NEW_CAIRO", "EXPIRED"):
                    ex_cnt += val
            dub_stats["banned_brokers"] = b_cnt
            dub_stats["excluded_or_old"] = ex_cnt
    except Exception:
        pass
    return dub_stats


TG_TOKEN_SHAPE = re.compile(r"^\d{6,}:[A-Za-z0-9_-]{30,}$")


def get_working_tg_token():
    """
    ✅ FIX: متغير البيئة TELEGRAM_BOT_TOKEN فيه التوكن **خام**
       (شكله `123456789:AAH...`)، مش base64 زي ما كان مكتوب في الكود القديم.
       بنجرّب الخام الأول، ولو ما طابقش الشكل بنفكّ base64 للتوافق مع أي إعداد قديم.
    """
    for raw in TG_B64_LIST:
        cands = []
        raw = (raw or "").strip()
        if not raw:
            continue
        if TG_TOKEN_SHAPE.match(raw):
            cands.append(raw)                       # توكن خام من البيئة
        else:
            try:                                    # متوافق مع الشكل القديم (base64)
                cands.append(base64.b64decode(raw).decode("utf-8").strip())
            except Exception:
                pass
        for tok in cands:
            if not tok:
                continue
            try:
                r = std_requests.get(f"https://api.telegram.org/bot{tok}/getMe", timeout=8)
                if r.status_code == 200 and r.json().get("ok"):
                    return tok
            except Exception:
                pass
    return ""


def sync_telegram_and_send_reports(data, run_report):
    tg_token = get_working_tg_token()
    if not tg_token:
        return

    chat_ids = set(str(x) for x in data.get("telegram_chat_ids", []) if str(x).strip())
    welcomed_ids = set(str(x) for x in data.get("telegram_welcomed_ids", []) if str(x).strip())

    try:
        std_requests.get(f"https://api.telegram.org/bot{tg_token}/deleteWebhook?drop_pending_updates=false", timeout=6)
    except Exception:
        pass

    last_update_id = int(data.get("telegram_last_update_id", 0) or 0)
    try:
        offset = last_update_id + 1 if last_update_id > 0 else 0
        r = std_requests.get(
            f"https://api.telegram.org/bot{tg_token}/getUpdates?limit=50&timeout=1&offset={offset}&allowed_updates=message,my_chat_member,channel_post",
            timeout=8
        )
        if r.status_code == 200:
            updates = r.json().get("result", [])
            for u in updates:
                uid = u.get("update_id", 0)
                if uid > last_update_id:
                    last_update_id = uid
                for key in ("message", "edited_message", "my_chat_member", "channel_post"):
                    msg = u.get(key)
                    if isinstance(msg, dict):
                        chat = msg.get("chat") or {}
                        cid = chat.get("id")
                        if cid:
                            chat_ids.add(str(cid))
                        frm = msg.get("from") or {}
                        fid = frm.get("id")
                        if fid and not frm.get("is_bot"):
                            chat_ids.add(str(fid))
    except Exception:
        pass

    ads = data.get("ads", [])
    notified_ids = set(int(x) for x in data.get("notified_ids_v1", []) if str(x).isdigit())

    if not notified_ids and ads:
        all_current_ids = [int(a["ad_id"]) for a in ads if "ad_id" in a]
        if len(all_current_ids) > 2:
            notified_ids.update(all_current_ids[2:])

    for cid in chat_ids:
        if cid not in welcomed_ids:
            welcome_txt = (
                "تم تفعيل رادار مصيدة الملاك VIP على تليجرام بنجاح.\n\n"
                "• هيوصلك هنا إشعار فوري بأي مالك جديد ينزل في القاهرة الجديدة والتجمعات فقط "
                "(دوبيزل + عقارماب + السوق المفتوح).\n"
                "• وهيوصلك تقرير الرن التفصيلي بعد كل جولة."
            )
            try:
                std_requests.post(
                    f"https://api.telegram.org/bot{tg_token}/sendMessage",
                    json={"chat_id": cid, "text": welcome_txt},
                    timeout=10
                )
                welcomed_ids.add(cid)
            except Exception:
                pass

    if chat_ids:
        new_ads_to_notify = [a for a in ads if int(a.get("ad_id", 0)) not in notified_ids]
        for a in reversed(new_ads_to_notify[:8]):
            aid = int(a.get("ad_id", 0))
            src = a.get("source", "دوبيزل")
            cat = a.get("category", "عقارات")
            sub = a.get("subtype", "وحدة")
            price = a.get("price_text", "مدرج بالإعلان")
            area = a.get("area", "مدرج")
            seller = a.get("seller_name", "المالك")
            title = a.get("title", "")
            url = a.get("url", "")

            msg_text = (
                f"مالك مباشر جديد ({src})\n"
                f"━━━━━━━━━━━━━━\n"
                f"الفئة: {cat} ({sub})\n"
                f"السعر: {price}\n"
                f"المساحة: {area}\n"
                f"الناشر: {seller} (مالك عقار)\n"
                f"العنوان: {title}\n"
                f"━━━━━━━━━━━━━━\n"
                f"رابط الإعلان المباشر:\n{url}"
            )
            sent_ok = False
            for cid in chat_ids:
                try:
                    resp = std_requests.post(
                        f"https://api.telegram.org/bot{tg_token}/sendMessage",
                        json={
                            "chat_id": cid,
                            "text": msg_text,
                            "disable_web_page_preview": False
                        },
                        timeout=10
                    )
                    if resp.status_code == 200:
                        sent_ok = True
                except Exception:
                    pass
            if sent_ok:
                notified_ids.add(aid)
            time.sleep(0.4)

        rep_msg = (
            f"تقرير الرن التفصيلي | مصيدة الملاك\n"
            f"━━━━━━━━━━━━━━\n"
            f"التوقيت: {run_report['run_time']}\n"
            f"إجمالي الملاك بالموقع الآن: {run_report['total_saved_owners']} مالك\n"
            f"   • دوبيزل: {run_report['dubizzle_total']} | عقارماب: {run_report['aqarmap_total']} | السوق المفتوح: {run_report['opensooq_total']}\n"
            f"   • وحدات بيع: {run_report['sale_total']} | وحدات إيجار: {run_report['rent_total']}\n"
            f"━━━━━━━━━━━━━━\n"
            f"تفاصيل ما حدث في هذا الرن:\n"
            f"• إعلانات تم فحصها بالرن: {run_report['total_inspected_this_run']}\n"
            f"• ملاك جدد تم صيدهم بالرن: {run_report['total_new_owners_this_run']}\n"
            f"• سماسرة وشركات تم حظرهم بالرن: {run_report['total_brokers_banned_this_run']}\n"
            f"• إعلانات مستبعدة (قديمة/خارج التجمع): {run_report['total_excluded_this_run']}\n"
            f"• إجمالي الحسابات المحظورة بالبلاك ليست: {run_report['total_blacklisted_accounts']} حساب"
        )
        for cid in chat_ids:
            try:
                std_requests.post(
                    f"https://api.telegram.org/bot{tg_token}/sendMessage",
                    json={"chat_id": cid, "text": rep_msg},
                    timeout=10
                )
            except Exception:
                pass

    data["telegram_chat_ids"] = sorted(list(chat_ids))
    data["telegram_welcomed_ids"] = sorted(list(welcomed_ids))
    data["notified_ids_v1"] = sorted(list(notified_ids))[-5000:]
    data["telegram_last_update_id"] = last_update_id


def run_extra_radar():
    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    now_dt = datetime.now(CAIRO_TZ)
    ads = data.get("ads", [])

    saved_meta = {}
    for a in ads:
        if "source" not in a:
            a["source"] = "دوبيزل"
        if "_extra_meta" in a and isinstance(a["_extra_meta"], dict):
            meta_cand = a.pop("_extra_meta")
            if not saved_meta:
                saved_meta = meta_cand

    # ✅ FIX(L7): كانت قائمة بـ 15 رقم إعلان مكتوبة يدوي في الكود، وبتتمسح من
    #    ads.json في **كل رَن** من غير أي سطر في اللوج. لو رجعت الإعلانات دي ظهرت
    #    تاني من المصدر، كانت بتتمسح تاني — يعني شغل ضايع للأبد.
    #    بقت من متغير بيئة (فاضية افتراضياً)، وأي حذف بيتسجّل في اللوج.
    unverified_fallback_ids = {
        int(x) for x in re.split(r"[,\s]+", (os.environ.get("DROP_AD_IDS") or "").strip())
        if x.isdigit()
    }
    if unverified_fallback_ids:
        print(f"⚠️  هيتم حذف {len(unverified_fallback_ids)} إعلان بسبب DROP_AD_IDS")
    all_existing_list = list(ads)
    for backup_ad in saved_meta.get("extra_ads_backup", []):
        if isinstance(backup_ad, dict) and "ad_id" in backup_ad:
            all_existing_list.append(backup_ad)

    kept_map = {}
    for a in all_existing_list:
        if "ad_id" not in a:
            continue
        aid = int(a["ad_id"])
        if aid in unverified_fallback_ids or aid in kept_map:
            continue
        if a.get("source") == "عقارماب" and int(a.get("price_num", 0)) == 0:
            continue
        # ✅ FIX(H3): إعلانات دوبيزل بتوصل متصنّفة صح من scraper.py (من الفئة الرسمية
        #    في breadcrumb دوبيزل). إعادة تصنيفها هنا بالكلمات المفتاحية كانت بتقلب النتيجة —
        #    إعلان "شقة للبيع" كان بيتحوّل "مبانى و أراضى".
        if a.get("source") != "دوبيزل" or not a.get("category"):
            deal, cat, sub = classify_unit(
                a.get("url", ""),
                a.get("title", ""),
                a.get("description", ""),
                int(a.get("price_num", 0))
            )
            a["deal"] = deal
            a["category"] = cat
            a["subtype"] = sub
        kept_map[aid] = a

    checked_extra = set(int(x) for x in (data.get("checked_extra_v15") or saved_meta.get("checked_extra_v15") or []) if str(x).isdigit())
    banned_accounts = set(data.get("banned_accounts_v7", []))

    if not data.get("telegram_chat_ids") and saved_meta.get("telegram_chat_ids"):
        data["telegram_chat_ids"] = saved_meta["telegram_chat_ids"]
    if not data.get("telegram_welcomed_ids") and saved_meta.get("telegram_welcomed_ids"):
        data["telegram_welcomed_ids"] = saved_meta["telegram_welcomed_ids"]
    if not data.get("notified_ids_v1") and saved_meta.get("notified_ids_v1"):
        data["notified_ids_v1"] = saved_meta["notified_ids_v1"]

    req_sess = std_requests.Session()
    cffi_sess = cffi_requests.Session(impersonate="chrome120")

    # ✅ FIX(M2): الإعلانات بتتخزن بمفتاح "url" مش "link" ⇒ القائمة دي كانت فاضية دايماً
    existing_os_urls = [
        (a.get("url") or a.get("link") or "")
        for a in (data.get("ads") or [])
        if a.get("source") == "السوق المفتوح" and (a.get("url") or a.get("link"))
    ]
    # Additional hardcoded OpenSooq listing URLs for more diverse crawling
    extra_os_start = ["https://eg.opensooq.com/ar/search/286924884", "https://eg.opensooq.com/ar/search/288468900", "https://eg.opensooq.com/ar/search/286978162"]
    existing_os_urls = [u for u in existing_os_urls if u] + [u for u in extra_os_start if u not in existing_os_urls]
    aqar_cands, os_cands = discover_extra_candidates(req_sess, cffi_sess, existing_os_urls)

    extra_inspected = 0
    extra_added = 0
    extra_banned = 0
    extra_excluded = 0

    for uid, cand_info in list(aqar_cands.items())[:30]:
        if uid in kept_map or uid in checked_extra:
            continue
        item, mark_chk, reason = parse_aqarmap_ad(req_sess, cffi_sess, uid, cand_info, banned_accounts)
        print(f"[Aqarmap Live Check] ID={uid} | Reason={reason}")
        if reason != "NO_PAGE":
            extra_inspected += 1
        if mark_chk:
            checked_extra.add(uid)
        if "BANNED" in reason:
            extra_banned += 1
        elif reason in ("OLD_AD", "EXCLUDED_AREA", "NOT_NEW_CAIRO", "EXPIRED_OR_REDIRECTED", "EXPIRED_OR_NO_PRICE"):
            extra_excluded += 1
        if item:
            kept_map[uid] = item
            extra_added += 1
            print(f"[Aqarmap] ADDED Live Owner: {uid} | {item['category']} ({item['subtype']}) | {item['price_text']} | {item['seller_name']}")
        time.sleep(3.2)

    for uid, cand_info in list(os_cands.items())[:20]:
        if uid in kept_map or uid in checked_extra:
            continue
        item, mark_chk, reason = parse_opensooq_ad(req_sess, cffi_sess, uid, cand_info, banned_accounts)
        print(f"[OpenSooq Live Check] ID={uid} | Reason={reason}")
        if reason != "NO_PAGE":
            extra_inspected += 1
        if mark_chk:
            checked_extra.add(uid)
        if "BANNED" in reason:
            extra_banned += 1
        elif reason in ("OLD_AD", "EXCLUDED_AREA", "NOT_NEW_CAIRO", "EXPIRED_OR_NO_PRICE"):
            extra_excluded += 1
        if item:
            kept_map[uid] = item
            extra_added += 1
            print(f"[OpenSooq] ADDED Live Owner: {uid} | {item['category']} ({item['subtype']}) | {item['price_text']} | {item['seller_name']}")
        time.sleep(3.2)

    final_ads = list(kept_map.values())
    # PERMANENT FIX: حذف الإعلانات القديمة (>7 أيام) من extra sources
    ad_cutoff = datetime.now(CAIRO_TZ) - timedelta(days=CHECKED_TTL_DAYS)
    kept_after_ttl = []
    ttl_pruned_extra = 0
    for a in final_ads:
        ts_str = str(a.get("scraped_at") or a.get("verified_at") or "")
        if ts_str:
            try:
                dt = datetime.fromisoformat(ts_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=CAIRO_TZ)
                if dt < ad_cutoff:
                    ttl_pruned_extra += 1
                    continue
            except Exception:
                pass
        kept_after_ttl.append(a)
    if ttl_pruned_extra:
        print(f"PERMANENT FIX: حُذف {ttl_pruned_extra} إعلان قديم (>{CHECKED_TTL_DAYS} أيام) من extra sources")
    final_ads = kept_after_ttl
    final_ads.sort(key=lambda x: (x.get("fresh_tier", 2), x.get("ad_id", 0)), reverse=True)

    dub_stats = parse_dubizzle_log()
    # ✅ FIX(C10): parse_dubizzle_log() بتقرا ملف dubizzle_run.log. لو الملف مش موجود
    #    (الـ workflow الجديد بيرفع اللوج كـ artifact بدل ما يهرّبه جوه ads.json)،
    #    الأرقام كانت بترجع صفر ⇒ العداد يظهر «0 مفحوص / 0 جديد» رغم إن السكريبر اشتغل.
    #    الحل: ناخد الأرقام من التقرير اللي scraper.py كتبه بنفسه في ads.json.
    if not any(dub_stats.values()):
        _prev = data.get("last_run_report") or {}
        dub_stats = {
            "inspected":       int(_prev.get("dubizzle_inspected") or 0),
            "added_owners":    int(_prev.get("dubizzle_new_owners") or 0),
            "banned_brokers":  int(_prev.get("total_brokers_banned_this_run") or 0),
            "excluded_or_old": int(_prev.get("total_excluded_this_run") or 0),
        }
        if any(dub_stats.values()):
            print(f"[report] مفيش dubizzle_run.log — أخدت أرقام دوبيزل من التقرير المحفوظ: {dub_stats}")

    dub_total = sum(1 for a in final_ads if a.get("source", "دوبيزل") == "دوبيزل")
    aqar_total = sum(1 for a in final_ads if a.get("source") == "عقارماب")
    os_total = sum(1 for a in final_ads if a.get("source") == "السوق المفتوح")
    sale_total = sum(1 for a in final_ads if a.get("deal") == "بيع")
    rent_total = sum(1 for a in final_ads if a.get("deal") == "إيجار")

    run_report = {
        "run_time": now_dt.strftime("%Y/%m/%d, %I:%M %p"),
        "total_saved_owners": len(final_ads),
        "dubizzle_total": dub_total,
        "aqarmap_total": aqar_total,
        "opensooq_total": os_total,
        "sale_total": sale_total,
        "rent_total": rent_total,
        "total_inspected_this_run": dub_stats["inspected"] + extra_inspected,
        "dubizzle_inspected": dub_stats["inspected"],
        "extra_inspected": extra_inspected,
        "total_new_owners_this_run": dub_stats["added_owners"] + extra_added,
        "dubizzle_new_owners": dub_stats["added_owners"],
        "extra_new_owners": extra_added,
        "total_brokers_banned_this_run": dub_stats["banned_brokers"] + extra_banned,
        "total_excluded_this_run": dub_stats["excluded_or_old"] + extra_excluded,
        "total_blacklisted_accounts": len(banned_accounts),
        # ✅ FIX: كان بيعدّ checked_ids_v10 (قائمة قديمة) — المرجع الحالي v11 (dict).
        "total_checked_ads_memory": len(checked_extra) + len(
            data.get("checked_ids_v11") or data.get("checked_ids_v10") or [])
    }

    print("==========================================")
    print(f"RUN REPORT SUMMARY: {json.dumps(run_report, ensure_ascii=False)}")
    print("==========================================")

    data["last_scrape"] = now_dt.strftime("%Y/%m/%d, %I:%M %p")
    data["total_ads"] = len(final_ads)
    data["last_run_report"] = run_report
    data["checked_extra_v15"] = sorted(list(checked_extra))[-4000:]
    data["banned_accounts_v7"] = sorted(list(banned_accounts))[-2500:]

    sync_telegram_and_send_reports(data, run_report)

    extra_only_list = [dict(a) for a in final_ads if a.get("source") in ("عقارماب", "السوق المفتوح")]
    meta_payload = {
        "checked_extra_v15": data["checked_extra_v15"][-2000:],
        "telegram_chat_ids": data.get("telegram_chat_ids", []),
        "telegram_welcomed_ids": data.get("telegram_welcomed_ids", []),
        "notified_ids_v1": data.get("notified_ids_v1", [])[-2000:],
        "extra_ads_backup": extra_only_list
    }
    attached_cnt = 0
    for a in final_ads:
        if a.get("source", "دوبيزل") == "دوبيزل":
            a["_extra_meta"] = meta_payload
            attached_cnt += 1
            if attached_cnt >= 3:
                break

    data["ads"] = final_ads

    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    run_extra_radar()
