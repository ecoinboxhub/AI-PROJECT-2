# Quick Reference Card - Demo Payloads

## 🔗 URLs
- Business Owner AI: http://localhost:8001/docs
- Customer AI: http://localhost:8000/docs
- Voice Agent: http://localhost:8003/docs

## 📋 Test Payloads (Copy & Paste Ready)

### 1️⃣ Technical Issue Fixed
```json
{
  "trigger_type": "technical_fixed",
  "business_id": "biz_123",
  "customer_id": "cust_456",
  "context": {
    "ticket_id": "TKT-001",
    "issue_summary": "Payment gateway outage",
    "resolution": "Gateway restored, all transactions processing normally"
  },
  "personalization": {
    "first_name": "Alice"
  }
}
```

### 2️⃣ Missing Order Located
```json
{
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
```

### 3️⃣ Promotional Update (Yearly Discount)
```json
{
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
```

## 🎯 What to Show in Response

For each test, highlight:
- ✅ `ready_for_delivery: true`
- ✅ `message_content` (personalized message)
- ✅ `customer_context` (from Customer AI)
- ✅ `kb_confidence` (knowledge base integration)
- ✅ Logs showing Customer AI calls

## 🚀 Quick Commands

```bash
# Check server status
python check_servers.py

# Run full demo test
python demo_test.py

# Run smoke test
python smoke_test.py
```

## 📊 Expected Results

All tests should show:
- Status: 200 OK
- ready_for_delivery: true
- message_content: Non-empty personalized message
- Voice session: Generated with audio

## ✅ Success Checklist

- [ ] All 3 servers running
- [ ] Technical fixed trigger works
- [ ] Order located trigger works  
- [ ] Promotional update trigger works
- [ ] Voice Agent generates audio
- [ ] Automated tests pass (3/3)
