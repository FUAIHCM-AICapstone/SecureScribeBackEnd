"""Firebase Admin SDK initialization"""

import json
import os

import firebase_admin
from firebase_admin import credentials

from app.core.config import settings
from app.utils.logging import logger


def initialize_firebase():
    if not firebase_admin._apps:
        try:
            key_content = settings.FIREBASE_SERVICE_ACCOUNT_KEY_PATH

            # Parse JSON content from env variable
            if isinstance(key_content, str):
                try:
                    # Try to parse as JSON string
                    key_dict = json.loads(key_content)
                except json.JSONDecodeError:
                    # If it's a file path, read from file
                    if os.path.exists(key_content):
                        logger.info(f"Reading Firebase key from file: {key_content}")
                        with open(key_content) as f:
                            key_dict = json.load(f)
                    else:
                        logger.error(f"Firebase service account key not found: {key_content}")
                        raise FileNotFoundError(f"Service account key not found: {key_content}")
            else:
                key_dict = key_content

            logger.info("Initializing Firebase with service account key")
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
            logger.info(f"Firebase apps: {list(firebase_admin._apps.keys())}")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            logger.error(f"Firebase apps before error: {list(firebase_admin._apps.keys())}")
            raise
    else:
        logger.info("Firebase already initialized")
        logger.info(f"Firebase apps: {list(firebase_admin._apps.keys())}")


# Don't call initialize on import - let main.py handle it
# initialize_firebase()
