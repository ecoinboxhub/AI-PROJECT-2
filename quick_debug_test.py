"""Quick debug test to see actual orchestrator response"""
import requests
import json

BUSINESS_AI_URL = "http://localhost:8001"

trigger_payload = {
    "trigger_type": "technical_fixed",
    "business_id": "biz_123",
    "customer_id": "cust_456",
    "context": {
        "ticket_id": "TKT-001",
        "issue_summary": "Payment gateway outage",
        "resolution": "Gateway restored"
    },
    "personalization": {
        "first_name": "Alice"
    }
}

print("Posting trigger to Business Owner AI...")
response = requests.post(
    f"{BUSINESS_AI_URL}/api/v1/orchestrator/triggers",
    json=trigger_payload,
    timeout=30
)

print(f"\nStatus Code: {response.status_code}")
print(f"\nFull Response:")
print(json.dumps(response.json(), indent=2))
