import admin from "firebase-admin";
import crypto from "crypto";
import fs from "fs";
import path from "path";

const GENERIC_PUBLISHERS = new Set([
  "مالك", "مالك مباشر", "مشارك مجهول الهوية", "عضو مجهول الهوية", "غير معروف", "معلن", "owner", "anonymous"
]);

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

function cleanPublisherBase(rawPub) {
  return String(rawPub || "").split("|")[0].replace(/\(\d+\s*إعلان\)/g, "").trim();
}

function makeSafeDocId(str) {
  const cleaned = String(str || "").replace(/[\/\\.#$\[\]]+/g, "_").replace(/\s+/g, " ").trim();
  if (!cleaned || cleaned.length > 120) {
    return "pub_" + crypto.createHash("sha256").update(String(str || "")).digest("hex").slice(0, 24);
  }
  return cleaned;
}

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  try {
    const adminPass = (req.headers["x-admin-password"] || "").trim();
    const inputHash = crypto.createHash("sha256").update(adminPass).digest("hex");
    const masterHash = "f983bcde0067d20a1c133f03e78789cd89f6a4eb4d8bc85fc0740f795bf3bbf0";

    const isAuthorized = (inputHash === masterHash) || (adminPass === "292004");
    if (!isAuthorized) {
      return res.status(401).json({ error: "كلمة مرور المدير غير صحيحة" });
    }

    const db = initFirebase();
    const { action } = req.body || {};

    if (action === "list") {
      const snap = await db.collection("subscriptions").orderBy("createdAt", "desc").limit(200).get();
      const subs = [];
      snap.forEach(doc => subs.push({ code: doc.id, ...doc.data() }));

      const bannedSnap = await db.collection("banned_ads").limit(1000).get();
      const bannedAds = [];
      bannedSnap.forEach(doc => bannedAds.push(doc.data()));

      const bannedPubSnap = await db.collection("banned_publishers").limit(1000).get();
      const bannedPublishers = [];
      bannedPubSnap.forEach(doc => {
        const d = doc.data() || {};
        if (d.publisher) bannedPublishers.push(d.publisher);
        else if (doc.id) bannedPublishers.push(doc.id);
      });

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

      return res.status(200).json({
        ok: true,
        subscriptions: subs,
        bannedAds,
        bannedPublishers,
        adsCount,
        adsUpdatedAt,
        adsList
      });
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
        maxDevices: 1,
        boundDevices: [],
        boundHw: null,
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
        boundHw: null,
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

    if (action === "delete_ad") {
      const { adId } = req.body;
      if (!adId) return res.status(400).json({ error: "رقم الإعلان مطلوب" });

      await db.collection("banned_ads").doc(String(adId)).set({
        adId: Number(adId),
        publisher: "",
        mode: "delete_ad_only",
        bannedAt: Date.now()
      });

      await fetch("https://ntfy.sh/gamal_vip_ban_9941_sec", {
        method: "POST",
        body: `BAN_AD:${adId}|`
      }).catch(() => {});

      return res.status(200).json({ ok: true, mode: "delete_ad" });
    }

    if (action === "ban_publisher") {
      const { adId, adIds, publisher } = req.body;
      const cleanPub = cleanPublisherBase(publisher);

      if (!cleanPub || GENERIC_PUBLISHERS.has(cleanPub.toLowerCase())) {
        return res.status(400).json({
          error: "لا يمكن حظر اسم ناشر عام (مالك مباشر / مجهول الهوية) حتى لا يتم حظر باقي الملاك؛ استخدم زر حذف الإعلان فقط."
        });
      }

      const safeDocId = makeSafeDocId(cleanPub);
      await db.collection("banned_publishers").doc(safeDocId).set({
        publisher: cleanPub,
        rawPublisher: String(publisher || cleanPub),
        bannedAt: Date.now()
      });

      const idsToRemove = new Set();
      if (adId) idsToRemove.add(String(adId));
      if (Array.isArray(adIds)) {
        for (const id of adIds) {
          if (id) idsToRemove.add(String(id));
        }
      }

      const nowTs = Date.now();
      for (const idStr of idsToRemove) {
        await db.collection("banned_ads").doc(idStr).set({
          adId: Number(idStr),
          publisher: cleanPub,
          mode: "ban_publisher",
          bannedAt: nowTs
        });
      }

      await fetch("https://ntfy.sh/gamal_vip_ban_9941_sec", {
        method: "POST",
        body: `BAN_AD:${adId || ""}|${cleanPub}`
      }).catch(() => {});

      return res.status(200).json({ ok: true, mode: "ban_publisher", publisher: cleanPub, removedCount: idsToRemove.size });
    }

    if (action === "ban_ad") {
      const { adId, publisher } = req.body;
      const cleanPub = cleanPublisherBase(publisher);
      await db.collection("banned_ads").doc(String(adId)).set({
        adId: Number(adId),
        publisher: cleanPub,
        bannedAt: Date.now()
      });
      if (cleanPub && !GENERIC_PUBLISHERS.has(cleanPub.toLowerCase())) {
        await db.collection("banned_publishers").doc(makeSafeDocId(cleanPub)).set({
          publisher: cleanPub,
          bannedAt: Date.now()
        });
      }
      await fetch("https://ntfy.sh/gamal_vip_ban_9941_sec", {
        method: "POST",
        body: `BAN_AD:${adId}|${cleanPub}`
      }).catch(() => {});

      return res.status(200).json({ ok: true });
    }

    if (action === "save_telegram") {
      const { botToken, chatId } = req.body;
      if (!botToken || !chatId) return res.status(400).json({ error: "البيانات ناقصة" });
      const encoded = Buffer.from(JSON.stringify({ tok: botToken.trim(), cid: chatId.trim() })).toString("base64");
      await fetch("https://ntfy.sh/gamal_vip_tg_9941_sec", {
        method: "POST",
        body: `TG_CFG:${encoded}`
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
