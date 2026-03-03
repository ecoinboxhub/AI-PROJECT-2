"""
Demo Test Script for Outbound Implementation
Demonstrates all three trigger types with detailed output
"""

import requests
import json
import time
from datetime import datetime

# Server URLs
BUSINESS_AI_URL = "http://localhost:8001"
CUSTOMER_AI_URL = "http://localhost:8000"
VOICE_AGENT_URL = "http://localhost:8003"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_result(label, data):
    """Print formatted result"""
    print(f"\n{label}:")
    print(json.dumps(data, indent=2))
    print()

def test_1_technical_fixed():
    """Test 1: Technical Issue Fixed Notification"""
    print_section("TEST 1: TECHNICAL ISSUE FIXED")
    
    print("📋 Scenario: Payment gateway was down, now fixed")
    print("   Customer: Alice (cust_456)")
    print("   Business: Tech Store (biz_123)")
    
    trigger_payload = {
        "trigger_type": "technical_fixed",
        "business_id": "biz_123",
        "customer_id": "cust_456",
        "context": {
            "ticket_id": "TKT-001",
            "issue_summary": "Payment gateway outage",
            "resolution": "Gateway restored, all transactions processing normally",
            "resolved_at": datetime.now().isoformat()
        },
        "personalization": {
            "first_name": "Alice"
        }
    }
    
    print("\n🔄 Step 1: Posting trigger to Business Owner AI...")
    print(f"   Endpoint: POST {BUSINESS_AI_URL}/api/v1/orchestrator/triggers")
    
    try:
        response = requests.post(
            f"{BUSINESS_AI_URL}/api/v1/orchestrator/triggers",
            json=trigger_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ SUCCESS!")
            print(f"   Trace ID: {result.get('trace_id')}")
            print(f"   Ready for delivery: {result.get('ready_for_delivery')}")
            print(f"   Message: {result.get('message_content', 'N/A')[:100]}...")
            
            # Step 2: Prepare voice session
            if result.get('message_content'):
                print("\n🔄 Step 2: Preparing voice session...")
                print(f"   Endpoint: POST {VOICE_AGENT_URL}/api/v1/outbound/session-prepare")
                
                voice_payload = {
                    "trigger_id": result.get('trace_id'),
                    "trigger_type": "technical_fixed",
                    "business_id": "biz_123",
                    "business_name": "Tech Store",
                    "customer_id": "cust_456",
                    "message_content": result.get('message_content'),
                    "personalization": trigger_payload['personalization'],
                    "context": trigger_payload['context']
                }
                
                voice_response = requests.post(
                    f"{VOICE_AGENT_URL}/api/v1/outbound/session-prepare",
                    json=voice_payload,
                    timeout=15
                )
                
                if voice_response.status_code == 200:
                    voice_result = voice_response.json()
                    print("   ✅ SUCCESS!")
                    print(f"   Session ID: {voice_result.get('session_id')}")
                    print(f"   Greeting: {voice_result.get('greeting', {}).get('text', 'N/A')[:100]}...")
                    print(f"   Audio generated: {'Yes' if voice_result.get('greeting', {}).get('audio_base64') else 'No'}")
                    
                    return True, result, voice_result
                else:
                    print(f"   ❌ FAILED: {voice_response.status_code}")
                    print(f"   Error: {voice_response.text}")
                    return False, result, None
        else:
            print(f"   ❌ FAILED: {response.status_code}")
            print(f"   Error: {response.text}")
            return False, None, None
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return False, None, None

def test_2_order_located():
    """Test 2: Missing Order Found"""
    print_section("TEST 2: MISSING ORDER LOCATED")
    
    print("📋 Scenario: Customer's missing order has been found")
    print("   Customer: Bob (cust_789)")
    print("   Order: ORD-5678")
    
    trigger_payload = {
        "trigger_type": "order_located",
        "business_id": "biz_123",
        "customer_id": "cust_789",
        "context": {
            "order_id": "ORD-5678",
            "status": "located and ready for dispatch",
            "location": "Central Warehouse",
            "expected_delivery": "Tomorrow"
        },
        "personalization": {
            "first_name": "Bob"
        }
    }
    
    print("\n🔄 Step 1: Posting trigger to Business Owner AI...")
    
    try:
        response = requests.post(
            f"{BUSINESS_AI_URL}/api/v1/orchestrator/triggers",
            json=trigger_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ SUCCESS!")
            print(f"   Message: {result.get('message_content', 'N/A')[:100]}...")
            
            if result.get('message_content'):
                print("\n🔄 Step 2: Preparing voice session...")
                
                voice_payload = {
                    "trigger_id": result.get('trace_id'),
                    "trigger_type": "order_located",
                    "business_id": "biz_123",
                    "business_name": "Tech Store",
                    "customer_id": "cust_789",
                    "message_content": result.get('message_content'),
                    "personalization": trigger_payload['personalization'],
                    "context": trigger_payload['context']
                }
                
                voice_response = requests.post(
                    f"{VOICE_AGENT_URL}/api/v1/outbound/session-prepare",
                    json=voice_payload,
                    timeout=15
                )
                
                if voice_response.status_code == 200:
                    voice_result = voice_response.json()
                    print("   ✅ SUCCESS!")
                    print(f"   Greeting: {voice_result.get('greeting', {}).get('text', 'N/A')[:100]}...")
                    return True, result, voice_result
                    
        return False, None, None
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return False, None, None

def test_3_promotional_update():
    """Test 3: Promotional Offer (Yearly Discount)"""
    print_section("TEST 3: PROMOTIONAL UPDATE - YEARLY DISCOUNT")
    
    print("📋 Scenario: Customer qualifies for yearly loyalty discount")
    print("   Customer: Carol (cust_321)")
    print("   Offer: 20% Yearly Loyalty Discount")
    
    trigger_payload = {
        "trigger_type": "promotional_update",
        "business_id": "biz_123",
        "customer_id": "cust_321",
        "context": {
            "offer": "20% Yearly Loyalty Discount",
            "offer_title": "Exclusive Yearly Loyalty Bonus",
            "discount_percentage": 20,
            "expiry": "2026-12-31",
            "bonus_points": 500
        },
        "personalization": {
            "first_name": "Carol"
        }
    }
    
    print("\n🔄 Step 1: Posting trigger to Business Owner AI...")
    
    try:
        response = requests.post(
            f"{BUSINESS_AI_URL}/api/v1/orchestrator/triggers",
            json=trigger_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ SUCCESS!")
            print(f"   Message: {result.get('message_content', 'N/A')[:100]}...")
            
            if result.get('message_content'):
                print("\n🔄 Step 2: Preparing voice session...")
                
                voice_payload = {
                    "trigger_id": result.get('trace_id'),
                    "trigger_type": "promotional_update",
                    "business_id": "biz_123",
                    "business_name": "Tech Store",
                    "customer_id": "cust_321",
                    "message_content": result.get('message_content'),
                    "personalization": trigger_payload['personalization'],
                    "context": trigger_payload['context']
                }
                
                voice_response = requests.post(
                    f"{VOICE_AGENT_URL}/api/v1/outbound/session-prepare",
                    json=voice_payload,
                    timeout=15
                )
                
                if voice_response.status_code == 200:
                    voice_result = voice_response.json()
                    print("   ✅ SUCCESS!")
                    print(f"   Greeting: {voice_result.get('greeting', {}).get('text', 'N/A')[:100]}...")
                    return True, result, voice_result
                    
        return False, None, None
            
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return False, None, None

def main():
    """Run all tests"""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  OUTBOUND CALL IMPLEMENTATION - COMPREHENSIVE DEMO TEST".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    print(f"\n📡 Server Status Check:")
    print(f"   Business Owner AI: {BUSINESS_AI_URL}")
    print(f"   Customer AI: {CUSTOMER_AI_URL}")
    print(f"   Voice Agent: {VOICE_AGENT_URL}")
    
    # Check servers
    try:
        r1 = requests.get(f"{BUSINESS_AI_URL}/health", timeout=5)
        print(f"   ✅ Business Owner AI: {r1.status_code}")
    except:
        print(f"   ❌ Business Owner AI: Not responding")
        
    try:
        r2 = requests.get(f"{CUSTOMER_AI_URL}/health", timeout=5)
        print(f"   ✅ Customer AI: {r2.status_code}")
    except:
        print(f"   ❌ Customer AI: Not responding")
        
    try:
        r3 = requests.get(f"{VOICE_AGENT_URL}/health", timeout=5)
        print(f"   ✅ Voice Agent: {r3.status_code}")
    except:
        print(f"   ❌ Voice Agent: Not responding")
    
    results = []
    
    # Run tests
    print("\n\n🚀 Starting Tests...\n")
    time.sleep(1)
    
    # Test 1
    success1, orch1, voice1 = test_1_technical_fixed()
    results.append(("Technical Fixed", success1))
    time.sleep(2)
    
    # Test 2
    success2, orch2, voice2 = test_2_order_located()
    results.append(("Order Located", success2))
    time.sleep(2)
    
    # Test 3
    success3, orch3, voice3 = test_3_promotional_update()
    results.append(("Promotional Update", success3))
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}  {test_name}")
    
    print(f"\n   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n   🎉 ALL TESTS PASSED! Implementation is fully functional!")
    else:
        print(f"\n   ⚠️  {total - passed} test(s) failed. Check logs above.")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
