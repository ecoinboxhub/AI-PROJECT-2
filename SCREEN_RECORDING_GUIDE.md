# Screen Recording Demo Guide - Outbound Call Implementation

## ✅ All Systems Operational

All three servers are running and fully functional:
- **Business Owner AI**: http://localhost:8001
- **Customer AI**: http://localhost:8000  
- **Voice Agent**: http://localhost:8003

## 🎬 Demo Script for Screen Recording

### Introduction (30 seconds)
"Today I'm demonstrating our AI-powered outbound call system. This system automatically detects business triggers and proactively contacts customers with personalized messages via voice calls."

### Demo Flow (5-7 minutes)

#### 1. Show System Architecture (1 minute)
- Open browser tabs for all three Swagger UIs:
  - http://localhost:8001/docs (Business Owner AI)
  - http://localhost:8000/docs (Customer AI)
  - http://localhost:8003/docs (Voice Agent)
- Explain: "Three AI services work together - Business AI detects triggers, Customer AI provides context, Voice Agent makes the call"

#### 2. Demo Test 1: Technical Issue Fixed (2 minutes)

**Navigate to**: http://localhost:8001/docs → POST `/api/v1/orchestrator/triggers`

**Payload**:
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

**Say**: "Let's simulate a technical issue that was just fixed. The payment gateway was down and is now restored. Watch how the system automatically prepares a customer notification."

**Show Response**:
- Point out `ready_for_delivery: true`
- Point out `message_content` with personalized greeting
- Point out the logs showing Customer AI integration

#### 3. Demo Test 2: Missing Order Located (2 minutes)

**Same endpoint**, new payload:
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

**Say**: "Now a customer's missing order has been found. The system automatically notifies them with order details."

**Show Response**: Highlight the order-specific message content

#### 4. Demo Test 3: Promotional Offer (2 minutes)

**Same endpoint**, new payload:
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

**Say**: "Finally, let's send a promotional offer - a yearly loyalty discount. This demonstrates targeted marketing automation."

**Show Response**: Highlight the promotional message with expiry date

#### 5. Voice Agent Integration (1 minute)

**Navigate to**: http://localhost:8003/docs → POST `/api/v1/outbound/session-prepare`

**Use the orchestration response** from any previous test and show:
- Session ID generated
- Greeting text prepared
- Audio synthesized (base64 encoded)

**Say**: "The Voice Agent receives the message and prepares everything needed for the actual phone call - including text-to-speech audio synthesis."

#### 6. Run Automated Test (1 minute)

**Open terminal** and run:
```bash
python demo_test.py
```

**Say**: "Here's our automated test suite running all three scenarios end-to-end. Watch as it tests technical fixes, order notifications, and promotional offers."

**Show**: All tests passing with ✅ marks

### Conclusion (30 seconds)
"As you can see, the system successfully:
1. Detects business triggers automatically
2. Retrieves customer context from Customer AI
3. Composes personalized messages
4. Prepares voice sessions for outbound calls
5. All three trigger types work flawlessly: technical fixes, order updates, and promotions"

## 📊 Key Points to Emphasize

1. **Automatic Detection**: System automatically detects when to call customers
2. **Personalization**: Uses customer names and specific details
3. **Three Trigger Types**: 
   - Technical fixes (service restoration)
   - Order updates (missing orders found)
   - Promotions (bonuses, discounts)
4. **End-to-End Integration**: Business AI → Customer AI → Voice Agent
5. **Production Ready**: All tests passing, error handling in place

## 🎯 Success Metrics to Show

- ✅ All 3 servers running
- ✅ All 3 trigger types working
- ✅ Customer AI integration successful
- ✅ Voice Agent session preparation working
- ✅ Audio synthesis functional
- ✅ Automated tests: 3/3 passing

## 💡 Tips for Recording

1. **Zoom in** on browser for better visibility
2. **Slow down** when showing JSON payloads
3. **Highlight** key fields in responses (message_content, ready_for_delivery)
4. **Pause** briefly after each successful response
5. **Keep terminal visible** when running automated tests
6. **Total time**: Aim for 5-7 minutes maximum

## 🚀 Quick Start Commands

```bash
# If servers aren't running, start them:
cd business_owner_ai && python main.py  # Terminal 1
cd customer_ai && python main.py        # Terminal 2
cd voice_agent && python main.py        # Terminal 3

# Run automated test:
python demo_test.py

# Run smoke test:
python smoke_test.py
```

---

**Ready to record!** All systems are operational and tested. Good luck with your presentation! 🎉
