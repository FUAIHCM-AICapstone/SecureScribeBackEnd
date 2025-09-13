import requests
import io

def test_webm_upload():
    """Test WebM file upload to the audio endpoint"""
    
    # Create a minimal WebM file header for testing
    webm_header = (
        b'\x1A\x45\xDF\xA3'  # EBML header
        b'\x01\x00\x00\x00\x00\x00\x00\x20'  # EBML header size
        b'\x42\x86\x81\x01'  # EBMLVersion = 1
        b'\x42\xF7\x81\x01'  # EBMLReadVersion = 1
        b'\x42\xF2\x81\x04'  # EBMLMaxIDLength = 4
        b'\x42\xF3\x81\x08'  # EBMLMaxSizeLength = 8
        b'\x42\x82\x84webm'  # DocType = "webm"
        b'\x42\x87\x81\x02'  # DocTypeVersion = 2
        b'\x42\x85\x81\x02'  # DocTypeReadVersion = 2
    )
    
    # Add some padding to make it look more like a real file
    webm_content = webm_header + b'\x00' * 100
    
    # Test with different content types that might be detected
    content_types_to_test = [
        "audio/webm",
        "video/webm"
    ]
    
    for content_type in content_types_to_test:
        print(f"\n🧪 Testing WebM upload with content-type: {content_type}")
        
        files = {
            'file': ('test.webm', io.BytesIO(webm_content), content_type)
        }
        
        data = {
            'meeting_id': '123e4567-e89b-12d3-a456-426614174000'
        }
        
        try:
            # Note: This will require authentication in real scenario
            # For testing, you might need to add proper auth headers
            response = requests.post(
                "http://localhost:8000/api/v1/audio-files/upload",
                files=files,
                data=data,
                # headers={"Authorization": "Bearer YOUR_TOKEN_HERE"},
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ WebM upload successful!")
                data = response.json()
                if 'data' in data and 'id' in data['data']:
                    print(f"📁 Audio ID: {data['data']['id']}")
                    print(f"🔗 File URL: {data['data'].get('file_url', 'N/A')}")
            elif response.status_code == 401:
                print("🔐 Authentication required (expected for this test)")
            else:
                print(f"❌ Upload failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Request error: {e}")

def test_file_validation():
    """Test the validate_file function directly"""
    from app.services.file import validate_file
    
    print("\n🔍 Testing validate_file function:")
    
    test_cases = [
        ("test.webm", "audio/webm", 1024),
        ("test.webm", "video/webm", 1024),
        ("test.wav", "audio/wav", 1024),
        ("test.mp3", "audio/mp3", 1024),
    ]
    
    for filename, mime_type, size in test_cases:
        result = validate_file(filename, mime_type, size)
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - File: {filename}, MIME: {mime_type}, Size: {size}")

if __name__ == "__main__":
    print("🧪 Testing WebM file upload functionality...")
    
    # Test the validation function
    try:
        test_file_validation()
    except ImportError:
        print("⚠️ Cannot import validation function - testing upload endpoint only")
    
    # Test the actual upload endpoint
    test_webm_upload()
    
    print("\n📝 Notes:")
    print("- If you get 401 errors, add proper authentication headers")
    print("- If WebM upload fails, check the server logs for detailed error messages")
    print("- The endpoint now supports both audio/webm and video/webm content types")