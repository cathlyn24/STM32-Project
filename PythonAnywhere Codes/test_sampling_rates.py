import time
import requests
from collections import deque
import statistics

# Test different sampling rates
SAMPLING_RATES = [10, 5, 2, 1, 0.5]  # seconds between samples
TEST_DURATION = 60  # 1 minute test per rate

def test_sampling_rate(interval_seconds):
    """Test a specific sampling rate"""
    print(f"\n=== Testing {interval_seconds}s interval ===")

    samples = []
    start_time = time.time()
    sample_count = 0

    while time.time() - start_time < TEST_DURATION:
        try:
            # Simulate getting data from device management platform
            response = requests.get('YOUR_DEVICE_PLATFORM_API/readings', timeout=5)
            if response.status_code == 200:
                data = response.json()
                samples.append(data)
                sample_count += 1
        except Exception as e:
            print(f"Error: {e}")

        time.sleep(interval_seconds)

    print(f"Collected {sample_count} samples in {TEST_DURATION}s")
    print(f"Average rate: {sample_count/TEST_DURATION:.2f} samples/second")
    return sample_count

# Run tests
for rate in SAMPLING_RATES:
    test_sampling_rate(rate)

