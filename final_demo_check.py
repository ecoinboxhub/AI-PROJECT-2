"""
Final Demo Check - Verify all systems before screen recording
Quick health check for all three services
"""

import requests
import sys

def check_service(name, url, port):
    """Check if a service is responding"""
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            print(f"✅ {name} (Port {port}): OPERATIONAL")
            return True
        else:
            print(f"⚠️  {name} (Port {port}): Responding but status {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ {name} (Port {port}): NOT RESPONDING - {str(e)}")
        return False

def main():
    print("="*70)
    print("  🔍 FINAL DEMO CHECK - System Health Verification")
    print("="*70)
    print()
    
    services = [
        ("Business Owner AI", "http://localhost:8001/health", 8001),
        ("Customer AI", "http://localhost:8000/health", 8000),
        ("Voice Agent", "http://localhost:8003/health", 8003)
    ]
    
    results = []
    for name, url, port in services:
        results.append(check_service(name, url, port))
    
    print()
    print("="*70)
    
    if all(results):
        print("  ✅ ALL SYSTEMS OPERATIONAL - READY FOR DEMO!")
        print("="*70)
        print()
        print("📋 Next Steps:")
        print("  1. Open browser tabs:")
        print("     - http://localhost:8001/docs (Business Owner AI)")
        print("     - http://localhost:8000/docs (Customer AI)")
        print("     - http://localhost:8003/docs (Voice Agent)")
        print()
        print("  2. Run demo test:")
        print("     python demo_test.py")
        print()
        print("  3. Start recording!")
        print()
        print("🎬 Good luck with your presentation! 🚀")
        return 0
    else:
        print("  ⚠️  SOME SYSTEMS NOT RESPONDING")
        print("="*70)
        print()
        print("🔧 Troubleshooting:")
        print("  1. Check if servers are running")
        print("  2. Wait 15 seconds and try again")
        print("  3. Restart servers if needed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
