from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

@app.route('/api/data', methods=['POST'])
def receive_data():
    try:
        # 1. Log headers for debugging (Check this in your Server Log)
        content_length = request.headers.get('Content-Length')
        content_type = request.headers.get('Content-Type')
        print(f"--- New Request ---")
        print(f"Content-Length: {content_length}")
        print(f"Content-Type: {content_type}")

        # 2. Get the raw data string
        raw_data = request.get_data().decode('utf-8')
        print(f"Raw data received: '{raw_data}'")

        if not raw_data:
            print("Error: Received an empty body")
            return "Body is empty", 400

        # 3. Parse the string into JSON
        try:
            data = json.loads(raw_data)
        except Exception as e:
            print(f"JSON Parse Error: {str(e)}")
            return "Invalid JSON format", 400

        # 4. Save to file
        log_path = '/home/cathlynramo/sensor_log.txt'
        with open(log_path, 'a') as f:
            f.write(json.dumps(data) + "\n")

        print("Successfully saved data to sensor_log.txt")
        return "SUCCESS", 200

    except Exception as e:
        print(f"Critical Server Error: {str(e)}")
        return f"Server Error: {str(e)}", 500

if __name__ == '__main__':
    app.run()
