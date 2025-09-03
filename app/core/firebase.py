import logging
import os

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings

logger = logging.getLogger(__name__)


def initialize_firebase():
    if not firebase_admin._apps:
        try:
            key_path = settings.FIREBASE_SERVICE_ACCOUNT_KEY_PATH
            if not os.path.exists(key_path):
                logger.error(f"Firebase service account key file not found: {key_path}")
                raise FileNotFoundError(
                    f"Service account key file not found: {key_path}"
                )

            logger.info(f"Initializing Firebase with service account key: {key_path}")
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
            logger.info(f"Firebase apps: {list(firebase_admin._apps.keys())}")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            logger.error(
                f"Firebase apps before error: {list(firebase_admin._apps.keys())}"
            )
            raise
    else:
        logger.info("Firebase already initialized")
        logger.info(f"Firebase apps: {list(firebase_admin._apps.keys())}")


# Don't call initialize on import - let main.py handle it
# initialize_firebase()
