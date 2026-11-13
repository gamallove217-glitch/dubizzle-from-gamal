import admin from "firebase-admin";
import crypto from "crypto";

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

function signToken(payload, secret) {
  const data = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const sig = crypto.createHmac("sha256", secret).update(data).digest("base64url");
  return `${data}.${sig}`;
}

export default async function handler(req, res) {
  if (req.method === "DELETE") {
    res.setHeader("Set-Cookie", "vip_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0");
    return res.status(200).json({ ok: true });
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const { code, deviceId } = req.body || {};
    if (!code || typeof code !== "string") {
      return res.status(400).json({ error: "يرجى إدخال كود الاشتراك" });
    }

    const currentUa = (req.headers["user-agent"] || "unknown").slice(0, 250);
    if (/FBAN|FBAV|Instagram|WhatsApp|Messenger|Telegram/i.test(currentUa)) {
      return res.status(400).json({
        error: "لا يمكن تفعيل الكود من متصفح المحادثة المؤقت. اضغط على النقاط الثلاث أعلى الشاشة واختر (فتح في Chrome أو Safari) لتفعيل الكود على جهازك."
      });
    }

    const cleanCode = code.trim().toUpperCase();
    const cleanDevice = String(deviceId || "").trim().slice(0, 120);
    if (!cleanDevice || cleanDevice.length < 8) {
      return res.status(400).json({ error: "تعذر قراءة بصمة الجهاز، تأكد من تفعيل الكوكيز في متصفحك" });
    }

    const currentIp = (req.headers["x-forwarded-for"] || req.socket?.remoteAddress || "unknown").split(",")[0].trim();

    const db = initFirebase();
    const docRef = db.collection("subscriptions").doc(cleanCode);
    const docSnap = await docRef.get();

    if (!docSnap.exists) {
      return res.status(401).json({ error: "كود الاشتراك غير صحيح أو غير موجود" });
    }

    const sub = docSnap.data();
    const now = Date.now();

    if (sub.status === "banned") {
      return res.status(403).json({
        error: "هذا الكود موقوف من قبل الإدارة. يرجى التواصل مع المسؤول."
      });
    }

    if (sub.expiresAt && now > sub.expiresAt) {
      await docRef.update({ status: "expired" });
      return res.status(403).json({ error: "انتهت صلاحية هذا الاشتراك. يرجى التجديد." });
    }

    let boundDevices = Array.isArray(sub.boundDevices) ? sub.boundDevices : [];
    const primaryDevice = boundDevices[0] || sub.boundHw || null;

    if (primaryDevice && primaryDevice !== cleanDevice) {
      return res.status(403).json({
        error: "هذا الكود مقفول بالفعل على جهاز آخر ولا يمكن استخدامه على أكثر من جهاز واحد."
      });
    }

    const durationDays = Number(sub.durationDays || 30);
    const expiresAt = sub.expiresAt || (now + durationDays * 24 * 60 * 60 * 1000);

    await docRef.update({
      status: "active",
      boundDevices: [cleanDevice],
      boundHw: cleanDevice,
      boundIp: currentIp,
      boundUa: currentUa,
      activatedAt: sub.activatedAt || now,
      expiresAt: expiresAt,
      lastLoginAt: now
    });

    const secret = process.env.SESSION_SECRET || "default_super_secret_change_me";
    const sessionToken = signToken({
      code: cleanCode,
      deviceId: cleanDevice,
      iat: now
    }, secret);

    const maxAgeSec = Math.max(60, Math.floor((expiresAt - now) / 1000));
    res.setHeader(
      "Set-Cookie",
      `vip_session=${sessionToken}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=${maxAgeSec}`
    );

    return res.status(200).json({
      ok: true,
      expiresAt: expiresAt,
      clientName: sub.clientName || "مشترك VIP"
    });
  } catch (err) {
    console.error("Auth error:", err);
    return res.status(500).json({ error: "خطأ داخلي في الخادم" });
  }
}
