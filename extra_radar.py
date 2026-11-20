import os, sys, re, json, time, stat, subprocess, urllib.parse, ctypes, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone, timedelta, date
import requests as std_requests

def init_win():
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

init_win()

CAIRO_TZ = timezone(timedelta(hours=2))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ads.json")
AQ_LIVE_BACKUP_FILE = os.path.join(BASE_DIR, "aqarmap_live_ads.json")
EXTRA_LIVE_BACKUP_FILE = os.path.join(BASE_DIR, "extra_live_ads.json")
FB_PENDING_FILE = os.path.join(BASE_DIR, "fb_pending_ads.json")
FB_MEMORY_FILE = os.path.join(BASE_DIR, "fb_memory.json")
FB_EXT_DIR = os.path.join(BASE_DIR, "fb_main_radar_ext")
ADMIN_CMD_TOPIC = "gamal_vip_cmd_9941_sec"
FB_PORT = 5005
MIN_CASH_SALE_PRICE = 1200000
MAX_AGE_DAYS = 2
AUTO_LOOP_MINUTES = 45
FB_PENDING_BATCH_COUNT = 0
DIRECT_PULL_QUEUE = []
PROCESSED_CMD_IDS = set()
HINDI_MAP = str.maketrans({"٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9", "٬": ",", "،": ",", "٫": "."})
BIDI_REGEX = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]')
SYNC_LOCK = threading.Lock()
ARABIC_MONTHS = {"يناير": 1, "فبراير": 2, "مارس": 3, "ابريل": 4, "أبريل": 4, "إبريل": 4, "مايو": 5, "يونيو": 6, "يونية": 6, "يوليو": 7, "يوليه": 7, "اغسطس": 8, "أغسطس": 8, "سبتمبر": 9, "اكتوبر": 10, "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12}

ZONES = [
    ("التجمع الخامس", "التجمع الخامس|تجمع خامس|fifth settlement|5th settlement|ميفيدا|mivida|هايد بارك|ماونتن فيو|كايرو فيستفال|كايرو فيستيفال|الباتيو|فيلت|سوديك|ستون ريزيدنس|ستون بارك|ايست تاون|ليك فيو|بالم هيلز التجمع|الحي الاول|الحي الثاني|الحي التاني|الحي الثالث|الحي التالت|الحي الرابع|الحي الخامس|الحي 1|الحي 2|الحي 3|الحي 4|الحي 5|غرب الجولف|الجامعه الامريكيه|الجامعة الامريكية|auc|فاطمه الشربتلي|فاطمة الشربتلي|مسجد الشرطه|مسجد الشرطة|بوينت 90|كونكورد".split("|")),
    ("التجمع الأول", "التجمع الأول|التجمع الاول|تجمع اول|first settlement|1st settlement|مجاورة|مجاوره".split("|")),
    ("التجمع الثالث", "التجمع الثالث|التجمع التالت|تجمع تالت|third settlement|3rd settlement|أربيلا|اربيلا|أرابيلا|ارابيلا|غرب ارابيلا|الهايكستب|المحلية|المحليه|اسكان الشباب|إسكان الشباب".split("|")),
    ("اللوتس", ["اللوتس", "لوتس", "lotus"]), ("النرجس", ["النرجس", "نرجس", "narges", "narjis"]), ("الياسمين", ["الياسمين", "ياسمين", "yasmeen", "jasmine"]), ("البنفسج", ["البنفسج", "بنفسج", "banafseg"]),
    ("الأندلس", ["الأندلس", "الاندلس", "اندلس", "andalus"]), ("جنوب الأكاديمية", ["جنوب الأكاديمية", "جنوب الاكاديمية", "الأكاديمية", "الاكاديميه"]), ("شرق الأكاديمية", ["شرق الأكاديمية", "شرق الاكاديمية"]),
    ("المستثمرين", ["المستثمرين", "investors"]), ("الشويفات", ["الشويفات", "choueifat"]), ("القرنفل", ["القرنفل", "قرنفل", "koronfel"]), ("التمر حنة", ["التمر حنة", "تمر حنة", "tamr hena"]),
    ("أبو الهول", ["أبو الهول", "ابو الهول", "جاردينيا هايتس", "جاردينيا"]), ("دار مصر", ["دار مصر", "سكن مصر", "جنة مصر", "جنه مصر", "فرجينيا"]), ("القطامية", ["القطامية", "القطاميه", "katameya"]), ("شارع التسعين", ["التسعين", "90th"]),
]
EXCLUDED_CITIES = "الرحاب|رحاب|rehab|مدينتي|مدينتى|madinaty|العبور|الشروق|مدينة بدر|مدينه بدر|هليوبوليس الجديدة|العاصمة الإدارية|العاصمه الاداريه|التجمع السادس|sixth settlement|كابيتال جاردنز|capital gardens|سراي|sarai|البروج|alburouj|طلالة|talala|دي جويا|dejoya|محور الأمل|تاج سيتي|تاج سيتى|taj city|تاج سلطان|العاشر من رمضان|6 أكتوبر|أكتوبر|الشيخ زايد|زايد|المعادي|زهراء المعادي|المقطم|الهضبة الوسطى|مدينة نصر|مصر الجديدة|شيراتون|النزهة|عين شمس|السلام|جسر السويس|حدائق القبة|المرج|شبرا|حلوان|15 مايو|الزمالك|المهندسين|الدقي|العجوزة|الهرم|فيصل|حدائق الأهرام|حدائق الاهرام|حدائق أكتوبر|الساحل الشمالي|العين السخنة|الجونة|الغردقة|شرم الشيخ|الإسكندرية|الاسكندرية|المستقبل|mostakbal|سمات|مقبرة|مقابر|مدفن|مدافن".split("|")
INSTALLMENT_SUBSTRINGS = "قسط|تقسيط|بالتقسيط|لتقسيط|اقساط|أقساط|باقساط|بأقساط|تكملة أقساط|تكمله اقساط|مقدم|بمقدم|بقدم |دفعة|دفعه|دفعات|تسهيلات|سداد|فترة سداد|سنوات سداد|أنظمة سداد|انظمه سداد|بدون فوائد|متبقي|المتبقي|والباقي|أوفر|اوفر|امكانية التقسيط|متاح تقسيط|ويوجد تقسيط|سنة التسليم 2027|سنة التسليم 2028|سنة التسليم 2029|سنة التسليم 2030|قيد الإنشاء|قيد الانشاء|down payment|downpayment|installment|installments|payment plan|فاليو|valu".split("|")
SAFE_CASH_NEGATIONS = "بدون تقسيط|لا يوجد تقسيط|ممنوع التقسيط|وليس تقسيط|مش تقسيط|بدون أقساط|بدون اقساط|خالص الثمن|خالصة الثمن|خالصه الثمن|ليس عليها أقساط|ليس عليها اقساط|لا يوجد أقساط|لا يوجد اقساط|مسدد بالكامل|مسددة بالكامل|غير متاح تقسيط|البيع كاش فقط|كاش فقط|كاش نهائي".split("|")
SAFE_OWNER_BROKER_NEGATIONS = "بدون وسيط|بدون وسطاء|ممنوع الوسطاء|يمتنع الوسطاء|لغير الوسطاء|عدم تدخل الوسطاء|عدم التعامل مع الوسطاء|لا للوسطاء|بدون سمسار|بدون سماسرة|بدون سماسره|ممنوع السماسرة|ممنوع السماسره|يمتنع السماسرة|يمتنع السماسره|بدون بروكر|ممنوع البروكر|يمتنع البروكر|من غير سمسار|من غير وسيط|من المالك مباشره|من المالك مباشر|المالك مباشره|المالك مباشر|من المالكه مباشره|من المالكه مباشر|المالكه مباشره|المالكه مباشر|التواصل مباشر مع المالك|التعامل مباشر مع المالك|مباشر من المالك|انا المالك|انا المالكه|بدون عموله|بدون عمولة|بدون عمولات".split("|")
BROKER_NAME_WORDS = "zone|real estate|realestate|realty|property|properties|homes|agency|agencies|broker|brokers|brokerage|investment|investments|development|developments|consult|consultant|consulting|company|marketing|scouts|vertex|redefine|irtkaz|ebtkar|imkan|falcon|realtors|trusted home|remax|coldwell|era|prime|capital|house|group|taki|vita|شركة|شركه|مكتب|تسويق|للتسويق|ماركتنج|سمسار|وسيط|استشاري|مستشار|للاستشارات|تطوير|للتطوير|للاستثمار|هومز|بروكر|ريال استيت|استيت|فيرتكس|ريديفاين|ارتكاز|إرتكاز|ابتكار|إبتكار|دار البناء|للمقاولات|للإنشاءات|للانشاءات|اللوتس العقارية|البيت المصري|ادارة املاك|إدارة أملاك|عقاري|عقارات|للعقارات|العقاريه|تاكي".split("|")
BROKER_TEXT_PHRASES = "انا وسيط|أنا وسيط|وسيط مش المالك|مش المالك|ليس المالك|وسيط عقاري|وسيط عقارى|وسيط من المالك|وسيط مع المالك|مباشر من المالك لدينا|انا بروكر|م بروكر|للتواصل مع البروكر|سمسار|سماسرة|سماسره|بروكر|broker|مكتب عقاري|مكتب عقارات|مكتب تسويق|ادارة املاك|عمولة شهر|عموله شهر|عمولة نصف شهر|عموله نصف شهر|عمولة المكتب|عموله المكتب|عمولة الشركة|عموله الشركه|بعموله|بعمولة|نسبة العمولة|يوجد عمولة|يوجد عموله|عمولة 1|عموله 1|عمولة 2|عموله 2|لماذا تختار شركتنا|شركتنا|شركة عقارات|شركه عقارات|شركة تسويق|شركه تسويق|للتسويق العقاري|للاستثمار العقاري|للتطوير العقاري|استشاري عقاري|مستشار عقاري|فريق المبيعات|قسم المبيعات|للتواصل مع قسم المبيعات|فريق من الخبراء|مجموعة متنوعة من الشقق|تقع عقاراتنا|زيارة معروضاتنا|سجل بياناتك|عائد إيجاري شهري مضمون|عائد ايجاري شهري مضمون|بعائد ايجاري يصل|كود الوحدة|كود الوحده|كود العقار|كود الشقة|كود الفيلا|الكود المرجعي|متاح لدينا|يتوفر لدينا|متوفر لدينا|لدينا أكثر من|متاح لدينا اكثر من|لدينا عقارات|متاح عروض اخري|متاح عروض أخرى|يوجد عروض اخري|متاح شقق اخري|متاح مساحات مختلفة|مساحات مختلفة|مساحات مختلفه|متوفر لدينا وحدات|متاح لدينا وحدات|باقل سعر بالمشروع|استمرار لعروضنا|والواقع يتحدث عنا|امتلك وحدتك|احجز وحدتك|اختار وحدتك|مطلوب وموجود|مطلوب ومعروض|متاح وحدات اخري|ضمن الاعضاء|اصدقاء ضمن الاعضاء|مجموعه عامه|مجموعه خاصه|معايا شقه|معايا شقة|معايا فيلا|بلوكيشن تحفه|بلوكيشن تحفة|ادفع بفاليو|مصاريف شراء".split("|")
FB_WANTED_PHRASES = "مطلوب شقه|مطلوب شقة|مطلوب فيلا|مطلوب للايجار|مطلوب للإيجار|مطلوب للشراء|مطلوب للبيع|مطلوب من المالك|بدور علي شقه|بدور على شقة|بدور علي فيلا|محتاج شقه|محتاج شقة|محتاجه شقه|محتاجة شقة|عايز شقه|عايز شقة|عايزة شقة|عايزه شقه|ابحث عن شقه|أبحث عن شقة|حد عنده شقه|حد عنده شقة|مطلوب عاجل|مطلوب فورا|مطلوب شريك|مطلوب شريكة|مطلوب روم ميت".split("|")

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
    if "facebook.com" not in u: return False
    return bool(re.search(r'(?:/share/[pv]/[A-Za-z0-9._\-]+|/posts/(?:\d+|pfbid[A-Za-z0-9]+)|/permalink/\d+|story_fbid=(?:\d+|pfbid[A-Za-z0-9]+)|multi_permalinks=\d+|/photo/?\?fbid=\d+|/groups/[^/]+/user/\d+|/groups/[^/]+/search/\?q=)', u))

def generate_facebook_main_extension():
    os.makedirs(FB_EXT_DIR, exist_ok=True)
    manifest = {
        "manifest_version": 3, "name": "Gamal Direct Home Feed & Link Puller v16.0", "version": "16.0",
        "description": "Home Feed Pending Approval Queue + Remote Link Puller + Auto-Like",
        "permissions": ["storage", "tabs", "clipboardRead", "clipboardWrite"],
        "host_permissions": ["https://www.facebook.com/*", "http://127.0.0.1:5005/*"],
        "background": {"service_worker": "background.js"},
        "content_scripts": [
            {"matches": ["https://www.facebook.com/*"], "js": ["main_world_hook.js"], "run_at": "document_start", "world": "MAIN"},
            {"matches": ["https://www.facebook.com/*"], "js": ["content.js"], "run_at": "document_idle"}
        ]
    }
    background_js = r"""
let activePullTabId = null;
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
    if (m && m.type === "FB_DIRECT_PULL_RESULT") {
        if (sender && sender.tab && sender.tab.id) {
            try { chrome.tabs.remove(sender.tab.id); } catch(e) {}
            if (activePullTabId === sender.tab.id) activePullTabId = null;
        }
        fetch("http://127.0.0.1:5005/fb_direct_ingest", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(m.payload)})
        .then(r => r.json()).then(() => sr({ok: true})).catch(() => sr({ok: false}));
        return true;
    }
});

setInterval(() => {
    if (activePullTabId !== null) return;
    fetch("http://127.0.0.1:5005/fb_poll_task")
    .then(r => r.json())
    .then(d => {
        if (d && d.url) {
            const sep = d.url.includes("?") ? "&" : "?";
            const targetUrl = d.url + sep + "g_direct_pull=1";
            chrome.tabs.create({url: targetUrl, active: true}, tab => {
                if (tab && tab.id) {
                    activePullTabId = tab.id;
                    setTimeout(() => {
                        if (activePullTabId === tab.id) {
                            try { chrome.tabs.remove(tab.id); } catch(e) {}
                            activePullTabId = null;
                        }
                    }, 18000);
                }
            });
        }
    }).catch(() => {});
}, 2500);
""".strip()

    main_world_hook_js = r"""
(function(){
if(window.__gamalMainHookV160)return;
window.__gamalMainHookV160=true;
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
if(n.message&&typeof n.message.text==="string"&&n.message.text.length>=18)cx.text=n.message.text;
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
if(!fM&&o.message&&typeof o.message.text==="string"&&o.message.text.length>=18)fM=o.message.text;
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
domEl.querySelectorAll('div[data-ad-preview="message"],div[data-ad-comet-preview="message"],div[data-ad-rendering-role="story_message"],div[dir="auto"],a[href],span[role="link"],h2,h3,h4').forEach(n=>nds.push(n));
for(const el of nds){
if(!fG&&el.href){
const mG=el.href.match(/facebook\.com\/groups\/([^/?&#]+)/);if(mG&&mG[1]!=="feed"&&mG[1]!=="discover")fG=mG[1];
const mGm=el.href.match(/set=(?:gm|pcb)\.(\d{10,25})/);if(mGm&&!fP)fP=mGm[1];
}
let fK=null;try{fK=Object.keys(el).find(k=>k.startsWith("__reactFiber$")||k.startsWith("__reactProps$"));}catch(e){}
if(!fK)continue;
let cur=el[fK];
for(let s=0;s<40&&cur;s++){
if(cur.memoizedProps)scan(cur.memoizedProps,0);
if(!fU&&cur.pendingProps)scan(cur.pendingProps,0);
if(fU&&fC&&fM)break;
cur=cur.return;
}
}
if(!fU&&fG&&fP)fU="https://www.facebook.com/groups/"+fG+"/permalink/"+fP+"/";
else if(!fU&&fP)fU="https://www.facebook.com/permalink.php?story_fbid="+fP;
return{url:fU,ctime:fC,pureMsg:fM,author:fA,groupId:fG};
}
function stamp(){
scanJson();
document.querySelectorAll("[data-g-inspect-req='1']").forEach(card=>{
card.removeAttribute("data-g-inspect-req");
try{
const res=extFiber(card),mEl=card.querySelector('div[data-ad-preview="message"],div[data-ad-comet-preview="message"],div[data-ad-rendering-role="story_message"]');
const cTxt=res.pureMsg||(mEl?mEl.innerText:""),mp=cTxt?rMap.get(nKey(cTxt)):null;
const fU=res.url||(mp&&mp.url)||"",fC=res.ctime||(mp&&mp.ctime)||0,fM=res.pureMsg||(mp&&mp.text)||"",fA=res.author||(mp&&mp.author)||"",fG=res.groupId||"";
if(fU)card.setAttribute("data-g-permalink",fU);
if(fC)card.setAttribute("data-g-ctime",String(fC));
if(fM)card.setAttribute("data-g-puremsg",fM);
if(fA)card.setAttribute("data-g-author",fA);
if(fG)card.setAttribute("data-g-groupid",fG);
}catch(e){}
});
}
window.addEventListener("gamal_fiber_scan",stamp);
setInterval(stamp,350);
})();
""".strip()

    content_js = r"""
(function(){
if(window.__gamalFbRadarV160)return;
window.__gamalFbRadarV160=true;
const slp=ms=>new Promise(r=>setTimeout(r,ms));
const H_MAP={"٠":"0","١":"1","٢":"2","٣":"3","٤":"4","٥":"5","٦":"6","٧":"7","٨":"8","٩":"9"};
const normD=s=>String(s||"").replace(/[٠-٩]/g,c=>H_MAP[c]||c);

if(location.search.includes("g_direct_pull=1")){
setTimeout(async()=>{
try{
await slp(2200);
const btns=document.querySelectorAll('div[role="button"],span[role="button"]');
for(const b of btns){
const bt=(b.innerText||"").trim();
if((bt==="عرض المزيد"||bt==="See more"||bt.includes("عرض المزيد"))&&!b.closest("ul")&&!b.closest("form")){
try{b.click();await slp(500);}catch(e){}
}
}
const msgNodes=document.querySelectorAll('div[data-ad-preview="message"],div[data-ad-comet-preview="message"],div[data-ad-rendering-role="story_message"],div[dir="auto"]');
let bestTxt="";
msgNodes.forEach(n=>{
if(n.closest("ul")||n.closest("form")||n.closest("nav"))return;
const t=normD((n.innerText||"").trim());
if(t.length>bestTxt.length&&t.length<3500)bestTxt=t;
});
if(!bestTxt)bestTxt=normD((document.body.innerText||"").substring(0,1800));
let author="مالك مباشر",groupName="";
document.querySelectorAll("h2 a,h3 a,h4 a,a[href*='/user/'],a[href*='/groups/']").forEach(a=>{
const t=(a.innerText||"").split("\n")[0].trim(),h=a.href||"";
if(h.includes("/groups/")&&!h.includes("/user/")&&!h.includes("/posts/")&&!h.includes("/permalink/")&&t.length>=3&&!groupName)groupName=t;
else if(t.length>=2&&t.length<=40&&author==="مالك مباشر"&&t!==groupName)author=t;
});
const cleanUrl=location.href.replace(/([?&])g_direct_pull=1(&|$)/,"$1").replace(/[?&]$/,"");
chrome.runtime.sendMessage({type:"FB_DIRECT_PULL_RESULT",payload:{url:cleanUrl,text:bestTxt,author:author,group_name:groupName}});
}catch(e){
chrome.runtime.sendMessage({type:"FB_DIRECT_PULL_RESULT",payload:{url:location.href,text:"",author:"مالك مباشر",group_name:""}});
}
},1000);
return;
}

const FEEDS=[
{name:"صفحتك الرئيسية (Home Feed)",url:"https://www.facebook.com/"},
{name:"الصفحة الرئيسية (الأحدث)",url:"https://www.facebook.com/?sk=h_chr"}
];
const RUN_MS=45*60*1000,REST_SEC=30*60,SWITCH_MS=16*60*1000;
const REAL_PROP_RE=/(شقه|شقة|فيلا|فيله|فيلات|دوبلكس|بنتهاوس|ستوديو|استوديو|رووف|روف|تاون\s*هاوس|توين\s*هاوس|شاليه|عماره|عمارة|محل|مكتب|عياده|عيادة|للايجار|للإيجار|للبيع|تمليك|ايجار|إيجار)/i;
const STRICT_OWNER_RE=/(من\s*المالك[ةه]?|المالك[ةه]?\s*مباشر[ةه]?|للمالك[ةه]?\s*مباشر[ةه]?|[أاإ]نا\s*المالك[ةه]?|مالك[ةه]?\s*(?:[أاإ]صل[يى]|العقار|الشق[ةه]|الفيل[اآه]|مباشر[ةه]?)|شقت[يى]|فيلت[يى]|بيت[يى]|ملك[يى])/i;
const BRK_FAST_RE=/(متاح\s*لدينا|يتوفر\s*لدينا|شركتنا|كود\s*الوحده|كود\s*الوحدة|عموله\s*شهر|عمولة\s*شهر|سمسار|بروكر|للتسويق\s*العقاري|مستشار\s*عقاري|مطلوب\s*شقه|مطلوب\s*شقة|مطلوب\s*للايجار|معايا\s*شقه|معايا\s*شقة|بلوكيشن\s*تحفه|بلوكيشن\s*تحفة|ادفع\s*بفاليو|تاكي|taki|valu)/i;
const SPONSORED_RE=/(مُموَّل|ممول|Sponsored|إعلان\s*ممول)/i;
const G_NOISE=/(ضمن الأعضاء|أصدقاء ضمن الأعضاء|مجموعة عامة|مجموعة خاصة|منشورًا في اليوم|منشورات في اليوم|انضمام إلى المجموعة)/i;
const G_WORDS=/(جروب|مجموعه|مجموعة|عقارات|شقق|سكان|اهالي|أهالي|بيع وشراء|ايجار وتمليك|إيجار وتمليك|سوق|ملتقى|رابطه|رابطة)/i;
const TIME_RE=/(الآن|توًا|حالا|just now|(?:^|\s)\d{1,2}\s*[دسيهأ](?:\s|$)|دقيقة|دقيقتين|دقائق|ساعة|ساعتين|ساعات|أمس|امس|الأمس|يوم|يومين|أيام|ايام|أسبوع|اسبوع|شهر|(?:^|\s)\d{1,2}\s*(?:m|h|d|w|mins?|hrs?)(?:\s|$)|يناير|فبراير|مارس|أبريل|ابريل|مايو|يونيو|يوليو|أغسطس|اغسطس|سبتمبر|أكتوبر|اكتوبر|نوفمبر|ديسمبر)/i;

let sentHashes=JSON.parse(localStorage.getItem("gamal_fb_sent_v160")||"[]");
let feedIdx=parseInt(localStorage.getItem("gamal_fb_fidx_v160")||"0",10)%FEEDS.length;
let runStartTs=parseInt(sessionStorage.getItem("gamal_fb_run_ts_v160")||String(Date.now()),10);
sessionStorage.setItem("gamal_fb_run_ts_v160",String(runStartTs));
let scannedCount=parseInt(sessionStorage.getItem("gamal_fb_sc_v160")||"0",10);
let acceptedCount=parseInt(sessionStorage.getItem("gamal_fb_ac_v160")||"0",10);
let pageLoadTs=Date.now(),consecutiveSeen=0,isResting=false;
let lastLogMsg="يرسل إعلانات (من المالك) لغرفة موافقتك الخاصة + جاهز لسحب أي رابط...";
let shadowInfo=null;
try{
const host=document.createElement("span"),sh=host.attachShadow({mode:"closed"}),box=document.createElement("div");
box.style.cssText="position:fixed;bottom:10px;left:10px;z-index:2147483647;background:#0f172a;color:#e2e8f0;padding:10px 14px;border-radius:10px;font-family:Tahoma,sans-serif;font-size:12px;border:1px solid #10b981;box-shadow:0 4px 16px rgba(0,0,0,0.65);direction:rtl;max-width:460px;line-height:1.6;";
sh.appendChild(box);document.documentElement.appendChild(host);shadowInfo=box;
box.addEventListener("click",e=>{
if(e.target&&e.target.id==="g_flush_btn"){
e.target.innerText="جاري الإرسال للوحة موافقتك...";
chrome.runtime.sendMessage({type:"FB_FLUSH_BATCH"},()=>{e.target.innerText="تم الإرسال للوحة موافقتك!";});
}
});
}catch(e){}

function updateUI(st){
try{
sessionStorage.setItem("gamal_fb_sc_v160",String(scannedCount));
sessionStorage.setItem("gamal_fb_ac_v160",String(acceptedCount));
const remMin=Math.max(0,Math.ceil((RUN_MS-(Date.now()-runStartTs))/60000));
document.title="[فحص:"+scannedCount+" | بانتظار موافقتك:"+acceptedCount+"] "+st;
if(shadowInfo){
const curN=FEEDS[feedIdx]?FEEDS[feedIdx].name:"الصفحة الرئيسية";
shadowInfo.innerHTML="<div><b>رادار غرفة الموافقة وسحب الروابط v16.0</b> | "+st+"</div><div style='color:#38bdf8;'>الوضع: <b>"+curN+"</b> (باقي للرفع: "+remMin+" د) <button id='g_flush_btn' style='background:#10b981;color:#000;border:none;border-radius:5px;padding:2px 8px;cursor:pointer;font-weight:bold;margin-right:6px;'>إرسال للوحة الموافقة الآن</button></div><div>تم فحص: <b>"+scannedCount+"</b> | أُرسل لغرفة موافقتك (مع لايك): <b style='color:#4ade80;'>"+acceptedCount+"</b></div><div style='color:#cbd5e1;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"+lastLogMsg+"</div>";
}
}catch(e){}
}
function saveHash(h){if(!sentHashes.includes(h)){sentHashes.push(h);if(sentHashes.length>3500)sentHashes=sentHashes.slice(-3500);localStorage.setItem("gamal_fb_sent_v160",JSON.stringify(sentHashes));}}
function hashStr(s){let h=0;for(let i=0;i<s.length;i++)h=((h<<5)-h)+s.charCodeAt(i)|0;return"fb_"+Math.abs(h);}

function cleanProfileHref(rawHref){
try{
const u=new URL(rawHref);
if(u.pathname==="/profile.php"&&u.searchParams.get("id"))return"https://www.facebook.com/profile.php?id="+u.searchParams.get("id");
return u.origin+u.pathname.replace(/\/+$/,"")+"/";
}catch(e){return"";}
}

function pressLikeOnOwnerCard(card){
try{
const btns=card.querySelectorAll('div[role="button"],span[role="button"]');
for(const b of btns){
if(b.closest("ul")||b.closest("form"))continue;
const ar=(b.getAttribute("aria-label")||"").trim(),tx=(b.innerText||"").trim();
if(b.getAttribute("aria-pressed")==="true")return;
if(ar==="أعجبني"||ar==="Like"||tx==="أعجبني"||tx==="Like"){b.click();return;}
}
}catch(e){}
}

async function expandAllSeeMoreInViewport(){
const btns=document.querySelectorAll('div[role="button"],span[role="button"]');
let clicked=0;
for(const b of btns){
if(b._gExp||b.closest("ul")||b.closest("form"))continue;
const r=b.getBoundingClientRect();
if(r.top<-200||r.top>window.innerHeight+300)continue;
const bt=(b.innerText||"").trim();
if(bt==="عرض المزيد"||bt==="See more"||bt==="… عرض المزيد"){
b._gExp=true;
try{b.click();clicked++;}catch(e){}
}
}
if(clicked>0)await slp(450);
}

function collectCards(){
const cSet=new Set();
const nodes=document.querySelectorAll('div[data-ad-preview="message"],div[data-ad-comet-preview="message"],div[data-ad-rendering-role="story_message"],div[dir="auto"]');
nodes.forEach(node=>{
if(node.closest("ul")||node.closest("form")||node.closest("nav"))return;
const txt=normD((node.innerText||"").trim());
if(txt.length<22||G_NOISE.test(txt))return;
if(!node.hasAttribute("data-ad-preview")&&!node.hasAttribute("data-ad-comet-preview")&&!node.hasAttribute("data-ad-rendering-role")){
if(!STRICT_OWNER_RE.test(txt))return;
}
let cur=node,best=null;
for(let i=0;i<12;i++){
if(!cur.parentElement)break;
cur=cur.parentElement;
const cT=(cur.innerText||"");if(cT.length>5200)break;
const lC=cur.querySelectorAll("a[href]").length;
const hasH=!!cur.querySelector('h2,h3,h4,a[href*="/posts/"],a[href*="/permalink/"],a[href*="story_fbid"],a[href*="/groups/"],a[href*="/user/"],a[href*="/photo"]');
if(cT.length>=55&&lC>=1&&hasH){best=cur;break;}
if(!best&&cT.length>=55&&lC>=1)best=cur;
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
shareBtn.click();await slp(580);
const menuItems=document.querySelectorAll('div[role="menuitem"],div[role="button"],span');
for(const mi of menuItems){
const mt=(mi.innerText||"").trim();
if(mt==="نسخ الرابط"||mt==="Copy link"){mi.click();await slp(260);break;}
}
const copied=document.documentElement.getAttribute("data-g-copied-url")||"";
if(copied&&copied.includes("facebook.com/"))return copied;
}catch(e){}
return"";
}

function extractBestBodyText(card){
const msgNode=card.querySelector('div[data-ad-preview="message"],div[data-ad-comet-preview="message"],div[data-ad-rendering-role="story_message"]');
const fMsg=(card.getAttribute("data-g-puremsg")||"").trim();
if(msgNode){
const mTxt=(msgNode.innerText||"").trim();
return normD(mTxt.length>=fMsg.length?mTxt:fMsg);
}
let bestDir="";
card.querySelectorAll('div[dir="auto"]').forEach(d=>{
if(d.closest("ul")||d.closest("form"))return;
const t=(d.innerText||"").trim();
if(t.length>bestDir.length&&t.length<3500)bestDir=t;
});
return normD(bestDir||fMsg||(card.innerText||"").trim());
}

async function inspectCandidateCard(card){
const moreBtns=card.querySelectorAll('div[role="button"],span[role="button"]');
for(const b of moreBtns){
const bt=(b.innerText||"").trim();
if((bt==="عرض المزيد"||bt==="See more"||bt.includes("عرض المزيد"))&&!b.closest("ul")&&!b.closest("form")){
try{b.click();await slp(450);}catch(e){}
break;
}
}
card.setAttribute("data-g-inspect-req","1");
window.dispatchEvent(new CustomEvent("gamal_fiber_scan"));
await slp(90);

let bodyText=extractBestBodyText(card);
if(bodyText.length<22||G_NOISE.test(bodyText))return null;

const hasExplicitOwner=STRICT_OWNER_RE.test(bodyText);
const hasPropWord=REAL_PROP_RE.test(bodyText);
if(!hasExplicitOwner||!hasPropWord){
if(!card._gS){
card._gS=true;scannedCount++;
lastLogMsg="تخطي (بدون المالك مباشر): "+bodyText.replace(/\s+/g," ").substring(0,38);
updateUI("يفحص الصفحة الرئيسية");
}
return null;
}

const keyHash=hashStr(bodyText.replace(/\s+/g," ").substring(0,90));
if(sentHashes.includes(keyHash)){
if(!card._gS){card._gS=true;consecutiveSeen++;}
return null;
}

const topLines=(card.innerText||"").split("\n").slice(0,7).map(x=>x.trim()).filter(Boolean);
const cardHeaderBlob=topLines.join(" ");
if(SPONSORED_RE.test(cardHeaderBlob)||BRK_FAST_RE.test(bodyText)){
card._gS=true;saveHash(keyHash);scannedCount++;
lastLogMsg="تخطي سمسار/ممول: "+bodyText.replace(/\s+/g," ").substring(0,36);
updateUI("يفحص الصفحة الرئيسية");
return null;
}

card.querySelectorAll("a,span[role='link']").forEach(a=>{
try{
a.dispatchEvent(new PointerEvent("pointerenter",{bubbles:true}));
a.dispatchEvent(new PointerEvent("pointerover",{bubbles:true}));
a.dispatchEvent(new MouseEvent("mouseover",{bubbles:true}));
a.dispatchEvent(new MouseEvent("mousedown",{bubbles:true}));
if(a.focus)a.focus({preventScroll:true});
}catch(e){}
});
await slp(150);
card.setAttribute("data-g-inspect-req","1");
window.dispatchEvent(new CustomEvent("gamal_fiber_scan"));
await slp(70);

let postUrl=card.getAttribute("data-g-permalink")||"",fiberCtime=parseInt(card.getAttribute("data-g-ctime")||"0",10)||0;
let fiberAuthor=(card.getAttribute("data-g-author")||"").trim(),groupId=(card.getAttribute("data-g-groupid")||"").trim();
let mediaPostId="",photoUrl="",groupName="",headerTimeHint="",authorFromLink="",groupProfileUrl="";

const msgNodeNow=card.querySelector('div[data-ad-preview="message"],div[data-ad-comet-preview="message"],div[data-ad-rendering-role="story_message"]');
card.querySelectorAll("a[href],abbr,span[aria-label]").forEach(a=>{
if(msgNodeNow&&msgNodeNow.contains(a))return;
const href=a.href||"",rawL=(a.innerText||"")+" "+(a.getAttribute("aria-label")||"");
const aTxt=normD(rawL).trim(),fLine=(a.innerText||"").split("\n")[0].trim();
if(G_NOISE.test(fLine))return;
const mG=href.match(/facebook\.com\/groups\/([^/?&#]+)/);if(mG&&mG[1]!=="feed"&&mG[1]!=="discover"&&!groupId)groupId=mG[1];
const mGm=href.match(/set=(?:gm|pcb)\.(\d{8,25})/);if(mGm&&!mediaPostId)mediaPostId=mGm[1];
const mId=href.match(/idorvanity=([^&]+)/);if(mId&&!groupId)groupId=mId[1];

if(href&&href.includes("/groups/")&&href.includes("/user/")){
if(!groupProfileUrl)groupProfileUrl=cleanProfileHref(href);
if(fLine.length>=2&&fLine.length<=42&&!G_WORDS.test(fLine)&&!authorFromLink)authorFromLink=fLine;
}else if(href&&href.includes("/groups/")&&!href.includes("/user/")&&!href.includes("/posts/")&&!href.includes("/permalink/")&&!href.includes("story_fbid=")){
if(fLine.length>=3&&fLine.length<=85&&!groupName)groupName=fLine;
}else if(href&&(href.includes("/user/")||href.includes("profile.php")||(!href.includes("/groups/")&&!href.includes("/posts/")&&!href.includes("/hashtag/")&&!href.includes("/photo")))){
if(fLine.length>=2&&fLine.length<=42&&!G_WORDS.test(fLine)&&fLine!==groupName){
if(!authorFromLink)authorFromLink=fLine;
if(!groupProfileUrl)groupProfileUrl=cleanProfileHref(href);
}
}
if(href&&!postUrl&&(href.includes("/posts/")||href.includes("/permalink/")||href.includes("story_fbid=")||href.includes("multi_permalinks="))){
postUrl=(href.includes("story_fbid=")||href.includes("multi_permalinks="))?href:href.split("?")[0];
}
if(href&&!photoUrl&&(href.includes("/photo/?")||href.includes("/photo.php?")))photoUrl=href;
if(!headerTimeHint&&aTxt&&aTxt.length<=42&&TIME_RE.test(aTxt))headerTimeHint=aTxt;
});

if(!postUrl&&groupId&&mediaPostId)postUrl="https://www.facebook.com/groups/"+groupId+"/permalink/"+mediaPostId+"/";
else if(!postUrl&&mediaPostId)postUrl="https://www.facebook.com/permalink.php?story_fbid="+mediaPostId;
if(!postUrl){
updateUI("ينسخ رابط البوست من زر (مشاركة -> نسخ الرابط)...");
const copiedLink=await clickShareAndCopyLink(card);
if(copiedLink)postUrl=copiedLink;
}
if(!postUrl&&photoUrl)postUrl=photoUrl;
if(!postUrl&&groupProfileUrl)postUrl=groupProfileUrl;
if(!postUrl&&groupId)postUrl="https://www.facebook.com/groups/"+groupId+"/search/?q="+encodeURIComponent(bodyText.substring(0,35));

const isAnonCard=cardHeaderBlob.includes("مجهول الهوية")||cardHeaderBlob.toLowerCase().includes("anonymous");
let authorName=isAnonCard?"مشارك مجهول الهوية":(fiberAuthor||authorFromLink||"مالك مباشر");
for(const ln of topLines){
const nl=normD(ln);
if(!headerTimeHint&&nl.length<=35&&TIME_RE.test(nl))headerTimeHint=nl;
if(ln.includes("مجهول الهوية")||ln.toLowerCase().includes("anonymous")){authorName="مشارك مجهول الهوية";break;}
}
if(groupName&&bodyText.startsWith(groupName))bodyText=bodyText.substring(groupName.length).trim();

return{hash:keyHash,url:postUrl,fiber_ctime:fiberCtime,author:authorName,profile_ads_count:1,group_id:groupId,group_name:groupName,header_time:headerTimeHint||normD(topLines.join(" | ")),text:bodyText.substring(0,2600)};
}

function sendBridge(d){
return new Promise(res=>{
try{chrome.runtime.sendMessage({type:"FB_POST_INGEST",payload:d},r=>res(r||{ok:false,accepted:false,reason:"No response"}));}
catch(e){res({ok:false,accepted:false,reason:String(e)});}
});
}

async function scanVisible(){
await expandAllSeeMoreInViewport();
const cards=collectCards();
for(const card of cards){
if(card._gS)continue;
const data=await inspectCandidateCard(card);
if(!data)continue;
consecutiveSeen=0;card._gS=true;scannedCount++;
const prv=data.text.replace(/\s+/g," ").substring(0,42);
const resp=await sendBridge(data);
if(resp&&resp.accepted){
saveHash(data.hash);
acceptedCount++;pressLikeOnOwnerCard(card);
lastLogMsg="أُرسل لغرفة موافقتك + لايك ("+data.author+"): "+prv;
}else{
saveHash(data.hash);
lastLogMsg="مرفوض ("+((resp&&resp.reason)||"فلتر")+"): "+prv;
}
updateUI("يرسل الملاك لغرفة موافقتك");
}
}

function startRestCycle(){
isResting=true;
updateUI("انتهت الرن (45د) -> جاري رفع الدفعة للوحة موافقتك...");
try{chrome.runtime.sendMessage({type:"FB_FLUSH_BATCH"},()=>{});}catch(e){}
let rSec=REST_SEC;
const iv=setInterval(()=>{
rSec-=5;
updateUI("تم الرفع للوحة الموافقة! استراحة 30 دقيقة ("+Math.ceil(Math.max(0,rSec)/60)+" د متبقية ثم Refresh)");
if(rSec<=0){clearInterval(iv);sessionStorage.setItem("gamal_fb_run_ts_v160",String(Date.now()));location.href=FEEDS[0].url;}
},5000);
}

async function loop(){
if(isResting)return;
if(location.pathname.startsWith("/search/")||location.pathname.startsWith("/groups/feed")){location.href=FEEDS[0].url;return;}
if(Date.now()-runStartTs>=RUN_MS){startRestCycle();return;}
if(Date.now()-pageLoadTs>=SWITCH_MS||consecutiveSeen>=24){
feedIdx=(feedIdx+1)%FEEDS.length;localStorage.setItem("gamal_fb_fidx_v160",String(feedIdx));
updateUI("تحديث الصفحة الرئيسية لجلب أحدث الإعلانات...");location.href=FEEDS[feedIdx].url;return;
}
await scanVisible();
window.scrollBy({top:Math.floor(400+Math.random()*140),behavior:"smooth"});
updateUI("فحص مباشر للصفحة الرئيسية");
setTimeout(loop,Math.floor(1750+Math.random()*450));
}
updateUI("بدأ رادار غرفة الموافقة وسحب الروابط v16.0...");
setTimeout(loop,900);
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
    return {"phones": {}, "authors": {}, "seen_hashes": [], "rejected_ids": []}

def save_fb_memory(mem):
    try:
        mem["seen_hashes"] = mem.get("seen_hashes", [])[-4000:]
        mem["rejected_ids"] = mem.get("rejected_ids", [])[-4000:]
        with open(FB_MEMORY_FILE, "w", encoding="utf-8") as f: json.dump(mem, f, ensure_ascii=False)
    except Exception: pass

def load_pending_fb_ads():
    if os.path.exists(FB_PENDING_FILE):
        try:
            with open(FB_PENDING_FILE, "r", encoding="utf-8") as f:
                arr = json.load(f)
                if isinstance(arr, list): return arr
        except Exception: pass
    return []

def save_pending_fb_ads(arr):
    try:
        with open(FB_PENDING_FILE, "w", encoding="utf-8") as f:
            json.dump(arr[:150], f, ensure_ascii=False, indent=2)
    except Exception: pass

def is_company_name(name):
    norm = normalize_ar(name)
    if not norm or norm.startswith(normalize_ar("مالك مباشر")) or "مجهول" in norm: return False
    for bw in BROKER_NAME_WORDS:
        nk = normalize_ar(bw)
        if (len(nk) <= 3 and re.search(rf'\b{re.escape(nk)}\b', norm)) or (len(nk) > 3 and nk in norm): return True
    return False

def clean_publisher_name(name):
    default_lbl = "مالك مباشر"
    if not name: return default_lbl
    s = strip_bidi(re.sub(r'<[^>]+>', ' ', str(name)))
    s = re.sub(r'(?:تواصل\s*مع\s*المعلن|اتصل\s*لمعرفه\s*السعر|اتصل\s*لمعرفة\s*السعر|عضو\s*منذ.*|الإعلانات\s*النشطة.*|\(\d+.*?\)|\d+\s*عقار.*|عقار\s*واحد|عقارين|اتصال|اتصل|واتساب|رسالة|Avatar|الصورة\s*الشخصية|user\s*logo|ملاحظة|حفظ|مشاركة|شارك|إبلاغ|تابِع|تابع|التقييم.*)', ' ', s, flags=re.I)
    s = re.sub(r'\s+', ' ', s).strip(" -_|:,><.★⭐•·+")
    norm_s = normalize_ar(s)
    if any(w in norm_s for w in ("اتصل", "لمعرفه", "السعر", "تواصل", "المعلن", "ملاحظه", "مشاركه", "ابلاغ", "تسجيل", "دخول", "شركات", "موثوقه", "جروب", "مجموعه", "عقارات التجمع", "شقق التجمع")): return default_lbl
    return default_lbl if (not s or len(s) < 2 or len(s) > 38 or re.search(r'[<>{}\[\]=/\\0-9]{4,}', s)) else s

def detect_zone(title, body_text):
    core = normalize_ar(re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', f"{title} {body_text[:2000]}"))
    for city in EXCLUDED_CITIES:
        if normalize_ar(city) in core: return None
    for z_name, keywords in ZONES:
        for kw in keywords:
            if normalize_ar(kw) in core: return z_name
    return "القاهرة الجديدة"

def is_strict_cash_sale(title, desc_text, price_num):
    if int(price_num or 0) < MIN_CASH_SALE_PRICE: return False
    full_text = normalize_ar(re.sub(r'بدروم|البدروم|بدرون', 'طابق سفلي', f"{title} {desc_text[:3000]}"))
    for neg in SAFE_CASH_NEGATIONS: full_text = full_text.replace(normalize_ar(neg), " ")
    for kw in INSTALLMENT_SUBSTRINGS:
        if normalize_ar(kw) in full_text: return False
    return not bool(re.search(r'\b\d+\s*%\s*(?:مقدم|تعاقد|دفعه|down)', full_text))

def has_broker_copywriting(title, desc_text):
    norm_body = normalize_ar(f"{title} {desc_text[:3500]}")
    for safe_neg in SAFE_OWNER_BROKER_NEGATIONS: norm_body = norm_body.replace(normalize_ar(safe_neg), " ")
    for bp in BROKER_TEXT_PHRASES:
        if normalize_ar(bp) in norm_body: return True, f"Broker Phrase ({bp})"
    if re.search(r'(?:code|كود)\s*[:\-]?\s*[a-z]{0,3}\d{2,7}\b', norm_body, re.I) or re.search(r'\bmsr\d{2,5}\b', norm_body, re.I):
        return True, "Broker Inventory Code"
    return False, ""

def is_verified_fb_owner_post(norm_pure_text):
    if any(k in norm_pure_text for k in ("ضمن الاعضاء", "اصدقاء ضمن الاعضاء", "مجموعه عامه", "مجموعه خاصه", "ادفع بفاليو", "تاكي")):
        return False, "كارت جروب أو إعلان ممول"
    if not re.search(r'(?:شقه|فيلا|فيله|فيلات|دوبلكس|بنتهاوس|ستوديو|استوديو|رووف|روف|تاون\s*هاوس|توين\s*هاوس|شاليه|عماره|محل|مكتب|عياده|للايجار|للبيع|ايجار|تمليك)', norm_pure_text):
        return False, "ليس عقاراً"
    strict_owner_re = r'(?:من\s*المالكه?|المالكه?\s*مباشره?|للمالكه?\s*مباشره?|انا\s*المالكه?|مالكه?\s*(?:اصلي|العقار|الشقه|الفيلا|مباشره?)|شقتي|فيلتي|بيتي|ملكي)'
    if re.search(strict_owner_re, norm_pure_text): return True, "مكتوب من المالك/المالكة صراحة"
    return False, "غير مكتوب فيه من المالك"

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
    m_hr = re.search(r'(\d{1,2})\s*(?:ساعه|ساعات|س(?:\s|$)|h(?:\s|$)|hrs?)', norm_h)
    if m_hr:
        hrs = int(m_hr.group(1))
        return (False, f"Old FB Hours ({hrs}h)", "", True) if hrs > 48 else (True, "OK", f"منذ {hrs} س", False)
    return True, "OK", "اليوم", False

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
    if any(k in norm_t for k in ("فيلا", "فيله", "تاون هاوس", "توين هاوس", "ستاند الون")): return "فلل"
    if any(k in norm_t for k in ("شقه", "دوبلكس", "بنتهاوس", "ستوديو", "استوديو", "رووف", "روف")): return "شقق"
    if any(k in norm_t for k in ("محل", "مكتب", "عياده", "مقر اداري", "تجاري", "صيدليه")): return "تجاري"
    if any(k in norm_t for k in ("قطعه ارض", "ارض للبيع", "عماره كامله", "مبني كامل")): return "أراضي"
    return "شقق"

def build_fb_ad_object(pure_raw_text, group_name, author_raw, post_url, orig_age_hint="اليوم", is_direct_admin=False):
    norm_t = normalize_ar(pure_raw_text)
    phones = list(set(re.findall(r'\b01[0125]\d{8}\b', re.sub(r'[\s\-]', '', pure_raw_text))))
    is_anon = ("مجهول" in author_raw or "anonymous" in author_raw.lower())
    pub_name = "مشارك مجهول الهوية" if is_anon else clean_publisher_name(author_raw)
    zone = detect_zone("", pure_raw_text) or "التجمع الخامس"
    if zone == "القاهرة الجديدة":
        cz = detect_zone("", group_name)
        zone = cz if (cz and cz != "القاهرة الجديدة") else "التجمع الخامس"
    is_rent = any(k in norm_t for k in ("للايجار", "ايجار", "تاجير", "مفروش", "شهريا", "في الشهر"))
    deal, cat = ("إيجار" if is_rent else "تمليك"), classify_fb_category(norm_t)
    price_num, price_str, _ = parse_facebook_colloquial_price(pure_raw_text, deal)
    area_m = re.search(r'(\d{2,4})\s*(?:متر|م2|م²|\bم\b)', norm_t)
    area_val = int(area_m.group(1)) if (area_m and 25 <= int(area_m.group(1)) <= 5000) else None
    clean_lines = [ln.strip() for ln in pure_raw_text.split("\n") if ln.strip() and ln.strip() != group_name and "ضمن الأعضاء" not in ln]
    first_line = (clean_lines[0] if clean_lines else pure_raw_text)[:85]
    title = first_line if len(first_line) >= 10 else f"{cat} ({deal}) في {zone} - {pub_name}"
    rooms_val = parse_rooms_ar(norm_t)
    now_dt = datetime.now(CAIRO_TZ)
    entry_ts = int(now_dt.timestamp())
    entry_age_label = f"سحب فوري {now_dt.strftime('%I:%M %p')}" if is_direct_admin else (f"دخل الرادار {now_dt.strftime('%I:%M %p')}" + (f" (نُشر {orig_age_hint})" if orig_age_hint else ""))
    uid = int("93" + str(abs(hash((norm_t[:75] or post_url))) % 1000000000))
    phone_note = f" | ت: {phones[0]}" if phones else ""
    return {
        "ad_id": uid, "id": f"fb_{uid}", "source": "فيسبوك", "title": title, "price": price_str, "price_num": price_num,
        "zone": zone, "location": zone, "cat": cat, "category": cat, "deal": deal, "type": deal, "area": area_val, "rooms": rooms_val,
        "publisher": pub_name + phone_note, "pub_ads": 1, "active_ads_count": 1, "age": entry_age_label, "fresh_tier": 3,
        "description": pure_raw_text[:650], "first_seen_ts": entry_ts, "timestamp": entry_ts, "desc_verified_v2": True,
        "verified_24h_v93": True, "verified_fb_v160": True, "url": post_url, "link": post_url, "verified_v12": True,
        "scraped_at": now_dt.strftime("%Y-%m-%d %I:%M %p"), "date": now_dt.strftime("%Y-%m-%d %H:%M")
    }

def process_direct_pulled_facebook_post(payload):
    pure_raw_text = strip_bidi(payload.get("text") or "").strip()
    group_name = strip_bidi(payload.get("group_name") or "").strip()
    author_raw = strip_bidi(payload.get("author") or "مالك مباشر").strip()
    post_url = (payload.get("url") or "").strip()
    if not pure_raw_text or len(pure_raw_text) < 10:
        pure_raw_text = f"إعلان مالك مباشر تم سحبه بالرابط من فيسبوك - {post_url}"
    fb_ad = build_fb_ad_object(pure_raw_text, group_name, author_raw, post_url, is_direct_admin=True)
    with SYNC_LOCK:
        extra_live = load_extra_live_backup()
        extra_live = [a for a in extra_live if int(a.get("ad_id") or 0) != fb_ad["ad_id"]]
        extra_live.insert(0, fb_ad)
        save_extra_live_backup(extra_live)
        print(f"\n  >>> [DIRECT LINK PULLED & PUBLISHED LIVE] {fb_ad['title'][:55]} | {fb_ad['zone']} <<<")
        guard_extra_ads_during_sleep(force_push=True)
    return True

def process_facebook_post_payload(payload):
    global FB_PENDING_BATCH_COUNT
    pure_raw_text = strip_bidi(payload.get("text") or "").strip()
    group_name = strip_bidi(payload.get("group_name") or "").strip()
    group_id = strip_bidi(payload.get("group_id") or "").strip()
    author_raw = strip_bidi(payload.get("author") or "مشارك مجهول الهوية").strip()
    header_time = strip_bidi(payload.get("header_time") or "")
    fiber_ctime = int(payload.get("fiber_ctime") or 0)
    post_url = (payload.get("url") or "").strip()
    post_hash = payload.get("hash") or ""
    if group_name: pure_raw_text = pure_raw_text.replace(group_name, " ").strip()
    short_preview = re.sub(r'\s+', ' ', pure_raw_text)[:55]
    if len(pure_raw_text) < 22: return False, "نص قصير", False

    norm_t = normalize_ar(pure_raw_text)
    is_true_owner, owner_proof_label = is_verified_fb_owner_post(norm_t)
    if not is_true_owner: return False, owner_proof_label, False

    mem = load_fb_memory()
    is_fresh, time_reason, orig_age_hint, is_explicit_old = parse_fb_strict_2days_header_time(header_time, fiber_ctime)
    if not is_fresh: return False, "منشور قديم (>يومين)", is_explicit_old

    if not is_direct_fb_post_permalink(post_url):
        q_enc = urllib.parse.quote(pure_raw_text[:35])
        post_url = f"https://www.facebook.com/groups/{group_id}/search/?q={q_enc}" if group_id else f"https://www.facebook.com/search/posts/?q={q_enc}"

    for wp in FB_WANTED_PHRASES:
        if normalize_ar(wp) in norm_t[:180]: return False, "طلب وليس عرض", False

    phones = list(set(re.findall(r'\b01[0125]\d{8}\b', re.sub(r'[\s\-]', '', pure_raw_text))))
    for ph in phones:
        ph_posts = mem.setdefault("phones", {}).setdefault(ph, [])
        if post_hash and post_hash not in ph_posts: ph_posts.append(post_hash)
    save_fb_memory(mem)

    if len(phones) >= 3: return False, "أرقام مبيعات متعددة", False
    for ph in phones:
        if len(mem.get("phones", {}).get(ph, [])) > 3: return False, "رقم مكرر لسمسار", False
    is_anon = ("مجهول" in author_raw or "anonymous" in author_raw.lower())
    pub_name = "مشارك مجهول الهوية" if is_anon else clean_publisher_name(author_raw)
    if not is_anon and pub_name != "مالك مباشر" and is_company_name(pub_name): return False, "حساب شركة/سمسار", False
    if re.search(r'(?:للايجار\s*اليومي|ايجار\s*يومي|شقه\s*فندقيه|شقق\s*فندقيه|اسبوعي)', norm_t): return False, "إيجار يومي/فندقي", False

    is_brk, brk_reason = has_broker_copywriting("", pure_raw_text)
    if is_brk: return False, "صيغة سمسار", False

    zone = detect_zone("", pure_raw_text)
    if not zone: return False, "مدينة مستبعدة", False
    if zone == "القاهرة الجديدة":
        context_zone = detect_zone("", group_name)
        if not context_zone: return False, "مدينة مستبعدة", False

    fb_ad = build_fb_ad_object(pure_raw_text, group_name, author_raw, post_url, orig_age_hint=orig_age_hint, is_direct_admin=False)
    if fb_ad["deal"] != "إيجار" and not is_strict_cash_sale("", pure_raw_text, fb_ad["price_num"]):
        return False, "تقسيط/مقدم", False
    if fb_ad["ad_id"] in mem.get("rejected_ids", []):
        return False, "مرفوض سابقا من المدير", False

    with SYNC_LOCK:
        pending_list = load_pending_fb_ads()
        existing_live_ids = {int(a.get("ad_id") or 0) for a in load_extra_live_backup()}
        if fb_ad["ad_id"] in existing_live_ids or any(int(p.get("ad_id") or 0) == fb_ad["ad_id"] for p in pending_list):
            return False, "موجود بالفعل", False
        pending_list.insert(0, fb_ad)
        save_pending_fb_ads(pending_list)
        FB_PENDING_BATCH_COUNT += 1
        print(f"\n  >>> [FB QUEUED FOR YOUR APPROVAL #{FB_PENDING_BATCH_COUNT}] ({fb_ad['age']}) | {fb_ad['publisher']} | {fb_ad['zone']} <<<")
    return True, "OK", False

class FacebookIngestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    def handle(self):
        try: super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError): pass
    def _send_cors(self, code=200):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "application/json")
        self.end_headers()
    def do_OPTIONS(self): self._send_cors(200)
    def do_GET(self):
        if self.path == "/fb_poll_task":
            self._send_cors(200)
            url_task = DIRECT_PULL_QUEUE.pop(0) if DIRECT_PULL_QUEUE else ""
            self.wfile.write(json.dumps({"url": url_task}).encode("utf-8"))
            return
        self._send_cors(404)
    def do_POST(self):
        global FB_PENDING_BATCH_COUNT
        if self.path == "/fb_flush":
            with SYNC_LOCK:
                print(f"\n  >>> [FB APPROVAL QUEUE SYNC] Pushing ({len(load_pending_fb_ads())} pending ads) to Admin Panel... <<<")
                guard_extra_ads_during_sleep(force_push=True)
                FB_PENDING_BATCH_COUNT = 0
            self._send_cors(200)
            self.wfile.write(b'{"ok":true}')
            return
        if self.path == "/fb_direct_ingest":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8", errors="replace"))
                process_direct_pulled_facebook_post(payload)
            except Exception: pass
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

def handle_remote_admin_command(cmd_text):
    cmd = str(cmd_text or "").strip()
    if cmd.startswith("PULL_URL|"):
        u = cmd.split("|", 1)[1].strip()
        if "facebook.com" in u and u not in DIRECT_PULL_QUEUE:
            DIRECT_PULL_QUEUE.append(u)
            print(f"\n  >>> [ADMIN PHONE COMMAND] Received Facebook Link to Pull Live: {u} <<<")
    elif cmd.startswith("APPROVE|"):
        aid_str = cmd.split("|", 1)[1].strip()
        with SYNC_LOCK:
            pending = load_pending_fb_ads()
            extra_live = load_extra_live_backup()
            approved_count = 0
            rem_pending = []
            for p in pending:
                if aid_str == "ALL" or str(p.get("ad_id")) == aid_str:
                    p["verified_fb_v160"] = True
                    extra_live.insert(0, p)
                    approved_count += 1
                else:
                    rem_pending.append(p)
            if approved_count > 0:
                save_pending_fb_ads(rem_pending)
                save_extra_live_backup(extra_live)
                print(f"\n  >>> [ADMIN APPROVED] Published +{approved_count} ad(s) from Pending Queue to Main Website! <<<")
                guard_extra_ads_during_sleep(force_push=True)
    elif cmd.startswith("REJECT|"):
        aid_str = cmd.split("|", 1)[1].strip()
        with SYNC_LOCK:
            pending = load_pending_fb_ads()
            mem = load_fb_memory()
            rem_pending = []
            rejected_count = 0
            for p in pending:
                if aid_str == "ALL" or str(p.get("ad_id")) == aid_str:
                    mem.setdefault("rejected_ids", []).append(int(p.get("ad_id") or 0))
                    rejected_count += 1
                else:
                    rem_pending.append(p)
            if rejected_count > 0:
                save_fb_memory(mem)
                save_pending_fb_ads(rem_pending)
                print(f"\n  >>> [ADMIN REJECTED] Deleted {rejected_count} ad(s) from Pending Queue! <<<")
                guard_extra_ads_during_sleep(force_push=True)

def start_admin_command_listener():
    def _poll():
        init_done = False
        while True:
            try:
                since_p = "10s" if init_done else "30m"
                r = std_requests.get(f"https://ntfy.sh/{ADMIN_CMD_TOPIC}/json?poll=1&since={since_p}", timeout=12)
                if r.status_code == 200:
                    for line in r.text.strip().splitlines():
                        if not line: continue
                        obj = json.loads(line)
                        cid, msg = obj.get("id"), obj.get("message", "")
                        if cid and cid not in PROCESSED_CMD_IDS:
                            PROCESSED_CMD_IDS.add(cid)
                            if init_done or msg.startswith(("APPROVE|", "REJECT|", "PULL_URL|")):
                                handle_remote_admin_command(msg)
                init_done = True
            except Exception: pass
            time.sleep(3)
    threading.Thread(target=_poll, daemon=True).start()

def start_fb_local_server():
    def _serve():
        try:
            srv = HTTPServer(("127.0.0.1", FB_PORT), FacebookIngestHandler)
            print(f"[Facebook Approval Queue & Link Puller v16.0] Listening on http://127.0.0.1:{FB_PORT}")
            srv.serve_forever()
        except Exception as e: print(f"[FB Receiver Notice] {e}")
    threading.Thread(target=_serve, daemon=True).start()

def a_u(ad): return ad.get("url") or ad.get("link") or ""

def is_valid_existing_extra_ad(ad):
    src = ad.get("source") or "دوبيزل"
    if src in ("دوبيزل", "عقارماب"): return True
    u = str(a_u(ad))
    if src != "فيسبوك" or not ad.get("verified_fb_v160") or not is_direct_fb_post_permalink(u): return False
    now_ts = int(datetime.now(CAIRO_TZ).timestamp())
    ad_ts = int(ad.get("first_seen_ts") or ad.get("timestamp") or 0)
    if ad_ts <= 0 or (now_ts - ad_ts) > ((MAX_AGE_DAYS + 1) * 86400): return False
    return True

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

def guard_extra_ads_during_sleep(force_push=False):
    extra_backup = load_extra_live_backup()
    save_extra_live_backup(extra_backup)
    pending_list = load_pending_fb_ads()
    if not os.path.exists(DATA_FILE): return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: d = json.load(f)
        if not isinstance(d, dict) or not isinstance(d.get("ads"), list): return
        cur_ads = d["ads"]
        has_invalid_fb = any(a.get("source") == "فيسبوك" and not is_valid_existing_extra_ad(a) for a in cur_ads)
        cur_ids = {a.get("ad_id") for a in cur_ads if a.get("source") in ("عقارماب", "فيسبوك") and is_valid_existing_extra_ad(a)}
        bak_ids = {a.get("ad_id") for a in extra_backup}
        if force_push or has_invalid_fb or not bak_ids.issubset(cur_ids):
            merged, seen_u = [], set()
            for ad in (extra_backup + [a for a in cur_ads if is_valid_existing_extra_ad(a)]):
                u = str(ad.get("ad_id") or a_u(ad))
                tk = normalize_ar((ad.get("description") or ad.get("title") or "")[:70]) if ad.get("source") == "فيسبوك" else u
                if not u or u in seen_u or tk in seen_u: continue
                seen_u.add(u); seen_u.add(tk); merged.append(ad)
            merged.sort(key=lambda x: (int(x.get("first_seen_ts") or 0), int(x.get("ad_id") or 0)), reverse=True)
            d["ads"], d["total"] = merged[:450], len(merged[:450])
            d["pending_ads"] = pending_list[:150]
            d["updated_at"] = datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %I:%M %p")
            aq_c = sum(1 for a in d["ads"] if a.get("source") == "عقارماب")
            fb_c = sum(1 for a in d["ads"] if a.get("source") == "فيسبوك")
            pend_c = len(d["pending_ads"])
            ok_p, p_info = atomic_write_and_git_push(d, f"Sync v16.0 (Live FB: {fb_c}, Pending Approval: {pend_c}, AQ: {aq_c})")
            print(f"    --> [Sync Complete] Live FB: ({fb_c}) | Pending Approval: ({pend_c}) | AqarMap: ({aq_c})!" if ok_p else f"    --> [Sync Notice] {p_info}")
    except Exception: pass

def main():
    global FB_PENDING_BATCH_COUNT
    generate_facebook_main_extension()
    start_fb_local_server()
    start_admin_command_listener()
    print("=== Starting Facebook Approval Queue & Instant Link Puller Radar v16.0 ===")
    with SYNC_LOCK:
        guard_extra_ads_during_sleep(force_push=True)
    print(f"[!] Reload extension once in Chrome -> {FB_EXT_DIR}")
    cycle_num = 1
    while True:
        print(f"\n>>> [Facebook Radar Cycle #{cycle_num} Active ({AUTO_LOOP_MINUTES}m)] Listening for Phone Links & Queuing 'من المالك' to Pending Approval... <<<")
        for _ in range((AUTO_LOOP_MINUTES * 60) // 30):
            time.sleep(30)
        if FB_PENDING_BATCH_COUNT > 0:
            with SYNC_LOCK:
                print(f"\n>>> [End of 45m Run] Pushing {FB_PENDING_BATCH_COUNT} pending Facebook ads to your Admin Approval Room... <<<")
                guard_extra_ads_during_sleep(force_push=True)
                FB_PENDING_BATCH_COUNT = 0
        cycle_num += 1

if __name__ == "__main__":
    main()
