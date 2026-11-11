const crypto = require("crypto");
const { db } = require("./_firebase");

function getClientIp(req) {
  const xff = req.headers["x-forwarded-for"];
  return xff ? xff.split(",")[0].trim() : (req.socket.remoteAddress || "0.0.0.0");
}

module.exports = async (req, res) => {
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate");

  if (req.method === "DELETE") {
    res.setHeader("Set-Cookie", "masyada_session=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0");
    return res.status(200).json({ ok: true });
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method Not Allowed" });
  }

  try {
    const { code, hwHash } = req.body || {};
    const cleanCode = String(code || "").trim().toUpperCase();
    const cleanHw = String(hwHash || "").trim();
    const clientIp = getClientIp(req);
    const userAgent = String(req.headers["user-agent"] || "unknown").trim();

    if (!cleanCode || !cleanHw) {
      return res.status(400).json({ error: "بيانات الدخول أو بصمة الجهاز ناقصة" });
    }

    const subRef = db.collection("subscriptions").doc(cleanCode);
    const subDoc = await subRef.get();

    if (!subDoc.exists) {
      return res.status(401).json({ error: "كود الاشتراك غير صحيح" });
    }

    const sub = subDoc.data();
    const now = Date.now();

    if (sub.status === "banned") {
      return res.status(403).json({
        error: "تم حظر هذا الاشتراك نهائيا بسبب محاولة مشاركة الحساب أو تغير بصمة الجهاز"
      });
    }

    if (sub.status === "used") {
      if (now > sub.expiresAt) {
        return res.status(403).json({ error: "انتهت صلاحية هذا الاشتراك، يرجى التجديد" });
      }

      const isSameDevice = (sub.boundUa === userAgent && sub.boundHw === cleanHw);
      const isSameIp = (sub.boundIp === clientIp);

      if (!isSameDevice || !isSameIp) {
        await subRef.update({
          status: "banned",
          bannedAt: now,
          banReason: `محاولة دخول بكود مستخدم من جهاز أو IP مختلف (${clientIp})`
        });
        return res.status(403).json({
          error: "تم رصد محاولة استخدام الكود على جهاز آخر. تم حظر الاشتراك نهائيا."
        });
      }

      const remainingSec = Math.max(60, Math.floor((sub.expiresAt - now) / 1000));
      res.setHeader(
        "Set-Cookie",
        `masyada_session=${sub.sessionId}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=${remainingSec}`
      );
      return res.status(200).json({ ok: true, brokerName: sub.brokerName, expiresAt: sub.expiresAt });
    }

    const sessionId = crypto.randomBytes(32).toString("hex");
    const durationMs = (Number(sub.durationDays) || 30) * 24 * 60 * 60 * 1000;
    const expiresAt = now + durationMs;
    const maxAgeSec = Math.floor(durationMs / 1000);

    await subRef.update({
      status: "used",
      sessionId: sessionId,
      boundIp: clientIp,
      boundUa: userAgent,
      boundHw: cleanHw,
      activatedAt: now,
      lastSeenAt: now,
      expiresAt: expiresAt
    });

    res.setHeader(
      "Set-Cookie",
      `masyada_session=${sessionId}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=${maxAgeSec}`
    );

    return res.status(200).json({
      ok: true,
      brokerName: sub.brokerName || "مشترك VIP",
      expiresAt: expiresAt
    });
  } catch (err) {
    return res.status(500).json({ error: "خطأ داخلي في السيرفر" });
  }
};
