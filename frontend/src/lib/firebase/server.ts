import * as admin from 'firebase-admin';

// Initialize Firebase Admin only once
if (!admin.apps.length) {
  try {
    let serviceAccount: admin.ServiceAccount | undefined = undefined;

    if (process.env.FIREBASE_CREDENTIALS) {
      try {
        const parsed = JSON.parse(process.env.FIREBASE_CREDENTIALS);
        serviceAccount = {
          projectId: parsed.project_id || parsed.projectId,
          clientEmail: parsed.client_email || parsed.clientEmail,
          privateKey: (parsed.private_key || parsed.privateKey)?.replace(/\\n/g, '\n'),
        };
      } catch (jsonErr) {
        console.error('Failed to parse FIREBASE_CREDENTIALS env variable:', jsonErr);
      }
    }

    if (!serviceAccount && process.env.FIREBASE_PROJECT_ID) {
      serviceAccount = {
        projectId: process.env.FIREBASE_PROJECT_ID,
        clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
        privateKey: process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, '\n'),
      };
    }

    // Fallback: If still no service account, use dummy credentials to prevent build failures
    if (!serviceAccount) {
      console.warn('⚠️ Firebase credentials not configured. Using dummy credential for build-time compilation.');
      serviceAccount = {
        projectId: 'dummy-project-id',
        clientEmail: 'dummy-client-email@example.com',
        privateKey: '-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDh\n-----END PRIVATE KEY-----\n',
      };
    }

    admin.initializeApp({
      credential: admin.credential.cert(serviceAccount),
      databaseURL: process.env.FIREBASE_DATABASE_URL,
    });
  } catch (error) {
    console.error('Firebase admin initialization error:', error);
  }
}

export const adminDb = admin.firestore();
export const adminAuth = admin.auth();
export const adminStorage = admin.storage();

