# 🎬 Quick Reference for Screen Recording Demo

## ✅ Pre-Recording Checklist

- [ ] All 3 servers running (check with browser tabs)
- [ ] Browser zoom at 125-150% for visibility
- [ ] Terminal font size increased
- [ ] Close unnecessary applications
- [ ] Prepare talking points

## 🌐 URLs to Open in Browser

1. **Business Owner AI**: http://localhost:8001/docs
2. **Customer AI**: http://localhost:8000/docs
3. **Voice Agent**: http://localhost:8003/docs

## 🎯 Demo Flow (7 minutes)

### 1. Introduction (30 sec)
"Demonstrating AI-powered outbound call system with three trigger types: technical fixes, order updates, and promotional offers."

### 2. Show Swagger UIs (30 sec)
- Open all three tabs
- Show they're all operational
- Explain the architecture briefly

### 3. Test 1: Technical Issue Fixed (2 min)

**Endpoint**: POST `/api/v1/orchestrator/triggers` on Business AI

**Payload** (copy-paste ready):
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

**What to say**: "Payment gateway was down, now restored. System automatically notifies customer Alice."

**What to show**: 
- `ready_for_delivery: true`
- `message_content` field
- Logs showing Customer AI calls

### 4. Test 2: Missing Order Located (2 min)

**Same endpoint**, different payload:
```json
{
  "trigger_type": "order_located",
  "business_id": "biz_123",
  "customer_id": "cust_789",
  "context": {
    "order_id": "ORD-5678",
    "status": "located and ready for dispatch",
    "location": "Central Warehouse"
  },
  "personalization": {
    "first_name": "Bob"
  }
}
```

**What to say**: "Customer Bob's missing order found. System prepares notification with order details."

### 5. Test 3: Promotional Offer (2 min)

**Same endpoint**, different payload:
```json
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
  "personalization": {
    "first_name": "Carol"
  }
}
```

**What to say**: "Yearly loyalty discount for customer Carol. Targeted promotional automation."

### 6. Run Automated Test (1 min)

**Command**:
```bash
python demo_test.py
```

**What to say**: "Automated test suite validates all three scenarios end-to-end."

**What to show**: All ✅ marks and final score 3/3

### 7. Conclusion (30 sec)
"System successfully:
- Detects triggers automatically
- Retrieves customer context
- Composes personalized messages
- Prepares voice sessions with audio
- All three trigger types working perfectly"

## 🎤 Key Talking Points

1. **Automatic Detection**: No manual intervention needed
2. **Personalization**: Uses customer names and specific details
3. **Three Trigger Types**: Technical, Orders, Promotions
4. **End-to-End**: Business AI → Customer AI → Voice Agent
5. **Production Ready**: All tests passing

## 📊 Success Metrics to Highlight

- ✅ 3/3 servers operational
- ✅ 3/3 trigger types working
- ✅ Customer AI integration successful
- ✅ Voice Agent audio synthesis working
- ✅ 100% test pass rate

## 💡 Recording Tips

1. **Speak slowly and clearly**
2. **Pause after each successful response** (2-3 seconds)
3. **Highlight key JSON fields** with cursor
4. **Keep terminal visible** during automated test
5. **Smile** - confidence shows!

## 🚀 Emergency Commands

If servers crash during recording:

```bash
# Terminal 1
cd business_owner_ai && C:\Python314\python.exe main.py

# Terminal 2
cd customer_ai && C:\Python314\python.exe main.py

# Terminal 3
cd voice_agent && C:\Python314\python.exe main.py
```

Wait 15 seconds for all to start, then continue.

## ✨ Final Checklist Before Recording

- [ ] All servers running (check browser tabs)
- [ ] demo_test.py works (run once to verify)
- [ ] Browser tabs arranged nicely
- [ ] Terminal ready with increased font
- [ ] Payloads copied to clipboard or notepad
- [ ] Deep breath - you got this! 🎉

---

**Total Time**: 7 minutes
**Difficulty**: Easy
**Success Rate**: 100% ✅

Good luck with your presentation! 🚀
