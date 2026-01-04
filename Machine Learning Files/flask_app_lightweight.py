from flask import Flask, request, jsonify, render_template_string
import json
import os
from inference_lightweight import add_and_predict

app = Flask(__name__)
log_path = 'sensor_log.txt'

@app.route('/api/data', methods=['POST'])
def receive_data():
    try:
        raw_data = request.get_data().decode('utf-8')
        if not raw_data:
            return jsonify({'error': 'Empty body'}), 400
        
        data = json.loads(raw_data)
        
        sensor_point = [
            data['ax'], data['ay'], data['az'],
            data['gx'], data['gy'], data['gz']
        ]
        
        prediction = add_and_predict(sensor_point)
        
        log_entry = {**data, 'prediction': prediction}
        with open(log_path, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return jsonify({
            'status': 'success',
            'prediction': prediction
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def view_data():
    data_list = []
    try:
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                for line in f:
                    try:
                        data_list.append(json.loads(line.strip()))
                    except:
                        pass
    except Exception as e:
        return f"Error: {str(e)}", 500
    
    data_list.reverse()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Activity Recognition Dashboard</title>
        <style>
            body { font-family: Arial; margin: 20px; background: #f5f5f5; }
            h1 { color: #333; }
            .stats { 
                background: white; 
                padding: 20px; 
                margin: 20px 0; 
                border-radius: 8px;
                display: flex;
                gap: 30px;
            }
            .stat-box { padding: 15px; border-radius: 5px; text-align: center; }
            .walking { background: #4CAF50; color: white; }
            .running { background: #2196F3; color: white; }
            table { width: 100%; border-collapse: collapse; background: white; }
            th { background: #333; color: white; padding: 12px; text-align: left; }
            td { padding: 10px; border-bottom: 1px solid #ddd; }
            .activity-badge { padding: 5px 10px; border-radius: 15px; color: white; font-weight: bold; }
            .badge-walking { background: #4CAF50; }
            .badge-running { background: #2196F3; }
        </style>
        <script>setTimeout(() => location.reload(), 5000);</script>
    </head>
    <body>
        <h1>🏃 Activity Recognition Dashboard</h1>
        <div class="stats">
            <div class="stat-box">
                <h3>Total Records</h3>
                <h2>{{ total }}</h2>
            </div>
            {% set walking = data_list|selectattr('prediction.activity', 'equalto', 'walking')|list|length %}
            {% set running = data_list|selectattr('prediction.activity', 'equalto', 'running')|list|length %}
            <div class="stat-box walking">
                <h3>Walking</h3>
                <h2>{{ walking }}</h2>
            </div>
            <div class="stat-box running">
                <h3>Running</h3>
                <h2>{{ running }}</h2>
            </div>
        </div>
        
        {% if data_list %}
        <table>
            <tr>
                <th>#</th>
                <th>Predicted Activity</th>
                <th>Confidence</th>
                <th>Accel (X,Y,Z)</th>
                <th>Gyro (X,Y,Z)</th>
            </tr>
            {% for data in data_list[:50] %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>
                    {% if data.prediction.activity %}
                    <span class="activity-badge badge-{{ data.prediction.activity }}">
                        {{ data.prediction.activity|upper }}
                    </span>
                    {% else %}
                    <span>Collecting...</span>
                    {% endif %}
                </td>
                <td>
                    {% if data.prediction.confidence %}
                    {{ "%.1f%%"|format(data.prediction.confidence * 100) }}
                    {% else %}
                    -
                    {% endif %}
                </td>
                <td>{{ "%.0f, %.0f, %.0f"|format(data.ax, data.ay, data.az) }}</td>
                <td>{{ "%.0f, %.0f, %.0f"|format(data.gx, data.gy, data.gz) }}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p>Waiting for sensor data...</p>
        {% endif %}
    </body>
    </html>
    """
    
    return render_template_string(html, data_list=data_list, total=len(data_list))

@app.route('/clear')
def clear_data():
    try:
        if os.path.exists(log_path):
            os.remove(log_path)
        return '<h2>Data cleared!</h2><a href="/">Go back</a>'
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run()
