import os, sys, re, json, time, random, stat, socket, base64, subprocess, urllib.parse, ctypes, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone, timedelta, date
import requests as std_requests
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

def disable_cmd_quickedit_and_sleep():
    if not sys.platform.startswith("win"): return
    try:
        os.system("chcp 65001 > nul")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        k32 = ctypes.windll.kernel32
        k32.SetThreadExecutionState(0x80000003)
        h, m = k32.GetStdHandle(-10), ctypes.c_uint32()
        if k32.GetConsoleMode(h, ctypes.byref(m)): k32.SetConsoleMode(h, (m.value & ~0x0040 & ~0x0020) | 0x0080)
    except Exception: pass

disable_cmd_quickedit_and_sleep()

CAIRO_TZ = timezone(timedelta(hours=2))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ads.json")
EXTRA_SEEN_FILE = os.path.join(BASE_DIR, "seen_extra_local.json")
AQ_LIVE_BACKUP_FILE = os.path.join(BASE_DIR, "aqarmap_live_ads.json")
EXTRA_LIVE_BACKUP_FILE = os.path.join(BASE_DIR, "extra_live_ads.json")
FB_MEMORY_FILE = os.path.join(BASE_DIR, "fb_memory.json")
FB_EXT_DIR = os.path.join(BASE_DIR, "fb_main_radar_ext")
TG_CONFIG_TOPIC = "gamal_vip_tg_9941_sec"
WARP_PROXY = "socks5h://127.0.0.1:40000"
FB_PORT = 5005
MIN_CASH_SALE_PRICE = 1200000
MAX_AGE_DAYS = 2
MAX_OWNER_ADS_AQ = 7
MAX_OWNER_ADS_FB = 8
AUTO_LOOP_MINUTES = 45
FB_PENDING_BATCH_COUNT = 0
HINDI_MAP = str.maketrans({"٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9", "٬": ",", "،": ",", "٫": "."})
BIDI_REGEX = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]')
SYNC_LOCK = threading.Lock()
ARABIC_MONTHS = {"يناير": 1, "فبراير": 2, "مارس": 3, "ابريل": 4, "أبريل": 4, "إبريل": 4, "مايو": 5, "يونيو": 6, "يونية": 6, "يوليو": 7, "يوليه": 7, "اغسطس": 8, "أغسطس": 8, "سبتمبر": 9, "اكتوبر": 10, "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12}

ZONES = [
    ("التجمع الخامس", "التجمع الخامس|fifth settlement|5th settlement|ميفيدا|mivida|هايد بارك|ماونتن فيو|كايرو فيستفال|كايرو فيستيفال|الباتيو|فيلت|سوديك|ستون ريزيدنس|ستون بارك|ايست تاون|ليك فيو|بالم هيلز التجمع|الحي الاول|الحي الثاني|الحي الثالث|الحي الرابع|الحي الخامس|غرب الجولف|الجامعه الامريكيه|الجامعة الامريكية|auc|فاطمه الشربتلي|فاطمة الشربتلي|مسجد الشرطه|مسجد الشرطة|بوينت 90|كونكورد".split("|")),
    ("التجمع الأول", "التجمع الأول|التجمع الاول|first settlement|1st settlement|مجاورة".split("|")),
    ("التجمع الثالث", "التجمع الثالث|third settlement|3rd settlement|أربيلا|اربيلا|أرابيلا|ارابيلا|غرب ارابيلا|الهايكستب|المحلية|المحليه|اسكان الشباب|إسكان الشباب".split("|")),
    ("اللوتس", ["اللوتس", "lotus"]), ("النرجس", ["النرجس", "narges", "narjis"]), ("الياسمين", ["الياسمين", "yasmeen", "jasmine"]), ("البنفسج", ["البنفسج", "banafseg"]),
    ("الأندلس", ["الأندلس", "الاندلس", "andalus"]), ("جنوب الأكاديمية", ["جنوب الأكاديمية", "جنوب الاكاديمية", "الأكاديمية", "الاكاديميه"]), ("شرق الأكاديمية", ["شرق الأكاديمية", "شرق الاكاديمية"]),
    ("المستثمرين", ["المستثمرين", "investors"]), ("الشويفات", ["الشويفات", "choueifat"]), ("القرنفل", ["القرنفل", "koronfel"]), ("التمر حنة", ["التمر حنة", "تمر حنة", "tamr hena"]),
    ("أبو الهول", ["أبو الهول", "ابو الهول", "جاردينيا هايتس", "جاردينيا"]), ("دار مصر", ["دار مصر", "سكن مصر", "جنة مصر", "جنه مصر", "فرجينيا"]), ("القطامية", ["القطامية", "القطاميه", "katameya"]), ("شارع التسعين", ["التسعين", "90th"]),
]
EXCLUDED_CITIES = "الرحاب|رحاب|rehab|مدينتي|مدينتى|madinaty|بيت الوطن|بيت وطن|beit al watan|beit el watan|bayt al watan|النورث هاوس|شمال الرحاب|العبور|الشروق|مدينة بدر|مدينه بدر|هليوبوليس الجديدة|العاصمة الإدارية|العاصمه الاداريه|التجمع السادس|sixth settlement|كابيتال جاردنز|capital gardens|سراي|sarai|البروج|alburouj|طلالة|talala|دي جويا|dejoya|محور الأمل|تاج سيتي|تاج سيتى|taj city|تاج سلطان|العاشر من رمضان|6 أكتوبر|أكتوبر|الشيخ زايد|زايد|المعادي|زهراء المعادي|المقطم|الهضبة الوسطى|مدينة نصر|مصر الجديدة|شيراتون|النزهة|عين شمس|السلام|جسر السويس|حدائق القبة|المرج|شبرا|حلوان|15 مايو|الزمالك|المهندسين|الدقي|العجوزة|الهرم|فيصل|حدائق الأهرام|حدائق الاهرام|حدائق أكتوبر|الساحل الشمالي|العين السخنة|الجونة|الغردقة|شرم الشيخ|الإسكندرية|الاسكندرية|المستقبل|mostakbal|سمات|مقبرة|مقابر|مدفن|مدافن".split("|")
INSTALLMENT_SUBSTRINGS = "قسط|تقسيط|بالتقسيط|لتقسيط|اقساط|أقساط|باقساط|بأقساط|تكملة أقساط|تكمله اقساط|مقدم|بمقدم|بقدم |دفعة|دفعه|دفعات|تسهيلات|سداد|فترة سداد|سنوات سداد|أنظمة سداد|انظمه سداد|بدون فوائد|متبقي|المتبقي|والباقي|أوفر|اوفر|امكانية التقسيط|متاح تقسيط|ويوجد تقسيط|سنة التسليم 2027|سنة التسليم 2028|سنة التسليم 2029|سنة التسليم 2030|قيد الإنشاء|قيد الانشاء|down payment|downpayment|installment|installments|payment plan".split("|")
SAFE_CASH_NEGATIONS = "بدون تقسيط|لا يوجد تقسيط|ممنوع التقسيط|وليس تقسيط|مش تقسيط|بدون أقساط|بدون اقساط|خالص الثمن|خالصة الثمن|خالصه الثمن|ليس عليها أقساط|ليس عليها اقساط|لا يوجد أقساط|لا يوجد اقساط|مسدد بالكامل|مسددة بالكامل|غير متاح تقسيط|البيع كاش فقط|كاش فقط|كاش نهائي".split("|")
SAFE_OWNER_BROKER_NEGATIONS = "بدون وسيط|بدون وسطاء|ممنوع الوسطاء|يمتنع الوسطاء|لغير الوسطاء|عدم تدخل الوسطاء|عدم التعامل مع الوسطاء|لا للوسطاء|بدون سمسار|بدون سماسرة|بدون سماسره|ممنوع السماسرة|ممنوع السماسره|يمتنع السماسرة|يمتنع السماسره|بدون بروكر|ممنوع البروكر|يمتنع البروكر|من غير سمسار|من غير وسيط|من المالك مباشره|من المالك مباشر|المالك مباشره|المالك مباشر|التواصل مباشر مع المالك|التعامل مباشر مع المالك|مباشر من المالك|انا المالك".split("|")
BROKER_NAME_WORDS = "zone|real estate|realestate|realty|property|properties|homes|agency|agencies|broker|brokers|brokerage|investment|investments|development|developments|consult|consultant|consulting|company|marketing|scouts|vertex|redefine|irtkaz|ebtkar|imkan|falcon|realtors|trusted home|remax|coldwell|era|prime|capital|house|group|شركة|شركه|مكتب|تسويق|للتسويق|ماركتنج|سمسار|وسيط|استشاري|مستشار|للاستشارات|تطوير|للتطوير|للاستثمار|هومز|بروكر|ريال استيت|استيت|فيرتكس|ريديفاين|ارتكاز|إرتكاز|ابتكار|إبتكار|دار البناء|للمقاولات|للإنشاءات|للانشاءات|اللوتس العقارية|البيت المصري|ادارة املاك|إدارة أملاك|عقاري|عقارات|للعقارات|العقاريه".split("|")
BROKER_TEXT_PHRASES = "انا وسيط|أنا وسيط|وسيط مش المالك|مش المالك|ليس المالك|وسيط عقاري|وسيط عقارى|وسيط من المالك|وسيط مع المالك|مباشر مع المالك|مباشر من المالك لدينا|انا بروكر|م بروكر|للتواصل مع البروكر|سمسار|سماسرة|سماسره|بروكر|broker|مكتب عقاري|مكتب عقارات|مكتب تسويق|ادارة املاك|عمولة شهر|عموله شهر|عمولة نصف شهر|عموله نصف شهر|عمولة المكتب|عموله المكتب|عمولة الشركة|عموله الشركه|بعموله|بعمولة|نسبة العمولة|يوجد عمولة|يوجد عموله|عمولة 1|عموله 1|عمولة 2|عموله 2|لماذا تختار شركتنا|شركتنا|شركة عقارات|شركه عقارات|شركة تسويق|شركه تسويق|للتسويق العقاري|للاستثمار العقاري|للتطوير العقاري|استشاري عقاري|مستشار عقاري|فريق المبيعات|قسم المبيعات|للتواصل مع قسم المبيعات|فريق من الخبراء|مجموعة متنوعة من الشقق|تقع عقاراتنا|زيارة معروضاتنا|سجل بياناتك|عائد إيجاري شهري مضمون|عائد ايجاري شهري مضمون|بعائد ايجاري يصل|كود الوحدة|كود الوحده|كود العقار|كود الشقة|كود الفيلا|الكود المرجعي|متاح لدينا|يتوفر لدينا|متوفر لدينا|لدينا أكثر من|متاح لدينا اكثر من|لدينا عقارات|متاح عروض اخري|متاح عروض أخرى|يوجد عروض اخري|متاح شقق اخري|متاح مساحات مختلفة|مساحات مختلفة|مساحات مختلفه|متوفر لدينا وحدات|متاح لدينا وحدات|باقل سعر بالمشروع|استمرار لعروضنا|والواقع يتحدث عنا|امتلك وحدتك|احجز وحدتك|اختار وحدتك|مطلوب وموجود|مطلوب ومعروض|متاح وحدات اخري|تواصل خاص|السعر خاص|التفاصيل خاص|انبوكس|inbox|للاستفسار والمعاينه|للتفاصيل والمعاينه|متاح شقق|متاح فلل|متاح وحدات|فرصه استثماريه|تحت سعر السوق|اقل من سعر السوق|باقل مقدم|نصف تشطيب|ضمن الاعضاء|اصدقاء ضمن الاعضاء|مجموعه عامه|مجموعه خاصه|سعر المتر|ريسبشن 3 قطع|بحري صريح|دبل فيس|لقطه|فرصه لن تتكرر".split("|")
FB_WANTED_PHRASES = "مطلوب شقه|مطلوب شقة|مطلوب فيلا|مطلوب للايجار|مطلوب للإيجار|مطلوب للشراء|مطلوب للبيع|مطلوب من المالك|بدور علي شقه|بدور على شقة|بدور علي فيلا|محتاج شقه|محتاج شقة|محتاجه شقه|محتاجة شقة|عايز شقه|عايز شقة|عايزة شقة|عايزه شقه|ابحث عن شقه|أبحث عن شقة|حد عنده شقه|حد عنده شقة|مطلوب عاجل|مطلوب فورا|مطلوب شريك|مطلوب شريكة|مطلوب روم ميت".split("|")

_AQ_B, _AQ_S = "https://aqarmap.com.eg/ar/", "?sort=publishedAt&direction=desc"
AQARMAP_SOURCES = [{"cat": c, "deal": d, "en": e, "max_p": m, "url": (_AQ_B + p + _AQ_S).replace("?&sort=", "?payment_method=1&sort=")} for c, d, e, m, p in [
    ("شقق", "إيجار", "Apartments (Rent)", 5, "for-rent/apartment/cairo/new-cairo/"), ("شقق", "إيجار", "Furnished Apts (Rent)", 4, "for-rent/furnished-apartment/cairo/new-cairo/"),
    ("فلل", "إيجار", "Villas (Rent)", 3, "for-rent/villa/cairo/new-cairo/"), ("تجاري", "إيجار", "Commercial (Rent)", 3, "for-rent/commercial/cairo/new-cairo/"),
    ("تجاري", "إيجار", "Administrative (Rent)", 3, "for-rent/administrative/cairo/new-cairo/"), ("تجاري", "إيجار", "Medical (Rent)", 2, "for-rent/medical/cairo/new-cairo/"),
    ("أراضي", "إيجار", "Buildings (Rent)", 2, "for-rent/building/cairo/new-cairo/"), ("أراضي", "إيجار", "Lands (Rent)", 2, "for-rent/land/cairo/new-cairo/"),
    ("شقق", "تمليك", "Apartments (Cash Sale)", 5, "for-sale/apartment/cairo/new-cairo/?payment_method=1&"), ("شقق", "تمليك", "Apartments (All Sale)", 4, "for-sale/apartment/cairo/new-cairo/"),
    ("فلل", "تمليك", "Villas (Cash Sale)", 3, "for-sale/villa/cairo/new-cairo/?payment_method=1&"), ("فلل", "تمليك", "Villas (All Sale)", 3, "for-sale/villa/cairo/new-cairo/"),
    ("تجاري", "تمليك", "Commercial (Sale)", 3, "for-sale/commercial/cairo/new-cairo/"), ("تجاري", "تمليك", "Administrative (Sale)", 3, "for-sale/administrative/cairo/new-cairo/"),
    ("تجاري", "تمليك", "Medical (Sale)", 2, "for-sale/medical/cairo/new-cairo/"), ("أراضي", "تمليك", "Lands (Sale)", 3, "for-sale/land/cairo/new-cairo/"),
    ("أراضي", "تمليك", "Buildings (Sale)", 2, "for-sale/building/cairo/new-cairo/")
]]

def strip_bidi(text): return BIDI_REGEX.sub("", str(text)).translate(HINDI_MAP) if text else ""
def normalize_ar(text):
    t = re.sub(r'[\u0640\u064B-\u065F]', '', strip_bidi(text).lower())
    return re.sub(r'\s+', ' ', re.sub(r'ى', 'ي', re.sub(r'ة', 'ه', re.sub(r'[إأآا]', 'ا', t)))).strip()

def clear_git_locks():
    git_dir = os.path.join(BASE_DIR, ".git")
    for rel in ["index.lock", "HEAD.lock", "config.lock", os.path.join("refs", "heads", "main.lock")]:
        p = os.path.join(git_dir, rel)
        if os.path.exists(p):
            try: os.remove(p)
            except Exception: pass
    if os.path.exists(os.path.join(git_dir, "rebase-merge")) or os.path.exists(os.path.join(git_dir, "rebase-apply")):
        subprocess.run(["git", "rebase", "--abort"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(os.path.join(git_dir, "MERGE_HEAD")):
        subprocess.run(["git", "merge", "--abort"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def fix_git_identity_for_vercel():
    clear_git_locks()
    subprocess.run(["git", "config", "user.name", "gamallove217-glitch"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "gamallove217@gmail.com"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def is_direct_fb_post_permalink(url_str):
    u = str(url_str or "").strip()
    if "facebook.com" not in u or "/search/" in u: return False
    return bool(re.search(r'(?:/share/[pv]/[A-Za-z0-9]+|/posts/(?:\d+|pfbid[A-Za-z0-9]+)|/permalink/\d+|story_fbid=(?:\d+|pfbid[A-Za-z0-9]+)|multi_permalinks=\d+|/photo/?\?fbid=\d+)', u))

def generate_facebook_main_extension():
    os.makedirs(FB_EXT_DIR, exist_ok=True)
    manifest = {
        "manifest_version": 3, "name": "Gamal Home Feed & Profile Owner Radar v13.0", "version": "13.0",
        "description": "Home Feed 45m/30m + Share Copy Link + Author Profile 1-8 Ads Inspector + End-of-Run Batch",
        "permissions": ["storage", "tabs", "clipboardRead", "clipboardWrite"],
        "host_permissions": ["https://www.facebook.com/*", "http://127.0.0.1:5005/*"],
        "background": {"service_worker": "background.js"},
        "content_scripts": [
            {"matches": ["https://www.facebook.com/*"], "js": ["main_world_hook.js"], "run_at": "document_start", "world": "MAIN"},
            {"matches": ["https://www.facebook.com/*"], "js": ["content.js"], "run_at": "document_idle"}
        ]
    }
    background_js = r"""
const pendingProfiles = new Map();
chrome.runtime.onMessage.addListener((m, sender, sr) => {
    if (m && m.type === "FB_POST_INGEST") {
        fetch("http://127.0.0.1:5005/fb_ingest", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(m.payload)})
        .then(r => r.json()).then(d => sr({ok: true, accepted: !!(d && d.accepted), reason: (d && d.reason) || ""}))
        .catch(e => sr({ok: false, accepted: false, reason: String(e)}));
        return true;
    }
    if (m && m.type === "FB_FLUSH_BATCH") {
        fetch("http://127.0.0.1:5005/fb_flush", {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"})
        .then(r => r.json()).then(d => sr({ok: true})).catch(e => sr({ok: false}));
        return true;
    }
    if (m && m.type === "FB_CHECK_PROFILE") {
        const sep = m.url.includes("?") ? "&" : "?";
        chrome.tabs.create({url: m.url + sep + "g_prof_check=1", active: false}, tab => {
            if (!tab || !tab.id) { sr({ok: false, count: 1, isBroker: false}); return; }
            const tid = tab.id;
            const timer = setTimeout(() => {
                if (pendingProfiles.has(tid)) {
                    pendingProfiles.delete(tid);
                    try { chrome.tabs.remove(tid); } catch(e) {}
                    sr({ok: true, count: 1, isBroker: false, reason: "timeout_pass"});
                }
            }, 6000);
            pendingProfiles.set(tid, {sr, timer});
        });
        return true;
    }
    if (m && m.type === "FB_PROFILE_RESULT" && sender && sender.tab && sender.tab.id) {
        const tid = sender.tab.id, entry = pendingProfiles.get(tid);
        if (entry) {
            clearTimeout(entry.timer); pendingProfiles.delete(tid);
            try { chrome.tabs.remove(tid); } catch(e) {}
            entry.sr({ok: true, count: m.count || 1, isBroker: !!m.isBroker, reason: m.reason || ""});
        }
        return false;
    }
});
""".strip()

    main_world_hook_js = r"""
(function(){
if(window.__gamalMainHookV130)return;
window.__gamalMainHookV130=true;
const D_RE=/https?:\/\/(?:www\.|m\.)?facebook\.com\/(?:share\/[pv]\/[A-Za-z0-9._\-]+|groups\/[^\/?#]+\/(?:posts|permalink)\/(?:\d+|pfbid[A-Za-z0-9]+)|permalink\.php\?story_fbid=[^&"'\s]+|story\.php\?story_fbid=[^&"'\s]+|[^\/?#]+\/posts\/(?:\d+|pfbid[A-Za-z0-9]+)|photo\/?\?fbid=\d+[^"'\s]*)/i;
try{
if(navigator.clipboard&&navigator.clipboard.writeText){
const origWT=navigator.clipboard.writeText.bind(navigator.clipboard);
navigator.clipboard.writeText=async function(txt){
const s=String(txt||"").trim();
if(s.includes("facebook.com/"))document.documentElement.setAttribute("data-g-copied-url",s);
return origWT(txt);
};
}
}catch(e){}
const rMap=new Map(),nKey=s=>String(s||"").replace(/\s+/g," ").trim().substring(0,45);
function idxTree(root){
if(!root||typeof root!=="object")return;
const vis=new WeakSet(),nowS=Math.floor(Date.now()/1000);
function walk(n,d,c){
if(!n||typeof n!=="object"||d>18||vis.has(n))return;
vis.add(n);
let cx=(n.comet_sections||n.post_id||(n.message&&typeof n.message.text==="string"))?Object.assign({},c):c;
if(typeof n.post_id==="string"&&/^\d{10,25}$/.test(n.post_id))cx.postId=n.post_id;
if(typeof n.wwwURL==="string"&&D_RE.test(n.wwwURL))cx.url=n.wwwURL;
if(typeof n.url==="string"&&D_RE.test(n.url))cx.url=n.url;
if(typeof n.creation_time==="number"&&n.creation_time>=1600000000&&n.creation_time<=nowS+600)cx.ctime=n.creation_time;
if(Array.isArray(n.actors)&&n.actors[0]&&typeof n.actors[0].name==="string")cx.author=n.actors[0].name;
if(n.message&&typeof n.message.text==="string"&&n.message.text.length>=22)cx.text=n.message.text;
let ks;try{ks=Object.keys(n);}catch(e){return;}
for(let i=0;i<Math.min(ks.length,55);i++){
const k=ks[i];if(k==="children"||k==="stateNode"||k==="return"||k==="sibling"||k==="child")continue;
let v;try{v=n[k];}catch(e){continue;}
if(v&&typeof v==="object")walk(v,d+1,cx);
}
if(cx.text&&(cx.url||cx.postId)){
let u=cx.url||("https://www.facebook.com/permalink.php?story_fbid="+cx.postId);
rMap.set(nKey(cx.text),{url:u,ctime:cx.ctime||0,author:cx.author||"",text:cx.text});
}
}
try{walk(root,0,{});}catch(e){}
}
function scanJson(){
document.querySelectorAll('script[type="application/json"]').forEach(sc=>{
if(sc._gS)return;sc._gS=true;
try{const t=sc.textContent||"";if(t.includes("creation_time")||t.includes("post_id"))idxTree(JSON.parse(t));}catch(e){}
});
}
const oO=XMLHttpRequest.prototype.open,oS=XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open=function(m,u){this._gU=String(u||"");return oO.apply(this,arguments);};
XMLHttpRequest.prototype.send=function(){
this.addEventListener("load",function(){
try{if(this._gU&&this._gU.includes("graphql")&&this.responseText){
this.responseText.split("\n").forEach(ln=>{if(ln.includes("creation_time")||ln.includes("post_id"))try{idxTree(JSON.parse(ln));}catch(e){}});
}}catch(e){}
});
return oS.apply(this,arguments);
};
function extFiber(domEl){
let fU="",fP="",fG="",fC=0,fM="",fA="";
const nowS=Math.floor(Date.now()/1000),vis=new WeakSet();
function scan(o,d){
if(!o||typeof o!=="object"||d>6||vis.has(o))return;
vis.add(o);
if(!fM&&o.message&&typeof o.message.text==="string"&&o.message.text.length>=22)fM=o.message.text;
if(!fA&&Array.isArray(o.actors)&&o.actors[0]&&typeof o.actors[0].name==="string")fA=o.actors[0].name;
let ks;try{ks=Object.keys(o);}catch(e){return;}
for(let i=0;i<Math.min(ks.length,48);i++){
const k=ks[i];if(k==="children"||k==="stateNode"||k==="return"||k==="sibling"||k==="child")continue;
let v;try{v=o[k];}catch(e){continue;}
if(v==null)continue;
if(typeof v==="string"){
if(!fU&&(v.includes("/posts/")||v.includes("/permalink")||v.includes("story_fbid="))){
const mU=v.match(D_RE);if(mU)fU=mU[0].replace(/\\u0025/g,"%").replace(/\\\//g,"/");
else if(v.startsWith("/groups/")&&(v.includes("/posts/")||v.includes("/permalink/")))fU="https://www.facebook.com"+v.split("?")[0];
}
if(!fP&&(k==="post_id"||k==="story_fbid"||k==="top_level_post_id"||k==="mf_story_key"||k==="legacy_fbid")&&(/^\d{10,25}$/.test(v)||/^pfbid[A-Za-z0-9]{15,}$/.test(v)))fP=v;
if(!fP&&k==="id"&&v.length>=16&&v.length<=120&&/^[A-Za-z0-9+/=]+$/.test(v)){try{const mD=atob(v).match(/(?::|_)(\d{11,22})$/);if(mD)fP=mD[1];}catch(e){}}
if(!fG&&(k==="group_id"||k==="groupID")&&/^\d{8,25}$/.test(v))fG=v;
}else if(typeof v==="number"){
if(!fC&&(k==="creation_time"||k==="publish_time"||k==="created_time"||k==="utime"||k==="timestamp")){
if(v>=1600000000&&v<=nowS+600)fC=Math.floor(v);
else if(v>=1600000000000&&v<=(nowS+600)*1000)fC=Math.floor(v/1000);
}
}else if(typeof v==="object")scan(v,d+1);
}
}
const nds=[domEl];
domEl.querySelectorAll('div[data-ad-preview="message"],div[data-ad-comet-preview="message"],div[data-ad-rendering-role="story_message"],a[href],span[role="link"],h2,h3,h4').forEach(n=>nds.push(n));
for(const el of nds){
if(!fG&&el.href){
const mG=el.href.match(/facebook\.com\/groups\/([^/?&#]+)/);if(mG&&mG[1]!=="feed"&&mG[1]!=="discover")fG=mG[1];
const mGm=el.href.match(/set=(?:gm|pcb)\.(\d{10,25})/);if(mGm&&!fP)fP=mGm[1];
}
let fK=null;try{fK=Object.keys(el).find(k=>k.startsWith("__reactFiber$")||k.startsWith("__reactProps$"));}catch(e){}
if(!fK)continue;
let cur=el[fK];
for(let s=0;s<28&&cur;s++){
if(cur.memoizedProps)scan(cur.memoizedProps,0);
if(!fU&&cur.pendingProps)scan(cur.pendingProps,0);
if(fU&&fC&&fM)break;
cur=cur.return;
}
}
if(!fU&&fG&&fP)fU="https://www.facebook.com/groups/"+fG+"/permalink/"+fP+"/";
else if(!fU&&fP)fU="https://www.facebook.com/permalink.php?story_fbid="+fP;
return{url:fU,ctime:fC,pureMsg:fM,author:fA};
}
function stamp(){
scanJson();
document.querySelectorAll("[data-g-inspect-req='1']").forEach(card=>{
card.removeAttribute("data-g-inspect-req");
try{
const res=extFiber(card),mEl=card.querySelector('div[data-ad-preview="message"],div[data-ad-comet-preview="message"],div[data-ad-rendering-role="story_message"]');
const cTxt=res.pureMsg||(mEl?mEl.innerText:""),mp=cTxt?rMap.get(nKey(cTxt)):null;
const fU=res.url||(mp&&mp.url)||"",fC=res.ctime||(mp&&mp.ctime)||0,fM=res.pureMsg||(mp&&mp.text)||"",fA=res.author||(mp&&mp.author)||"";
if(fU)card.setAttribute("data-g-permalink",fU);
if(fC)card.setAttribute("data-g-ctime",String(fC));
if(fM)card.setAttribute("data-g-puremsg",fM);
if(fA)card.setAttribute("data-g-author",fA);
}catch(e){}
});
}
window.addEventListener("gamal_fiber_scan",stamp);
setInterval(stamp,400);
})();
""".strip()

    content_js = r"""
(function(){
if(window.__gamalFbRadarV130)return;
window.__gamalFbRadarV130=true;
if(location.search.includes("g_prof_check=1")){
setTimeout(async()=>{
try{
window.scrollBy(0,1100);await new Promise(r=>setTimeout(r,800));
window.scrollBy(0,1100);await new Promise(r=>setTimeout(r,600));
const bodyTxt=(document.body.innerText||"");
const BRK_BIO=/(real\s*estate|property\s*consultant|broker|remax|coldwell|تسويق\s*عقاري|مستشار\s*عقاري|شركة\s*عقارات|مكتب\s*عقارات|سمسار|بروكر|للاستثمار\s*العقاري)/i;
const isBioBrk=BRK_BIO.test(bodyTxt.substring(0,1600));
const msgNodes=document.querySelectorAll('div[data-ad-preview="message"],div[data-ad-comet-preview="message"],div[data-ad-rendering-role="story_message"]');
const articles=document.querySelectorAll('div[role="article"]');
const cnt=Math.max(msgNodes.length,articles.length,1);
const zList=["النرجس","اللوتس","الياسمين","البنفسج","الاندلس","الأندلس","القرنفل","المستثمرين","دار مصر","سكن مصر","الشويفات","القطامية"];
let zHits=0;for(const z of zList){if(bodyTxt.includes(z))zHits++;}
const isBrk=isBioBrk||cnt>8||zHits>=3;
const rsn=isBioBrk?"بروفايل شركة/سمسار":(cnt>8?("ناشر "+cnt+" إعلان (>8)"):(zHits>=3?"ينشر في عدة مناطق (سمسار)":"مالك موثق ("+cnt+" إعلان)"));
chrome.runtime.sendMessage({type:"FB_PROFILE_RESULT",count:cnt,isBroker:isBrk,reason:rsn});
}catch(e){chrome.runtime.sendMessage({type:"FB_PROFILE_RESULT",count:1,isBroker:false,reason:"ok"});}
},1200);
return;
}
const FEEDS=[
{name:"الرئيسية (الأحدث أولاً بأول)",url:"https://www.facebook.com/?sk=h_chr"},
{name:"خلاصة أحدث منشورات جروباتك",url:"https://www.facebook.com/groups/feed/"}
];
const RUN_MS=45*60*1000,REST_SEC=30*60,SWITCH_MS=11*60*1000;
const PROP_RE=/(شقه|شقة|فيلا|دوبلكس|بنتهاوس|ستوديو|استوديو|رووف|روف|محل|مكتب|عياده|عيادة|ارضي|أرضي|بجاردن|للايجار|للإيجار|للبيع|تمليك|ايجار|إيجار|مفروش|غرف|ثلاث غرف|غرفتين|ريسبشن)/i;
const OWNER_FAST_RE=/(من\s*المالك|المالك\s*مباشر|انا\s*المالك|أنا\s*المالك|شقتي|فيلتي|بيتي|ملكي|بدون\s*وسيط|بدون\s*وسطاء|ممنوع\s*الوسطاء|يمتنع\s*الوسطاء|لا\s*للوسطاء|بدون\s*سمسار|بدون\s*سماسرة|بدون\s*سماسره|ممنوع\s*السماسره|بدون\s*بروكر)/i;
const G_NOISE=/(ضمن الأعضاء|أصدقاء ضمن الأعضاء|مجموعة عامة|مجموعة خاصة|منشورًا في اليوم|منشورات في اليوم|انضمام إلى المجموعة)/i;
const G_WORDS=/(جروب|مجموعه|مجموعة|عقارات|شقق|سكان|اهالي|أهالي|بيع وشراء|ايجار وتمليك|إيجار وتمليك|سوق|ملتقى|رابطه|رابطة)/i;
const H_MAP={"٠":"0","١":"1","٢":"2","٣":"3","٤":"4","٥":"5","٦":"6","٧":"7","٨":"8","٩":"9"};
const normD=s=>String(s||"").replace(/[٠-٩]/g,c=>H_MAP[c]||c);
const TIME_RE=/(الآن|توًا|حالا|just now|(?:^|\s)\d{1,2}\s*[دسيهأ](?:\s|$)|دقيقة|دقيقتين|دقائق|ساعة|ساعتين|ساعات|أمس|امس|الأمس|يوم|يومين|أيام|ايام|أسبوع|اسبوع|شهر|(?:^|\s)\d{1,2}\s*(?:m|h|d|w|mins?|hrs?)(?:\s|$)|يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يوليو|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر)/i;

let sentHashes=JSON.parse(localStorage.getItem("gamal_fb_sent_v130")||"[]");
let profCache=JSON.parse(localStorage.getItem("gamal_fb_pcache_v130")||"{}");
let feedIdx=parseInt(localStorage.getItem("gamal_fb_fidx_v130")||"0",10)%FEEDS.length;
let runStartTs=parseInt(sessionStorage.getItem("gamal_fb_run_ts_v130")||String(Date.now()),10);
sessionStorage.setItem("gamal_fb_run_ts_v130",String(runStartTs));
let scannedCount=parseInt(sessionStorage.getItem("gamal_fb_sc_v130")||"0",10);
let acceptedCount=parseInt(sessionStorage.getItem("gamal_fb_ac_v130")||"0",10);
let pageLoadTs=Date.now(),consecutiveSeen=0,isResting=false;
let lastLogMsg="يخزن الملاك الموثقين ويرفعهم دفعة واحدة آخر الرن...";
let shadowInfo=null;
try{
const host=document.createElement("span"),sh=host.attachShadow({mode:"closed"}),box=document.createElement("div");
box.style.cssText="position:fixed;bottom:10px;left:10px;z-index:2147483647;background:#0f172a;color:#e2e8f0;padding:10px 14px;border-radius:10px;font-family:Tahoma,sans-serif;font-size:12px;border:1px solid #10b981;box-shadow:0 4px 16px rgba(0,0,0,0.65);direction:rtl;max-width:460px;line-height:1.6;";
sh.appendChild(box);document.documentElement.appendChild(host);shadowInfo=box;
}catch(e){}

function updateUI(st){
try{
sessionStorage.setItem("gamal_fb_sc_v130",String(scannedCount));
sessionStorage.setItem("gamal_fb_ac_v130",String(acceptedCount));
const remMin=Math.max(0,Math.ceil((RUN_MS-(Date.now()-runStartTs))/60000));
document.title="[فحص:"+scannedCount+" | مخزن:"+acceptedCount+"] "+st;
if(shadowInfo){
const curN=FEEDS[feedIdx]?FEEDS[feedIdx].name:"الصفحة الرئيسية";
shadowInfo.innerHTML="<div><b>رادار الصفحة الرئيسية وفحص البروفايل v13.0</b> | "+st+"</div><div style='color:#38bdf8;'>الوضع: <b>"+curN+"</b> (باقي لنهاية الرن والرفع: "+remMin+" د)</div><div>تم فحص: <b>"+scannedCount+"</b> | ملاك مخزنون للرفع (1-8 إعلانات): <b style='color:#4ade80;'>"+acceptedCount+"</b></div><div style='color:#cbd5e1;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"+lastLogMsg+"</div>";
}
}catch(e){}
}
function saveHash(h){if(!sentHashes.includes(h)){sentHashes.push(h);if(sentHashes.length>3500)sentHashes=sentHashes.slice(-3500);localStorage.setItem("gamal_fb_sent_v130",JSON.stringify(sentHashes));}}
function hashStr(s){let h=0;for(let i=0;i<s.length;i++)h=((h<<5)-h)+s.charCodeAt(i)|0;return"fb_"+Math.abs(h);}

function collectCards(){
const cSet=new Set();
document.querySelectorAll('div[data-ad-preview="message"],div[data-ad-comet-preview="message"],div[data-ad-rendering-role="story_message"]').forEach(node=>{
const txt=(node.innerText||"").trim();
if(txt.length<25||!PROP_RE.test(txt)||G_NOISE.test(txt))return;
let cur=node,best=null;
for(let i=0;i<11;i++){
if(!cur.parentElement)break;
cur=cur.parentElement;
const cT=(cur.innerText||"");if(cT.length>4500)break;
const lC=cur.querySelectorAll("a[href]").length;
const hasH=!!cur.querySelector('h2,h3,h4,a[href*="/posts/"],a[href*="/permalink/"],a[href*="story_fbid"],a[href*="/groups/"],a[href*="/user/"]');
if(cT.length>=65&&lC>=2&&hasH){best=cur;break;}
if(!best&&cT.length>=65&&lC>=2)best=cur;
}
if(best)cSet.add(best);
});
return Array.from(cSet);
}

async function clickShareAndCopyLink(card){
try{
document.documentElement.removeAttribute("data-g-copied-url");
const btns=card.querySelectorAll('div[role="button"],span[role="button"],div[aria-label]');
let shareBtn=null;
for(const b of btns){
const lbl=((b.innerText||"")+" "+(b.getAttribute("aria-label")||"")).trim();
if(/^(مشاركة|Share)$/i.test(lbl)||lbl.includes("مشاركة")){shareBtn=b;break;}
}
if(!shareBtn)return"";
shareBtn.click();
await new Promise(r=>setTimeout(r,360));
const menuItems=document.querySelectorAll('div[role="menuitem"],div[role="button"],span');
for(const mi of menuItems){
const mt=(mi.innerText||"").trim();
if(mt==="نسخ الرابط"||mt==="Copy link"){mi.click();await new Promise(r=>setTimeout(r,200));break;}
}
const copied=document.documentElement.getAttribute("data-g-copied-url")||"";
if(copied&&copied.includes("facebook.com/"))return copied;
}catch(e){}
return"";
}

function checkAuthorProfileInBg(profileUrl){
return new Promise(resolve=>{
if(!profileUrl){resolve({ok:true,count:1,isBroker:false,reason:"بدون رابط بروفايل"});return;}
const pKey=profileUrl.split("?")[0];
if(profCache[pKey]){resolve(profCache[pKey]);return;}
try{
chrome.runtime.sendMessage({type:"FB_CHECK_PROFILE",url:pKey},resp=>{
const res=resp||{ok:true,count:1,isBroker:false,reason:""};
profCache[pKey]=res;
localStorage.setItem("gamal_fb_pcache_v130",JSON.stringify(profCache));
resolve(res);
});
}catch(e){resolve({ok:true,count:1,isBroker:false,reason:""});}
});
}

async function inspectCandidateCard(card){
const msgNode=card.querySelector('div[data-ad-preview="message"],div[data-ad-comet-preview="message"],div[data-ad-rendering-role="story_message"]');
if(!msgNode)return null;
const btns=card.querySelectorAll('div[role="button"],span[role="button"]');
for(const b of btns){
const bt=(b.innerText||"").trim();
if((bt==="عرض المزيد"||bt==="See more"||bt==="… عرض المزيد")&&!b.closest("ul")&&!b.closest("form")){
try{b.click();await new Promise(r=>setTimeout(r,150));}catch(e){}
break;
}
}
card.setAttribute("data-g-inspect-req","1");
window.dispatchEvent(new CustomEvent("gamal_fiber_scan"));
await new Promise(r=>setTimeout(r,70));
let bodyText=(card.getAttribute("data-g-puremsg")||msgNode.innerText||"").trim();
if(bodyText.length<25||!PROP_RE.test(bodyText)||G_NOISE.test(bodyText))return null;

const keyHash=hashStr(bodyText.replace(/\s+/g," ").substring(0,90));
if(sentHashes.includes(keyHash)){
if(!card._gS){card._gS=true;consecutiveSeen++;}
return null;
}
if(!OWNER_FAST_RE.test(bodyText)){
card._gS=true;saveHash(keyHash);scannedCount++;
lastLogMsg="تخطي سريع: "+bodyText.replace(/\s+/g," ").substring(0,38);
updateUI("فحص سريع للرئيسية");
return null;
}
card.querySelectorAll("a,span[role='link']").forEach(a=>{
try{
a.dispatchEvent(new PointerEvent("pointerover",{bubbles:true}));
a.dispatchEvent(new MouseEvent("mouseover",{bubbles:true}));
if(a.focus)a.focus({preventScroll:true});
}catch(e){}
});
await new Promise(r=>setTimeout(r,80));
card.setAttribute("data-g-inspect-req","1");
window.dispatchEvent(new CustomEvent("gamal_fiber_scan"));
await new Promise(r=>setTimeout(r,50));

let postUrl=card.getAttribute("data-g-permalink")||"",fiberCtime=parseInt(card.getAttribute("data-g-ctime")||"0",10)||0;
let fiberAuthor=(card.getAttribute("data-g-author")||"").trim(),groupId="",mediaPostId="",photoUrl="",groupName="",headerTimeHint="",authorFromLink="",authorProfileUrl="";

card.querySelectorAll("a[href],abbr,span[aria-label]").forEach(a=>{
if(msgNode.contains(a))return;
const href=a.href||"",rawL=(a.innerText||"")+" "+(a.getAttribute("aria-label")||"");
const aTxt=normD(rawL).trim(),fLine=(a.innerText||"").split("\n")[0].trim();
if(G_NOISE.test(fLine))return;
const mG=href.match(/facebook\.com\/groups\/([^/?&#]+)/);if(mG&&mG[1]!=="feed"&&mG[1]!=="discover"&&!groupId)groupId=mG[1];
const mGm=href.match(/set=(?:gm|pcb)\.(\d{8,25})/);if(mGm&&!mediaPostId)mediaPostId=mGm[1];
const mId=href.match(/idorvanity=([^&]+)/);if(mId&&!groupId)groupId=mId[1];

if(href&&href.includes("/groups/")&&href.includes("/user/")){
if(!authorProfileUrl)authorProfileUrl=href.split("?")[0];
if(fLine.length>=2&&fLine.length<=42&&!G_WORDS.test(fLine)&&!authorFromLink)authorFromLink=fLine;
}else if(href&&href.includes("/groups/")&&!href.includes("/user/")&&!href.includes("/posts/")&&!href.includes("/permalink/")&&!href.includes("story_fbid=")){
if(fLine.length>=3&&fLine.length<=85&&!groupName)groupName=fLine;
}else if(href&&(href.includes("/user/")||href.includes("profile.php")||(!href.includes("/groups/")&&!href.includes("/posts/")&&!href.includes("/hashtag/")&&!href.includes("/photo")))){
if(fLine.length>=2&&fLine.length<=42&&!G_WORDS.test(fLine)&&fLine!==groupName){
if(!authorFromLink)authorFromLink=fLine;
if(!authorProfileUrl)authorProfileUrl=href.split("?")[0];
}
}
if(href&&!postUrl&&(href.includes("/posts/")||href.includes("/permalink/")||href.includes("story_fbid=")||href.includes("multi_permalinks="))){
postUrl=(href.includes("story_fbid=")||href.includes("multi_permalinks="))?href:href.split("?")[0];
}
if(href&&!photoUrl&&(href.includes("/photo/?")||href.includes("/photo.php?")))photoUrl=href;
if(!headerTimeHint&&aTxt&&aTxt.length<=42&&TIME_RE.test(aTxt))headerTimeHint=aTxt;
});

if(!postUrl){
updateUI("ينسخ رابط البوست من زر مشاركة...");
const copiedLink=await clickShareAndCopyLink(card);
if(copiedLink)postUrl=copiedLink;
}
if(!postUrl&&groupId&&mediaPostId)postUrl="https://www.facebook.com/groups/"+groupId+"/permalink/"+mediaPostId+"/";
else if(!postUrl&&mediaPostId)postUrl="https://www.facebook.com/permalink.php?story_fbid="+mediaPostId;
else if(!postUrl&&photoUrl)postUrl=photoUrl;

const topLines=(card.innerText||"").split("\n").slice(0,6).map(x=>x.trim()).filter(Boolean);
let authorName=fiberAuthor||authorFromLink||"مالك مباشر";
for(const ln of topLines){
const nl=normD(ln);
if(!headerTimeHint&&nl.length<=35&&TIME_RE.test(nl))headerTimeHint=nl;
if(ln.includes("مجهول الهوية")||ln.toLowerCase().includes("anonymous")){authorName="مشارك مجهول الهوية";authorProfileUrl="";break;}
}
if(groupName&&bodyText.startsWith(groupName))bodyText=bodyText.substring(groupName.length).trim();

let profAdCount=1;
if(authorProfileUrl&&authorName!=="مشارك مجهول الهوية"){
updateUI("يفحص بروفايل ("+authorName+") (1-8 إعلانات)...");
const pRes=await checkAuthorProfileInBg(authorProfileUrl);
profAdCount=pRes.count||1;
if(pRes.isBroker||profAdCount>8){
card._gS=true;saveHash(keyHash);scannedCount++;
lastLogMsg="مرفوض بروفايل ("+pRes.reason+"): "+authorName;
updateUI("رفض سمسار بعد فحص البروفايل");
return null;
}
}
return{hash:keyHash,url:postUrl,fiber_ctime:fiberCtime,author:authorName,profile_ads_count:profAdCount,group_name:groupName,header_time:headerTimeHint||normD(topLines.join(" | ")),text:bodyText.substring(0,2600)};
}

function sendBridge(d){
return new Promise(res=>{
try{chrome.runtime.sendMessage({type:"FB_POST_INGEST",payload:d},r=>res(r||{ok:false,accepted:false,reason:"No response"}));}
catch(e){res({ok:false,accepted:false,reason:String(e)});}
});
}

async function scanVisible(){
const cards=collectCards();
for(const card of cards){
if(card._gS)continue;
const data=await inspectCandidateCard(card);
if(!data)continue;
consecutiveSeen=0;card._gS=true;saveHash(data.hash);scannedCount++;
const prv=data.text.replace(/\s+/g," ").substring(0,42);
const resp=await sendBridge(data);
if(resp&&resp.accepted){acceptedCount++;lastLogMsg="تم تخزين مالك لنهاية الرن ("+data.profile_ads_count+" إعلان): "+prv;}
else{lastLogMsg="مرفوض ("+((resp&&resp.reason)||"فلتر")+"): "+prv;}
updateUI("يقلب ويخزن لنهاية الرن");
}
}

function startRestCycle(){
isResting=true;
updateUI("انتهت الرن (45د) -> جاري رفع كل الإعلانات المخزنة دفعة واحدة...");
try{chrome.runtime.sendMessage({type:"FB_FLUSH_BATCH"},()=>{});}catch(e){}
let rSec=REST_SEC;
const iv=setInterval(()=>{
rSec-=5;
updateUI("تم رفع الدفعة! استراحة أمان 30 دقيقة ("+Math.ceil(Math.max(0,rSec)/60)+" د متبقية ثم Refresh)");
if(rSec<=0){
clearInterval(iv);
sessionStorage.setItem("gamal_fb_run_ts_v130",String(Date.now()));
location.href=FEEDS[0].url;
}
},5000);
}

async function loop(){
if(isResting)return;
if(location.pathname.startsWith("/search/")){location.href=FEEDS[feedIdx].url;return;}
if(Date.now()-runStartTs>=RUN_MS){startRestCycle();return;}
if(Date.now()-pageLoadTs>=SWITCH_MS||consecutiveSeen>=18){
feedIdx=(feedIdx+1)%FEEDS.length;
localStorage.setItem("gamal_fb_fidx_v130",String(feedIdx));
updateUI("تحديث الصفحة الرئيسية لجلب أحدث الإعلانات...");
location.href=FEEDS[feedIdx].url;
return;
}
await scanVisible();
window.scrollBy({top:Math.floor(640+Math.random()*240),behavior:"smooth"});
updateUI("فحص سريع للصفحة الرئيسية");
setTimeout(loop,Math.floor(1400+Math.random()*600));
}
updateUI("بدأ رادار الصفحة الرئيسية وفحص البروفايل v13.0...");
setTimeout(loop,1100);
})();
""".strip()

    with open(os.path.join(FB_EXT_DIR, "manifest.json"), "w", encoding="utf-8") as f: json.dump(manifest, f, ensure_ascii=False, indent=2)
    with open(os.path.join(FB_EXT_DIR, "background.js"), "w", encoding="utf-8") as f: f.write(background_js)
    with open(os.path.join(FB_EXT_DIR, "main_world_hook.js"), "w", encoding="utf-8") as f: f.write(main_world_hook_js)
    with open(os.path.join(FB_EXT_DIR, "content.js"), "w", encoding="utf-8") as f: f.write(content_js)

def load_fb_memory():
    if os.path.exists(FB_MEMORY_FILE):
        try:
            with open(FB_MEMORY_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict): return d
        except Exception: pass
    return {"phones": {}, "authors": {}, "seen_hashes": []}

def save_fb_memory(mem):
    try:
        mem["seen_hashes"] = mem.get("seen_hashes", [])[-4000:]
        with open(FB_MEMORY_FILE, "w", encoding="utf-8") as f: json.dump(mem, f, ensure_ascii=False)
    except Exception: pass

def has_broker_copywriting(title, desc_text):
    norm_body = normalize_ar(f"{title} {desc_text[:3500]}")
    for safe_neg in SAFE_OWNER_BROKER_NEGATIONS: norm_body = norm_body.replace(normalize_ar(safe_neg), " ")
    for bp in BROKER_TEXT_PHRASES:
        if normalize_ar(bp) in norm_body: return True, f"Broker Phrase ({bp})"
    if re.search(r'(?:code|كود)\s*[:\-]?\s*[a-z]{0,3}\d{2,7}\b', norm_body, re.I) or re.search(r'\bmsr\d{2,5}\b', norm_body, re.I):
        return True, "Broker Inventory Code"
    return False, ""

def is_verified_fb_owner_post(norm_pure_text):
    if any(k in norm_pure_text for k in ("ضمن الاعضاء", "اصدقاء ضمن الاعضاء", "مجموعه عامه", "مجموعه خاصه")):
        return False, "كارت جروب وليس منشور"
    explicit_owner_re = r'(?:من\s*المالك|المالك\s*مباشر|انا\s*المالك|مالك\s*العقار|مالك\s*الشقه|مالك\s*الفيلا|شقتي|فيلتي|بيتي|ملكي|بتاعتي|بدون\s*وسيط|بدون\s*وسطاء|ممنوع\s*الوسطاء|يمتنع\s*الوسطاء|لغير\s*الوسطاء|لا\s*للوسطاء|عدم\s*تدخل\s*الوسطاء|بدون\s*سمسار|بدون\s*سماسره|ممنوع\s*السماسره|يمتنع\s*السماسره|بدون\s*بروكر|ممنوع\s*البروكر)'
    if re.search(explicit_owner_re, norm_pure_text): return True, "مالك مباشر موثق"
    return False, "بدون دليل مالك صريح"

def parse_fb_strict_2days_header_time(header_str, fiber_ctime=0):
    now_dt = datetime.now(CAIRO_TZ)
    now_ts = int(now_dt.timestamp())
    if fiber_ctime and fiber_ctime >= 1600000000:
        diff_sec = max(0, now_ts - int(fiber_ctime))
        if diff_sec > (MAX_AGE_DAYS * 86400): return False, f"Old FB Post ({round(diff_sec / 86400, 1)}d > 2d)", "", True
        if diff_sec < 3600: return True, "OK", f"منذ {max(1, diff_sec // 60)} د", False
        if diff_sec < 86400: return True, "OK", f"منذ {diff_sec // 3600} س", False
        return True, "OK", f"منذ {diff_sec // 86400} يوم", False
    clean_h, norm_h = strip_bidi(header_str), normalize_ar(header_str)
    if re.search(r'\b(?:202[0-5])\b', norm_h): return False, "Old FB Year (<2026)", "", True
    if re.search(r'(?:منذ|قبل)?\s*(?:\d+\s*)?(?:اسبوع|اسابيع|اسبوعين|شهر|شهور|اشهر|سنه|سنوات|\d+\s*w\b|\d+\s*أ\b)', norm_h): return False, "Old FB Post (>1w)", "", True
    m_old_d = re.search(r'(?:^|\s)([3-9]|\d{2,})\s*(?:يوم|ايام|ي(?:\s|$)|d(?:\s|$))', norm_h)
    if m_old_d: return False, f"Old FB Post ({m_old_d.group(1)}d > 2d)", "", True
    for m_cal in re.finditer(r'(\d{1,2})\s+(يناير|فبراير|مارس|ابريل|أبريل|إبريل|مايو|يونيو|يونية|يوليو|يوليه|اغسطس|أغسطس|سبتمبر|اكتوبر|أكتوبر|نوفمبر|ديسمبر)(?:\s+(202\d))?', clean_h):
        d_val, m_name = int(m_cal.group(1)), m_cal.group(2)
        y_val = int(m_cal.group(3)) if m_cal.group(3) else now_dt.year
        m_val = ARABIC_MONTHS.get(m_name, 0)
        if m_val > 0:
            try:
                d_diff = (now_dt.date() - date(y_val, m_val, d_val)).days
                if d_diff < 0 or d_diff > MAX_AGE_DAYS: return False, f"Old FB Date ({d_val} {m_name} > 2d)", "", True
                return True, "OK", ("اليوم" if d_diff == 0 else f"منذ {d_diff} يوم"), False
            except Exception: return False, "Invalid FB Date", "", False
    if re.search(r'(?:الان|توا|حالا|just now)', norm_h): return True, "OK", "الآن", False
    m_min = re.search(r'(\d{1,2})\s*(?:دقيقه|دقائق|دقايق|د(?:\s|$)|m(?:\s|$)|mins?)', norm_h)
    if m_min: return True, "OK", f"منذ {m_min.group(1)} د", False
    if re.search(r'(?:دقيقه|دقيقتين)', norm_h): return True, "OK", "منذ دقائق", False
    m_hr = re.search(r'(\d{1,2})\s*(?:ساعه|ساعات|س(?:\s|$)|h(?:\s|$)|hrs?)', norm_h)
    if m_hr:
        hrs = int(m_hr.group(1))
        return (False, f"Old FB Hours ({hrs}h)", "", True) if hrs > 48 else (True, "OK", f"منذ {hrs} س", False)
    if re.search(r'(?:ساعه|ساعتين)', norm_h): return True, "OK", "منذ ساعة", False
    if re.search(r'(?:امس|الامس|امبارح|yesterday|1\s*ي(?:\s|$)|1\s*d(?:\s|$)|منذ\s*يوم|قبل\s*يوم)', norm_h): return True, "OK", "منذ يوم", False
    if re.search(r'(?:منذ\s*يومين|قبل\s*يومين|2\s*ي(?:\s|$)|2\s*d(?:\s|$)|يومين)', norm_h): return True, "OK", "منذ يومين", False
    return False, "Unverified FB Date", "", False

def parse_facebook_colloquial_price(text, deal):
    clean_t, norm_t = strip_bidi(text), normalize_ar(text)
    if deal != "إيجار":
        m_mil_k = re.search(r'(\d{1,2})\s*مليون\s*(?:و\s*)?(\d{2,3})\s*الف', norm_t)
        if m_mil_k:
            val = int(m_mil_k.group(1)) * 1000000 + int(m_mil_k.group(2)) * 1000
            return val, f"{val:,} ج.م", True
        m_mil_half = re.search(r'(\d{1,2})\s*مليون\s*و\s*(?:نص|نصف)', norm_t)
        if m_mil_half:
            val = int(m_mil_half.group(1)) * 1000000 + 500000
            return val, f"{val:,} ج.م", True
        m_mil_dec = re.search(r'(\d{1,2}(?:\.\d{1,3})?)\s*مليون', norm_t)
        if m_mil_dec:
            val = int(float(m_mil_dec.group(1)) * 1000000)
            if val >= MIN_CASH_SALE_PRICE: return val, f"{val:,} ج.م", True
    else:
        m_k = re.search(r'(?:السعر|الايجار|إيجار|بـ|ب|مطلوب)\s*(\d{1,3})\s*(?:الف|ألف|تلاف)', norm_t) or re.search(r'\b(\d{1,2}(?:\.\d)?)\s*(?:الف|ألف)\s*(?:جنيه|ج|شهريا|في الشهر)?', norm_t)
        if m_k:
            val = int(float(m_k.group(1)) * 1000)
            if 3000 <= val <= 400000: return val, f"{val:,} ج.م", True
    for m_num in re.findall(r'([\d,]{4,12})\s*(?:جنيه|ج\.?م|ج\b|شهريا|كاش)', clean_t):
        val = int(re.sub(r'[^\d]', '', m_num))
        if (deal == "إيجار" and 3000 <= val <= 500000) or (deal != "إيجار" and MIN_CASH_SALE_PRICE <= val <= 500000000): return val, f"{val:,} ج.م", True
    return ((1, "السعر بالتفاصيل (خاص)", False) if deal == "إيجار" else (MIN_CASH_SALE_PRICE, "كاش (السعر بالتفاصيل)", False))

def parse_rooms_ar(norm_t):
    rooms_m = re.search(r'(\d{1,2})\s*(?:غرف|غرفه|نوم|وصاله)', norm_t)
    if rooms_m and 1 <= int(rooms_m.group(1)) <= 15: return int(rooms_m.group(1))
    if re.search(r'\b(?:ثلاث|ثلاثه|تلات|تلاته)\s*(?:غرف|غرفه|نوم)', norm_t): return 3
    if re.search(r'\b(?:غرفتين|اثنين\s*غرفه)\b', norm_t): return 2
    if re.search(r'\b(?:اربع|اربعه)\s*(?:غرف|غرفه|نوم)', norm_t): return 4
    if re.search(r'\b(?:خمس|خمسه)\s*(?:غرف|غرفه|نوم)', norm_t): return 5
    return None

def classify_fb_category(norm_t):
    if any(k in norm_t for k in ("شقه", "دوبلكس", "بنتهاوس", "ستوديو", "استوديو", "رووف", "روف")): return "شقق"
    if any(k in norm_t for k in ("فيلا", "تاون هاوس", "توين هاوس", "ستاند الون")): return "فلل"
    if any(k in norm_t for k in ("محل", "مكتب", "عياده", "مقر اداري", "تجاري", "صيدليه")): return "تجاري"
    if any(k in norm_t for k in ("قطعه ارض", "ارض للبيع", "عماره كامله", "مبني كامل")): return "أراضي"
    return "شقق"

def process_facebook_post_payload(payload):
    global FB_PENDING_BATCH_COUNT
    pure_raw_text = strip_bidi(payload.get("text") or "").strip()
    group_name = strip_bidi(payload.get("group_name") or "").strip()
    author_raw = strip_bidi(payload.get("author") or "مشارك مجهول الهوية").strip()
    prof_ads_cnt = max(1, int(payload.get("profile_ads_count") or 1))
    header_time = strip_bidi(payload.get("header_time") or "")
    fiber_ctime = int(payload.get("fiber_ctime") or 0)
    post_url = (payload.get("url") or "").strip()
    post_hash = payload.get("hash") or ""
    if group_name: pure_raw_text = pure_raw_text.replace(group_name, " ").strip()
    short_preview = re.sub(r'\s+', ' ', pure_raw_text)[:55]
    if len(pure_raw_text) < 25: return False, "نص قصير", False

    norm_t = normalize_ar(pure_raw_text)
    if any(k in norm_t for k in ("ضمن الاعضاء", "اصدقاء ضمن الاعضاء", "مجموعه عامه", "مجموعه خاصه")): return False, "كارت جروب وليس منشور", False
    if prof_ads_cnt > MAX_OWNER_ADS_FB: return False, f"سمسار ({prof_ads_cnt} إعلانات بالبروفايل)", False

    mem = load_fb_memory()
    if post_hash and post_hash in mem.get("seen_hashes", []): return False, "مفحوص سابقا", False
    is_fresh, time_reason, orig_age_hint, is_explicit_old = parse_fb_strict_2days_header_time(header_time, fiber_ctime)
    if not is_fresh:
        if post_hash: mem.setdefault("seen_hashes", []).append(post_hash); save_fb_memory(mem)
        print(f"  [FB SCAN] [- REJECTED FB] {time_reason} | {short_preview}")
        return False, "منشور قديم (>يومين)", is_explicit_old

    if not is_direct_fb_post_permalink(post_url):
        print(f"  [FB SCAN] [- REJECTED FB] No Direct Post Permalink | {short_preview}")
        return False, "بدون رابط بوست مباشر", False

    if post_hash: mem.setdefault("seen_hashes", []).append(post_hash)
    for wp in FB_WANTED_PHRASES:
        if normalize_ar(wp) in norm_t[:180]:
            save_fb_memory(mem)
            print(f"  [FB SCAN] [- REJECTED FB] Wanted Post ({wp}) | {short_preview}")
            return False, "طلب وليس عرض", False

    phones = list(set(re.findall(r'\b01[0125]\d{8}\b', re.sub(r'[\s\-]', '', pure_raw_text))))
    for ph in phones:
        ph_posts = mem.setdefault("phones", {}).setdefault(ph, [])
        if post_hash and post_hash not in ph_posts: ph_posts.append(post_hash)

    is_anon = ("مجهول" in author_raw or "anonymous" in author_raw.lower())
    pub_name = "مشارك مجهول الهوية" if is_anon else clean_publisher_name(author_raw)
    if pub_name == "مالك مباشر" and is_anon: pub_name = "مشارك مجهول الهوية"
    if not is_anon and pub_name != "مالك مباشر":
        au_posts = mem.setdefault("authors", {}).setdefault(pub_name, [])
        if post_hash and post_hash not in au_posts: au_posts.append(post_hash)
    save_fb_memory(mem)

    if len(phones) >= 2: return False, "أرقام مبيعات متعددة", False
    for ph in phones:
        if len(mem.get("phones", {}).get(ph, [])) > 1: return False, "رقم مكرر في أكثر من إعلان (سمسار)", False
    if not is_anon and pub_name != "مالك مباشر" and is_company_name(pub_name):
        print(f"  [FB SCAN] [- REJECTED FB] Broker Account ({pub_name}) | {short_preview}")
        return False, "حساب شركة/سمسار", False
    if re.search(r'(?:للايجار\s*اليومي|ايجار\s*يومي|شقه\s*فندقيه|شقق\s*فندقيه|اسبوعي)', norm_t): return False, "إيجار يومي/فندقي", False

    is_brk, brk_reason = has_broker_copywriting("", pure_raw_text)
    if is_brk:
        print(f"  [FB SCAN] [- REJECTED FB] {brk_reason} | {short_preview}")
        return False, "صيغة سمسار", False

    is_true_owner, owner_proof_label = is_verified_fb_owner_post(norm_t)
    if not is_true_owner:
        print(f"  [FB SCAN] [- REJECTED FB] {owner_proof_label} | {short_preview}")
        return False, owner_proof_label, False

    zone = detect_zone("", pure_raw_text)
    if not zone: return False, "مدينة مستبعدة", False
    if zone == "القاهرة الجديدة":
        context_zone = detect_zone("", group_name)
        if not context_zone: return False, "مدينة مستبعدة", False
        if context_zone != "القاهرة الجديدة": zone = context_zone
        elif any(k in normalize_ar(f"{pure_raw_text} {group_name}") for k in ("التجمع", "القاهره الجديده")): zone = "التجمع الخامس"
        else: return False, "خارج مناطق التجمع", False

    is_rent = any(k in norm_t for k in ("للايجار", "ايجار", "مفروش", "شهريا", "في الشهر"))
    deal, cat = ("إيجار" if is_rent else "تمليك"), classify_fb_category(norm_t)
    price_num, price_str, has_real_price = parse_facebook_colloquial_price(pure_raw_text, deal)
    if deal != "إيجار" and not is_strict_cash_sale("", pure_raw_text, price_num): return False, "تقسيط/مقدم", False

    area_m = re.search(r'(\d{2,4})\s*(?:متر|م2|م²|\bم\b)', norm_t)
    area_val = int(area_m.group(1)) if (area_m and 25 <= int(area_m.group(1)) <= 5000) else None
    if not has_real_price and not area_val and not phones: return False, "إعلان مبهم بدون سعر أو مساحة أو رقم", False

    clean_lines = [ln.strip() for ln in pure_raw_text.split("\n") if ln.strip() and ln.strip() != group_name and "ضمن الأعضاء" not in ln]
    first_line = (clean_lines[0] if clean_lines else pure_raw_text)[:85]
    title = first_line if len(first_line) >= 12 else f"{cat} ({deal}) في {zone} - {pub_name}"

    ai_ok, ai_reason = analyze_with_ai(title, pure_raw_text, pub_name, deal, cat, price_num, "فيسبوك")
    if not ai_ok:
        print(f"  [FB SCAN] [- REJECTED FB by AI] {ai_reason} | {short_preview}")
        return False, "رفض ذكاء اصطناعي (سمسار)", False

    rooms_val = parse_rooms_ar(norm_t)
    now_dt = datetime.now(CAIRO_TZ)
    entry_ts = int(now_dt.timestamp())
    entry_age_label = f"دخل الرادار {now_dt.strftime('%I:%M %p')}" + (f" (نُشر {orig_age_hint})" if orig_age_hint else "")
    uid = int("93" + str(abs(hash(norm_t[:75])) % 1000000000))
    phone_note = f" | ت: {phones[0]}" if phones else ""

    fb_ad = {
        "ad_id": uid, "id": f"fb_{uid}", "source": "فيسبوك", "title": title, "price": price_str, "price_num": price_num,
        "zone": zone, "location": zone, "cat": cat, "category": cat, "deal": deal, "type": deal, "area": area_val, "rooms": rooms_val,
        "publisher": pub_name + phone_note, "pub_ads": prof_ads_cnt, "active_ads_count": prof_ads_cnt, "age": entry_age_label, "fresh_tier": 3,
        "description": pure_raw_text[:600], "first_seen_ts": entry_ts, "timestamp": entry_ts, "desc_verified_v2": True,
        "verified_24h_v93": True, "verified_fb_v130": True, "url": post_url, "link": post_url, "verified_v12": True,
        "scraped_at": now_dt.strftime("%Y-%m-%d %I:%M %p"), "date": now_dt.strftime("%Y-%m-%d %H:%M")
    }
    with SYNC_LOCK:
        extra_live = load_extra_live_backup()
        extra_live.insert(0, fb_ad)
        save_extra_live_backup(extra_live)
        FB_PENDING_BATCH_COUNT += 1
        print(f"\n  >>> [FB STORED FOR END-OF-RUN BATCH #{FB_PENDING_BATCH_COUNT}] ({entry_age_label}) | {pub_name}{phone_note} ({prof_ads_cnt} ads) | {zone} | {post_url[:65]} <<<")
    return True, "OK", False

class FacebookIngestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    def handle(self):
        try: super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError): pass
    def _send_cors(self, code=200):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "application/json")
        self.end_headers()
    def do_OPTIONS(self): self._send_cors(200)
    def do_POST(self):
        global FB_PENDING_BATCH_COUNT
        if self.path == "/fb_flush":
            with SYNC_LOCK:
                print(f"\n  >>> [FB RUN COMPLETE] Pushing stored batch ({FB_PENDING_BATCH_COUNT} new FB ads) to GitHub & Website now... <<<")
                guard_extra_ads_during_sleep(force_push=True)
                FB_PENDING_BATCH_COUNT = 0
            self._send_cors(200)
            self.wfile.write(b'{"ok":true}')
            return
        if self.path != "/fb_ingest": self._send_cors(404); return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8", errors="replace"))
            ok, reason, is_old = process_facebook_post_payload(payload)
            self._send_cors(200)
            self.wfile.write(json.dumps({"accepted": ok, "reason": reason, "is_old": is_old}).encode("utf-8"))
        except Exception as e:
            try:
                self._send_cors(200)
                self.wfile.write(json.dumps({"accepted": False, "reason": str(e), "is_old": False}).encode("utf-8"))
            except Exception: pass

def start_fb_local_server():
    def _serve():
        try:
            srv = HTTPServer(("127.0.0.1", FB_PORT), FacebookIngestHandler)
            print(f"[Facebook Home Feed & Profile Receiver v13.0] Listening live on http://127.0.0.1:{FB_PORT}/fb_ingest")
            srv.serve_forever()
        except Exception as e: print(f"[FB Receiver Notice] {e}")
    threading.Thread(target=_serve, daemon=True).start()

def a_u(ad): return ad.get("url") or ad.get("link") or ""

def fetch_remote_ads_list():
    try:
        clear_git_locks()
        subprocess.run(["git", "fetch", "origin", "main"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
        res = subprocess.run(["git", "show", "origin/main:ads.json"], cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=15)
        if res.returncode == 0 and res.stdout:
            d = json.loads(res.stdout)
            if isinstance(d, dict) and isinstance(d.get("ads"), list): return d["ads"]
    except Exception: pass
    return []

def load_extra_live_backup():
    combined = []
    for fpath in [EXTRA_LIVE_BACKUP_FILE, AQ_LIVE_BACKUP_FILE]:
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    arr = json.load(f)
                    if isinstance(arr, list):
                        for a in arr:
                            if is_valid_existing_extra_ad(a): combined.append(a)
            except Exception: pass
    dedup, seen_u = [], set()
    for a in combined:
        u = str(a.get("ad_id") or a_u(a))
        txt_k = normalize_ar((a.get("description") or a.get("title") or "")[:70]) if a.get("source") == "فيسبوك" else u
        if u and u not in seen_u and txt_k not in seen_u:
            seen_u.add(u); seen_u.add(txt_k); dedup.append(a)
    return dedup

def save_extra_live_backup(extra_ads_list):
    try:
        if os.path.exists(EXTRA_LIVE_BACKUP_FILE):
            try: os.chmod(EXTRA_LIVE_BACKUP_FILE, stat.S_IWRITE)
            except Exception: pass
        with open(EXTRA_LIVE_BACKUP_FILE, "w", encoding="utf-8") as f: json.dump(extra_ads_list[:220], f, ensure_ascii=False, indent=2)
    except Exception: pass

def atomic_write_and_git_push(data_payload, commit_msg):
    fix_git_identity_for_vercel()
    for attempt in range(1, 4):
        try:
            clear_git_locks()
            subprocess.run(["git", "fetch", "origin", "main"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            subprocess.run(["git", "reset", "--mixed", "origin/main"], cwd=BASE_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            if os.path.exists(DATA_FILE):
                try: os.chmod(DATA_FILE, stat.S_IWRITE)
                except Exception: pass
            with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data_payload, f, ensure_ascii=False, indent=2)
            subprocess.run(["git", "add", "-f", "ads.json"], cwd=BASE_DIR, capture_output=True, timeout=15)
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=BASE_DIR, capture_output=True, timeout=15)
            p_res = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=BASE_DIR, capture_output=True, text=True, timeout=120)
            if p_res.returncode == 0: return True, "OK"
        except Exception as e:
            if attempt == 3: return False, str(e)
            time.sleep(3)
    return False, "Push failed"

def load_persistent_seen_ids():
    seen_set = set()
    if os.path.exists(EXTRA_SEEN_FILE):
        try:
            with open(EXTRA_SEEN_FILE, "r", encoding="utf-8") as f:
                arr = json.load(f)
                if isinstance(arr, list):
                    for x in arr:
                        try: seen_set.add(int(x))
                        except Exception: pass
        except Exception: pass
    return seen_set

def save_persistent_seen_ids(seen_set):
    try:
        if os.path.exists(EXTRA_SEEN_FILE):
            try: os.chmod(EXTRA_SEEN_FILE, stat.S_IWRITE)
            except Exception: pass
        with open(EXTRA_SEEN_FILE, "w", encoding="utf-8") as f: json.dump(list(seen_set)[-20000:], f)
    except Exception: pass

def is_warp_up():
    try:
        with socket.create_connection(("127.0.0.1", 40000), timeout=0.8): return True
    except Exception: return False

class SmartFetcher:
    def __init__(self):
        self.warp_active = is_warp_up()
        base_headers = {"Accept-Language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7", "Referer": "https://www.google.com/", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8", "Upgrade-Insecure-Requests": "1"}
        self.warp_sess = cffi_requests.Session(impersonate="chrome120", proxies={"http": WARP_PROXY, "https": WARP_PROXY}) if self.warp_active else None
        if self.warp_sess: self.warp_sess.headers.update(base_headers)
        self.direct_sess = cffi_requests.Session(impersonate="chrome120")
        self.direct_sess.headers.update(base_headers)

    def _is_valid_html(self, html, req_regex=None):
        if not html or len(html) < 1500 or "Pardon Our Interruption" in html or "Just a moment..." in html or "<title>Attention Required!" in html: return False
        return not (req_regex and not re.search(req_regex, html))

    def get_html(self, raw_url, req_regex=None, require_path_sub=None):
        url = urllib.parse.quote(urllib.parse.unquote(raw_url), safe=":/?&=#%")
        statuses = []
        if self.warp_active and self.warp_sess:
            try:
                r = self.warp_sess.get(url, timeout=18, allow_redirects=True)
                final_u = str(r.url or url)
                if require_path_sub and require_path_sub not in final_u: return "", "Redirected_To_Search", final_u
                if r.status_code == 200 and self._is_valid_html(r.text, req_regex): return r.text, "200 (WARP)", final_u
                statuses.append(f"WARP:{r.status_code}")
            except Exception: statuses.append("WARP:ERR")
        try:
            r = self.direct_sess.get(url, timeout=18, allow_redirects=True)
            final_u = str(r.url or url)
            if require_path_sub and require_path_sub not in final_u: return "", "Redirected_To_Search", final_u
            if r.status_code == 200 and self._is_valid_html(r.text, req_regex): return r.text, "200 (Direct)", final_u
            statuses.append(f"Direct:{r.status_code}")
        except Exception: statuses.append("Direct:ERR")
        return "", " | ".join(statuses), url

def is_company_name(name):
    norm = normalize_ar(name)
    if not norm or norm.startswith(normalize_ar("مالك مباشر")) or "مجهول" in norm: return False
    for bw in BROKER_NAME_WORDS:
        nk = normalize_ar(bw)
        if len(nk) <= 3:
            if re.search(rf'\b{re.escape(nk)}\b', norm): return True
        elif nk in norm: return True
    return False

def clean_publisher_name(name):
    default_lbl = "مالك مباشر"
    if not name: return default_lbl
    s = strip_bidi(re.sub(r'<[^>]+>', ' ', str(name)))
    s = re.sub(r'(?:تواصل\s*مع\s*المعلن|اتصل\s*لمعرفه\s*السعر|اتصل\s*لمعرفة\s*السعر|عضو\s*منذ.*|الإعلانات\s*النشطة.*|\(\d+.*?\)|\d+\s*عقار.*|عقار\s*واحد|عقارين|اتصال|اتصل|واتساب|رسالة|Avatar|الصورة\s*الشخصية|user\s*logo|ملاحظة|حفظ|مشاركة|شارك|إبلاغ|تابِع|تابع|التقييم.*)', ' ', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip(" -_|:,><.★⭐•·+")
    norm_s = normalize_ar(s)
    if any(bad_w in norm_s for bad_w in ("اتصل", "لمعرفه", "السعر", "تواصل", "المعلن", "ملاحظه", "مشاركه", "ابلاغ", "تسجيل", "دخول", "شركات", "موثوقه", "جروب", "مجموعه", "عقارات التجمع", "شقق التجمع")): return default_lbl
    if not s or len(s) < 2 or len(s) > 38 or re.search(r'[<>{}\[\]=/\\0-9]{4,}', s): return default_lbl
    return s

def detect_zone(title, body_text):
    raw_core = re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', f"{title} {body_text[:2000]}")
    core = normalize_ar(raw_core)
    for city in EXCLUDED_CITIES:
        if normalize_ar(city) in core: return None
    for z_name, keywords in ZONES:
        for kw in keywords:
            if normalize_ar(kw) in core: return z_name
    return "القاهرة الجديدة"

def is_strict_cash_sale(title, desc_text, price_num):
    if int(price_num or 0) < MIN_CASH_SALE_PRICE: return False
    raw_combined = re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', f"{title} {desc_text[:3000]}")
    full_text = normalize_ar(raw_combined)
    for neg in SAFE_CASH_NEGATIONS: full_text = full_text.replace(normalize_ar(neg), " ")
    for kw in INSTALLMENT_SUBSTRINGS:
        if normalize_ar(kw) in full_text: return False
    return not bool(re.search(r'\b\d+\s*%\s*(?:مقدم|تعاقد|دفعه|down)', full_text))

def parse_aqarmap_strict_2days_date(text_block):
    now_dt = datetime.now(CAIRO_TZ)
    now_ts = int(now_dt.timestamp())
    clean_t = strip_bidi(text_block)
    for m_ar_cal in re.finditer(r'\b(\d{1,2})\s+(يناير|فبراير|مارس|ابريل|أبريل|إبريل|مايو|يونيو|يونية|يوليو|يوليه|اغسطس|أغسطس|سبتمبر|اكتوبر|أكتوبر|نوفمبر|ديسمبر)\s+(202\d)\b', clean_t[:3000]):
        d_val, m_name, y_val = int(m_ar_cal.group(1)), m_ar_cal.group(2), int(m_ar_cal.group(3))
        m_val = ARABIC_MONTHS.get(m_name, 0)
        if m_val > 0:
            try:
                d_diff = (now_dt.date() - date(y_val, m_val, d_val)).days
                if d_diff < 0 or d_diff > MAX_AGE_DAYS: return False, f"Old AqarMap Ad ({d_val} {m_name} {y_val} > {MAX_AGE_DAYS}d)", 0, 0
                if d_diff == 0: return True, f"اليوم ({d_val} {m_name})", 3, now_ts - 3600
                elif d_diff == 1: return True, f"منذ يوم ({d_val} {m_name})", 3, now_ts - 72000
                else: return True, f"منذ يومين ({d_val} {m_name})", 2, now_ts - 150000
            except Exception: return False, "Invalid AqarMap Date", 0, 0
    return False, "Unverified AqarMap Date", 0, 0

def extract_aqarmap_candidates_from_search_html(html, src, seen_ids, extra_checked, banned_ids):
    out = []
    if not html: return out
    soup = BeautifulSoup(html, "html.parser")
    seen_local = set()
    for a in soup.find_all("a", href=re.compile(r'/ar/listing/\d{5,12}')):
        href_str = str(a.get("href", "")).split("?")[0].strip()
        m = re.search(r'^(/ar/listing/(\d{5,12})[^"\'\s<>\\]*)$', href_str)
        if not m: continue
        path, num_str = m.group(1), m.group(2)
        uid = int("91" + num_str)
        if uid in seen_local or uid in seen_ids or uid in extra_checked or uid in banned_ids: continue
        seen_local.add(uid)
        card = a
        for _ in range(4):
            if not card.parent or len(card.parent.get_text(" ", strip=True)) > 650: break
            card = card.parent
        has_company_logo = any("/companies/" in str(img.get("src") or "").lower() or "company-logo" in str(img.get("src") or "").lower() or ("logo" in strip_bidi(img.get("alt") or "").lower() and "user logo" not in strip_bidi(img.get("alt") or "").lower() and "aqarmap" not in strip_bidi(img.get("alt") or "").lower()) for img in card.find_all("img"))
        if has_company_logo: extra_checked.add(uid); continue
        norm_c = normalize_ar(card.get_text(" ", strip=True))
        if any(normalize_ar(city) in norm_c for city in EXCLUDED_CITIES): extra_checked.add(uid); continue
        if src["deal"] != "إيجار" and any(k in norm_c for k in ("بالتقسيط", "قسط علي", "تكمله اقساط")): extra_checked.add(uid); continue
        seen_ids.add(uid)
        out.append({"ad_id": uid, "num_str": num_str, "source": "عقارماب", "en_src": "AqarMap", "url": "https://aqarmap.com.eg" + path, "cat": src["cat"], "deal": src["deal"]})
    return out

def extract_aqarmap_details(html, deal, expected_num_str, final_url):
    if "/ar/listing/" not in str(final_url): return None, "Redirected to Search Page"
    soup_full = BeautifulSoup(html, "html.parser")
    canonical_url = final_url
    can_tag = soup_full.find("link", {"rel": "canonical"}) or soup_full.find("meta", {"property": "og:url"})
    if can_tag:
        c_href = (can_tag.get("href") or can_tag.get("content") or "").strip()
        if c_href.startswith("http"):
            if "/ar/listing/" not in c_href: return None, "Canonical URL is Search Page"
            canonical_url = c_href
    for tag in soup_full.find_all(["header", "nav", "footer", "script", "style", "noscript"]): tag.decompose()
    h1 = soup_full.find("h1")
    title = strip_bidi((h1.get_text(" ", strip=True) if h1 else "").split("|")[0]).strip()
    if not title or len(title) < 5: return None, "Empty title"
    full_txt = strip_bidi(soup_full.get_text(" ", strip=True))
    specs_start, desc_start = full_txt.find("تفاصيل الإعلان"), full_txt.find("وصف الإعلان")
    if specs_start == -1 or desc_start == -1: return None, "Redirected to Search Page (Missing Specs)"
    is_fresh_2d, age_label, fresh_tier, official_ts = parse_aqarmap_strict_2days_date(full_txt[:specs_start + 1200])
    if not is_fresh_2d: return None, age_label
    specs_txt = full_txt[specs_start:desc_start]
    norm_specs = normalize_ar(specs_txt)
    if expected_num_str and f"eg-{expected_num_str}" not in norm_specs: return None, f"Mismatched Listing ID (Expected EG-{expected_num_str})"
    if re.search(r'نوع\s*المعلن\s*[:\-]?\s*(?:مسوق|مطور|شركه|وسيط|broker|developer)', norm_specs): return None, "AqarMap Role: Broker/Developer"
    if "مالك عقار" not in norm_specs: return None, "AqarMap Role: Not Verified Owner"
    if re.search(r'(?:سنه\s*التسليم|سنه\s*البناء)\s*[:\-]?\s*20(?:27|28|29|30)\b', norm_specs): return None, "Off-Plan Future Delivery (2027+)"

    desc_raw = full_txt[desc_start + len("وصف الإعلان"):]
    desc_cut = len(desc_raw)
    for marker in ["أظهر المزيد", "مزايا العقار", "وقت الوصول", "الموقع على الخريطة", "تواصل مع المعلن"]:
        idx_m = desc_raw.find(marker)
        if idx_m != -1 and idx_m < desc_cut: desc_cut = idx_m
    pure_desc = desc_raw[:min(2500, desc_cut)].strip()

    pub_name, pub_ads = "مالك مباشر", 1
    for m_sel in re.finditer(r'تواصل\s*مع\s*المعلن', html):
        seller_html = html[m_sel.start():m_sel.start() + 4000]
        s_block = strip_bidi(BeautifulSoup(seller_html, "html.parser").get_text(" | ", strip=True))
        norm_s = normalize_ar(s_block)
        if not re.search(r'(?:0\s*عقار|عقار\s*واحد|عقارين|\d+\s*عقارات|\d+\s*عقار)', norm_s): continue
        if "company-img" in seller_html or "/companies/" in seller_html.lower(): return None, "Company Account"
        if re.search(r'\b[345]\.[0-9]\b', norm_s): return None, "Subscribed Broker Rating Badge"
        if "0 عقار" in norm_s or "عقار واحد" in norm_s: pub_ads = 1
        elif "عقارين" in norm_s: pub_ads = 2
        else:
            m_cnt = re.search(r'\b(\d{1,5})\s*(?:عقارات|عقار)\b', norm_s)
            if m_cnt: pub_ads = int(m_cnt.group(1))
        parts = [p.strip() for p in s_block.split("|") if p.strip() and "تواصل مع المعلن" not in p]
        for idx_p, p in enumerate(parts[:10]):
            norm_p = normalize_ar(p)
            if re.search(r'^(?:0\s*عقار|عقار\s*واحد|(?:\d+\s*)?عقارين|\d+\s*عقارات|\d+\s*عقار)$', norm_p) and idx_p >= 1:
                cand_prev = clean_publisher_name(parts[idx_p - 1])
                if cand_prev != "مالك مباشر": pub_name = cand_prev; break
            cand = clean_publisher_name(p)
            if cand != "مالك مباشر": pub_name = cand
        break

    if is_company_name(pub_name): return None, f"Company/Broker Name ({pub_name})"
    if pub_ads > MAX_OWNER_ADS_AQ: return None, f"Broker Count ({pub_ads} > {MAX_OWNER_ADS_AQ})"
    is_brk_txt, brk_reason = has_broker_copywriting(title, pure_desc)
    if is_brk_txt: return None, brk_reason
    zone = detect_zone(title, pure_desc)
    if not zone: return None, "Excluded Zone"

    price_context = full_txt[:1500] + " " + specs_txt
    if deal != "إيجار" and re.search(r'ج\.?م\s*(?:بالتقسيط|تكمله\s*اقساط)', normalize_ar(price_context)): return None, "Installment Price Badge"
    price_num, price_str = 0, "السعر بالتفاصيل"
    for m_p in re.findall(r'([\d,]{4,15})\s*(?:جنيه|ج\.?م|EGP)', price_context, re.I):
        val = int(re.sub(r'[^\d]', '', m_p))
        if (deal == "إيجار" and 2500 <= val <= 4000000) or (deal != "إيجار" and MIN_CASH_SALE_PRICE <= val <= 1500000000):
            price_num, price_str = val, f"{val:,} ج.م"; break
    if price_num == 0: return None, "Missing/Zero Price"
    if deal != "إيجار" and not is_strict_cash_sale(title, pure_desc, price_num): return None, f"Installment or Downpayment ({price_num:,})"

    top_specs_blob = full_txt[:2200] + " " + specs_txt + " " + pure_desc
    area_m = re.search(r'(\d{2,4})\s*(?:متر|م²|م2|sqm)', top_specs_blob, re.I)
    rooms_m = re.search(r'(\d{1,2})\s*(?:غرف|غرفة|غرفه|نوم)', top_specs_blob)
    return {"title": title, "body_text": pure_desc[:2000], "zone": zone, "pub_name": pub_name, "pub_ads": max(1, pub_ads), "price_num": price_num, "price_str": price_str, "area": (int(area_m.group(1)) if area_m else None), "rooms": (int(rooms_m.group(1)) if (rooms_m and 1 <= int(rooms_m.group(1)) <= 20) else None), "age_label": age_label, "fresh_tier": fresh_tier, "real_ts": official_ts, "canonical_url": canonical_url}, "OK"

def is_valid_existing_extra_ad(ad):
    src = ad.get("source") or "دوبيزل"
    if src == "دوبيزل": return True
    u = str(a_u(ad))
    if src == "عقارماب" and (not ad.get("verified_aq_v100") or "/ar/listing/" not in u): return False
    if src == "فيسبوك" and (not ad.get("verified_fb_v130") or not is_direct_fb_post_permalink(u)): return False
    if src not in ("عقارماب", "فيسبوك"): return False
    now_ts = int(datetime.now(CAIRO_TZ).timestamp())
    ad_ts = int(ad.get("first_seen_ts") or ad.get("timestamp") or 0)
    if ad_ts <= 0 or (now_ts - ad_ts) > ((MAX_AGE_DAYS + 1) * 86400): return False
    pub, title, desc, zone = ad.get("publisher", ""), ad.get("title", ""), ad.get("description", ""), ad.get("zone", "")
    deal, price_num = ad.get("deal", "تمليك"), int(ad.get("price_num", 0) or 0)
    max_allowed = MAX_OWNER_ADS_FB if src == "فيسبوك" else MAX_OWNER_ADS_AQ
    if price_num <= 0 or int(ad.get("pub_ads", 1) or 1) > max_allowed or is_company_name(pub): return False
    is_brk, _ = has_broker_copywriting(title, desc)
    if is_brk: return False
    norm_all = normalize_ar(f"{title} {zone}")
    if any(normalize_ar(city) in norm_all for city in EXCLUDED_CITIES): return False
    if deal != "إيجار" and not is_strict_cash_sale(title, desc, price_num): return False
    return True

def sync_ads_to_github_now(data_obj, new_extra_ads, existing_ads, extra_checked, tg_cfg, notified_ids, run_report, msg_label):
    with SYNC_LOCK:
        disk_ads = []
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    d_disk = json.load(f)
                    if isinstance(d_disk, dict) and isinstance(d_disk.get("ads"), list): disk_ads = d_disk["ads"]
            except Exception: pass
        all_pool = new_extra_ads + load_extra_live_backup() + disk_ads + existing_ads + fetch_remote_ads_list()
        merged_ads, seen_u = [], set()
        for ad in all_pool:
            if not is_valid_existing_extra_ad(ad): continue
            u = str(ad.get("ad_id") or a_u(ad))
            txt_k = normalize_ar((ad.get("description") or ad.get("title") or "")[:70]) if ad.get("source") == "فيسبوك" else u
            if not u or u in seen_u or txt_k in seen_u: continue
            seen_u.add(u); seen_u.add(txt_k); merged_ads.append(ad)
        merged_ads.sort(key=lambda x: (int(x.get("first_seen_ts") or 0), int(x.get("ad_id") or 0)), reverse=True)
        merged_ads = merged_ads[:450]
        extra_live = [a for a in merged_ads if a.get("source") in ("عقارماب", "فيسبوك")]
        save_extra_live_backup(extra_live)
        aq_cnt = sum(1 for a in extra_live if a.get("source") == "عقارماب")
        fb_cnt = sum(1 for a in extra_live if a.get("source") == "فيسبوك")
        data_obj["updated_at"] = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
        data_obj["total"] = len(merged_ads)
        data_obj["last_run_report"] = run_report
        data_obj["ads"] = merged_ads
        data_obj["extra_checked_ids"] = list(extra_checked)[-10000:]
        data_obj["telegram_config"] = tg_cfg
        data_obj["telegram_notified_ids"] = list(notified_ids)[-5000:]
        if not os.environ.get("GITHUB_ACTIONS"):
            ok_p, p_info = atomic_write_and_git_push(data_obj, f"{msg_label} (AqarMap: {aq_cnt}, Facebook: {fb_cnt})")
            if ok_p: print(f"    --> [BATCH SYNC COMPLETE] {msg_label} | Live on Site -> AqarMap: ({aq_cnt}) | Facebook: ({fb_cnt})!")
            else: print(f"    --> [LOCAL SAVE] {p_info}")
        return merged_ads, aq_cnt, fb_cnt

def guard_extra_ads_during_sleep(force_push=False):
    extra_backup = load_extra_live_backup()
    if not os.path.exists(DATA_FILE): return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: d = json.load(f)
        if not isinstance(d, dict) or not isinstance(d.get("ads"), list): return
        cur_ads = d["ads"]
        cur_extra_ids = {a.get("ad_id") for a in cur_ads if a.get("source") in ("عقارماب", "فيسبوك") and is_valid_existing_extra_ad(a)}
        backup_ids = {a.get("ad_id") for a in extra_backup}
        has_invalid = any((a.get("source") or "دوبيزل") != "دوبيزل" and not is_valid_existing_extra_ad(a) for a in cur_ads)
        if force_push or not backup_ids.issubset(cur_extra_ids) or has_invalid:
            clean_pool = extra_backup + [a for a in cur_ads if is_valid_existing_extra_ad(a)]
            merged, seen_u = [], set()
            for ad in clean_pool:
                u = str(ad.get("ad_id") or a_u(ad))
                txt_k = normalize_ar((ad.get("description") or ad.get("title") or "")[:70]) if ad.get("source") == "فيسبوك" else u
                if not u or u in seen_u or txt_k in seen_u: continue
                seen_u.add(u); seen_u.add(txt_k); merged.append(ad)
            merged.sort(key=lambda x: (int(x.get("first_seen_ts") or 0), int(x.get("ad_id") or 0)), reverse=True)
            d["ads"] = merged[:450]
            d["total"] = len(d["ads"])
            d["updated_at"] = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
            aq_c = sum(1 for a in extra_backup if a.get("source") == "عقارماب")
            fb_c = sum(1 for a in extra_backup if a.get("source") == "فيسبوك")
            ok_p, p_info = atomic_write_and_git_push(d, f"Batch Sync Extra Owners (AqarMap: {aq_c}, Facebook: {fb_c})")
            if ok_p: print(f"    --> [Batch Push] Synced AqarMap ({aq_c}) & Facebook ({fb_c}) owners to GitHub & Vercel!")
            else: print(f"    --> [Batch Push Notice] {p_info}")
    except Exception: pass

def sync_telegram_config(current_cfg):
    cfg = dict(current_cfg or {})
    try:
        r = std_requests.get(f"https://ntfy.sh/{TG_CONFIG_TOPIC}/json?poll=1&since=168h", timeout=10)
        if r.status_code == 200:
            for line in r.text.strip().splitlines():
                if not line: continue
                msg = json.loads(line).get("message", "")
                if msg.startswith("TG_CFG:"):
                    decoded = json.loads(base64.b64decode(msg.replace("TG_CFG:", "").strip()).decode("utf-8"))
                    if decoded.get("tok") and decoded.get("cid"): cfg["tok"], cfg["cid"] = decoded["tok"].strip(), str(decoded["cid"]).strip()
    except Exception: pass
    return cfg

def analyze_with_ai(title, visible_text, pub_name, deal, cat, price_num, source):
    url = "https://gamal216.pythonanywhere.com/analyze"
    payload = {"text": f"{title} {visible_text[:2000]}", "title": title, "description": visible_text[:2000], "publisher": pub_name, "deal": deal, "cat": cat, "price_num": price_num, "source": source, "active_ads_count": 1}
    try:
        response = std_requests.post(url, json=payload, timeout=12)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                if result.get("decision") == "مرفوض": return False, "AI Rejected"
                analysis = result.get("analysis", "")
                if "سمسار" in analysis and "مالك حقيقي" not in analysis: return False, "AI Detected Broker"
                return True, "Owner"
    except Exception: pass
    if deal != "إيجار":
        ok = is_strict_cash_sale(title, visible_text, price_num)
        return ok, ("Owner" if ok else "Installment Suspect")
    return True, "Owner"

def run_extra_radar():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        except Exception: data = {"ads": []}
    else: data = {"ads": []}
    if not isinstance(data, dict): data = {"ads": data if isinstance(data, list) else []}

    raw_existing = load_extra_live_backup() + data.get("ads", []) + fetch_remote_ads_list()
    extra_checked = load_persistent_seen_ids()
    banned_ids = set(data.get("banned_ad_ids", []))
    notified_ids = set(data.get("telegram_notified_ids", []))
    tg_cfg = sync_telegram_config(data.get("telegram_config", {}))
    run_report = data.get("last_run_report", {})

    fetcher = SmartFetcher()
    existing_ads, seen_existing_u = [], set()
    for ad in raw_existing:
        u = str(ad.get("ad_id") or a_u(ad))
        if u and u not in seen_existing_u and is_valid_existing_extra_ad(ad):
            seen_existing_u.add(u); existing_ads.append(ad)

    seen_ids = {a.get("ad_id") for a in existing_ads if a.get("ad_id")}
    new_extra_ads, aq_candidates = [], []

    for src in AQARMAP_SOURCES:
        for page in range(1, src.get("max_p", 3) + 1):
            page_url = src["url"] if page == 1 else f"{src['url']}&page={page}"
            html, status_info, _ = fetcher.get_html(page_url, req_regex=r'/ar/listing/\d+')
            found_aq = extract_aqarmap_candidates_from_search_html(html, src, seen_ids, extra_checked, banned_ids)
            aq_candidates.extend(found_aq)
            print(f"[AqarMap] {src['en']} p.{page} -> {status_info} (Candidates: {len(found_aq)})")
            time.sleep(random.uniform(0.4, 0.8))

    save_persistent_seen_ids(extra_checked)
    all_candidates = [x for x in aq_candidates if x["deal"] == "إيجار"][:160] + [x for x in aq_candidates if x["deal"] != "إيجار"][:160]
    print(f"\n[AqarMap + Facebook Radar v13.0] AqarMap Unchecked: {len(aq_candidates)} | Inspecting: {len(all_candidates)}")

    aq_added, total_c = 0, len(all_candidates)
    for idx, item in enumerate(all_candidates, 1):
        uid, num_str = item["ad_id"], item.get("num_str", "")
        try:
            html, st_ad, final_url = fetcher.get_html(item["url"], require_path_sub="/ar/listing/")
            if st_ad == "Redirected_To_Search":
                extra_checked.add(uid)
                print(f"  [{idx}/{total_c}] [- REJECTED AqarMap] Redirected to Search Page")
                continue
            if not html: continue
            info, reason = extract_aqarmap_details(html, item["deal"], num_str, final_url)
            if reason != "Empty title":
                extra_checked.add(uid)
                if idx % 15 == 0: save_persistent_seen_ids(extra_checked)
            if not info:
                print(f"  [{idx}/{total_c}] [- REJECTED AqarMap] {reason}")
                continue
            is_owner, ai_reason = analyze_with_ai(info["title"], info["body_text"], info["pub_name"], item["deal"], item["cat"], info["price_num"], "عقارماب")
            if not is_owner:
                print(f"  [{idx}/{total_c}] [- REJECTED AqarMap] {ai_reason}")
                continue
            real_post_ts = int(info.get("real_ts") or time.time())
            now_cairo = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
            verified_url = info.get("canonical_url") or final_url
            new_extra_ads.append({
                "ad_id": uid, "id": f"ext_{uid}", "source": "عقارماب", "title": info["title"], "price": info["price_str"], "price_num": info["price_num"],
                "zone": info["zone"], "location": info["zone"], "cat": item["cat"], "category": item["cat"], "deal": item["deal"], "type": item["deal"],
                "area": info["area"], "rooms": info["rooms"], "publisher": info["pub_name"], "pub_ads": info["pub_ads"], "active_ads_count": info["pub_ads"],
                "age": info["age_label"], "fresh_tier": info["fresh_tier"], "description": info["body_text"][:500], "first_seen_ts": real_post_ts, "timestamp": real_post_ts,
                "desc_verified_v2": True, "verified_24h_v93": True, "verified_aq_v100": True, "url": verified_url, "link": verified_url, "verified_v12": True,
                "scraped_at": now_cairo, "date": datetime.fromtimestamp(real_post_ts, CAIRO_TZ).strftime("%Y-%m-%d %H:%M")
            })
            aq_added += 1
            print(f"  [{idx}/{total_c}] [+ STORED AQARMAP FOR END-OF-RUN BATCH] ({info['age_label']}) | {info['pub_name']} ({info['pub_ads']} ads) | Price: {info['price_num']:,} EGP")
            time.sleep(random.uniform(0.5, 0.8))
        except Exception: continue

    save_persistent_seen_ids(extra_checked)
    print(f"\n>>> [End-of-Run Batch Push] Sending all collected AqarMap & Facebook ads to GitHub & Website now... <<<")
    merged_ads, aq_total, fb_total = sync_ads_to_github_now(data, new_extra_ads, existing_ads, extra_checked, tg_cfg, notified_ids, run_report, f"Cycle Batch Complete (+{aq_added} AQ)")
    print(f"=== Cycle Complete: Batch Sent +{aq_added} AqarMap | Live on Site -> AqarMap: {aq_total} | Facebook: {fb_total} ===")

def main():
    global FB_PENDING_BATCH_COUNT
    generate_facebook_main_extension()
    if os.environ.get("GITHUB_ACTIONS"):
        run_extra_radar()
        return
    start_fb_local_server()
    print("=== Starting 24/7 AqarMap + Facebook Home Feed & Profile Owner Radar v13.0 (End-of-Run Batch Mode) ===")
    print(f"[!] Load unpacked extension once in Chrome -> {FB_EXT_DIR}")
    cycle_num = 1
    while True:
        print(f"\n>>> Starting Extra Radar Cycle #{cycle_num} at {datetime.now(CAIRO_TZ).strftime('%H:%M:%S')} <<<")
        try:
            run_extra_radar()
            FB_PENDING_BATCH_COUNT = 0
        except Exception as e:
            print(f"[Error in Cycle #{cycle_num}]: {e}")
        cycle_num += 1
        print(f"\n[Auto-Loop] Sleeping for {AUTO_LOOP_MINUTES}m (Facebook storing in background -> pushes batch at end of run)...")
        for _ in range((AUTO_LOOP_MINUTES * 60) // 30):
            time.sleep(30)
        if FB_PENDING_BATCH_COUNT > 0:
            with SYNC_LOCK:
                print(f"\n>>> [End of 45m Cycle] Pushing {FB_PENDING_BATCH_COUNT} stored Facebook ads in batch... <<<")
                guard_extra_ads_during_sleep(force_push=True)
                FB_PENDING_BATCH_COUNT = 0

if __name__ == "__main__":
    main()
