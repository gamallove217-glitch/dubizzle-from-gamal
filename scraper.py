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

# FIX(M9): توقيت القاهرة الحقيقي — بيراعي التوقيت الصيفي (UTC+3 من أبريل لأكتوبر)
try:
    from zoneinfo import ZoneInfo
    CAIRO_TZ = ZoneInfo("Africa/Cairo")
except Exception:
    CAIRO_TZ = timezone(timedelta(hours=2))
AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
# ✅ الميزانيات الزمنية بقت متغيرات بيئة — الـ workflow يتحكم فيها من غير تعديل كود.
MAX_RUNTIME_SECONDS = int(os.environ.get("MAX_RUNTIME_SECONDS", str(25 * 60)) or 1500)
# FIX(C8): اسم الموضوع بقى من GitHub Secrets. لو السر مش موجود، بيرجع للاسم القديم
# عشان السكريبر مايوقعش — بس الاسم القديم مكشوف فلازم تحط السر.
BAN_TOPIC = os.environ.get("NTFY_BAN_TOPIC", "gamal_masyada_bans_2738_v1")
# FIX(C8): حمايات موضوع الحظر العلني — التفاصيل في fetch_manual_bans_from_cloud()
BAN_SECRET = (os.environ.get("NTFY_BAN_SECRET") or "").strip()
MAX_CLOUD_BANS = int(os.environ.get("MAX_CLOUD_BANS", "12") or 12)
CLOUD_BAN_MAX_AGE_DAYS = int(os.environ.get("CLOUD_BAN_MAX_AGE_DAYS", "60") or 60)
# FIX(M8): ميزانية زمن للاستكشاف لوحده، عشان ماياكلش وقت الطابور
DISCOVERY_BUDGET_SECONDS = int(os.environ.get("DISCOVERY_BUDGET_SECONDS", str(4 * 60)) or 240)
# ✅ FIX: اللوج الحي على GitHub أثبت المشكلة دي — الاكتشاف خد 277 ثانية من أصل
#    ميزانية 480، ففضل للفحص 203 ثانية بس ⇒ فحص 52 إعلان من 120 ووقف،
#    وفاضل 67 في الطابور ما اتفحصوش. دلوقتي للفحص ميزانيته المستقلة.
INSPECTION_BUDGET_SECONDS = int(os.environ.get("INSPECTION_BUDGET_SECONDS", str(10 * 60)) or 600)
# FIX(C6): عدد محاولات NO_CNT قبل ما نعلّم الإعلان كمفحوص
NO_CNT_MAX_TRIES = 3
# FIX(H2): ذاكرة المفحوص بتنتهي بعد كام يوم (للأسباب القابلة للتغيّر زي OLD_AD)
CHECKED_TTL_DAYS = 14

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
    "المستثمرين", "النورث هاوس", "القرنفل", "تمر حنة", "اللؤلؤة",
    "ابو الهول", "أبو الهول", "جاردينيا هايتس", "غرب الجولف", "غرب أرابيلا", "غرب ارابيلا",
    "أرابيلا", "ارابيلا", "الشويفات", "الداون تاون", "التسعين", "القطامية", "القطاميه",
    "كايرو فيستيفال", "كايرو فستيفال", "ميفيدا", "ماونتن فيو", "هايد بارك", "بالم هيلز",
    "سوديك", "فيليت", "ايست تاون", "ايستاون", "زيد ايست", "تريو", "ازار", "دار مصر",
    "سكن مصر", "جنة", "الجامعة الأمريكية", "الجامعه الامريكيه", "الجولدن سكوير",
    "فيلدج جيت", "سيتي جيت", "ليك فيو", "مكسيم", "الحي التكميلي",
    "الدبلوماسيين", "لافيستا", "الباتيو", "مون فالي", "ذا سكوير", "فيفث سكوير", "سراي"
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
    "شاليه للبيع", "شاليه للإيجار", "شاليه للايجار", "راس الحكمة", "رأس الحكمة", "مراسي", "الجونة",
    # 🆕 بيت الوطن — ممنوعة زي مدينتي بالظبط، بس بحماية من «تبعد عن بيت الوطن»
    "بيت الوطن", "بيت الوطنى", "بيت الوطن الجديد"
]

EXCLUDE_CITIES = STRICT_FORBIDDEN_EVERYWHERE + [
    "الرحاب", "مدينة الرحاب", "مدينتي", "مدينتى", "الشروق", "مدينة الشروق",
    "مدينة المستقبل", "المستقبل سيتي", "بدر", "مدينة بدر", "العبور", "العاصمة الإدارية",
    "تاج سيتي"
]

FRONTEND_SANITIZE_WORDS = [
    "مصر الجديدة", "مصر الجديده", "مدينة نصر", "مدينه نصر", "زهراء مدينة نصر",
    "الكوربة", "أرض الجولف", "ارض الجولف", "ميدان الحجاز", "روكسي", "الماظة", "ألماظة",
    "شيراتون", "النزهة", "عباس العقاد", "مكرم عبيد", "مصطفى النحاس",
    "الرحاب", "مدينتي", "الشروق", "العاصمة الإدارية", "مدينة المستقبل", "عقارات مصايف",
    "بيت الوطن", "بيت الوطنى"
]

# ==============================================================================
#  🛡️ حماية من اللبس (طلب المالك 2026-11-09)
# ------------------------------------------------------------------------------
#  المشكلة: المطابقة الحرفية للكلمات بتظلم الإعلان السليم.
#    • «شقة تبعد عن بيت الوطن 5 دقايق»   ⇒ مش في بيت الوطن، لازم تفضل
#    • «بدون أقساط من المالك»             ⇒ كاش، لازم تفضل
#    • «بدون مقدم»                        ⇒ كانت مصنّفة سمسار! غلط صريح
#  الحل: لما نلاقي كلمة، نبصّ في الـ 26 حرف اللي قبلها. لو فيه نفي أو
#        إشارة مسافة **بيحكمها مباشرةً** (من غير حرف عطف بينهم) ⇒ نتجاهلها.
#  حرف العطف مهم: «بدون مقدم وأقساط على 5 سنين» ⇒ «بدون» بتحكم «مقدم» بس،
#        «أقساط» بعد الواو ⇒ إعلان تقسيط ⇒ مرفوض. صح.
# ==============================================================================

# كلمات التقسيط/الأقساط — لو الإعلان نفسه بيقدّمها ⇒ مرفوض
INSTALLMENT_WORDS = [
    "بالتقسيط", "تقسيط", "أقساط", "اقساط", "بالأقساط", "بالاقساط", "قسط",
    "مقدم", "بقدم", "بمقدم", "دفعة", "دفعه", "أقل مقدم", "اقل مقدم",
    "تسهيلات", "تسهيل", "نظام سداد", "أنظمة سداد", "انظمة سداد",
    "خطة سداد", "خطط سداد", "سداد ميسر", "سداد مرن",
    "على سنوات", "علي سنوات", "على سنين", "علي سنين", "لسنوات", "لسنين",
    "خصم الكاش", "سعر الشركة",
    "installment", "installments", "down payment", "payment plan",
]

# النفي — لو جه قبل الكلمة مباشرةً ⇒ الكلمة ملغاة
NEGATION_RE = re.compile(
    r"(?:^|[\s،,;.\-–—(|«»\"])"
    r"(?:بدون|بلا|لا|مش|ليس|غير|من\s+غير|منغير|مفيش|خالي|خالٍ|مبقتش|no|not|without|zero)"
    r"(?=$|[\s،,;.\-–—)|«»\"])"
)

# إشارة مسافة/مرجع — لو جه قبل اسم المنطقة ⇒ المنطقة مش موقع الإعلان
AREA_HINT_RE = re.compile(
    r"(?:يبعد|تبعد|بعاد|بعيد|بعيده|قريب|قريبه|قرب|بجوار|بجانب|جنب|خلف|خلفها|"
    r"أمام|امام|وراء|ورا|مقابل|خارج|ناحية|اتجاه|حوالي|تقريبا|تقريباً|"
    r"على\s+بعد|علي\s+بعد|بعد|لسه\s+موصل|"
    r"(?:^|[\s،,;.\-–—(|])(?:مش|ليس|غير|بدون|بلا|لا)(?=$|[\s،,;.\-–—)|]))"
)

# حروف العطف — لو فصلت بين النفي والكلمة ⇒ النفي ما بيحكمهاش
CONJUNCTION_MARKS = (" و", "،", ",", "+", "|", " أو ", " او ", " ثم ", ";", " وكذلك ", " و")

LOOKBACK_CHARS = 26


def _governed_before(text, start, pattern):
    """فيه حاجة من `pattern` بتحكم الكلمة اللي عند الموضع `start`؟"""
    if not text or start <= 0:
        return False
    window = text[max(0, start - LOOKBACK_CHARS):start]
    best = None
    for m in pattern.finditer(window):
        best = m                       # آخر تطابق = الأقرب للكلمة
    if best is None:
        return False
    between = window[best.end():]
    if any(c in between for c in CONJUNCTION_MARKS):
        return False                   # فيه عطف ⇒ النفي/المرجع ما بيحكمش الكلمة
    return True


def area_is_the_location(text, area):
    """`area` مذكورة كموقع حقيقي للإعلان (مش كمرجع مسافة)؟"""
    t = text or ""
    for m in re.finditer(re.escape(area), t):
        if not _governed_before(t, m.start(), AREA_HINT_RE):
            return True
    return False


def has_installment_offer(text):
    """الإعلان نفسه معروض بتقسيط/أقساط؟ بيتجاهل «بدون أقساط» و«لا تقسيط»."""
    t = (text or "").lower()
    for w in INSTALLMENT_WORDS:
        wl = w.lower()
        for m in re.finditer(re.escape(wl), t):
            if not _governed_before(t, m.start(), NEGATION_RE):
                return True
    return False


def forbidden_area_hit(text, forbidden_list):
    """بيرجّع أول منطقة محظورة الإعلان **واقع فيها فعلاً**، أو None."""
    for bad in forbidden_list:
        if area_is_the_location(text, bad):
            return bad
    return None


DUBIZZLE_CATEGORY_BASES = [
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-sale/1st-settlement/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/new-cairo/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/apartments-duplex-for-rent/1st-settlement/",
    "https://www.dubizzle.com.eg/properties/villas-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/villas-for-sale/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/villas-for-sale/1st-settlement/",
    "https://www.dubizzle.com.eg/properties/villas-for-rent/new-cairo/",
    "https://www.dubizzle.com.eg/properties/villas-for-rent/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/villas-for-rent/1st-settlement/",
    "https://www.dubizzle.com.eg/properties/commercial-for-sale/new-cairo/",
    "https://www.dubizzle.com.eg/properties/commercial-for-sale/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/commercial-for-sale/1st-settlement/",
    "https://www.dubizzle.com.eg/properties/commercial-for-rent/new-cairo/",
    "https://www.dubizzle.com.eg/properties/commercial-for-rent/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/commercial-for-rent/1st-settlement/",
    "https://www.dubizzle.com.eg/properties/buildings-lands/new-cairo/",
    "https://www.dubizzle.com.eg/properties/buildings-lands/5th-settlement/",
    "https://www.dubizzle.com.eg/properties/buildings-lands/1st-settlement/"
]


# ==============================================================================
#  فلترة أولية بالعنوان — بدون أي طلب شبكة (البيانات جاية من JSON-LD مجاناً)
# ------------------------------------------------------------------------------
#  القياس الحي على 811 عنوان من 16 صفحة فئة (2026-11-09):
#     BROKER  246 (30%)  ⇒ بنتخطاهم تماماً، توفير 30% من ميزانية الجلب
#     UNKNOWN 472 (58%)  ⇒ بنفحصهم عادي
#     OWNER    14 (2%)   ⇒ أولوية قصوى، بنفحصهم الأول
#  وتم التحقق إن الفلتر ما بيرفضش ولا واحد من الـ 29 مالك المؤكدين في ads.json
#  (بعد استثناء "فرصة استثمارية" اللي كانت إشارة خاطئة).
# ==============================================================================

OWNER_TITLE_SIGNALS = [
    "من المالك", "المالك مباشرة", "المالك مباشره", "مالك مباشر", "من مالك",
    "مباشر من المالك", "المالك فقط", "صاحب العقار", "من صاحب", "مالك العقار",
    "بدون وسيط", "بدون سمسار", "بدون سمسرة", "بدون عمولة", "بدون عمولات",
    "no broaker", "no broakers", "no broker", "no brokers", "no commission",
    "direct from owner", "from owner", "from the owner", "owner direct",
    "owner only", "direct owner",
]

BROKER_TITLE_SIGNALS = [
    "مقدم", "بقدم", "قسط", "أقساط", "اقساط", "تقسيط", "تسهيلات", "تسهيل", "سداد",
    "دايركت", "استلام فوري", "استلام فورى", "لقطة", "لقطه", "ألترا لوكس",
    "الترا لوكس", "دفعة", "دفعه", "على سنوات", "علي سنوات", "على سنين", "علي سنين",
        # ⚠️ «بدون مقدم» اتشالت — كانت بتظلم المالك اللي بيبيع كاش
    "بأقل مقدم", "باقل مقدم", "أقل مقدم", "اقل مقدم", "للتسويق",
    "تسويق عقاري", "شركة عقارية", "كمبوند بالتقسيط", "وحدات بالتقسيط",
    "خصم الكاش", "خصم الكاش ", "سعر الشركة", "بأقل من سعر الشركة",
]


def classify_title_signal(title):
    """
    بيرجّع "OWNER" / "BROKER" / "UNKNOWN".
    ⚠️ إشارة المالك بتتفحص الأول — عشان "Direct from Owner" ما تتحسبش سمسار.
    """
    t = (title or "").lower()
    if any(w.lower() in t for w in OWNER_TITLE_SIGNALS):
        return "OWNER"
    # 🛡️ كلمات التقسيط بتتفحص بوعي بالنفي: «بدون أقساط» ⇒ مش سمسار
    if has_installment_offer(t):
        return "BROKER"
    if any(w.lower() in t for w in BROKER_TITLE_SIGNALS):
        return "BROKER"
    return "UNKNOWN"


# أولوية الطابور: كلما قلّ الرقم زاد التقدم
SIGNAL_PRIORITY = {"OWNER": 0, "UNKNOWN": 1, "BROKER": 3}


BREADCRUMB_MAP = {
    "شقق للبيع":            ("بيع",   "شقق للبيع"),
    "شقق للإيجار":          ("إيجار", "شقق للإيجار"),
    "شقق للايجار":          ("إيجار", "شقق للإيجار"),
    "فلل للبيع":            ("بيع",   "فلل للبيع"),
    "فلل للإيجار":          ("إيجار", "فلل للإيجار"),
    "فلل للايجار":          ("إيجار", "فلل للإيجار"),
    "عقار تجارى للبيع":     ("بيع",   "عقار تجاري للبيع"),
    "عقار تجاري للبيع":     ("بيع",   "عقار تجاري للبيع"),
    "عقار تجارى للإيجار":   ("إيجار", "عقار تجاري للإيجار"),
    "عقار تجاري للإيجار":   ("إيجار", "عقار تجاري للإيجار"),
    # مبانى و أراضى: الفئة موحّدة (بيع وإيجار) ⇒ Deal بيتحدد من السعر/الكلمات
    "مبانى و أراضى":        (None,    "مبانى و أراضى"),
    "مباني و أراضي":        (None,    "مبانى و أراضى"),
    "مباني واراضي":         (None,    "مبانى و أراضى"),
}


def map_breadcrumb_category(bc_cat, price_num=0):
    """
    بيحوّل الفئة الرسمية من دوبيزل لـ (deal, category).
    ✅ أدق بكتير من تخمين الكلمات المفتاحية — دي الفئة اللي دوبيزل نفسها مصنّف بيها الإعلان.
    """
    hit = BREADCRUMB_MAP.get((bc_cat or "").strip())
    if not hit:
        return None, None
    deal, category = hit
    if deal is None:
        deal = "إيجار" if 0 < price_num < 150000 else "بيع"
    return deal, category


def sanitize_desc_for_frontend(text):
    s = text or ""
    for w in FRONTEND_SANITIZE_WORDS:
        s = s.replace(w, " ")
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


def classify_deal_category_subtype(url, title_clean, desc_clean, before_desc_clean, price_num):
    u_dec = urllib.parse.unquote(url).lower()
    t_low = (title_clean or "").lower()
    t_and_u = f"{t_low} {u_dec}".lower()
    header_str = (before_desc_clean or "").lower()

    deal = "بيع"
    if any(w in header_str for w in ["للإيجار", "للايجار", "غرض العقار للإيجار", "غرض العقار للايجار"]) or any(
        w in t_and_u for w in ["rent", "إيجار", "ايجار", "للايجار", "للإيجار", "مفروش", "شهري"]
    ):
        deal = "إيجار"
    elif 0 < price_num < 150000:
        deal = "إيجار"

    is_explicit_apt = any(w in t_low for w in ["شقة", "شقه", "apartment", "flat", "دوبلكس", "دوبليكس", "بنتهاوس", "ستوديو", "استوديو", "studio", "رووف", "روف"])

    if (any(w in header_str for w in ["مبانى و أراضى", "مباني و أراضي", "مباني واراضي", "buildings-lands"]) or any(
        w in t_and_u for w in ["قطعة أرض", "قطعه ارض", "أرض للبيع", "ارض للبيع", "أرض سكنية", "ارض سكنيه", "أرض تجارية", "عمارة كاملة", "عماره كامله", "عمارة للبيع", "عماره للبيع", "مبنى كامل"]
    )) and not is_explicit_apt:
        return deal, "مبانى و أراضى", "مبانى و أراضى"

    if (any(w in header_str for w in ["عقار تجارى", "عقار تجاري", "عقارات تجارية", "commercial-for"]) or any(
        w in t_and_u for w in ["retail", "shop", "medical", "clinic", "office", "business park", "مكتب", "إداري", "اداري", "عيادة", "عياده", "محل ", "محل للبيع", "محل للايجار", "محل للإيجار", "تجاري", "تجارى", "معرض", "صيدلية", "صيدليه", "مقر اداري", "مقر إداري", "مبنى تجاري", "مبنى إداري", "مخزن", "مصنع", "مطعم", "كافيه"]
    )) and not is_explicit_apt:
        category = "عقار تجاري للإيجار" if deal == "إيجار" else "عقار تجاري للبيع"
        return deal, category, "عقار تجاري"

    if any(w in t_and_u for w in ["شقة فندقية", "شقه فندقيه", "فندقية", "فندقيه", "serviced"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "شقة فندقية"

    if any(w in t_and_u for w in ["ستوديو", "استوديو", "studio"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "ستوديو"

    if any(w in t_and_u for w in ["غرفة للإيجار", "غرفه للايجار", "غرفة مفروشة", "غرفة مشتركة", "سكن طلاب"]) and not is_explicit_apt and (0 < price_num < 150000):
        return "إيجار", "شقق للإيجار", "غرفة"

    if any(w in t_and_u for w in ["دوبلكس", "دوبليكس", "duplex"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "دوبلكس"

    if any(w in t_and_u for w in ["بنتهاوس", "penthouse"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "بنتهاوس"

    if any(w in t_and_u for w in ["سطح", "رووف", "روف ", "روف-", "roof"]) or t_and_u.startswith("روف"):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "سطح"

    if any(w in t_and_u for w in ["شقة", "شقه", "apartment"]):
        category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
        return deal, category, "شقة"

    cleaned_t_and_h = strip_villa_neighborhood_names(f"{t_and_u} {header_str}")
    if any(w in header_str for w in ["فلل للبيع", "فلل للإيجار", "فلل للايجار", "villas-for"]) or any(
        w in cleaned_t_and_h for w in ["فيلا منفصلة", "فيلا مستقلة", "تاون هاوس", "توين هاوس", "ستاند الون", "فيلا للبيع", "فيلا للايجار", "فيلا للإيجار", "ڤيلا", "townhouse", "twinhouse", "standalone"]
    ):
        category = "فلل للإيجار" if deal == "إيجار" else "فلل للبيع"
        return deal, category, "فيلا"

    category = "شقق للإيجار" if deal == "إيجار" else "شقق للبيع"
    return deal, category, "شقة"


def fetch_manual_bans_from_cloud():
    """
    ⚠️ FIX(C8) — موضوع ntfy ده **علني**، وأي حد يقرا مصدر الصفحة يعرف اسمه.
       يعني أي حد كان يقدر يعمل:
           curl -d '{"ad_id":504238147}' https://ntfy.sh/<الموضوع>
       والإعلان ده يتمسح من ads.json **للأبد** (بيدخل hard_banned_ids + checked).
       بل ويقدر يحظر اسم مالك فيمسح كل إعلاناته.

       الحل الكامل محتاج خادم وسيط (Cloudflare Worker) — لأن أي سرّ مكتوب في صفحة
       ثابتة هو سرّ علني بحكم الطبيعة. لحد ما تعمل كده، الحمايات دي بتحدّ الضرر:

       1) BAN_SECRET — لو حطيت السر ده في GitHub Secrets، مفيش رسالة حظر هتتقبل
          إلا لو فيها نفس السر. (زرار الحظر في الصفحة هيبطل يشتغل — هتحظر يدوي
          بـ curl. ده مقصود: أمان على حساب راحة.)
       2) MAX_CLOUD_BANS — سقف عدد الحظورات في الرَن الواحد؛ يمنع مسح جماعي.
       3) CLOUD_BAN_MAX_AGE_DAYS — تجاهل الرسائل القديمة.
       4) كل حاجة بتتطبع في اللوج — يبقى باين فوراً لو حد عبث.
    """
    manual_ad_ids = set()
    manual_accounts = set()
    rejected_unsigned = 0
    rejected_old = 0
    try:
        r = std_requests.get(f"https://ntfy.sh/{BAN_TOPIC}/json?poll=1&since=all", timeout=10)
        if r.status_code == 200:
            now_ts = time.time()
            for line in r.text.strip().split("\n"):
                if not line:
                    continue
                try:
                    pkt = json.loads(line)
                    msg = pkt.get("message")
                    if not msg:
                        continue

                    ts = pkt.get("time") or 0
                    if ts and (now_ts - float(ts)) > CLOUD_BAN_MAX_AGE_DAYS * 86400:
                        rejected_old += 1
                        continue

                    b = json.loads(msg)

                    if BAN_SECRET and str(b.get("secret", "")) != BAN_SECRET:
                        rejected_unsigned += 1
                        continue

                    if b.get("ad_id"):
                        manual_ad_ids.add(int(b["ad_id"]))
                    sname = str(b.get("seller_name", "")).lower().strip()
                    if sname and sname not in ("مالك", "المالك"):
                        manual_accounts.add(f"name:{sname}")
                    sacc = str(b.get("account_id", "")).lower().strip()
                    if sacc and sacc not in ("name:مالك", "name:المالك"):
                        manual_accounts.add(sacc)
                except Exception:
                    pass
    except Exception:
        pass

    total = len(manual_ad_ids) + len(manual_accounts)
    if total > MAX_CLOUD_BANS:
        print(f"🛑 تحذير أمني: جت {total} طلب حظر من السحابة — أكتر من السقف "
              f"({MAX_CLOUD_BANS}). هيتنفّذ أول {MAX_CLOUD_BANS} بس. "
              f"لو إنت ما عملتش كده يدوي، يبقى فيه حد بيعبث بالموضوع العلني.")
        manual_ad_ids = set(sorted(manual_ad_ids)[:MAX_CLOUD_BANS])
        room = max(0, MAX_CLOUD_BANS - len(manual_ad_ids))
        manual_accounts = set(sorted(manual_accounts)[:room])

    if manual_ad_ids or manual_accounts:
        print(f"☁️  حظر سحابي: {len(manual_ad_ids)} إعلان | {len(manual_accounts)} حساب")
    if rejected_unsigned:
        print(f"🛑 اترفضت {rejected_unsigned} رسالة حظر من غير التوقيع الصحيح (BAN_SECRET)")
    if rejected_old:
        print(f"☁️  اترفضت {rejected_old} رسالة حظر قديمة (>{CLOUD_BAN_MAX_AGE_DAYS} يوم)")

    return manual_ad_ids, manual_accounts


def load_existing():
    kept = []
    dropped_unverified = []
    dropped_banned = []
    hard_banned_ids = {
        504371289, 504371232, 504371218, 504371178, 209365202,
        209420390, 504354549, 504144709
    }
    banned_accounts = set()
    preserved_top_keys = {}
    nocnt_attempts = {}

    cloud_ban_ids, cloud_ban_accs = fetch_manual_bans_from_cloud()
    hard_banned_ids |= cloud_ban_ids
    banned_accounts |= cloud_ban_accs
    # FIX(H2): الذاكرة بقت dict {ad_id: {"ts": ..., "reason": ...}} بدل set مجهول التاريخ
    checked = {int(i): {"ts": datetime.now(CAIRO_TZ).isoformat(), "reason": "HARD_BANNED"}
               for i in hard_banned_ids}

    try:
        with open("ads.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            nocnt_attempts = dict(data.get("nocnt_attempts_v1", {}) or {})
            # ✅ FIX(C10): "last_run_report" اتشالت من القائمة دي — scraper.py بقى
            #    بيكتبها بنفسه. لو فضلت هنا كانت بتكتب فوق التقرير الجديد بالتقرير
            #    القديم المجمّد (وده بالظبط اللي كان بيجمّد العداد على 29).
            for k in ("checked_extra_v13", "checked_extra_v14", "checked_extra_v15", "telegram_chat_ids", "telegram_welcomed_ids", "notified_ids_v1", "telegram_last_update_id"):
                if k in data:
                    preserved_top_keys[k] = data[k]

            banned_accounts |= set(data.get("banned_accounts_v7", []))
            banned_accounts.discard("name:مالك")
            banned_accounts.discard("name:المالك")

            for a in data.get("ads", []):
                aid = int(a.get("ad_id", 0))
                raw_sname = str(a.get("seller_name", "")).lower().strip()
                sname = f"name:{raw_sname}" if raw_sname not in ("", "مالك", "المالك") else ""
                sacc = str(a.get("account_id", "")).lower().strip()
                if sacc in ("name:مالك", "name:المالك"):
                    sacc = ""
                if aid in hard_banned_ids or (sname and sname in banned_accounts) or (sacc and sacc in banned_accounts):
                    dropped_banned.append((aid, str(a.get("seller_name", ""))[:24]))
                    hard_banned_ids.add(aid)
                    # FIX(H2): checked بقى dict — .add() كان هيرمي AttributeError
                    # جوه try/except فاضي، يعني كان هيفسُد تحميل ads.json بالكامل بصمت.
                    checked[int(aid)] = {"ts": datetime.now(CAIRO_TZ).isoformat(),
                                         "reason": "BANNED_ACCOUNT"}
                    continue
                if a.get("verified_v11") is True or a.get("verified_v12") is True:
                    # ✅ FIX(H3 في scraper): الكود كان **بيعيد تصنيف كل إعلان دوبيزل محفوظ
                    #    في كل رَن** بالكلمات المفتاحية — فبيمسح التصنيف الصح اللي جاي من
                    #    الـ breadcrumb الرسمي وقت الإضافة. يعني الإعلان يتصنّف صح أول مرة،
                    #    وبعدين يتقلب في الرَن اللي بعده. (نفس عيب H3 اللي في extra_radar.)
                    #    دلوقتي: بنحترم التصنيف المحفوظ، وبنكمّل الناقص بس.
                    if a.get("source", "دوبيزل") == "دوبيزل":
                        if not a.get("category") or not a.get("deal"):
                            deal, cat, sub = classify_deal_category_subtype(
                                a.get("url", ""), a.get("title", ""),
                                a.get("description", ""), "", int(a.get("price_num", 0)))
                            a["deal"] = deal or a.get("deal")
                            a["category"] = cat or a.get("category")
                            a["subtype"] = a.get("subtype") or sub
                        a["description"] = sanitize_desc_for_frontend(a.get("description", ""))
                    kept.append(a)
                else:
                    # ✅ FIX: الإعلانات دي كانت بتترمي **من غير أي سطر في اللوج** —
                    #    مستحيل تعرف إن بياناتك بتقل. دلوقتي بتتسجّل.
                    dropped_unverified.append((aid, a.get("source", "دوبيزل"),
                                               str(a.get("seller_name", ""))[:24]))

            # FIX(H2): هجرة من checked_ids_v11 (dict) أو من v10/v7 (list قديمة)
            if isinstance(data.get("checked_ids_v11"), dict):
                for k, v in data["checked_ids_v11"].items():
                    try:
                        checked[int(k)] = v if isinstance(v, dict) else {"ts": "", "reason": "LEGACY"}
                    except Exception:
                        pass
            else:
                legacy = data.get("checked_ids_v10") or data.get("checked_ids_v7") or []
                for old_cid in legacy:
                    try:
                        checked[int(old_cid)] = {"ts": "", "reason": "LEGACY"}
                    except Exception:
                        pass

            # FIX(H2): نسيان الأسباب "المرنة" بعد CHECKED_TTL_DAYS يوم
            # (السبب: الذاكرة كانت أبدية — 1140 ID متراكم، ومع إضافة عشرات IDs
            #  دفعة واحدة من extract_same_seller_ads_to_ban() المجمّع القابل للفحص
            #  كان بينكمش بشكل رتيب لحد ما بقى `Fresh unchecked candidates: 0` للأبد)
            cutoff = datetime.now(CAIRO_TZ) - timedelta(days=CHECKED_TTL_DAYS)
            pruned = 0
            for aid in list(checked.keys()):
                info = checked[aid] or {}
                reason = str(info.get("reason", ""))
                if aid in hard_banned_ids or any(reason.startswith(h) for h in HARD_REJECT_REASONS):
                    continue                      # رفض صلب ⇒ يفضل للأبد
                ts = str(info.get("ts", ""))
                if not ts:
                    continue                      # LEGACY بدون تاريخ ⇒ نحتفظ بيه
                try:
                    dt = datetime.fromisoformat(ts)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=CAIRO_TZ)
                    if dt < cutoff:
                        del checked[aid]
                        pruned += 1
                except Exception:
                    pass
            if pruned:
                print(f"FIX(H2): نسيان {pruned} ID قديم من ذاكرة المفحوص (TTL={CHECKED_TTL_DAYS} يوم)")
    except Exception:
        pass

    # ✅ FIX: بنبلّغ عن أي إعلان اتحذف وليه — قبل كده كان بيختفي في صمت تام.
    if dropped_banned:
        print(f"⚠️  حُذف {len(dropped_banned)} إعلان محفوظ لأن حساب البائع بقى محظور:")
        for aid, nm in dropped_banned[:10]:
            print(f"     - {aid} | {nm}")
    if dropped_unverified:
        print(f"⚠️  حُذف {len(dropped_unverified)} إعلان محفوظ من غير علامة verified_v11/v12:")
        for aid, src, nm in dropped_unverified[:10]:
            print(f"     - {aid} | {src} | {nm}")

    return (kept, checked, banned_accounts, preserved_top_keys, nocnt_attempts,
            dropped_banned, dropped_unverified)


def normalize_dubizzle_url(raw_u):
    if not raw_u:
        return None, None
    u = urllib.parse.unquote(urllib.parse.unquote(str(raw_u))).strip()
    # FIX: صفحات بروكسي جوجل بترجع اللينكات بمضيف translate.goog — لازم نرجّعها للأصل.
    # (اتأكد بالقياس: 92 لينك /ad/ في الصفحة، 0 منهم اتطبع قبل الإصلاح)
    u = re.sub(r"^https?://[^/\s]*translate\.goog/", "https://www.dubizzle.com.eg/", u)
    u = u.split("?")[0]  # FIX: اقطع query string بتاع بروكسي الترجمة قبل المطابقة
    u = re.sub(r"^https?://(?:www\.)?dubizzle\.com\.eg/+en/ad/", "https://www.dubizzle.com.eg/ad/", u)
    u = re.sub(r"^/+en/ad/", "/ad/", u)
    if u.startswith("/ad/"):
        u = "https://www.dubizzle.com.eg" + u
    m = re.search(r"(https?://(?:www\.)?dubizzle\.com\.eg/ad/[^\s\"'<>)\]]+?-ID(\d+)\.html)", u)
    if not m:
        return None, None
    full_u = m.group(1)
    ad_id = int(m.group(2))
    p = urllib.parse.urlsplit(full_u)
    clean_path = urllib.parse.quote(p.path, safe="/-._~")
    return f"https://www.dubizzle.com.eg{clean_path}", ad_id


def clean_markdown_to_text(md):
    txt = (md or "").translate(AR_DIGITS)
    txt = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", txt)
    txt = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", txt)
    txt = re.sub(r"https?://\S+", " ", txt)
    txt = re.sub(r"\bImage\s*\d+:?\b", " ", txt, flags=re.I)
    txt = re.sub(r"[*#_`~>]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def get_card_tier(card_text):
    t = card_text.translate(AR_DIGITS)
    if re.search(r"منذ\s*(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)", t):
        return 3
    m_d = re.search(r"منذ\s*(\d+)\s*(?:أيام|ايام|يوم)", t)
    if m_d:
        d = int(m_d.group(1))
        if d == 1:
            return 2
        if d <= 5:
            return 1
        return 0
    if re.search(r"منذ\s*(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة)", t):
        return 0
    return 1


def extract_links_from_text_or_html(raw_content):
    links = {}
    if not raw_content:
        return links
    for m in re.finditer(r"(?:https?://(?:www\.)?dubizzle\.com\.eg)?/+(?:en/)?ad/[^\s\"'<>)\]]+?-ID(\d+)\.html", raw_content):
        clean_u, ad_id = normalize_dubizzle_url(m.group(0))
        if not clean_u or not ad_id:
            continue
        window = raw_content[max(0, m.start() - 260):min(len(raw_content), m.end() + 260)]
        card_snip = clean_markdown_to_text(window)
        # FIX(M5): لو النافذة بيانات منظمة (JSON-LD / state) فهي نص إعلانات تانية أو ميتاداتا،
        # مش وصف الإعلان نفسه ⇒ ما نحكمش بيها على المنطقة. الحكم الحقيقي بيحصل على صفحة الإعلان.
        if any(k in card_snip for k in ('"@type"', '"position"', 'itemListElement', 'addressCountry', 'accommodationCategory')):
            card_snip = ""
        if ad_id not in links or len(card_snip) > len(links[ad_id][1]):
            links[ad_id] = (clean_u, card_snip)
    return links


# ==============================================================================
#  طبقة الجلب الجديدة  —  FIX(C2) + FIX(C4) + FIX(C5)
# ------------------------------------------------------------------------------
#  القياس الحي يوم 2026-11-09 على دوبيزل:
#     مباشر (curl_cffi / requests)     -> 403
#     r.jina.ai على صفحات الفئات       -> 200 بس المحتوى "error 503" (287 حرف)
#     r.jina.ai على صفحات الإعلانات    -> 200 بس نص مشوّه (تنقّل الموقع بدل الإعلان)
#     translate.goog (بروكسي جوجل)     -> 200 / 2 ميجابايت / المحتوى كامل  ✅
# ==============================================================================

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
BASE_HEADERS = {"User-Agent": UA, "Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7"}


def to_translate_proxy(url):
    """يحوّل أي URL لنسخة بروكسي ترجمة جوجل (بتعدي حماية البوتات)."""
    p = urllib.parse.urlsplit(url)
    host = p.netloc.replace(".", "-")
    q = (p.query + "&" if p.query else "") + "_x_tr_sl=en&_x_tr_tl=ar&_x_tr_hl=ar"
    return f"https://{host}.translate.goog{p.path}?{q}"


DATE_MARKER = "[تاريخ النشر]"
CAT_MARKER = "[فئة دوبيزل]"

# ✅ سطر الـ breadcrumb في صفحة الإعلان شكله:  "<العنوان> - <الفئة> - <رقم الإعلان>"
#    ودي **أدق مصدر للتصنيف** — من دوبيزل نفسها، مش تخمين بالكلمات المفتاحية.
DUBIZZLE_CATEGORIES = (
    "شقق للبيع", "شقق للإيجار", "شقق للايجار", "فلل للبيع", "فلل للإيجار", "فلل للايجار",
    "عقار تجارى للبيع", "عقار تجارى للإيجار", "عقار تجاري للبيع", "عقار تجاري للإيجار",
    "مبانى و أراضى", "مباني و أراضي", "مباني واراضي",
    "عقارات مصايف للبيع", "عقارات مصايف للإيجار",
)
BREADCRUMB_RE = re.compile(
    r"^(.{4,200}?)\s+-\s+(" + "|".join(re.escape(c) for c in DUBIZZLE_CATEGORIES) +
    r")\s+-\s+(\d{6,})\s*$", re.M
)

# علامات بداية محتوى الإعلان الحقيقي (بعد قائمة الفئات الضخمة)
CONTENT_ANCHORS = ("الوصف", "الموقع", "تم النشر بواسطة", "المساحة", "إجمالي السعر",
                   "السعر", "ج.م", "EGP", "غرف النوم", "الحمامات", "رقم الإعلان")


CONTENT_LABELS = {
    "الوصف", "الموقع", "السعر", "إجمالي السعر", "المساحة", "غرف النوم", "الحمامات",
    "تفاصيل", "الكماليات", "تم النشر بواسطة", "رقم الإعلان", "إظهار الرقم", "واتساب",
    "سلامتك تهمنا", "مشاركة الإعلان", "الإبلاغ عن هذا الإعلان", "عضو منذ",
    "الإعلانات النشطة", "مواصفات العقار", "نوع العقار", "غرض العقار", "الطابق",
    "شاهد المزيد من إعلانات", "خصائص العقار", "تفاصيل العقار",
}
MENU_LINE_MAX = 48


def _looks_like_menu_line(line):
    """سطر القائمة = من غير أرقام، ومش واحد من علامات محتوى الإعلان."""
    l = (line or "").strip()
    if not l or l in CONTENT_LABELS:
        return False
    if re.search(r"\d", l):
        return False                    # الأسعار والمقاسات وأرقام الإعلانات فيها أرقام
    if len(l) <= MENU_LINE_MAX:
        return True
    # أسطر ملخّص القوائم الطويلة: "سيارات للبيع; سيارات للإيجار; كاوتش، بطاريات..."
    if ";" in l or "؛" in l:
        return True
    return False


MENU_RUN_MIN = 10     # أقل طول لـ"جيش" أسطر قوائم يستحق الحذف


def strip_site_menu(text):
    """
    بيشيل قوائم فئات موقع دوبيزل الضخمة اللي بتتحشر جوه صفحة الإعلان.

    القياس الحي على إعلان واحد:
        610 سطر ⇒ 602 منهم أسطر قوائم، و8 أسطر بس محتوى حقيقي.

    الطريقة: بنحذف أي **جيش متواصل** من أسطر القوائم طوله >= MENU_RUN_MIN.
    الجيوش القصيرة (1-3 أسطر) بتفضل — لأنها غالباً محتوى حقيقي
    (مثلاً اسم البائع "Ahmed Abdul Fattah" سطر قصير من غير أرقام
     وكان بيترمي بالغلط في النسخة الأولى من الإصلاح).

    الضرر قبل الإصلاح:
        • تصنيف غلط: إعلان "شقة للبيع" بيتصنّف "مبانى و أراضى"
        • رفض غلط: كلمات ممنوعة من القوائم ("المعادي"، "الهرم") ترفض إعلان سليم
        • نص 71 ألف حرف بدل 2-3 آلاف ⇒ إهدار في المعالجة
    """
    if not text:
        return text
    m_bc = BREADCRUMB_RE.search(text)
    start = m_bc.end() if m_bc else 0
    head, rest = text[:start], text[start:]

    lines = rest.split("\n")
    keep = [True] * len(lines)
    i = 0
    while i < len(lines):
        if _looks_like_menu_line(lines[i]):
            j = i
            while j < len(lines) and _looks_like_menu_line(lines[j]):
                j += 1
            if (j - i) >= MENU_RUN_MIN:          # جيش قوائم ⇒ احذفه كله
                for k in range(i, j):
                    keep[k] = False
            i = j
        else:
            i += 1

    return head + "\n" + "\n".join(l for l, k in zip(lines, keep) if k)


def parse_breadcrumb(text):
    """بيرجّع (title, dubizzle_category, ad_id) من سطر الـ breadcrumb — أو (None,)*3."""
    m = BREADCRUMB_RE.search(text or "")
    if not m:
        return None, None, None
    return m.group(1).strip(), m.group(2).strip(), int(m.group(3))

# نمط تاريخ الإعلان النسبي في دوبيزل
DATE_REL_RE = re.compile(
    r"منذ\s*\d*\s*(?:ثانية|ثواني|دقيقة|دقائق|ساعة|ساعات|ساعه|يوم|أيام|ايام|يومًا|يوما|"
    r"أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة|سنه|سنوات)"
)


def html_to_text(html):
    """
    FIX(C5) — النسخة الصحيحة.

    ⚠️ اكتشاف مهم بالقياس: **محتوى الإعلان نفسه (التاريخ + السعر + الوصف + بوكس البائع)
       عايش جوه عناصر <header> متداخلة**. فحذف `header` من الصفحة — اللي كان بيعمله
       الكود الأصلي في direct_dubizzle_fetch — كان بيدمّر الإعلان كله:
          • مع الحذف:  body = 9584 حرف، 602 من 610 سطر = قوائم الموقع، ومفيش "الوصف" خالص
          • بدون حذف:  التاريخ والسعر والوصف وبوكس البائع كلهم موجودين

       عشان كده هنا بنحذف السكربتات والتنسيقات بس، وبنعتمد على strip_site_menu()
       لإزالة قوائم الموقع (602 سطر ضوضاء) بدل ما نحذف عناصر كاملة.
    """
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    title_line = f"# {h1.get_text(' ', strip=True)}\n" if h1 else ""

    links_buf = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/profile/" in href:
            full = "https://www.dubizzle.com.eg" + href if href.startswith("/") else href
            links_buf.append(f"[{a.get_text(' ', strip=True)}]({full})")

    for tag in soup.find_all(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    body = soup.get_text("\n", strip=True)

    # ✅ تاريخ الإعلان = أول تاريخ نسبي في الصفحة (تواريخ الإعلانات المشابهة بتيجي بعدين).
    #    مستثنين "عضو منذ <سنة>" لأنه تاريخ تسجيل البائع مش تاريخ الإعلان.
    own_date = ""
    body_no_member = re.sub(r"عضو\s*منذ\s*\d{4}", " ", body)
    m = DATE_REL_RE.search(body_no_member)
    if m:
        own_date = re.sub(r"\s+", " ", m.group(0)).strip()

    bc_title, bc_cat, bc_id = parse_breadcrumb(body)
    date_line = f"{DATE_MARKER} {own_date}\n" if own_date else ""
    cat_line = f"{CAT_MARKER} {bc_cat}\n" if bc_cat else ""

    body = strip_site_menu(body)

    return title_line + date_line + cat_line + "\n" + body + "\n" + "\n".join(links_buf)


def is_valid_ad_page(text):
    """
    FIX(C4): شرط صلاحية صارم لصفحة الإعلان.

    ❌ الشرط القديم كان: `"تم النشر بواسطة" in t or "/ad/" in t or "لم يعد..." in t`
       → "/ad/" بيتحقق في أي صفحة تنقّل، فالسكريبر كان بيقبل نفايات
         (نص فعلي لقيه: "عربيات وقطع غيار سيارات للبيع ... مرسيدس بنز هيونداي")
         وبعدين tier=0 ⇒ OLD_AD ⇒ رفض + تعليم أبدي كـ"مفحوص".
    ✅ الجديد: لازم يبقى فيه محتوى إعلان حقيقي.
    """
    if not text or len(text) < 1500:
        return False
    if "لم يعد هذا الإعلان متاح" in text or "هذا الإعلان غير متاح" in text:
        return True          # صفحة صالحة (إعلان منتهي) — لازم نرجّعها عشان نُعلّمها checked
    has_desc = "الوصف" in text
    has_seller = "تم النشر بواسطة" in text
    has_specs = any(w in text for w in ("المساحة", "غرف", "الحمامات", "ج.م", "جنيه", "الموقع"))
    return has_desc and (has_seller or has_specs)


def fetch_listing_page(url, cffi_sess, timeout_sec=30, tries=3):
    """
    يجيب صفحة فئة/قائمة (مش صفحة إعلان). بيرجّع HTML خام أو "".
    ⚠️ ما ينطبقش عليها is_valid_ad_page() — صفحات القوائم بطبيعتها
       ما فيهاش "الوصف" ولا "تم النشر بواسطة".
    """
    for i in range(tries):
        try:
            r = cffi_sess.get(to_translate_proxy(url), headers=BASE_HEADERS, timeout=timeout_sec)
            if r.status_code == 200 and len(r.text) > 20000:
                if re.search(r"/ad/[^\s\"'<>]+?-ID\d+\.html", r.text):
                    return r.text
        except Exception:
            pass
        time.sleep(1.2 * (i + 1))

    for i in range(2):                                   # احتياطي: Jina
        try:
            r = cffi_sess.get("https://r.jina.ai/" + url, headers=BASE_HEADERS, timeout=25)
            if r.status_code == 200 and re.search(r"-ID\d+\.html", r.text or ""):
                return r.text
        except Exception:
            pass
        time.sleep(2)
    return ""


def fetch_ad_page(url, cffi_sess, req_sess=None, timeout_sec=30, tries=3):
    """
    مسار الجلب الموحّد لصفحة الإعلان التفصيلية.
    يستبدل direct_dubizzle_fetch() + jina_get() بالكامل.
    الترتيب: translate.goog → r.jina.ai → مباشر.
    """
    # 1) بروكسي جوجل (الأعلى نجاحاً في القياسات)
    for i in range(tries):
        try:
            r = cffi_sess.get(to_translate_proxy(url), headers=BASE_HEADERS, timeout=timeout_sec)
            if r.status_code == 200 and len(r.text) > 20000:
                txt = html_to_text(r.text)
                if is_valid_ad_page(txt):
                    return txt
        except Exception:
            pass
        time.sleep(1.2 * (i + 1))

    # 2) Jina Reader (احتياطي)
    for i in range(2):
        try:
            r = cffi_sess.get("https://r.jina.ai/" + url, headers=BASE_HEADERS, timeout=25)
            if r.status_code == 429:
                time.sleep(8 + i * 5)
                continue
            if r.status_code == 200 and is_valid_ad_page(r.text):
                return r.text
        except Exception:
            pass
        time.sleep(1.5)

    # 3) مباشر (آخر محاولة)
    for sess in [s for s in (cffi_sess, req_sess) if s is not None]:
        try:
            r = sess.get(url, headers=BASE_HEADERS, timeout=20)
            if r.status_code == 200 and len(r.text) > 20000:
                txt = html_to_text(r.text)
                if is_valid_ad_page(txt):
                    return txt
        except Exception:
            pass
    return ""


def parse_listing_jsonld(html):
    """
    🎁 صفحة الفئة فيها <script application/ld+json> بـ ItemList فيه ~46 إعلان،
    وكل إعلان فيه: name + url + mainEntity{accommodationCategory, numberOfBedrooms}
    + offers{businessFunction: Sell/Lease}.
    ⇒ 46 إعلان من **طلب واحد** بدون فتح أي صفحة إعلان.
    """
    m = re.search(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html or "", re.S)
    if not m:
        return []
    try:
        j = json.loads(m.group(1))
    except Exception:
        return []

    def walk(o):
        if isinstance(o, dict):
            if o.get("@type") == "ItemList":
                yield o
            for v in o.values():
                yield from walk(v)
        elif isinstance(o, list):
            for v in o:
                yield from walk(v)

    out = []
    for il in walk(j):
        for e in il.get("itemListElement", []) or []:
            it = e.get("item") or {}
            me = it.get("mainEntity") or {}
            off = it.get("offers") or {}
            cu, aid = normalize_dubizzle_url(it.get("url") or me.get("url") or "")
            bf = str(off.get("businessFunction", "")).lower()
            out.append({
                "ad_id": aid,
                "url": cu,
                "title": (it.get("name") or me.get("name") or ""),
                "accommodation_category": me.get("accommodationCategory", ""),
                "bedrooms": me.get("numberOfBedrooms"),
                "deal_hint": "إيجار" if ("lease" in bf or "rent" in bf) else ("بيع" if "sell" in bf else ""),
            })
        break
    return out


def get_featured_ad_ids(html):
    """
    بيرجّع IDs الإعلانات المميزة/المدفوعة ("ad_ids" + "ad_ids_set_2" + "ad_ids_set_3").
    💡 القياس أثبت إن الصفحة الأولى ~97% سماسرة — ومعظمهم في البلوك المميّز ده.
    """
    featured = set()
    for key in ("ad_ids", "ad_ids_set_2", "ad_ids_set_3", "ad_ids_set_4"):
        m = re.search(rf'"{key}":\[([^\]]*)\]', html or "")
        if m:
            featured.update(int(x) for x in re.findall(r'"(\d+)"', m.group(1)))
    return featured


def fetch_live_dubizzle_categories(req_sess, cffi_sess):
    """
    FIX(C2) + FIX(H2) + التحسين الاستراتيجي.

    التغييرات مقابل النسخة القديمة:
      1) مسار الجلب بقى fetch_listing_page (بروكسي جوجل) بدل jina_get — كان بيرجع 503.
      2) الصفحات بقت 1 و 4-8 بدل 1-3 فقط.
         القياس الحي (عينة 5 إعلانات من كل صفحة):
            صفحة 1: مالك=0  سمسار=4      صفحة 6: مالك=1  سمسار=4
            صفحة 5: مالك=0  سمسار=4      صفحة 7: مالك=2  سمسار=3
         ⇒ السماسرة بيعملوا إعادة نشر كل ساعة فبيحتكروا أول صفحات.
      3) تخطي الإعلانات المميزة/المدفوعة (get_featured_ad_ids) — دي تقريباً كلها سماسرة.
      4) FIX(M5): فلترة المناطق بقت على **عنوان الإعلان نفسه** من JSON-LD
         بدل نافذة ±260 حرف اللي كانت بتاخد نص الإعلانات المجاورة.
      5) FIX(M8): ميزانية زمنية مستقلة (DISCOVERY_BUDGET_SECONDS) عشان ماياكلش وقت الطابور.
      6) عدد الصفحات بقى 40 بدل 14 (الجلب بقى أسرع وأكثر موثوقية).
    """
    live_found = {}
    skipped_broker_titles = 0
    start = time.time()

    all_cat_pages = []
    for base in DUBIZZLE_CATEGORY_BASES:
        all_cat_pages.append(base)                      # صفحة 1
        for pg in (4, 5, 6, 7, 8):                      # صفحات أعمق = ملاك أكتر
            all_cat_pages.append(f"{base}?page={pg}")
    random.shuffle(all_cat_pages)

    pages_done = 0
    for cat_url in all_cat_pages[:40]:
        if (time.time() - start) > DISCOVERY_BUDGET_SECONDS:
            print(f"Discovery budget reached after {pages_done} pages")
            break

        raw_html = fetch_listing_page(cat_url, cffi_sess, timeout_sec=28)
        if not raw_html:
            continue
        pages_done += 1

        featured = get_featured_ad_ids(raw_html)

        # FIX(M5): عنوان كل إعلان من JSON-LD (بيانات دقيقة، مش نص مجاور)
        ld_titles = {}
        for row in parse_listing_jsonld(raw_html):
            if row.get("ad_id") and row.get("url"):
                ld_titles[row["ad_id"]] = row

        for ad_id, (u, card_snip) in extract_links_from_text_or_html(raw_html).items():
            if ad_id in featured:
                continue                                # تخطي المدفوع/المميز

            ld = ld_titles.get(ad_id) or {}
            own_title = ld.get("title") or card_snip

            if forbidden_area_hit(own_title, STRICT_FORBIDDEN_EVERYWHERE):
                continue
            tier = get_card_tier(card_snip) if card_snip else 1
            if tier == 0:
                continue

            # 🎯 فلترة أولية بالعنوان (بدون أي طلب شبكة):
            #    BROKER ⇒ نتخطاه تماماً — وفّر 30% من ميزانية الجلب في القياس الحي
            signal = classify_title_signal(own_title)
            if signal == "BROKER":
                skipped_broker_titles += 1
                continue

            prio = SIGNAL_PRIORITY[signal]
            if ad_id in featured:
                prio += 1          # الإعلانات المدفوعة/المميزة تتأخر (مش بتتلغى)

            if ad_id not in live_found or prio < live_found[ad_id][3] or tier > live_found[ad_id][2]:
                live_found[ad_id] = (u, own_title, tier, prio)

        time.sleep(0.4)

    print(f"Discovery: {pages_done} pages | {len(live_found)} candidates | "
          f"{skipped_broker_titles} broker-titles skipped (free) | {time.time() - start:.0f}s")
    return live_found


def slice_from_h1(raw_text):
    m_h1 = re.search(r"^#\s+.+$", raw_text, flags=re.M)
    if m_h1:
        return raw_text[max(0, m_h1.start() - 180):]
    return raw_text


def tier_from_age_label(label):
    """يحوّل نص عمر الإعلان ("منذ 3 ساعات") لرقم tier — 3=أحدث، 0=قديم."""
    t = (label or "").translate(AR_DIGITS)
    if re.search(r"(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)", t):
        return 3
    m = re.search(r"(\d+)\s*(?:أيام|ايام|يومًا|يوما|يوم)", t)
    if m:
        d = int(m.group(1))
        if d > 5:
            return 0
        return 2 if d == 1 else 1
    if re.search(r"(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة|سنه|سنوات)", t):
        return 0
    return 0


def check_ad_freshness(raw_text):
    # ✅ الأولوية للتاريخ المستخرج من <header> (اللي html_to_text حقنته بعلامة واضحة).
    #    السبب: عناصر <article> للإعلانات المشابهة فيها تواريخ إعلانات تانية
    #    ("منذ 2 أسابيع") ولو اتقريت الأول هترفض إعلان عمره ساعات.
    m_own = re.search(re.escape(DATE_MARKER) + r"\s*(منذ[^\n]{2,40})", raw_text or "")
    if m_own:
        label = re.sub(r"\s+", " ", m_own.group(1)).strip()
        return tier_from_age_label(label), label

    sliced = slice_from_h1(raw_text)
    before_desc = sliced.split("الوصف")[0] if "الوصف" in sliced else sliced[:2200]
    header_txt = clean_markdown_to_text(before_desc)

    m_old = re.search(
        r"منذ\s*(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة|سنه|سنوات)",
        header_txt
    )
    if m_old:
        return 0, m_old.group(0)

    m_old2 = re.search(
        r"(\d+)?\s*(أسبوع|اسبوع|أسابيع|اسابيع|شهر|أشهر|اشهر|شهور|سنة|سنه|سنوات)\s*(?:مضى|مضت)",
        header_txt
    )
    if m_old2:
        return 0, m_old2.group(0)

    m_days = re.search(r"منذ\s*(\d+)\s*(?:أيام|ايام|يومًا|يوما|يوم)", header_txt)
    if m_days:
        d = int(m_days.group(1))
        if d > 5:
            return 0, m_days.group(0)
        if d == 1:
            return 2, m_days.group(0)
        return 1, m_days.group(0)

    m_days2 = re.search(r"(\d+)\s*(?:أيام|ايام|يومًا|يوما|يوم)\s*(?:مضى|مضت)", header_txt)
    if m_days2:
        d = int(m_days2.group(1))
        if d > 5:
            return 0, m_days2.group(0)
        if d == 1:
            return 2, m_days2.group(0)
        return 1, m_days2.group(0)

    m_hours = re.search(
        r"منذ\s*(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)",
        header_txt
    )
    if m_hours:
        return 3, m_hours.group(0)

    m_hours2 = re.search(
        r"(\d+)?\s*(ثواني|ثانية|دقائق|دقيقة|دقيقه|ساعات|ساعة|ساعه)\s*(?:مضى|مضت)",
        header_txt
    )
    if m_hours2:
        return 3, m_hours2.group(0)

    return 0, "OLD_OR_UNKNOWN_DATE"


# --------------------------------------------------------------------------------
#  FIX(C3) + FIX(H1) — استخراج البائع وعدد إعلاناته النشطة
# --------------------------------------------------------------------------------
#  الشكل الحقيقي لبوكس البائع في صفحة دوبيزل (اتأكد منه بالقياس الحي 2026-11-09):
#
#      تم النشر بواسطة
#      Ahmed Abdul Fattah        ← الاسم
#      عضو منذ
#      2014                      ← سنة التسجيل (دي اللي كانت بتتلخبط مع عدد الإعلانات)
#      الإعلانات النشطة
#      1                         ← العدد الحقيقي ✅
#      إظهار الرقم
#      واتساب
#      رقم الإعلان
#      504238147
#
#  الأخطاء الأربعة اللي كانت في النسخة القديمة:
#    (1) كان بيدور على "رقم + إعلانات نشطة" — والترتيب الفعلي معكوس!
#    (2) كان بياخد min() من كل الأرقام في الصفحة كلها (بما فيها سنة العضوية)
#    (3) كان بياخد split("تم النشر بواسطة")[-1] = **آخر** ظهور (من ويدجت إعلانات مشابهة)
#        ⇒ 3 إعلانات مختلفة تماماً رجّعت نفس البائع "Property Hills One 1" و cnt=221
#    (4) كان بيفرض cnt=99 لو "/companies/" موجود في **أي حتة** في النص
#        ⇒ لينك فوتر الموقع بيحوّل كل مالك مباشر لسمسار
#        ⇒ 19 من 21 إعلان في آخر رن اترفدوا بـ BANNED_BROKER_99_ADS
# --------------------------------------------------------------------------------

COMPANY_HINTS = ("real estate", "realestate", "real-estate", "properties", "property",
                 "developments", "development", "investment", "consultancy", "holding",
                 "company", "للعقارات", "للتطوير", "للاستثمار العقاري", "شركة", "مؤسسة",
                 "وسيط", "مسوق عقاري", "للتسويق")

# ✅ النمط الكامل: الاسم + سنة العضوية + عدد الإعلانات النشطة في مطابقة واحدة
PAT_SELLER_FULL = re.compile(
    r"تم النشر بواسطة\s*(.{2,55}?)\s*عضو منذ\s*(\d{4})\s*"
    r"(?:الإعلانات|الاعلانات)\s*(?:ال)?نشطة\s*(\d{1,4})"
)
PAT_SELLER_NAME = re.compile(
    r"تم النشر بواسطة\s*(.{2,55}?)(?:\s*عضو منذ|\s*(?:الإعلانات|الاعلانات)\s*(?:ال)?نشطة)"
)
PAT_ACTIVE_ADS = re.compile(r"(?:الإعلانات|الاعلانات)\s*(?:ال)?نشطة\s*(\d{1,4})")
# ✅ البروفايل فقط — مش /companies/ (اللي هو دليل شركات الموقع في الفوتر)
PAT_PROFILE_LINK = re.compile(r"dubizzle\.com\.eg/(?:en/)?profile/([^\s\"'/?#)\]]+)")


def extract_seller_account_and_active_ads(text_src):
    """
    بيرجّع (cnt, seller, account_id).
    cnt = 0 معناها "مش معروف" — ودي **مش** سبب رفض (شوف FIX(C6) في inspect_and_parse).
    """
    if not text_src:
        return 0, "", ""

    clean = clean_markdown_to_text(text_src)
    cnt, seller = 0, "مالك"

    # 1) المطابقة الكاملة (الأدق — بتثبت إننا جوه بوكس البائع الحقيقي)
    m = PAT_SELLER_FULL.search(clean)
    if m:
        seller = m.group(1).strip(" .-:|")
        cnt = int(m.group(3))
    else:
        # 2) أنماط احتياطية لو ترتيب الصفحة اتغير
        m_name = PAT_SELLER_NAME.search(clean)
        if m_name:
            seller = m_name.group(1).strip(" .-:|")
        m_cnt = PAT_ACTIVE_ADS.search(clean)      # ✅ أول ظهور = بوكس الإعلان نفسه
        if m_cnt:
            cnt = int(m_cnt.group(1))

    # 3) account_id من لينك البروفايل
    account_id = ""
    m_prof = PAT_PROFILE_LINK.search(text_src)
    if m_prof:
        account_id = m_prof.group(1).strip().lower()

    if seller in ("مالك", "المالك", "") and account_id:
        seller = account_id
    if not account_id and seller not in ("مالك", "المالك", ""):
        account_id = f"name:{seller.lower().strip()}"

    # 4) FIX(C3): كشف الشركات من **اسم البائع نفسه** أو من علامة "شركة موثقة"،
    #             مش من وجود لينك /companies/ في أي حتة في الصفحة.
    if seller not in ("مالك", "المالك", ""):
        low = seller.lower()
        if "شركة موثقة" in clean or any(h in low for h in COMPANY_HINTS):
            cnt = max(cnt, 99)

    return cnt, seller, account_id


def extract_same_seller_ads_to_ban(raw_text):
    banned_ad_ids = set()
    if not raw_text or "شاهد المزيد من إعلانات" not in raw_text:
        return banned_ad_ids
    after_more = raw_text.split("شاهد المزيد من إعلانات", 1)[1][:4000]
    for m in re.finditer(r"-ID(\d+)\.html", after_more):
        banned_ad_ids.add(int(m.group(1)))
    return banned_ad_ids


def extract_related_fresh(raw_text, exclude_ids=None):
    related = {}
    if not raw_text:
        return related
    exclude_ids = exclude_ids or set()

    for rid, (ru, rcard) in extract_links_from_text_or_html(raw_text).items():
        if rid in exclude_ids:
            continue
        if forbidden_area_hit(rcard, STRICT_FORBIDDEN_EVERYWHERE):
            continue
        tier = get_card_tier(rcard)
        if tier == 0:
            continue
        if any(w in rcard for w in NEW_CAIRO_WORDS):
            related[rid] = (ru, rcard, tier)
    return related


# FIX(H2): أسباب الرفض "الصلبة" ما بتنتهيش، و"المرنة" بتنتهي بعد CHECKED_TTL_DAYS
HARD_REJECT_REASONS = ("EXPIRED", "OLD_AD", "EXCLUDED_AREA", "BANNED_ACCOUNT", "BANNED_BROKER")


def mark_checked(checked_ids, ad_ids, reason):
    """يسجّل ID(s) في ذاكرة المفحوص مع التوقيت والسبب (بدل set.add المجهول)."""
    ts = datetime.now(CAIRO_TZ).isoformat()
    if isinstance(ad_ids, int):
        ad_ids = [ad_ids]
    for aid in ad_ids:
        checked_ids[int(aid)] = {"ts": ts, "reason": reason}


def inspect_and_parse(req_sess, cffi_sess, ad_id, url, snippet, banned_accounts,
                      checked_ids, nocnt_attempts=None):
    # FIX(C2/C4/C5): مسار الجلب الجديد بدل jina_get
    raw_s = fetch_ad_page(url, cffi_sess, req_sess)
    if not raw_s:
        return None, False, "NO_PAGE", {}

    if "لم يعد هذا الإعلان متاح" in raw_s or "هذا الإعلان لم يعد متاح" in raw_s or "هذا الإعلان غير متاح" in raw_s:
        return None, True, "EXPIRED", {}

    tier, age_label = check_ad_freshness(raw_s)
    if tier == 0 and age_label != "OLD_OR_UNKNOWN_DATE":
        print(f"Skipped Old Ad {ad_id}: Age={age_label}")
        return None, True, "OLD_AD", {}

    cnt, seller, account_id = extract_seller_account_and_active_ads(raw_s)
    sname_key = f"name:{seller.lower().strip()}" if (seller and seller not in ("مالك", "المالك")) else ""

    if (account_id and account_id in banned_accounts) or (sname_key and sname_key in banned_accounts):
        same_broker_ids = extract_same_seller_ads_to_ban(raw_s)
        mark_checked(checked_ids, same_broker_ids, "BANNED_ACCOUNT_SIBLINGS")
        print(f"Skipped Banned Account ({seller}) on Ad {ad_id}")
        return None, True, "BANNED_ACCOUNT", {}

    fallback_s = ""
    if cnt == 0:
        fallback_s = fetch_ad_page(url + "?abs=1", cffi_sess, req_sess, tries=2)
        if fallback_s:
            if "لم يعد هذا الإعلان متاح" in fallback_s or "هذا الإعلان لم يعد متاح" in fallback_s:
                return None, True, "EXPIRED", {}
            if tier == 0:
                tier, age_label = check_ad_freshness(fallback_s)
            cnt2, seller2, acc2 = extract_seller_account_and_active_ads(fallback_s)
            if cnt2 > cnt:
                cnt = cnt2
            if seller == "مالك" and seller2 != "مالك":
                seller = seller2
            if not account_id and acc2:
                account_id = acc2

    if tier == 0:
        print(f"Skipped Old Ad {ad_id}: Age={age_label}")
        return None, True, "OLD_AD", {}

    # FIX(C6): الكود القديم كان بيرجّع mark_checked=False ⇒ الإعلان يُعاد فحصه كل رن
    # للأبد، فيستنزف ميزانية الـ 8 دقايق والطابور ما بيتقدمش ⇒ صفر إضافة.
    # الحل: عدّاد محاولات. بعد NO_CNT_MAX_TRIES نعلّمه كمفحوص (سبب مرن بينتهي بـ TTL)
    # عشان يسيب مكانه لإعلانات تانية، ويتجرّب تاني بعد أسبوعين.
    if cnt == 0:
        if nocnt_attempts is None:
            return None, False, "NO_CNT", {}
        tries = int(nocnt_attempts.get(str(ad_id), 0)) + 1
        nocnt_attempts[str(ad_id)] = tries
        if tries < NO_CNT_MAX_TRIES:
            print(f"NO_CNT for {ad_id} (attempt {tries}/{NO_CNT_MAX_TRIES}) — هيتجرب تاني")
            return None, False, "NO_CNT_RETRY", {}
        nocnt_attempts.pop(str(ad_id), None)
        print(f"NO_CNT for {ad_id} بعد {tries} محاولات — بيتعلّم كمفحوص مؤقتاً")
        return None, True, "NO_CNT", {}

    print(f"Checked Ad {ad_id} ({age_label}): Active_Ads={cnt} | Seller={seller}")

    if cnt not in (1, 2, 3, 4):
        if cnt != 99:
            if account_id and account_id not in ("name:مالك", "name:المالك"):
                banned_accounts.add(account_id)
            if seller and seller not in ("مالك", "المالك"):
                banned_accounts.add(f"name:{seller.lower().strip()}")
            same_broker_ids = extract_same_seller_ads_to_ban(raw_s)
            if fallback_s:
                same_broker_ids |= extract_same_seller_ads_to_ban(fallback_s)
            mark_checked(checked_ids, same_broker_ids, f"BANNED_BROKER_{cnt}_ADS_SIBLINGS")
        return None, True, f"BANNED_BROKER_{cnt}_ADS", {}

    related_today = extract_related_fresh(raw_s, exclude_ids=checked_ids)
    if fallback_s:
        related_today.update(extract_related_fresh(fallback_s, exclude_ids=checked_ids))

    sliced_raw = slice_from_h1(raw_s)
    combined_raw = sliced_raw + "\n" + (slice_from_h1(fallback_s) if fallback_s else "")
    desc_clean = ""
    for src in [sliced_raw, fallback_s]:
        if src and "الوصف" in src:
            after_desc = src.split("الوصف")[-1]
            for stop_w in ["تم النشر بواسطة", "الموقع", "معرّف الإعلان", "معرف الإعلان", "رقم الإعلان", "اقرأ المزيد في التطبيق", "الكماليات"]:
                if stop_w in after_desc:
                    after_desc = after_desc.split(stop_w)[0]
            cand = clean_markdown_to_text(after_desc)
            if len(cand) > len(desc_clean):
                desc_clean = cand

    title_clean = ""
    m_h1 = re.search(r"^#\s+(.+)$", raw_s, flags=re.M)
    if m_h1:
        title_clean = clean_markdown_to_text(m_h1.group(1))
    if not title_clean:
        m_t = re.search(r"Title:\s*(.+?)(?:\n|\|)", raw_s)
        if m_t:
            title_clean = clean_markdown_to_text(m_t.group(1))

    top_sec = clean_markdown_to_text(sliced_raw.split("تم النشر بواسطة")[0] if "تم النشر بواسطة" in sliced_raw else sliced_raw[:2500])
    before_desc_clean = clean_markdown_to_text(sliced_raw.split("الوصف")[0] if "الوصف" in sliced_raw else sliced_raw[:1400])
    loc_box_clean = clean_markdown_to_text(combined_raw.split("الموقع")[-1][:220]) if "الموقع" in combined_raw else ""

    official_loc_and_title = f"{title_clean} {before_desc_clean} {loc_box_clean}"
    entire_ad_text = f"{official_loc_and_title} {desc_clean}"

    # 🛡️ FIX(طلب المالك): المطابقة بقت واعية بالسياق.
    #    «تبعد عن بيت الوطن 5 دقايق» ⇒ مش في بيت الوطن ⇒ الإعلان يعدي.
    #    «شقة في بيت الوطن»         ⇒ مرفوض.
    bad_hit = forbidden_area_hit(official_loc_and_title, STRICT_FORBIDDEN_EVERYWHERE)
    if bad_hit:
        print(f"Skipped Excluded Area ({bad_hit}) in Ad {ad_id}")
        return None, True, "EXCLUDED_AREA", {}

    bad_hit = forbidden_area_hit(official_loc_and_title, EXCLUDE_CITIES)
    if bad_hit:
        print(f"Skipped Excluded Location ({bad_hit}) in Ad {ad_id}")
        return None, True, "EXCLUDED_AREA", {}

    # 🛡️ FIX(طلب المالك): مرفوض أي إعلان نفسه بالتقسيط/الأقساط.
    #    «بدون أقساط» و«لا تقسيط» و«كاش فقط» ⇒ بيتقبلوا عادي.
    if has_installment_offer(f"{official_loc_and_title} {desc_clean}"):
        print(f"Skipped Installment Ad (تقسيط/أقساط) in Ad {ad_id}")
        return None, True, "INSTALLMENT_AD", {}

    if not any(w in official_loc_and_title for w in STRICT_NEW_CAIRO_HEADER):
        print(f"Skipped Non-New-Cairo Location in Ad {ad_id}")
        return None, True, "NOT_NEW_CAIRO", {}

    if not any(w in entire_ad_text for w in NEW_CAIRO_WORDS):
        return None, True, "NOT_NEW_CAIRO", {}

    all_price_text = f"{top_sec} {desc_clean} {clean_markdown_to_text(snippet)}"
    price_num = 0
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

    area = "مدرج بالإعلان"
    m_area = re.search(r"(?:المساحة|مساحة|المساحه)[^\d]{0,12}(\d{2,4})", top_sec + " " + desc_clean)
    if not m_area:
        m_area = re.search(r"\b(\d{2,4})\s*(?:متر|م2|م²|sqm)\b", top_sec + " " + desc_clean, re.I)
    if m_area:
        area = f"{m_area.group(1)} م²"

    beds = ""
    m_beds = re.search(r"(?:غرف نوم|غرف|غرفة)[^\d]{0,8}(\d{1,2})", top_sec + " " + desc_clean)
    if m_beds and 1 <= int(m_beds.group(1)) <= 12:
        beds = f"{m_beds.group(1)} غرف"

    baths = ""
    m_baths = re.search(r"(?:الحمامات|حمامات|حمام)[^\d]{0,8}(\d{1,2})", top_sec + " " + desc_clean)
    if m_baths and 1 <= int(m_baths.group(1)) <= 10:
        baths = f"{m_baths.group(1)} حمام"

    deal, category, subtype = classify_deal_category_subtype(url, title_clean, desc_clean, before_desc_clean, price_num)

    # ✅ الفئة الرسمية من breadcrumb دوبيزل بتتفوق على تخمين الكلمات المفتاحية.
    #    (النوع الفرعي subtype لسه من الكلمات — دوبيزل ما بتديّهوش في الـ breadcrumb)
    bc_title, bc_cat, bc_id = parse_breadcrumb(raw_s)
    if bc_cat:
        bc_deal, bc_category = map_breadcrumb_category(bc_cat, price_num)
        if bc_deal:
            deal = bc_deal
        if bc_category:
            category = bc_category
        if not title_clean and bc_title:
            title_clean = clean_markdown_to_text(bc_title)

    now_iso = datetime.now(CAIRO_TZ).isoformat()
    safe_desc = sanitize_desc_for_frontend(desc_clean[:680] if desc_clean else title_clean)

    return {
        "ad_id": ad_id,
        "source": "دوبيزل",
        "title": title_clean[:130] if title_clean else "وحدة بالقاهرة الجديدة",
        "price_num": price_num,
        "price_text": price_text,
        "area": area,
        "beds": beds,
        "baths": baths,
        "deal": deal,
        "category": category,
        "subtype": subtype,
        "seller_name": seller,
        "account_id": account_id,
        "seller_ads_count": cnt,
        "fresh_tier": tier,
        "description": f"[{age_label}] {safe_desc}",
        "url": url,
        "today_verified": True,
        "verified_v12": True,
        "scraped_at": now_iso
    }, True, f"ADDED_OWNER_{cnt}_ADS", related_today


def scrape_all():
    run_start = time.time()
    (existing_ads, checked_ids, banned_accounts, preserved_top_keys, nocnt_attempts,
     dropped_banned, dropped_unverified) = load_existing()
    now_dt = datetime.now(CAIRO_TZ)
    kept_ads = {int(a["ad_id"]): a for a in existing_ads if "ad_id" in a}

    req_sess = std_requests.Session()
    cffi_sess = cffi_requests.Session(impersonate="chrome120")

    candidates = fetch_live_dubizzle_categories(req_sess, cffi_sess)

    def as_quad(val):
        """يوحّد الشكل: (url, snip, tier, priority) — extract_related_fresh بترجّع 3 بس."""
        return (val[0], val[1], val[2], val[3] if len(val) > 3 else 1)

    dubizzle_existing_only = [a for a in existing_ads if a.get("source", "دوبيزل") == "دوبيزل"]
    for a in dubizzle_existing_only[:8]:
        try:
            raw_seed = fetch_ad_page(a["url"], cffi_sess, req_sess, timeout_sec=22, tries=2)
            for rid, rval in extract_related_fresh(raw_seed, exclude_ids=checked_ids).items():
                q = as_quad(rval)
                if rid not in candidates or q[3] < candidates[rid][3] or q[2] > candidates[rid][2]:
                    candidates[rid] = q
            time.sleep(0.5)
        except Exception:
            pass

    unchecked = [
        (uid, v[0], v[1], v[2], v[3] if len(v) > 3 else 1)
        for uid, v in candidates.items()
        if uid not in kept_ads and uid not in checked_ids
    ]
    # 🎯 الترتيب الجديد: الأولوية (مالك أولاً) ← ثم الحداثة ← ثم الأحدث ID.
    #    ❌ القديم كان (tier, ad_id) تنازلياً ⇒ الأحدث أولاً ⇒ وكل الأحدث سماسرة
    #       (القياس: 29 من 30 إعلان في الصفحة الأولى سماسرة)
    unchecked.sort(key=lambda x: (x[4], -x[3], -x[0]))

    queue = list(unchecked[:120])   # FIX: كان 50 — الاستكشاف بقى بيرجّع 300+ مرشح
    queued_ids = {x[0] for x in queue}

    print(f"Kept existing owners: {len(kept_ads)} | Fresh unchecked candidates: {len(queue)} | Banned accounts: {len(banned_accounts)}")

    stats = {}
    inspected = 0

    inspect_start = time.time()
    while queue and (time.time() - inspect_start) < INSPECTION_BUDGET_SECONDS \
            and (time.time() - run_start) < MAX_RUNTIME_SECONDS:
        uid, u, snip, tier, prio = queue.pop(0)
        if uid in kept_ads or uid in checked_ids:
            continue
        inspected += 1
        try:
            item, should_mark, reason, discovered_today = inspect_and_parse(
                req_sess, cffi_sess, uid, u, snip, banned_accounts, checked_ids, nocnt_attempts
            )
            stats[reason] = stats.get(reason, 0) + 1
            if should_mark:
                # FIX(H2): سجّل السبب والتوقيت مش مجرد ID
                mark_checked(checked_ids, uid, reason)
            if item:
                kept_ads[uid] = item
                print(
                    f"[{inspected}] ADDED: {uid} | {item['category']} ({item['subtype']}) | "
                    f"{item['price_text']} | {item['seller_name']} (Active Ads: {item['seller_ads_count']})"
                )
            added_new_to_q = False
            for rid, rval in discovered_today.items():
                ru, rsnip, rtier = rval[0], rval[1], rval[2]
                if rid not in kept_ads and rid not in checked_ids and rid not in queued_ids and len(queue) < 150:
                    # الإعلانات المكتشفة من صفحة إعلان مالك ⇒ أولوية عالية (جيرانه غالباً ملاك)
                    queue.append((rid, ru, rsnip, rtier, 1))
                    queued_ids.add(rid)
                    added_new_to_q = True
            if added_new_to_q:
                queue.sort(key=lambda x: (x[4], -x[3], -x[0]))
        except Exception as e:
            print(f"[{inspected}] Error {uid}: {e}")

        time.sleep(0.9)

    print(f"Total inspected this run: {inspected} | Queue remaining: {len(queue)} | Total banned accounts: {len(banned_accounts)}")
    print(f"Inspection Summary: {stats}")

    final_ads = list(kept_ads.values())
    final_ads.sort(key=lambda x: (x.get("fresh_tier", 2), x.get("ad_id", 0)), reverse=True)

    # ══ FIX(C10): scraper.py ماكانش بيكتب last_run_report خالص ══
    # كان بينقل التقرير القديم زي ما هو (preserved_top_keys)، والكاتب الوحيد كان
    # extra_radar.py — وبيجيب أرقام دوبيزل عن طريق **تحليل ملف لوج** مش من البيانات.
    # النتيجة: العداد اللي إنت شايفه في الصفحة (dubizzle_total) بيتجمّد تماماً لو
    # extra_radar مااشتغلش أو فشل أو اللوج ماوصلوش. ده سبب تاني لتجمّد «29».
    # دلوقتي كل سكريبر بيكتب أرقامه الحقيقية بنفسه، من البيانات مباشرة.
    prev_report = preserved_top_keys.get("last_run_report") or {}
    added_owners    = sum(v for k, v in stats.items() if k.startswith("ADDED_OWNER"))
    banned_brokers  = sum(v for k, v in stats.items() if k.startswith("BANNED"))
    excluded_or_old = sum(v for k, v in stats.items() if k in (
        "OLD_AD", "OLD_OR_UNKNOWN_DATE", "EXPIRED", "EXCLUDED_AREA", "NOT_NEW_CAIRO"))
    extra_inspected = int(prev_report.get("extra_inspected") or 0)
    extra_added     = int(prev_report.get("extra_new_owners") or 0)

    dub_total    = sum(1 for a in final_ads if a.get("source", "دوبيزل") == "دوبيزل")
    aqar_total   = sum(1 for a in final_ads if a.get("source") == "عقارماب")
    os_total     = sum(1 for a in final_ads if a.get("source") == "السوق المفتوح")
    sale_total   = sum(1 for a in final_ads if a.get("deal") == "بيع")
    rent_total   = sum(1 for a in final_ads if a.get("deal") == "إيجار")

    run_report = {
        "run_time": now_dt.strftime("%Y/%m/%d, %I:%M %p"),
        "total_saved_owners": len(final_ads),
        "dubizzle_total": dub_total,
        "aqarmap_total": aqar_total,
        "opensooq_total": os_total,
        "sale_total": sale_total,
        "rent_total": rent_total,
        "total_inspected_this_run": inspected + extra_inspected,
        "dubizzle_inspected": inspected,
        "extra_inspected": extra_inspected,
        "total_new_owners_this_run": added_owners + extra_added,
        "dubizzle_new_owners": added_owners,
        "extra_new_owners": extra_added,
        "total_brokers_banned_this_run": banned_brokers,
        "total_excluded_this_run": excluded_or_old,
        "total_blacklisted_accounts": len(banned_accounts),
        "total_checked_ads_memory": len(checked_ids),
    }
    print("==========================================")
    print(f"RUN REPORT SUMMARY: {json.dumps(run_report, ensure_ascii=False)}")
    print("==========================================")

    checked_list = sorted(checked_ids.keys())[-8000:]
    out = {
        "last_scrape": now_dt.strftime("%Y/%m/%d, %I:%M %p"),
        "total_ads": len(final_ads),
        # FIX(H2): الشكل الجديد (dict فيه السبب والتوقيت) — هو المرجع الأساسي
        "checked_ids_v11": {str(k): v for k, v in list(checked_ids.items())[-8000:]},
        # توافق رجعي: extra_radar.py و index.html لسه بيقروا القوائم دي
        "checked_ids_v7": checked_list[-5000:],
        "checked_ids_v10": checked_list[-5000:],
        "banned_accounts_v7": sorted(list(banned_accounts))[-2000:],
        # FIX(C6): عدّاد محاولات NO_CNT — بينجو بين الرنات
        "nocnt_attempts_v1": {k: v for k, v in list(nocnt_attempts.items())[-1500:]},
        "last_run_report": run_report,
        "ads": final_ads
    }
    for k, v in preserved_top_keys.items():
        out[k] = v
    # ✅ ضمان إضافي: التقرير الجديد ما يتكتبش فوقه أي حاجة محفوظة
    out["last_run_report"] = run_report

    with open("ads.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(final_ads)} verified fresh New Cairo owner ads.")


if __name__ == "__main__":
    scrape_all()
