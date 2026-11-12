const fs = require("fs");
const path = require("path");
const crypto = require("crypto");
const { db, admin } = require("./_firebase");

const OWNER_PASS_SHA256 = "44ab142b5171cd63db89e3186367c9a7a2a28e5daee21305214ff6626d9fb842";

function isAuthorizedAdmin(inputPass) {
  if (!inputPass) return false;
  const clean = String(inputPass).trim();
  if (process.env.ADMIN_PASSWORD && clean === process.env.ADMIN_PASSWORD.trim()) return true;
  const hash = crypto.createHash("sha256").update(clean).digest("hex");
  return hash === OWNER_PASS_SHA256;
}

module.exports = async (req, res) => {
  res.setHeader("Cache-Control", "no-store");
  const pass = req.headers["x-admin-password"];

  if (!isAuthorizedAdmin(pass)) {
    return res.status(401).json({ error: "غير مصرح" });
  }

  try {
    if (req.method === "GET") {
      const snap = await db.collection("subscriptions").orderBy("createdAt", "desc").limit(200).get();
      const subs = snap.docs.map(d => ({ code: d.id, ...d.data() }));
      const tgDoc = await db.collection("settings").doc("telegram").get();
      const bansDoc = await db.collection("settings").doc("bans").get();
      const bannedAdIds = bansDoc.exists ? (bansDoc.data().adIds || []) : [];
      const bannedSellers = bansDoc.exists ? (bansDoc.data().sellers || []) : [];

      const adsPath = path.join(process.cwd(), "ads.json");
      const parsed = JSON.parse(fs.readFileSync(adsPath, "utf-8"));

      const cleanAds = (parsed.ads || []).filter(ad => {
        if (!ad || !ad.ad_id) return false;
        if (bannedAdIds.includes(Number(ad.ad_id))) return false;
        const sname = String(ad.seller_name || "").trim().toLowerCase();
        if (sname && bannedSellers.includes(sname)) return false;
        if (Number(ad.seller_ads_count || 1) > 4) return false;
        return true;
      });

      return res.status(200).json({
        subscriptions: subs,
        telegram: tgDoc.exists ? tgDoc.data() : {},
        lastScrape: parsed.last_scrape || "",
        lastRunReport: parsed.last_run_report || {},
        totalBlacklisted: (parsed.banned_accounts_v7 || []).length,
        ads: cleanAds
      });
    }

    if (req.method === "POST") {
      const { action } = req.body || {};

      if (action === "GENERATE_CODE") {
        const { brokerName, durationDays } = req.body;
        const rand = crypto.randomBytes(4).toString("hex").toUpperCase();
        const code = `VIP-${rand.slice(0, 4)}-${rand.slice(4, 8)}`;
        const data = {
          brokerName: String(brokerName || "سمسار مشترك").trim(),
          durationDays: Number(durationDays) || 30,
          status: "unused",
          createdAt: Date.now(),
          boundIp: null,
          boundUa: null,
          boundHw: null,
          sessionId: null,
          expiresAt: null
        };
        await db.collection("subscriptions").doc(code).set(data);
        return res.status(200).json({ ok: true, code, data });
      }

      if (action === "UPDATE_SUB") {
        const { code, newStatus } = req.body;
        const ref = db.collection("subscriptions").doc(String(code));
        if (newStatus === "DELETE") {
          await ref.delete();
        } else if (newStatus === "RESET") {
          await ref.update({
            status: "unused",
            sessionId: null,
            boundIp: null,
            boundUa: null,
            boundHw: null,
            banReason: null
          });
        } else {
          await ref.update({ status: newStatus });
        }
        return res.status(200).json({ ok: true });
      }

      if (action === "BAN_AD") {
        const { adId, sellerName } = req.body;
        const bansRef = db.collection("settings").doc("bans");
        const updateData = {};
        if (adId) updateData.adIds = admin.firestore.FieldValue.arrayUnion(Number(adId));
        if (sellerName) updateData.sellers = admin.firestore.FieldValue.arrayUnion(String(sellerName).trim().toLowerCase());
        await bansRef.set(updateData, { merge: true });

        await fetch("https://ntfy.sh/gamal_masyada_bans_2738_v1", {
          method: "POST",
          body: JSON.stringify({ ad_id: Number(adId || 0), seller_name: sellerName || "" })
        }).catch(() => {});

        return res.status(200).json({ ok: true });
      }

      if (action === "SAVE_TELEGRAM") {
        const { botToken, chatId } = req.body;
        await db.collection("settings").doc("telegram").set({
          botToken: String(botToken || "").trim(),
          chatId: String(chatId || "").trim(),
          updatedAt: Date.now()
        });

        const encoded = Buffer.from(JSON.stringify({ tok: botToken, cid: chatId })).toString("base64");
        await fetch("https://ntfy.sh/gamal_masyada_tgcfg_2738_v1", {
          method: "POST",
          body: encoded
        }).catch(() => {});

        return res.status(200).json({ ok: true });
      }
    }

    return res.status(400).json({ error: "طلب غير معروف" });
  } catch (err) {
    return res.status(500).json({ error: "خطأ داخلي" });
  }
};
