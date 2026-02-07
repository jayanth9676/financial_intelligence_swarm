import urllib.request
import json
import time
import sys

BASE_URL = "http://localhost:8000"
UETR = "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e"

def pretty_print(data):
    print(json.dumps(data, indent=2))

def test_investigation():
    print(f"\n--- Testing Investigation for {UETR} ---")
    url = f"{BASE_URL}/investigate"
    data = json.dumps({"uetr": UETR}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req) as response:
            print("Response stream started...")
            for line in response:
                line = line.decode("utf-8").strip()
                if not line: continue
                
                if line.startswith("d:"):
                    data = json.loads(line[2:])
                    if data.get("type") == "tool_call":
                        print(f"[TOOL] {data.get('agent')}: {data.get('tool_name')}")
                    elif data.get("type") == "verdict":
                        print("[VERDICT] Received verdict")
                        # pretty_print(data)
    except Exception as e:
        print(f"Investigation failed: {e}")
        # If 404, maybe we need to ingest or seed?
        # But UETR should be seeded.

def test_annex_iv():
    print(f"\n--- Testing Annex IV for {UETR} ---")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/annex-iv/{UETR}") as response:
            data = json.loads(response.read().decode("utf-8"))
            print("Annex IV Data received:")
            print(f"System Name: {data.get('system_description', {}).get('name')}")
            print(f"Risk Level: {data.get('transaction_record', {}).get('risk_level')}")
    except Exception as e:
        print(f"Annex IV failed: {e}")

def test_sar_generation():
    print(f"\n--- Testing SAR Generation for {UETR} ---")
    try:
        # First generate
        req = urllib.request.Request(f"{BASE_URL}/generate-sar/{UETR}", method="POST")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            print(f"SAR Generated: {data.get('report_id')}")
            
        # Then check PDF endpoint (just check status)
        print("Checking SAR PDF endpoint...")
        pdf_url = f"{BASE_URL}/generate-sar-pdf/{UETR}"
        conn = urllib.request.urlopen(pdf_url)
        print(f"PDF Endpoint Status: {conn.getcode()}")
        print(f"Content-Type: {conn.headers.get('Content-Type')}")
    except Exception as e:
        print(f"SAR Generation failed: {e}")

if __name__ == "__main__":
    # Ensure backend is up
    try:
        urllib.request.urlopen(f"{BASE_URL}/")
    except:
        print("Backend not running? Please start uvicorn.")
        sys.exit(1)

    test_investigation()
    time.sleep(1)
    test_annex_iv()
    time.sleep(1)
    test_sar_generation()
