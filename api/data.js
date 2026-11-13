import admin from "firebase-admin";
import crypto from "crypto";
import fs from "fs";
import path from "path";

function initFirebase() {
  if (!admin.apps.length) {
    const privateKey = (process.env.FIREBASE_PRIVATE_KEY || "").replace(/\\n/g, "\n");
    admin.initializeApp({
      credential: admin.credential.cert({
        projectId: process.env.FIREBASE_PROJECT_ID,
        clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
        privateKey: privateKey
      })
    });
  }
  return admin.firestore();
}

function verifyToken(token, secret) {
  try {
    const [data, sig] = token.split(".");
    if (!data || !sig) return null;
    const expectedSig = crypto.createHmac("sha256", secret).update(data).digest("base64url");
    if (sig !== expectedSig) return null;
    return JSON.parse(Buffer.from(data, "base64url").toString("utf8"));
  } catch (e) {
    return null;
  }
}

function parseCookies(cookieHeader) {
  const list = {};
  if (!cookieHeader) return list;
  cookieHeader.split(";").forEach(cookie => {
    let [name, ...rest] = cookie.split("=");
    name = name?.trim();
    if (!name) return;
    list[name] = decodeURIComponent(rest.join("=").trim());
  });
  return list;
}

export default async function handler(req, res) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const cookies = parseCookies(req.headers.cookie);
    const sessionToken = cookies.vip_session;
    if (!sessionToken) {
      return res.status(401).json({ error: "غير مصرح: يرجى تسجيل الدخول بكود الاشتراك" });
    }

    const secret = process.env.SESSION_SECRET || "default_super_secret_change_me";
    const payload = verifyToken(sessionToken, secret);
    if (!payload || !payload.code) {
      return res.status(401).json({ error: "جلسة غير صالحة، أعد تسجيل الدخول" });
    }

    const currentDevice = String(req.headers["x-device-id"] || payload.deviceId || "").trim().slice(0, 120);
    const db = initFirebase();
    const subDoc = await db.collection("subscriptions").doc(payload.code).get();

    if (!subDoc.exists) {
      return res.status(401).json({ error: "الاشتراك غير موجود" });
    }

    const sub = subDoc.data();
    const now = Date.now();

    if (sub.status === "banned") {
      return res.status(403).json({
        error: "هذا الكود موقوف من قبل الإدارة."
      });
    }

    if (sub.expiresAt && now > sub.expiresAt) {
      return res.status(403).json({ error: "انتهت صلاحية الاشتراك" });
    }

    const boundDevices = Array.isArray(sub.boundDevices) ? sub.boundDevices : [];
    const primaryDevice = boundDevices[0] || sub.boundHw || null;

    if (!primaryDevice) {
      await subDoc.ref.update({
        boundDevices: [currentDevice],
        boundHw: currentDevice
      });
    } else if (primaryDevice !== currentDevice) {
      res.setHeader("Set-Cookie", "vip_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0");
      return res.status(403).json({
        error: "هذا الكود مقفول على جهاز آخر بالفعل ولا يمكن فتحه على هذا الجهاز."
      });
    }

    let adsData = { ads: [] };
    try {
      const filePath = path.join(process.cwd(), "ads.json");
      const rawFile = fs.readFileSync(filePath, "utf8");
      adsData = JSON.parse(rawFile);
    } catch (readErr) {
      return res.status(500).json({ error: "تعذر قراءة ملف العقارات المحلي" });
    }

    const bannedSnap = await db.collection("banned_ads").get();
    const bannedIds = new Set();
    const bannedPubs = new Set();
    bannedSnap.forEach(d => {
      const data = d.data();
      if (data.adId) bannedIds.add(Number(data.adId));
      if (data.publisher) bannedPubs.add(data.publisher);
    });

    const filteredAds = (adsData.ads || []).filter(ad => {
      if (bannedIds.has(Number(ad.ad_id))) return false;
      if (ad.publisher && bannedPubs.has(ad.publisher)) return false;
      return true;
    });

    filteredAds.sort((a, b) => {
      const tierDiff = (b.fresh_tier || 1) - (a.fresh_tier || 1);
      if (tierDiff !== 0) return tierDiff;
      return (b.first_seen_ts || 0) - (a.first_seen_ts || 0);
    });

    res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate");
    return res.status(200).json({
      updated_at: adsData.updated_at,
      total: filteredAds.length,
      clientName: sub.clientName || "مشترك VIP",
      expiresAt: sub.expiresAt,
      ads: filteredAds
    });
  } catch (err) {
    console.error("Data API error:", err);
    return res.status(500).json({ error: "خطأ داخلي في الخادم" });
  }
}
