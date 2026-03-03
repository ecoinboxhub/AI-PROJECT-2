"""Quick test to see actual response"""
import requests
import json

payload = {
    "trigger_type": "technical_fixed",
    "business_id": "biz_123",
    "customer_id": "cust_456",
    "context": {
        "issue_summary": "Payment gateway outage",
        "resolution": "Gateway restored"
    },
    "personalization": {"first_name": "Alice"}
}

print("Sending request...")
response = requests.post(
    "http://localhost:8001/api/v1/orchestrator/triggers",
    json=payload,
    timeout=30
)

print(f"\nStatus: {response.status_code}")
print(f"\nResponse:")
print(json.dumps(response.json(), indent=2))
