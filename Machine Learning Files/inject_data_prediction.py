import requests
import time

url = "https://cathlynramo.pythonanywhere.com/api/upload"

print("Sending 60 sensor readings...")
for i in range(60):
    data = {
        "ax": -0.037 + (i % 10) * 0.001,
        "ay": 0.001 + (i % 5) * 0.001,
        "az": 1.005 + (i % 8) * 0.002,
        "gx": 0,
        "gy": 0,
        "gz": 0
    }
    
    response = requests.post(url, json=data)
    if response.status_code == 200:
        print(f"✓ Sent {i+1}/60", end='\r')
    else:
        print(f"\n✗ Failed at {i+1}")
        break
    
    time.sleep(0.1)

print("\n✓ Done! Wait 10 seconds for prediction...")
time.sleep(10)

# Check result
response = requests.get(f"{url.replace('/upload', '/realtime')}")
print(f"\nResult: {response.json()}")
