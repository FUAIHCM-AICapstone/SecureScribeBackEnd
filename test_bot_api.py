#!/usr/bin/env python3
"""
Quick test script for bot API connectivity
"""
import requests
import json

def test_direct_bot_api():
    """Test direct connection to bot API"""
    try:
        url = "http://localhost:3000/ping"
        response = requests.get(url, timeout=5)
        print(f"Direct Bot API: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Direct Bot API Error: {e}")
        return False

def test_via_api():
    """Test via our API endpoint"""
    try:
        # Trigger the celery task
        url = "http://localhost:8000/api/v1/test-bot-ping"
        response = requests.post(url, timeout=5)
        result = response.json()
        task_id = result.get("task_id")
        print(f"API Trigger: {response.status_code} - Task ID: {task_id}")

        if task_id:
            # Check result
            result_url = f"http://localhost:8000/api/v1/test-bot-result/{task_id}"
            for i in range(10):  # Try for 30 seconds
                response = requests.get(result_url, timeout=5)
                result = response.json()
                print(f"Task Status: {result}")

                if result.get("status") == "completed":
                    return result.get("result", {}).get("success", False)
                elif result.get("status") == "pending":
                    import time
                    time.sleep(3)
                else:
                    break

        return False
    except Exception as e:
        print(f"API Test Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Bot API connectivity...")
    print("=" * 50)

    direct_ok = test_direct_bot_api()
    print()

    api_ok = test_via_api()
    print()

    if direct_ok and api_ok:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
        if not direct_ok:
            print("   - Direct bot API connection failed")
        if not api_ok:
            print("   - API/Celery test failed")

