import httpx
import asyncio
import json

API_URL = "http://127.0.0.1:8000"
UETR = "eb9a5c8e-2f3b-4c7a-9d1e-5f8a2b3c4d5e"

async def check_stream_duplicates():
    print(f"Checking stream for UETR: {UETR}")
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        # 1. Clear data first to ensure fresh start (optional, but good for restart test)
        # await client.post(f"{API_URL}/clear-data") 
        # await client.post(f"{API_URL}/ingest", json=...) # We assume data exists
        
        message_counts = {}
        
        async with client.stream("POST", f"{API_URL}/investigate", json={"uetr": UETR}) as response:
            async for line in response.aiter_lines():
                if line.startswith("d:"):
                    data = json.loads(line[2:])
                    if data.get("type") == "message":
                        content = data.get("content", "")[:50] # Check first 50 chars
                        agent = data.get("speaker", "unknown")
                        key = f"{agent}:{content}"
                        message_counts[key] = message_counts.get(key, 0) + 1
                        print(f"Received ({message_counts[key]}): {agent} - {content}...")

    print("\n--- Summary ---")
    for key, count in message_counts.items():
        if count > 1:
            print(f"DUPLICATE FOUND ({count}x): {key}")
        else:
            print(f"Unique: {key}")

if __name__ == "__main__":
    asyncio.run(check_stream_duplicates())
