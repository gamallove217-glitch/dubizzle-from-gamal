import json
import os
import random
import re
import time
import urllib.parse
import requests as std_requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

CAIRO_TZ = timezone(timedelta(hours=2))
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
TG_TOKEN = "9185906527:AAHRgql8B_k-Y4fB7CrAjjaQXhvo6Rz7xFU"

STRICT_NEW_CAIRO_HEADER = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "القطامية", "القطاميه"
]

NEW_CAIRO_WORDS = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "التجمع", "الحي الأول", "الحي الاول", "الحي الثاني",
    "الحي التاني", "الحي الثالث", "الحي التالت", "الحي الرابع", "الحي الخامس",
    "النرجس", "اللوتس", "الأندلس", "الاندلس", "الياسمين", "البنفسج",
    "جنوب الأكاديمية", "جنوب الاكاديمية", "الاكاديمية", "شرق الأكاديمية", "شرق الاكاديمية",
    "المستثمرين", "بيت الوطن", "النورث هاوس", "القرنفل", "تمر حنة", "اللؤلؤة",
    "ابو الهول", "أبو الهول", "جاردينيا هايتس", "غرب الجولف", "غرب أرابيلا", "غرب ارابيلا",
    "أرابيلا", "ارابيلا", "الشويفات", "الداون تاون", "التسعين", "القطامية", "القطاميه",
    "كايرو فيستيفال", "كايرو فستيفال", "ميفيدا", "ماونتن فيو", "هايد بارك", "بالم هيلز",
    "سوديك", "فيليت", "ايست تاون", "ايستاون", "زيد ايست", "تريو", "ازار", "دار مصر",
    "سكن مصر", "جنة", "الجامعة الأمريكية", "الجامعه الامريكيه", "الجولدن سكوير",
    "الدبلوماسيين", "لافيستا", "الباتيو", "مون فالي", "ذا سكوير", "فيفث سكوير", "سراي"
]

FORBIDDEN_URL_SLUGS = [
    "el-rehab", "madinaty", "mostakbal-city", "new-heliopolis", "el-shorouk",
    "badr-city", "new-administrative-capital", "el-obour", "nasr-city", "heliopolis",
    "maadi", "mokattam", "sheikh-zayed", "6th-of-october", "chalet", "north-coast",
    "ain-sokhna", "شاليهات-مصايف", "شقق-ومنازل-العطلات", "الرحاب", "مدينتي",
    "الشروق", "العاصمة-الادارية", "المستقبل", "مدينة-نصر", "مصر-الجديدة"
]

STRICT_FORBIDDEN_EVERYWHERE = [
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
    "الرحاب", "مدينة الرحاب", "مدينتي", "مدينتى", "الشروق", "مدينة الشروق",
    "مدينة المستقبل", "المستقبل سيتي", "مدينة بدر", "العبور", "العاصمة الإدارية",
    "العاصمه الاداريه", "تاج سيتي", "هليوبوليس الجديدة", "هليوبوليس الجديده"
]

BROKER_AND_COMPANY_PHRASES = [
    "متاح اكتر من", "متاح أكثر من", "بمساحات مختلفه", "بمساحات مختلفة",
    "متاح لدينا", "يوجد لدينا", "متوفر لدينا", "لدينا عروض", "لدينا وحدات",
    "أدوار متكررة", "ادوار متكرره", "أطول فترة سداد", "اطول فتره سداد",
    "بدون فوائد", "سجل بياناتك", "امتلك وحدتك", "احجز وحدتك", "احجز شقتك",
    "تعاقد الآن", "تعاقد الان", "بمقدم يبدأ من", "اقساط تصل الى", "أقساط تصل إلى",
    "باقساط متساويه", "بأقساط متساوية", "بالتقسيط المريح", "بدون عمولة", "بدون عمولات",
    "عمولة المكتب", "عموله المكتب", "كود الإعلان", "كود الاعلان", "كود الوحدة", "كود الوحده",
    "للتسويق العقاري", "للاستثمار العقاري", "للتطوير العقاري", "مطور عقاري",
    "شركة عقارية", "مكتب عقاري", "مكتب عقارات", "لعدم الإحراج مع الزملاء",
    "بخصم 50%", "بخصم كاش", "طرح جديد", "مرحلة جديدة"
]

BROKER_SELLER_WORDS = [
    "real estate", "realestate", "properties", "property", "group", "developments",
    "development", "developer", "realtor", "realtors", "broker", "investment",
    "logo", "للتسويق", "للعقارات", "للاستثمار", "للتطوير", "جروب", "شركة", "شركه",
    "مكتب", "عقارك", "بيتك", "هوم", "home", "capital", "house", "consulting", "agency"
]

AQARMAP_SETTLEMENT_ZONES = [
    "cairo/new-cairo/the-5th-settlement",
    "cairo/new-cairo/compounds-in-fifth-settlement",
    "cairo/new-cairo/first-settlement",
    "cairo/new-cairo/third-settlement",
    "cairo/new-cairo/el-katameya"
]

AQARMAP_PROP_TYPES = [
    ("for-sale", "apartment"),
    ("for-rent", "apartment"),
    ("for-rent", "furnished-apartment"),
    ("for-sale", "villa"),
    ("for-rent", "villa"),
    ("for-sale", "land"),
    ("for-rent", "land"),
    ("for-sale", "building"),
    ("for-rent", "building"),
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
    'site:aqarmap.com.eg/ar/listing/ "التجمع الخامس" "مالك عقار" -الرحاب -مدينتي -المستقبل -الشروق',
    'site:aqarmap.com.eg/ar/listing/ "القاهرة الجديدة" "مالك عقار" -الرحاب -مدينتي -المستقبل -الشروق',
    'site:aqarmap.com.eg/ar/listing/ "التجمع الأول" "مالك عقار" -الرحاب -مدينتي',
    'site:aqarmap.com.eg/ar/listing/ "التجمع الثالث" "مالك عقار" -الرحاب -مدينتي',
    'site:aqarmap.com.eg/ar/listing/ "القطامية" "مالك عقار" -الرحاب -مدينتي',
    'site:aqarmap.com.eg/ar/listing/ "النرجس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "اللوتس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "الياسمين" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "البنفسج" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "بيت الوطن" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "جنوب الأكاديمية" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "الأندلس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "المستثمرين" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "القرنفل" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "شقة مفروشة" "التجمع الخامس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "فيلا" "التجمع الخامس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "إداري" "التجمع الخامس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "تجاري" "التجمع الخامس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "طبي" "التجمع الخامس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "أراضي" "التجمع الخامس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing/ "مباني" "التجمع الخامس" "مالك عقار"',
    'site:eg.opensooq.com/ar/ "التجمع الخامس" "المعلن" "المالك" -الرحاب -مدينتي -الشروق',
    'site:eg.opensooq.com/ar/ "القاهرة الجديدة" "المعلن" "المالك" -الرحاب -مدينتي -الشروق',
    'site:eg.opensooq.com/ar/ "التجمع الخامس" "شقق للايجار" "المالك"',
    'site:eg.opensooq.com/ar/ "التجمع الخامس" "فلل" "المالك"',
    'site:eg.opensooq.com/ar/ "التجمع الخامس" "تجاري" "المالك"',
    'site:eg.opensooq.com/ar/ "التجمع الخامس" "أراضي" "المالك"',
    'site:eg.opensooq.com/ar/ "التجمع الخامس" "عمارات" "المالك"'
]


def clean_text(md):
    txt = (md or "").translate(AR_DIGITS)
    txt = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"[*#_`~>]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


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
    t_and_u = f"{title_clean} {u_dec}".lower()
    header_str = (header_clean or "").lower()
    all_check = f"{t_and_u} {header_str}"

    deal = "بيع"
    if any(w in all_check for w in [
        "للإيجار", "للايجار", "for-rent", "شقق للايجار", "فلل للايجار",
        "تجاري للايجار", "أراضي للايجار", "عمارات للايجار", "غرف ومشاركة",
        "furnished-apartment", "شقة مفروشة", "شقق مفروشة", "إيجار مفروش"
    ]):
        deal = "إيجار"
    elif 0 < price_num < 150000:
        deal = "إيجار"

    if any(w in all_check for w in [
        "/land/", "أراضي للبيع", "أراضي للايجار", "اراضي للبيع", "قطعة أرض",
        "قطعه ارض", "أرض للبيع", "ارض للبيع", "أرض سكنية", "أرض تجارية", "أراض "
    ]):
        return deal, "مبانى و أراضى", "أراض"

    if any(w in all_check for w in [
        "/building/", "عمارات للبيع", "عمارات للايجار", "عمارة كاملة", "عماره كامله",
        "عمارة للبيع", "عماره للبيع", "مبنى كامل", "مباني للبيع", "مبنى للبيع"
    ]):
        return deal, "مبانى و أراضى", "مبنى"

    if any(w in all_check for w in [
        "/medical/", "عيادة", "عياده", "صيدلية", "صيدليه", "مركز طبي", "وحدة طبية", "طبي للبيع", "طبي للإيجار"
    ]):
        category = "عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"
        return deal, category, "طبي"

    if any(w in all_check for w in [
        "/administrative/", "مكتب", "إداري", "اداري", "مقر إداري", "مقر اداري", "وحدة إدارية", "مكاتب"
    ]):
        category = "عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"
        return deal, category, "إداري"

    if any(w in all_check for w in [
        "/commercial/", "تجاري للبيع", "تجاري للايجار", "محل ", "محل للبيع", "محل للإيجار",
        "محل للايجار", "تجاري", "تجارى", "معرض", "مخزن", "مصنع", "مطعم", "كافيه"
    ]):
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

    if any(w in all_check for w in ["غرف ومشاركة", "غرفة للإيجار", "غرفه للايجار", "غرفة مفروشة", "غرفة "]):
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

    if any(w in t_and_u for w in ["شقة", "شقه", "apartment", "/apartment/", "شقق للبيع", "شقق للايجار"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "شقة"

    cleaned_t = strip_villa_neighborhood_names(all_check)
    if any(w in cleaned_t for w in [
        "/villa/", "فلل - قصور", "فلل قصور", "فيلا منفصلة", "فيلا مستقلة",
        "تاون هاوس", "توين هاوس", "ستاند الون", "فيلا للبيع", "فيلا للإيجار",
        "فيلا للايجار", "ڤيلا", "townhouse", "twinhouse", "standalone", "villa"
    ]):
        category = "فلل للإيجار" if deal == "إيجار" else "فلل للبيع"
        return deal, category, "فيلا"

    category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
    return deal, category, "شقة"


def is_broker_seller_name(seller_name):
    s = (seller_name or "").lower().strip()
    if not s:
        return False
    return any(w in s for w in BROKER_SELLER_WORDS)


def has_forbidden_url_slug(url):
    u_dec = urllib.parse.unquote(url).lower()
    return any(slug in u_dec for slug in FORBIDDEN_URL_SLUGS)


def check_aqarmap_freshness(clean_all, lid):
    if re.search(r"\b(201\d|202[0-5])\b", clean_all[:650]):
        return False, "OLD_YEAR"
    old_months = ["يناير", "فبراير", "مارس", "أبريل", "ابريل", "مايو", "يونيو", "يوليو", "أغسطس", "اغسطس", "سبتمبر"]
    for om in old_months:
        if f"{om} 2026" in clean_all[:750]:
            return False, f"OLD_MONTH_{om}"
    if "نوفمبر 2026" in clean_all[:900] or "اليوم" in clean_all[:600] or "أمس" in clean_all[:600]:
        return True, "نوفمبر 2026"
    if lid >= 7350000:
        return True, "حديث (عقارماب)"
    return False, "OLD_LISTING_ID"


def check_opensooq_freshness(clean_all, oid):
    header_part = clean_all[:950]
    m_rel = re.search(r"قبل\s*(\d+)?\s*(دقيقة|دقائق|ساعة|ساعات|ساعه|يوم|يومين)", header_part)
    if m_rel:
        return True, m_rel.group(0)
    if "أمس" in header_part or "اليوم" in header_part:
        return True, "اليوم/أمس"
    m_date = re.search(r"\b(\d{2})-(11)-2026\b", header_part)
    if m_date:
        return True, m_date.group(0)
    if oid >= 289000000:
        return True, "حديث (السوق المفتوح)"
    return False, "OLD_OPENSOOQ"


def fetch_page(req_sess, cffi_sess, url, timeout_sec=20):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        r = cffi_sess.get("https://r.jina.ai/" + url, headers=headers, timeout=timeout_sec)
        if r.status_code == 200 and len(r.text) > 500 and "Too Many Requests" not in r.text:
            return r.text
    except Exception:
        pass

    try:
        r2 = cffi_sess.get(url, headers=headers, timeout=timeout_sec)
        if r2.status_code == 200 and len(r2.text) > 800:
            soup = BeautifulSoup(r2.text, "lxml")
            h1 = soup.find("h1")
            title_line = f"# {h1.get_text(' ', strip=True)}\n" if h1 else ""
            links_buf = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/listing/" in href or "/ar/" in href:
                    base = "https://aqarmap.com.eg" if "aqarmap" in url else "https://eg.opensooq.com"
                    full_h = base + href if href.startswith("/") else href
                    links_buf.append(full_h)
            return title_line + "\n" + soup.get_text(" ", strip=True) + "\n" + "\n".join(links_buf)
    except Exception:
        pass
    return ""


def discover_extra_candidates(req_sess, cffi_sess):
    aqar_urls = {}
    opensooq_urls = {}

    aqar_combos = [
        f"https://aqarmap.com.eg/ar/{deal}/{ptype}/{zone}/"
        for zone in AQARMAP_SETTLEMENT_ZONES
        for (deal, ptype) in AQARMAP_PROP_TYPES
    ]
    random.shuffle(aqar_combos)

    for cat_u in aqar_combos[:6]:
        raw_cat = fetch_page(req_sess, cffi_sess, cat_u, timeout_sec=18)
        if raw_cat:
            for m in re.finditer(r"(?:https?://aqarmap\.com\.eg)?(/ar/listing/(\d{7})-[^\s\"'<>)\]]+)", raw_cat):
                lid = int(m.group(2))
                full_u = "https://aqarmap.com.eg" + m.group(1)
                if lid >= 7330000 and not has_forbidden_url_slug(full_u):
                    aqar_urls[700000000 + lid] = full_u
        time.sleep(0.5)

    os_sample = list(OPENSOOQ_CATEGORY_URLS)
    random.shuffle(os_sample)
    for os_u in os_sample[:4]:
        raw_os = fetch_page(req_sess, cffi_sess, os_u, timeout_sec=18)
        if raw_os:
            for m in re.finditer(r"(?:https?://eg\.opensooq\.com)?(/ar/[^\s\"'<>)\]]+?/(\d{9,10}))", raw_os):
                oid = int(m.group(2))
                full_u = "https://eg.opensooq.com" + m.group(1)
                if oid >= 288500000 and not has_forbidden_url_slug(full_u):
                    opensooq_urls[800000000 + (oid % 100000000)] = (full_u, oid)
        time.sleep(0.5)

    q_list = list(EXTRA_QUERIES)
    random.shuffle(q_list)
    for q in q_list[:14]:
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
                        m_aq = re.search(r"(https?://aqarmap\.com\.eg/ar/listing/(\d{7})-[^\s\"'<>)\]]+)", target)
                        if m_aq:
                            lid = int(m_aq.group(2))
                            if lid >= 7330000:
                                aqar_urls[700000000 + lid] = m_aq.group(1)
                        m_os = re.search(r"(https?://eg\.opensooq\.com/ar/[^\s\"'<>)\]]+?/(\d{9,10}))", target)
                        if m_os:
                            oid = int(m_os.group(2))
                            if oid >= 288500000:
                                opensooq_urls[800000000 + (oid % 100000000)] = (m_os.group(1), oid)
            except Exception:
                pass
            time.sleep(0.12)

    return aqar_urls, opensooq_urls


def parse_aqarmap_ad(req_sess, cffi_sess, uid, url, banned_accounts):
    if has_forbidden_url_slug(url):
        return None, True, "EXCLUDED_AREA"

    lid = uid - 700000000
    raw = fetch_page(req_sess, cffi_sess, url)
    if not raw:
        return None, False, "NO_PAGE"

    clean_all = clean_text(raw)

    for bad in STRICT_FORBIDDEN_EVERYWHERE:
        if bad in clean_all:
            return None, True, "EXCLUDED_AREA"

    if not re.search(r"نوع\s*المعلن[\s:.•\-]*(?:مالك\s*عقار|مالك\s*العقار|المالك)", clean_all):
        return None, True, "BANNED_BROKER_TYPE"

    if re.search(r"نوع\s*المعلن[\s:.•\-]*(?:مطور|مسوق|شركة|وسيط|مكتب)", clean_all):
        return None, True, "BANNED_BROKER_TYPE"

    is_fresh, age_lbl = check_aqarmap_freshness(clean_all, lid)
    if not is_fresh:
        return None, True, "OLD_AD"

    if not any(w in clean_all for w in STRICT_NEW_CAIRO_HEADER):
        return None, True, "NOT_NEW_CAIRO"
    if not any(w in clean_all for w in NEW_CAIRO_WORDS):
        return None, True, "NOT_NEW_CAIRO"

    seller = "مالك عقار"
    seller_sec = clean_all.split("تواصل مع المعلن")[-1][:260] if "تواصل مع المعلن" in clean_all else clean_all[-450:]

    m_s = re.search(r"([A-Za-z\u0600-\u06FF\s]{2,35}?)\s*(?:عقار واحد|إعلان واحد|\d+\s*(?:عقار|إعلان|اعلان))", seller_sec)
    if m_s:
        cand_s = m_s.group(1).replace("تواصل مع المعلن", "").strip(" .-:|")
        if 2 <= len(cand_s) <= 35:
            seller = cand_s

    acc_key = f"name:{seller.lower().strip()}" if seller not in ("مالك", "مالك عقار", "المالك") else ""
    if acc_key and acc_key in banned_accounts:
        return None, True, "BANNED_ACCOUNT"

    if is_broker_seller_name(seller):
        if acc_key:
            banned_accounts.add(acc_key)
        return None, True, "BANNED_BROKER_NAME"

    for phrase in BROKER_AND_COMPANY_PHRASES:
        if phrase in clean_all:
            if acc_key:
                banned_accounts.add(acc_key)
            return None, True, "BANNED_BROKER_TEXT"

    title_clean = "وحدة من المالك بالقاهرة الجديدة"
    m_h1 = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    if m_h1:
        title_clean = clean_text(m_h1.group(1))[:130]

    price_num = 0
    for pm in re.finditer(r"(\d[\d,]{3,11})\s*(?:جنيه|ج\.م|جم|EGP)", clean_all):
        val = int(pm.group(1).replace(",", ""))
        if val >= 2000:
            price_num = val
            break
    price_text = f"{price_num:,} ج.م" if price_num > 0 else "مدرج بالإعلان"

    area = "مدرج بالإعلان"
    m_area = re.search(r"(\d{2,4})\s*(?:متر|م²|م2)", clean_all)
    if m_area:
        area = f"{m_area.group(1)} م²"

    beds = ""
    m_beds = re.search(r"(?:الغرف|غرف)[^\d]{0,8}(\d{1,2})", clean_all)
    if m_beds and 1 <= int(m_beds.group(1)) <= 12:
        beds = f"{m_beds.group(1)} غرف"

    baths = ""
    m_baths = re.search(r"(?:الحمامات|حمام)[^\d]{0,8}(\d{1,2})", clean_all)
    if m_baths and 1 <= int(m_baths.group(1)) <= 10:
        baths = f"{m_baths.group(1)} حمام"

    desc_clean = clean_all
    if "تفاصيل العقار" in clean_all:
        desc_clean = clean_all.split("تفاصيل العقار")[-1][:650]

    deal, category, subtype = classify_unit(url, title_clean, clean_all[:800], price_num)
    now_iso = datetime.now(CAIRO_TZ).isoformat()

    return {
        "ad_id": uid,
        "source": "عقارماب",
        "title": title_clean,
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
        "description": f"[عقارماب • {age_lbl}] {desc_clean[:600]}",
        "url": url,
        "today_verified": True,
        "verified_v12": True,
        "scraped_at": now_iso
    }, True, "ADDED_OWNER_AQARMAP"


def parse_opensooq_ad(req_sess, cffi_sess, uid, url, oid, banned_accounts):
    if has_forbidden_url_slug(url):
        return None, True, "EXCLUDED_AREA"

    raw = fetch_page(req_sess, cffi_sess, url)
    if not raw:
        return None, False, "NO_PAGE"

    clean_all = clean_text(raw)

    for bad in STRICT_FORBIDDEN_EVERYWHERE:
        if bad in clean_all:
            return None, True, "EXCLUDED_AREA"

    if not re.search(r"المعلن[\s:.•\-]*المالك", clean_all):
        return None, True, "BANNED_BROKER_TYPE"

    is_fresh, age_lbl = check_opensooq_freshness(clean_all, oid)
    if not is_fresh:
        return None, True, "OLD_AD"

    if not any(w in clean_all for w in STRICT_NEW_CAIRO_HEADER):
        return None, True, "NOT_NEW_CAIRO"
    if not any(w in clean_all for w in NEW_CAIRO_WORDS):
        return None, True, "NOT_NEW_CAIRO"

    seller = "مالك العقار"
    m_av = re.search(r"Avatar[\s.•\-]*([A-Za-z\u0600-\u06FF0-9_\s]{2,35}?)\s*(?:تابِع|الردّ|التقييم)", clean_all)
    if m_av:
        cand_s = m_av.group(1).strip(" .-:|")
        if 2 <= len(cand_s) <= 35:
            seller = cand_s

    acc_key = f"name:{seller.lower().strip()}" if seller not in ("مالك", "مالك العقار", "المالك") else ""
    if acc_key and acc_key in banned_accounts:
        return None, True, "BANNED_ACCOUNT"

    if is_broker_seller_name(seller):
        if acc_key:
            banned_accounts.add(acc_key)
        return None, True, "BANNED_BROKER_NAME"

    for phrase in BROKER_AND_COMPANY_PHRASES:
        if phrase in clean_all:
            if acc_key:
                banned_accounts.add(acc_key)
            return None, True, "BANNED_BROKER_TEXT"

    title_clean = "وحدة من المالك بالقاهرة الجديدة"
    m_h1 = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    if m_h1:
        title_clean = clean_text(m_h1.group(1))[:130]

    price_num = 0
    for pm in re.finditer(r"(\d[\d,]{3,11})\s*(?:جنيه|ج\.م|جم|EGP)", clean_all):
        val = int(pm.group(1).replace(",", ""))
        if val >= 2000:
            price_num = val
            break
    price_text = f"{price_num:,} ج.م" if price_num > 0 else "مدرج بالإعلان"

    area = "مدرج بالإعلان"
    m_area = re.search(r"(?:المساحة|مساحة)[^\d]{0,10}(\d{2,4})", clean_all)
    if m_area:
        area = f"{m_area.group(1)} م²"

    beds = ""
    m_beds = re.search(r"(\d{1,2})\s*غرف", clean_all)
    if m_beds and 1 <= int(m_beds.group(1)) <= 12:
        beds = f"{m_beds.group(1)} غرف"

    desc_clean = clean_all
    if "الوصف" in clean_all:
        desc_clean = clean_all.split("الوصف")[-1].split("بلغ عن إساءة")[0][:620]

    deal, category, subtype = classify_unit(url, title_clean, clean_all[:800], price_num)
    now_iso = datetime.now(CAIRO_TZ).isoformat()

    return {
        "ad_id": uid,
        "source": "السوق المفتوح",
        "title": title_clean,
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
        "description": f"[السوق المفتوح • {age_lbl}] {desc_clean[:600]}",
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


def sync_telegram_and_send_reports(data, run_report):
    chat_ids = set(str(x) for x in data.get("telegram_chat_ids", []) if str(x).strip())
    welcomed_ids = set(str(x) for x in data.get("telegram_welcomed_ids", []) if str(x).strip())
    last_update_id = int(data.get("telegram_last_update_id", 0))
    manual_report_requested = False

    try:
        r = std_requests.get(
            f"https://api.telegram.org/bot{TG_TOKEN}/getUpdates?offset={last_update_id + 1}",
            timeout=10
        )
        if r.status_code == 200:
            updates = r.json().get("result", [])
            for u in updates:
                uid_up = int(u.get("update_id", 0))
                if uid_up > last_update_id:
                    last_update_id = uid_up
                msg = u.get("message") or u.get("my_chat_member") or {}
                chat = msg.get("chat") or {}
                cid = chat.get("id")
                if cid:
                    chat_ids.add(str(cid))
                txt_in = str(msg.get("text", "")).strip()
                if any(w in txt_in for w in ["تقرير", "ملخص", "احصائيات", "إحصائيات", "/start", "تفعيل"]):
                    manual_report_requested = True
    except Exception:
        pass

    ads = data.get("ads", [])
    notified_ids = set(int(x) for x in data.get("notified_ids_v1", []) if str(x).isdigit())

    first_time_setup = False
    if not notified_ids and ads:
        first_time_setup = True
        all_current_ids = [int(a["ad_id"]) for a in ads if "ad_id" in a]
        if len(all_current_ids) > 1:
            notified_ids.update(all_current_ids[1:])

    for cid in chat_ids:
        if cid not in welcomed_ids:
            welcome_txt = (
                "تم تفعيل رادار مصيدة الملاك VIP على تليجرام بنجاح.\n\n"
                "• هيوصلك هنا إشعار فوري بأي مالك جديد ينزل في القاهرة الجديدة والتجمعات فقط "
                "(دوبيزل + عقارماب + السوق المفتوح).\n"
                "• وفي أي وقت ابعت كلمة (تقرير) هيرد عليك البوت بتفاصيل آخر رن كاملة."
            )
            try:
                std_requests.post(
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
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
                        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
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

    should_send_summary = (
        first_time_setup
        or manual_report_requested
        or run_report["total_new_owners_this_run"] > 0
    )

    if chat_ids and should_send_summary:
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
                    f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                    json={"chat_id": cid, "text": rep_msg},
                    timeout=10
                )
            except Exception:
                pass

    data["telegram_chat_ids"] = sorted(list(chat_ids))
    data["telegram_welcomed_ids"] = sorted(list(welcomed_ids))
    data["telegram_last_update_id"] = last_update_id
    data["notified_ids_v1"] = sorted(list(notified_ids))[-5000:]


def run_extra_radar():
    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    now_dt = datetime.now(CAIRO_TZ)
    ads = data.get("ads", [])
    for a in ads:
        if "source" not in a:
            a["source"] = "دوبيزل"

    kept_map = {int(a["ad_id"]): a for a in ads if "ad_id" in a}
    checked_ids = set(int(x) for x in data.get("checked_ids_v7", []) if str(x).isdigit())
    banned_accounts = set(data.get("banned_accounts_v7", []))

    req_sess = std_requests.Session()
    cffi_sess = cffi_requests.Session(impersonate="chrome120")

    aqar_cands, os_cands = discover_extra_candidates(req_sess, cffi_sess)

    extra_inspected = 0
    extra_added = 0
    extra_banned = 0
    extra_excluded = 0

    for uid, u in list(aqar_cands.items())[:20]:
        if uid in kept_map or uid in checked_ids:
            continue
        extra_inspected += 1
        item, mark_chk, reason = parse_aqarmap_ad(req_sess, cffi_sess, uid, u, banned_accounts)
        if mark_chk:
            checked_ids.add(uid)
        if "BANNED" in reason:
            extra_banned += 1
        elif reason in ("OLD_AD", "EXCLUDED_AREA", "NOT_NEW_CAIRO"):
            extra_excluded += 1
        if item:
            kept_map[uid] = item
            extra_added += 1
            print(f"[Aqarmap] ADDED Owner: {uid} | {item['category']} ({item['subtype']}) | {item['price_text']} | {item['seller_name']}")
        time.sleep(0.7)

    for uid, (u, oid) in list(os_cands.items())[:14]:
        if uid in kept_map or uid in checked_ids:
            continue
        extra_inspected += 1
        item, mark_chk, reason = parse_opensooq_ad(req_sess, cffi_sess, uid, u, oid, banned_accounts)
        if mark_chk:
            checked_ids.add(uid)
        if "BANNED" in reason:
            extra_banned += 1
        elif reason in ("OLD_AD", "EXCLUDED_AREA", "NOT_NEW_CAIRO"):
            extra_excluded += 1
        if item:
            kept_map[uid] = item
            extra_added += 1
            print(f"[OpenSooq] ADDED Owner: {uid} | {item['category']} ({item['subtype']}) | {item['price_text']} | {item['seller_name']}")
        time.sleep(0.7)

    final_ads = list(kept_map.values())
    final_ads.sort(key=lambda x: (x.get("fresh_tier", 2), x.get("ad_id", 0)), reverse=True)

    dub_stats = parse_dubizzle_log()

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
        "total_checked_ads_memory": len(checked_ids)
    }

    print("==========================================")
    print(f"RUN REPORT SUMMARY: {json.dumps(run_report, ensure_ascii=False)}")
    print("==========================================")

    data["last_scrape"] = now_dt.strftime("%Y/%m/%d, %I:%M %p")
    data["total_ads"] = len(final_ads)
    data["last_run_report"] = run_report
    data["ads"] = final_ads
    data["checked_ids_v7"] = sorted(list(checked_ids))[-5000:]
    data["banned_accounts_v7"] = sorted(list(banned_accounts))[-2500:]

    sync_telegram_and_send_reports(data, run_report)

    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    run_extra_radar()
