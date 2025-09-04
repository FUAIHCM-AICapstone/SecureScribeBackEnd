#!/usr/bin/env python3
"""
Database cleanup script for test data
Run this after test execution to clean up all test data
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.db import SessionLocal
from tests.conftest import prune_database

if __name__ == "__main__":
    print("🧹 Starting database cleanup...")
    db = SessionLocal()
    try:
        prune_database(db)
        print("✅ Database cleanup completed!")
    except Exception as e:
        print(f"❌ Database cleanup failed: {e}")
        sys.exit(1)
    finally:
        db.close()
