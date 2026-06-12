import firebase_admin
from firebase_admin import credentials, firestore
from ..config.settings import settings
from loguru import logger
import os
import json

class FirebaseDB:
    _db = None

    @classmethod
    def get_db(cls):
        if cls._db is None:
            logger.debug("Establishing connection to Firestore...")
            try:
                if not firebase_admin._apps:
                    # 1. Primary: Load from Environment Variable (JSON String)
                    if settings.FIREBASE_CREDENTIALS:
                        try:
                            # If it's already a dict (e.g. from a test or manual inject), don't load
                            if isinstance(settings.FIREBASE_CREDENTIALS, dict):
                                cred_dict = settings.FIREBASE_CREDENTIALS
                            else:
                                cred_dict = json.loads(settings.FIREBASE_CREDENTIALS)
                            
                            cred = credentials.Certificate(cred_dict)
                            firebase_admin.initialize_app(cred)
                            logger.info("✅ Firebase initialized from FIREBASE_CREDENTIALS")
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ FIREBASE_CREDENTIALS is not valid JSON: {e}")
                            raise
                        except Exception as e:
                            logger.error(f"❌ Failed to parse FIREBASE_CREDENTIALS: {e}")
                            raise
                    
                    # 2. Secondary: Fallback to local file for dev only
                    else:
                        # Try to find it in backend root
                        backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        cred_path = os.path.join(backend_root, "serviceAccountKey.json")
                        
                        if os.path.exists(cred_path):
                            cred = credentials.Certificate(cred_path)
                            firebase_admin.initialize_app(cred)
                            logger.warning(f"⚠️ Firebase initialized from local file: {cred_path} (DEV ONLY)")
                        else:
                            logger.debug("Attempting Firebase Application Default Credentials (ADC)...")
                            try:
                                firebase_admin.initialize_app()
                                logger.info("ℹ️ Firebase initialized with Application Default Credentials")
                            except Exception as adc_err:
                                logger.error("❌ No Firebase credentials found in env or file.")
                                raise adc_err
                
                cls._db = firestore.client()
                logger.info("✅ Firestore client successfully connected.")
            except Exception as e:
                logger.error(f"❌ Critical Error: Failed to initialize Firebase: {e}")
                raise
        return cls._db

# Initialize on demand via get_db()
db = None

def get_db():
    return FirebaseDB.get_db()


