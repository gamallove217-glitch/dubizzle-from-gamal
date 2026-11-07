import base64
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

TG_B64_LIST = [
    "OTE4NTkwNjUyNzpBQUhSZ3FsOEJfay1ZNGZCN0NyQWpqYVFYaHZvNlJ6N3hGVQ==",
    "OTE4NTkwNjUyNzpBQUhSZ3FJOFJfay1ZNGZCN0NyQWpqYVFYaHZvNlJ6N3hGVQ=="
]

STRICT_NEW_CAIRO_HEADER = [
    "القاهرة الجديدة", "القاهره الجديده", "التجمع الخامس", "التجمع الأول", "التجمع الاول",
    "التجمع الثالث", "التجمع السادس", "القطامية", "القطاميه", "new cairo", "5th settlement",
    "fifth settlement", "katameya", "the-5th-settlement", "compounds-in-fifth-settlement",
    "first-settlement", "third-settlement", "el-katameya", "new-cairo"
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
    "الدبلوماسيين", "لافيستا", "الباتيو", "مون فالي", "ذا سكوير", "فيفث سكوير", "سراي",
    "القطاع الأول", "القطاع الثاني", "القطاع الثالث", "القطاع الرابع", "الزهور", "الأشرفية",
    "new cairo", "5th settlement", "fifth settlement", "the-5th-settlement",
    "compounds-in-fifth-settlement", "first-settlement", "third-settlement", "el-katameya"
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
    "تاج سيتي", "هليوبوليس الجديدة", "هليوبوليس الجديده"
]

WORDS_TO_SANITIZE_IN_DESC = [
    "مصر الجديدة", "مصر الجديده", "مدينة نصر", "مدينه نصر", "الرحاب", "مدينة الرحاب",
    "مدينتي", "مدينتى", "الشروق", "مدينة الشروق", "مدينة المستقبل", "المستقبل سيتي",
    "مدينة بدر", "العبور", "العاصمة الإدارية", "العاصمه الاداريه", "تاج سيتي",
    "هليوبوليس الجديدة", "جاردينيا سيتي", "المقطم", "المعادي", "شيراتون", "النزهة",
    "جاردينيا"
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

AQARMAP_VERIFIED_SEEDS_DATA = {
    707092368: {
        "url": "https://aqarmap.com.eg/ar/listing/7092368-for-sale-cairo-new-cairo-the-5th-settlement-new-narges/",
        "title": "شقة 212 متر للبيع بالتجمع الخامس النرجس الجديدة من المالك",
        "snippet": "المعلن مالك عقار شقة للبيع في النرجس الجديدة التجمع الخامس القاهرة الجديدة مساحة 212 متر 3 غرف 3 حمام تشطيب الترا سوبر لوكس أول سكن السعر 7,400,000 جنيه"
    },
    707283386: {
        "url": "https://aqarmap.com.eg/ar/listing/7283386-for-sale-cairo-new-cairo-compounds-in-fifth-settlement/",
        "title": "شقة للبيع في كمبوند بالتجمع الخامس القاهرة الجديدة من المالك",
        "snippet": "المعلن مالك عقار شقة مميزة للبيع بكمبوند في التجمع الخامس القاهرة الجديدة 3 غرف 3 حمام استلام فوري من المالك مباشرة"
    },
    707114653: {
        "url": "https://aqarmap.com.eg/ar/listing/7114653-for-sale-cairo-new-cairo-compounds-in-fifth-settlement/",
        "title": "شقة 145 متر للبيع بكمبوند بالتجمع الخامس من المالك مباشرة",
        "snippet": "المعلن مالك عقار شقة 145 متر للبيع بالتجمع الخامس القاهرة الجديدة 2 غرف 2 حمام متشطبة بالكامل السعر 6,000,000 جنيه"
    },
    707019572: {
        "url": "https://aqarmap.com.eg/ar/listing/7019572-for-sale-cairo-new-cairo-compounds-in-fifth-settlement/",
        "title": "شقة متشطبة بكمبوند الباتيو أورو التجمع الخامس الجولدن سكوير",
        "snippet": "المعلن مالك عقار شقة متشطبة للبيع بكمبوند الباتيو اورو التجمع الخامس القاهرة الجديدة مساحة 170 متر 2 غرف 2 حمام السعر 2,200,000 جنيه"
    },
    707002090: {
        "url": "https://aqarmap.com.eg/ar/listing/7002090-for-rent-cairo-new-cairo-compounds-in-fifth-settlement/",
        "title": "شقة للإيجار في كمبوند جاليريا مون فالي التجمع الخامس",
        "snippet": "المعلن مالك عقار شقة للايجار في كمبوند جاليريا مون فالي التجمع الخامس القاهرة الجديدة مساحة 133 متر 2 غرف 2 حمام السعر 40,000 جنيه"
    }
}

OPENSOOQ_VERIFIED_IDS = [
    289668370
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
    'site:aqarmap.com.eg/ar/listing "بيت الوطن" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "جنوب الأكاديمية" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "الأندلس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "المستثمرين" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "القرنفل" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "فيلا" "التجمع الخامس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "إداري" "التجمع الخامس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "تجاري" "التجمع الخامس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "طبي" "التجمع الخامس" "مالك عقار"',
    'site:aqarmap.com.eg/ar/listing "أراضي" "التجمع الخامس" "مالك عقار"',
    'site:eg.opensooq.com/ar "التجمع الخامس" "المالك"',
    'site:eg.opensooq.com/ar "القاهرة الجديدة" "المالك"',
    'site:eg.opensooq.com/ar "التجمع الخامس" "من المالك"'
]


def clean_text(md):
    txt = (md or "")
    txt = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]+", "", txt)
    txt = txt.translate(AR_DIGITS)
    txt = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"[*#_`~>|/\\]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def sanitize_for_dubizzle_compatibility(text):
    s = text or ""
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
    if any(w in all_check for w in [
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
        "قطعه ارض", "أرض للبيع", "ارض للبيع", "أرض سكنية", "أرض تجارية", "أراض "
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
        "مكتب اداري", "مكتب إداري", "إداري", "اداري", "مقر إداري", "مقر اداري", "وحدة إدارية"
    ]) and not is_explicit_apt:
        if not any(w in all_check for w in ["retail", "shop", "محل"]):
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
        text_no_build_year[:1600]
    )
    if m_pub:
        day_num, month_ar, yr_str = int(m_pub.group(1)), m_pub.group(2), m_pub.group(3)
        if yr_str == "2026":
            return True, f"{day_num} {month_ar} 2026"
        return False, f"OLD_YEAR_{yr_str}"

    if "اليوم" in text_no_build_year[:1200] or "أمس" in text_no_build_year[:1200] or "2026" in text_no_build_year[:1200]:
        return True, "2026"
    if lid >= 5500000:
        return True, "2026"
    return False, "OLD_LISTING_ID"


def check_opensooq_freshness(core_text, oid):
    m_rel = re.search(r"قبل\s*(\d+)?\s*(دقيقة|دقائق|ساعة|ساعات|ساعه|يوم|يومين|أيام|ايام)", core_text[:1500])
    if m_rel:
        return True, m_rel.group(0)
    if "أمس" in core_text[:1500] or "اليوم" in core_text[:1500]:
        return True, "اليوم/أمس"
    m_date = re.search(r"\b(\d{2})-(\d{2})-(20\d{2})\b", core_text[:1500])
    if m_date:
        dd, mm, yyyy = int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3))
        if yyyy == 2026 and mm == 11 and dd >= 1:
            return True, m_date.group(0)
        return False, f"OLD_DATE_{m_date.group(0)}"
    if oid >= 289400000:
        return True, "حديث (السوق المفتوح)"
    return False, "OLD_OPENSOOQ"


def extract_html_content(html_str, url):
    if not html_str or len(html_str) < 600 or "Just a moment" in html_str or "Attention Required!" in html_str:
        return "", "", []
    soup = BeautifulSoup(html_str, "lxml")
    base = "https://aqarmap.com.eg" if "aqarmap" in url else "https://eg.opensooq.com"
    links = []
    for a in soup.find_all("a", href=True):
        raw_href = a["href"]
        href = urllib.parse.unquote(raw_href)
        if "/listing/" in href or re.search(r"/\d{9,10}\b", href):
            full_h = base + raw_href if raw_href.startswith("/") else raw_href
            links.append(full_h)

    h1 = soup.find("h1")
    h1_txt = h1.get_text(" ", strip=True) if h1 else ""
    t_line = f"# {h1_txt}\n" if h1_txt else ""

    for tag in soup.find_all(["head", "title", "script", "style", "nav", "footer", "noscript", "svg", "iframe"]):
        tag.decompose()

    body_txt = soup.get_text(" ", strip=True)
    return t_line, body_txt, links


def fetch_page(req_sess, cffi_sess, url, timeout_sec=14):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com.eg/"
    }
    combined_parts = []
    links_buf = []
    title_line = ""

    enc_u = urllib.parse.quote(url, safe="")
    proxy_urls = [
        url,
        f"https://api.allorigins.win/raw?url={enc_u}",
        f"https://api.codetabs.com/v1/proxy?quest={enc_u}"
    ]

    for p_url in proxy_urls:
        try:
            r2 = cffi_sess.get(p_url, headers=headers, timeout=timeout_sec, allow_redirects=True)
            if r2.status_code == 200 and len(r2.text) > 800:
                t_l, b_txt, l_list = extract_html_content(r2.text, url)
                if b_txt and ("متر" in b_txt or "جنيه" in b_txt or "المعلن" in b_txt or l_list):
                    if t_l and not title_line:
                        title_line = t_l
                    combined_parts.append(b_txt)
                    links_buf.extend(l_list)
                    break
        except Exception:
            pass

    joined_now = " ".join(combined_parts)
    need_jina = (
        not combined_parts
        or ("aqarmap" in url and "/listing/" in url and "مالك" not in joined_now and "المعلن" not in joined_now)
        or ("opensooq" in url and "/search/" in url and "المعلن" not in joined_now)
    )
    if need_jina:
        try:
            r = cffi_sess.get("https://r.jina.ai/" + url, headers=headers, timeout=12)
            if r.status_code == 200 and len(r.text) > 500 and "Too Many Requests" not in r.text and "Target URL returned error 403" not in r.text:
                txt = r.text
                m_h1 = re.search(r"^#\s+(.+)$", txt, flags=re.M)
                if m_h1 and not title_line:
                    title_line = f"# {m_h1.group(1).strip()}\n"
                combined_parts.append(txt)
        except Exception:
            pass

    if not combined_parts and not links_buf:
        return ""
    return title_line + "\n" + "\n".join(combined_parts) + "\n" + "\n".join(links_buf)


def discover_extra_candidates(req_sess, cffi_sess):
    aqar_cands = {}
    opensooq_cands = {}

    for uid, sdata in AQARMAP_VERIFIED_SEEDS_DATA.items():
        aqar_cands[uid] = {
            "url": sdata["url"],
            "title": sdata["title"],
            "snippet": sdata["snippet"]
        }

    for oid in OPENSOOQ_VERIFIED_IDS:
        opensooq_cands[800000000 + (oid % 100000000)] = {
            "url": f"https://eg.opensooq.com/ar/search/{oid}",
            "oid": oid,
            "title": "",
            "snippet": ""
        }

    q_list = list(EXTRA_QUERIES)
    random.shuffle(q_list)
    for q in q_list[:16]:
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

                        a_title = clean_text(a.get_text(" ", strip=True))
                        parent_blk = a.find_parent(["div", "li"])
                        if parent_blk and parent_blk.find_parent(["div", "li"]):
                            parent_blk = parent_blk.find_parent(["div", "li"])
                        snippet_txt = clean_text(parent_blk.get_text(" ", strip=True)) if parent_blk else a_title

                        m_aq = re.search(r"(https?://aqarmap\.com\.eg/ar/listing/(\d{7})-[^\s\"'<>)\]]+)", target)
                        if m_aq:
                            lid = int(m_aq.group(2))
                            uid = 700000000 + lid
                            if uid not in aqar_cands:
                                aqar_cands[uid] = {
                                    "url": m_aq.group(1),
                                    "title": a_title,
                                    "snippet": f"المعلن مالك عقار {a_title} {snippet_txt}"
                                }

                        m_os = re.search(r"eg\.opensooq\.com/ar/[^\s\"'<>)\]]+?/(\d{9,10})", target)
                        if m_os:
                            oid = int(m_os.group(1))
                            uid = 800000000 + (oid % 100000000)
                            if oid >= 289000000 and uid not in opensooq_cands:
                                opensooq_cands[uid] = {
                                    "url": f"https://eg.opensooq.com/ar/search/{oid}",
                                    "oid": oid,
                                    "title": a_title,
                                    "snippet": f"المعلن المالك {a_title} {snippet_txt}"
                                }
            except Exception:
                pass
            time.sleep(0.1)

    return aqar_cands, opensooq_cands


def parse_aqarmap_ad(req_sess, cffi_sess, uid, cand_info, banned_accounts):
    url = cand_info["url"]
    fallback_title = cand_info.get("title", "")
    fallback_snippet = cand_info.get("snippet", "")

    if has_forbidden_url_slug(url):
        return None, True, "EXCLUDED_AREA"

    lid = uid - 700000000
    if lid < 5500000:
        return None, True, "OLD_AD"

    raw = fetch_page(req_sess, cffi_sess, url)
    used_fallback = False

    if not raw or len(raw) < 400 or ("متر" not in raw and "جنيه" not in raw and "المعلن" not in raw):
        if fallback_snippet and len(fallback_snippet) > 25:
            raw = f"# {fallback_title}\n{fallback_snippet}"
            used_fallback = True
        else:
            return None, False, "NO_PAGE"

    clean_full = clean_text(raw)

    pos_spec = clean_full.find("مالك عقار")
    if pos_spec == -1:
        pos_spec = clean_full.find("نوع المعلن")
    if pos_spec == -1:
        pos_spec = clean_full.find("المعلن")
    if pos_spec == -1:
        pos_spec = 0

    ad_core = clean_full[max(0, pos_spec - 800): pos_spec + 3000]

    seller_sec = ""
    if "تواصل مع المعلن" in clean_full:
        seller_sec = clean_full.split("تواصل مع المعلن", 1)[1][:280]

    for cut_marker in ["إعلانات ذات صلة", "تواصل مع أصحاب العقارات المماثلة"]:
        if cut_marker in ad_core and ad_core.find(cut_marker) > 500:
            ad_core = ad_core[:ad_core.find(cut_marker)]

    if not used_fallback:
        if "مالك عقار" not in clean_full and "مالك العقار" not in clean_full:
            return None, True, "BANNED_BROKER_TYPE"
    else:
        if any(bw in clean_full for bw in ["شركة عقارية", "مطور عقاري", "مسوق عقاري", "بأقساط على", "مقدم 10%", "مقدم 5%"]):
            return None, True, "BANNED_BROKER_TYPE"

    is_fresh, age_lbl = check_aqarmap_freshness(ad_core, lid)
    if not is_fresh:
        return None, True, "OLD_AD"

    desc_clean = ad_core
    if "وصف الإعلان" in ad_core:
        desc_clean = ad_core.split("وصف الإعلان", 1)[1]
    elif "مالك عقار" in ad_core:
        desc_clean = ad_core.split("مالك عقار", 1)[1]

    for end_m in ["مزايا العقار", "حفظ ملاحظة", "تواصل مع المعلن", "أظهر المزيد", "وقت الوصول", "تم إضافة الإعلان"]:
        if end_m in desc_clean:
            desc_clean = desc_clean.split(end_m, 1)[0]

    title_clean = fallback_title or "وحدة من المالك بالقاهرة الجديدة"
    m_h1 = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    if m_h1 and len(clean_text(m_h1.group(1))) > 5:
        title_clean = clean_text(m_h1.group(1)).split("|")[0].split("- عقارماب")[0].strip()[:130]

    header_only = f"{title_clean} {ad_core[:450]}"
    header_and_desc = f"{header_only} {desc_clean} {urllib.parse.unquote(url)}"

    for bad in STRICT_FORBIDDEN_HEADER:
        if bad in title_clean:
            return None, True, "EXCLUDED_AREA"

    if not any(w in header_and_desc.lower() for w in [x.lower() for x in STRICT_NEW_CAIRO_HEADER]):
        return None, True, "NOT_NEW_CAIRO"
    if not any(w in header_and_desc.lower() for w in [x.lower() for x in NEW_CAIRO_WORDS]):
        return None, True, "NOT_NEW_CAIRO"

    seller = "مالك عقار"
    m_s = re.search(r"([A-Za-z\u0600-\u06FF\s]{2,35}?)\s*(?:\d+\.\d+\s*)?(?:عقار واحد|إعلان واحد|\d+\s*(?:عقار|عقارين|إعلان|اعلان))", seller_sec)
    if m_s:
        cand_s = m_s.group(1).replace("تواصل مع المعلن", "").strip(" .-:|")
        if 2 <= len(cand_s) <= 35 and "شركات" not in cand_s and "سجل" not in cand_s:
            seller = cand_s

    for m_cnt in re.finditer(r"\b(\d{1,4})\s*(?:عقار|عقارات|إعلان|اعلان)", seller_sec):
        if int(m_cnt.group(1)) > 20:
            return None, True, "BANNED_BROKER_PORTFOLIO"

    acc_key = f"name:{seller.lower().strip()}" if seller not in ("مالك", "مالك عقار", "المالك") else ""
    if acc_key and acc_key in banned_accounts:
        return None, True, "BANNED_ACCOUNT"

    price_num = 0
    for pm in re.finditer(r"(\d[\d,]{3,11})\s*(?:جنيه|ج\.م|جم|EGP)", ad_core):
        val = int(pm.group(1).replace(",", ""))
        if val >= 2000:
            price_num = val
            break
    price_text = f"{price_num:,} ج.م" if price_num > 0 else "مدرج بالإعلان"

    area = "مدرج بالإعلان"
    m_area = re.search(r"(\d{2,4})\s*(?:متر|م²|م2)", ad_core)
    if m_area:
        area = f"{m_area.group(1)} م²"

    beds = ""
    m_beds = re.search(r"(?:الغرف|غرف)[^\d]{0,8}(\d{1,2})", ad_core)
    if m_beds and 1 <= int(m_beds.group(1)) <= 12:
        beds = f"{m_beds.group(1)} غرف"

    baths = ""
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
    fallback_title = cand_info.get("title", "")
    fallback_snippet = cand_info.get("snippet", "")

    if has_forbidden_url_slug(url):
        return None, True, "EXCLUDED_AREA"

    if oid < 289000000:
        return None, True, "OLD_AD"

    raw = fetch_page(req_sess, cffi_sess, url)
    if not raw or len(raw) < 300:
        if fallback_snippet and len(fallback_snippet) > 25:
            raw = f"# {fallback_title}\n{fallback_snippet}"
        else:
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

    title_clean = fallback_title or "وحدة من المالك بالقاهرة الجديدة"
    m_h1 = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    if m_h1 and len(clean_text(m_h1.group(1))) > 5:
        title_clean = clean_text(m_h1.group(1)).split("|")[0].strip()[:130]

    header_only = f"{title_clean} {ad_core[:400]}"
    header_and_desc = f"{title_clean} {ad_core.split('بلغ عن إساءة')[0]}"

    for bad in STRICT_FORBIDDEN_HEADER:
        if bad in title_clean:
            return None, True, "EXCLUDED_AREA"

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
    price_text = f"{price_num:,} ج.م" if price_num > 0 else "مدرج بالإعلان"

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


def get_working_tg_token():
    for b64_s in TG_B64_LIST:
        try:
            tok = base64.b64decode(b64_s).decode("utf-8")
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
        std_requests.get(f"https://api.telegram.org/bot{tg_token}/deleteWebhook", timeout=6)
    except Exception:
        pass

    try:
        r = std_requests.get(
            f"https://api.telegram.org/bot{tg_token}/getUpdates?limit=100",
            timeout=10
        )
        if r.status_code == 200:
            updates = r.json().get("result", [])
            for u in updates:
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

    old_october_opensooq_ids = {889052484, 888278850}
    kept_map = {}
    for a in ads:
        if "ad_id" not in a:
            continue
        aid = int(a["ad_id"])
        if aid in old_october_opensooq_ids:
            continue
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

    for backup_ad in saved_meta.get("extra_ads_backup", []):
        if isinstance(backup_ad, dict) and "ad_id" in backup_ad:
            b_id = int(backup_ad["ad_id"])
            if b_id not in kept_map and b_id not in old_october_opensooq_ids:
                kept_map[b_id] = backup_ad

    checked_extra = set(int(x) for x in (data.get("checked_extra_v11") or saved_meta.get("checked_extra_v11") or []) if str(x).isdigit())
    checked_extra.update(old_october_opensooq_ids)
    banned_accounts = set(data.get("banned_accounts_v7", []))

    if not data.get("telegram_chat_ids") and saved_meta.get("telegram_chat_ids"):
        data["telegram_chat_ids"] = saved_meta["telegram_chat_ids"]
    if not data.get("telegram_welcomed_ids") and saved_meta.get("telegram_welcomed_ids"):
        data["telegram_welcomed_ids"] = saved_meta["telegram_welcomed_ids"]
    if not data.get("notified_ids_v1") and saved_meta.get("notified_ids_v1"):
        data["notified_ids_v1"] = saved_meta["notified_ids_v1"]

    req_sess = std_requests.Session()
    cffi_sess = cffi_requests.Session(impersonate="chrome120")

    aqar_cands, os_cands = discover_extra_candidates(req_sess, cffi_sess)

    extra_inspected = 0
    extra_added = 0
    extra_banned = 0
    extra_excluded = 0

    for uid, cand_info in list(aqar_cands.items())[:18]:
        if uid in kept_map or uid in checked_extra:
            continue
        item, mark_chk, reason = parse_aqarmap_ad(req_sess, cffi_sess, uid, cand_info, banned_accounts)
        print(f"[Aqarmap Check] ID={uid} | Reason={reason}")
        if reason != "NO_PAGE":
            extra_inspected += 1
        if mark_chk:
            checked_extra.add(uid)
        if "BANNED" in reason:
            extra_banned += 1
        elif reason in ("OLD_AD", "EXCLUDED_AREA", "NOT_NEW_CAIRO"):
            extra_excluded += 1
        if item:
            kept_map[uid] = item
            extra_added += 1
            print(f"[Aqarmap] ADDED Owner: {uid} | {item['category']} ({item['subtype']}) | {item['price_text']} | {item['seller_name']}")
        time.sleep(0.5)

    for uid, cand_info in list(os_cands.items())[:12]:
        if uid in kept_map or uid in checked_extra:
            continue
        item, mark_chk, reason = parse_opensooq_ad(req_sess, cffi_sess, uid, cand_info, banned_accounts)
        print(f"[OpenSooq Check] ID={uid} | Reason={reason}")
        if reason != "NO_PAGE":
            extra_inspected += 1
        if mark_chk:
            checked_extra.add(uid)
        if "BANNED" in reason:
            extra_banned += 1
        elif reason in ("OLD_AD", "EXCLUDED_AREA", "NOT_NEW_CAIRO"):
            extra_excluded += 1
        if item:
            kept_map[uid] = item
            extra_added += 1
            print(f"[OpenSooq] ADDED Owner: {uid} | {item['category']} ({item['subtype']}) | {item['price_text']} | {item['seller_name']}")
        time.sleep(0.5)

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
        "total_checked_ads_memory": len(checked_extra) + len(data.get("checked_ids_v7", []))
    }

    print("==========================================")
    print(f"RUN REPORT SUMMARY: {json.dumps(run_report, ensure_ascii=False)}")
    print("==========================================")

    data["last_scrape"] = now_dt.strftime("%Y/%m/%d, %I:%M %p")
    data["total_ads"] = len(final_ads)
    data["last_run_report"] = run_report
    data["checked_extra_v11"] = sorted(list(checked_extra))[-4000:]
    data["banned_accounts_v7"] = sorted(list(banned_accounts))[-2500:]

    sync_telegram_and_send_reports(data, run_report)

    extra_only_list = [dict(a) for a in final_ads if a.get("source") in ("عقارماب", "السوق المفتوح")]
    meta_payload = {
        "checked_extra_v11": data["checked_extra_v11"][-2000:],
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
