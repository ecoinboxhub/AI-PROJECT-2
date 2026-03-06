"""
Demo Test Script for Screen Recording
Tests all three outbound trigger types with clear visual output
"""

import requests
import json
import time

BUSINESS_BASE = "http://localhost:8001"
VOICE_BASE = "http://localhost:8003"

def print_header(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def print_success(message):
    print(f"✅ {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def test_trigger(name, payload):
    """Test a single trigger type"""
    print_header(f"TEST: {name.upper()}")
    print_info(f"Trigger Type: {payload['trigger_type']}")
    print_info(f"Customer: {payload['personalization']['first_name']}")
    
    # Post to Business AI
    print("\n📤 Posting trigger to Business Owner AI...")
    try:
        resp = requests.post(
            f"{BUSINESS_BASE}/api/v1/orchestrator/triggers",
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        result = resp.json()
        
        print_success("Orchestration successful!")
        print(f"\n📝 Message Content:")
        print(f"   {result.get('message_content', 'N/A')}")
        print(f"\n📊 Details:")
        print(f"   - Ready for Delivery: {result.get('ready_for_delivery')}")
        print(f"   - KB Confidence: {result.get('kb_confidence', 'N/A')}")
        print(f"   - Trace ID: {result.get('trace_id', 'N/A')}")
        
        # Prepare voice session
        print("\n📞 Preparing Voice Agent session...")
        voice_payload = {
            "trigger_id": result.get("trace_id") or result.get("trigger_id") or "",
            "trigger_type": payload["trigger_type"],
            "business_id": payload["business_id"],
            "business_name": payload["business_id"],
            "customer_id": payload["customer_id"],
            "message_content": result.get("message_content", ""),
            "personalization": payload.get("personalization", {}),
            "tts_options": {"format": "MP3"}
        }
        
        voice_resp = requests.post(
            f"{VOICE_BASE}/api/v1/outbound/session-prepare",
            json=voice_payload,
            timeout=30
        )
        voice_resp.raise_for_status()
        voice_result = voice_resp.json()
        
        print_success("Voice session prepared!")
        print(f"\n🎤 Greeting:")
        print(f"   {voice_result.get('greeting', {}).get('text', 'N/A')}")
        print(f"\n📊 Session Details:")
        print(f"   - Session ID: {voice_result.get('session_id', 'N/A')}")
        print(f"   - Audio Generated: {'Yes' if voice_result.get('greeting', {}).get('audio_base64') else 'No'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print_header("🎯 OUTBOUND CALL IMPLEMENTATION DEMO")
    print("\nTesting three trigger types:")
    print("  1. Technical Issue Fixed")
    print("  2. Missing Order Located")
    print("  3. Promotional Update")
    
    time.sleep(1)
    
    # Test 1: Technical Fixed
    test1 = test_trigger(
        "Technical Issue Fixed",
        {
            "trigger_type": "technical_fixed",
            "business_id": "biz_123",
            "customer_id": "cust_456",
            "context": {
                "ticket_id": "TKT-001",
                "issue_summary": "Payment gateway outage",
                "resolution": "Gateway restored, all transactions processing normally"
            },
            "personalization": {"first_name": "Alice"}
        }
    )
    
    time.sleep(2)
    
    # Test 2: Order Located
    test2 = test_trigger(
        "Missing Order Located",
        {
            "trigger_type": "order_located",
            "business_id": "biz_123",
            "customer_id": "cust_789",
            "context": {
                "order_id": "ORD-5678",
                "status": "located and ready for dispatch",
                "location": "Central Warehouse"
            },
            "personalization": {"first_name": "Bob"}
        }
    )
    
    time.sleep(2)
    
    # Test 3: Promotional Update
    test3 = test_trigger(
        "Promotional Update",
        {
            "trigger_type": "promotional_update",
            "business_id": "biz_123",
            "customer_id": "cust_321",
            "context": {
                "offer": "20% Yearly Loyalty Discount",
                "offer_title": "Exclusive Yearly Loyalty Bonus",
                "discount_percentage": 20,
                "expiry": "2026-12-31"
            },
            "personalization": {"first_name": "Carol"}
        }
    )
    
    # Summary
    print_header("📊 TEST SUMMARY")
    results = [
        ("Technical Issue Fixed", test1),
        ("Missing Order Located", test2),
        ("Promotional Update", test3)
    ]
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n🎯 Final Score: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready for production.")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")

if __name__ == "__main__":
    main()
