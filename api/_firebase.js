const admin = require("firebase-admin");

if (!admin.apps.length) {
  const rawKey = (process.env.FIREBASE_PRIVATE_KEY || "")
    .trim()
    .replace(/^["']|["']$/g, "")
    .replace(/\\n/g, "\n");

  admin.initializeApp({
    credential: admin.credential.cert({
      projectId: (process.env.FIREBASE_PROJECT_ID || "").trim(),
      clientEmail: (process.env.FIREBASE_CLIENT_EMAIL || "").trim(),
      privateKey: rawKey
    })
  });
}

const db = admin.firestore();
module.exports = { admin, db };
