const fs = require("fs");
const path = require("path");
const { db } = require("./_firebase");

const STRICT_IP_BAN = true;

function getClientIp(req) {
  const xff = req.headers["x-forwarded-for"];
  return xff ? xff.split(",")[0].trim() : (req.socket.remoteAddress || "0.0.0.0");
}

function parseCookies(cookieHeader) {
  const list = {};
  if (!cookieHeader) return list;
  cookieHeader.split(";").forEach(cookie => {
    let [name, ...rest] = cookie.split("=");
    name = name ? name.trim() : "";
    if (name) list[name] = decodeURIComponent(rest.join("=").trim());
  });
  return list;
}

async function readAdsSource() {
  try {
    const adsPath = path.join(process.cwd(), "ads.json");
    if (fs.existsSync(adsPath)) {
      return JSON.parse(fs.readFileSync(adsPath, "utf-8"));
    }
  } catch (e) {}
  const r = await fetch("https://raw.githubusercontent.com/gamallove217-glitch/dubizzle-from-gamal/main/ads.json?t=" + Date.now());
  return await r.json();
}

module.exports = async (req, res) => {
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate");
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method Not Allowed" });
  }

  try {
    const cookies = parseCookies(req.headers.cookie);
    const sessionId = cookies["masyada_session"];
    const currentHw = String(req.headers["x-hw-hash"] || "").trim();
    const currentUa = String(req.headers["user-agent"] || "unknown").trim();
    const currentIp = getClientIp(req);

    if (!sessionId) {
      return res.status(401).json({ error: "غير مصرح، يرجى تسجيل الدخول بكود الاشتراك" });
    }

    const snap = await db.collection("subscriptions").where("sessionId", "==", sessionId).limit(1).get();
    if (snap.empty) {
      res.setHeader("Set-Cookie", "masyada_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0");
      return res.status(401).json({ error: "جلسة غير صالحة" });
    }

    const subDoc = snap.docs[0];
    const sub = subDoc.data();
    const now = Date.now();

    if (sub.status === "banned") {
      res.setHeader("Set-Cookie", "masyada_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0");
      return res.status(403).json({ error: "تم حظر اشتراكك نهائيا لمخالفة شروط عدم مشاركة الحساب" });
    }

    if (now > sub.expiresAt) {
      res.setHeader("Set-Cookie", "masyada_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0");
      return res.status(403).json({ error: "انتهت مدة اشتراكك" });
    }

    const uaMismatch = (sub.boundUa !== currentUa);
    const hwMismatch = (sub.boundHw !== currentHw);
    const ipMismatch = (STRICT_IP_BAN && sub.boundIp !== currentIp);

    if (uaMismatch || hwMismatch || ipMismatch) {
      await subDoc.ref.update({
        status: "banned",
        bannedAt: now,
        banReason: `مشاركة جلسة: تغير البصمة أو الـ IP من (${sub.boundIp}) إلى (${currentIp})`
      });
      res.setHeader("Set-Cookie", "masyada_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0");
      return res.status(403).json({
        error: "تم رصد فتح الحساب من جهاز أو عنوان IP مختلف. تم حظر الاشتراك نهائيا وإيقاف الخدمة."
      });
    }

    await subDoc.ref.update({ lastSeenAt: now });

    const bansDoc = await db.collection("settings").doc("bans").get();
    const bannedAdIds = bansDoc.exists ? (bansDoc.data().adIds || []) : [];
    const bannedSellers = bansDoc.exists ? (bansDoc.data().sellers || []) : [];

    const parsed = await readAdsSource();
    const cleanAds = (parsed.ads || [])
      .filter(ad => {
        if (!ad || !ad.ad_id) return false;
        if (bannedAdIds.includes(Number(ad.ad_id))) return false;
        const sname = String(ad.seller_name || "").trim().toLowerCase();
        if (sname && bannedSellers.includes(sname)) return false;
        if (Number(ad.seller_ads_count || 1) > 4) return false;
        return true;
      })
      .map(ad => ({
        ad_id: ad.ad_id,
        source: ad.source || "دوبيزل",
        title: ad.title,
        price_text: ad.price_text,
        price_num: ad.price_num,
        area: ad.area,
        beds: ad.beds,
        baths: ad.baths,
        deal: ad.deal,
        category: ad.category,
        subtype: ad.subtype,
        seller_name: ad.seller_name,
        description: ad.description,
        url: ad.url,
        scraped_at: ad.scraped_at
      }));

    return res.status(200).json({
      last_scrape: parsed.last_scrape || "",
      brokerName: sub.brokerName || "مشترك VIP",
      expiresAt: sub.expiresAt,
      ads: cleanAds
    });
  } catch (err) {
    return res.status(500).json({ error: "تعذر جلب البيانات" });
  }
};
