"""
Lightweight inference using scikit-learn (no TensorFlow needed!)
"""

import numpy as np
import pickle
import json

# Load model and scaler
with open('lightweight_model.pkl', 'rb') as f:
    model = pickle.load(f)

with open('scaler_params.json', 'r') as f:
    scaler_params = json.load(f)

WINDOW_SIZE = scaler_params['window_size']
N_FEATURES = scaler_params['n_features']
MEAN = np.array(scaler_params['mean'])
STD = np.array(scaler_params['std'])

sensor_buffer = []

def preprocess_data(data_point):
    data_array = np.array(data_point)
    normalized = (data_array - MEAN) / (STD + 1e-8)
    return normalized

def extract_features(window):
    """Extract statistical features from a window"""
    window_array = np.array(window)
    features = []
    
    for axis in range(6):
        axis_data = window_array[:, axis]
        features.extend([
            np.mean(axis_data),
            np.std(axis_data),
            np.min(axis_data),
            np.max(axis_data),
            np.median(axis_data)
        ])
    
    return features

def predict_activity(sensor_data):
    if len(sensor_data) < WINDOW_SIZE:
        return {
            'error': f'Need {WINDOW_SIZE} samples, got {len(sensor_data)}',
            'activity': None,
            'confidence': None
        }
    
    window = sensor_data[-WINDOW_SIZE:]
    normalized = [preprocess_data(point) for point in window]
    features = extract_features(normalized)
    
    # Predict
    prediction = model.predict([features])[0]
    probabilities = model.predict_proba([features])[0]
    
    activity = "running" if prediction == 1 else "walking"
    confidence = float(max(probabilities))
    
    return {
        'activity': activity,
        'confidence': confidence,
        'probability': float(probabilities[1])
    }

def add_and_predict(data_point):
    global sensor_buffer
    
    sensor_buffer.append(data_point)
    
    if len(sensor_buffer) > WINDOW_SIZE:
        sensor_buffer = sensor_buffer[-WINDOW_SIZE:]
    
    if len(sensor_buffer) == WINDOW_SIZE:
        return predict_activity(sensor_buffer)
    else:
        return {
            'status': 'collecting',
            'samples_needed': WINDOW_SIZE - len(sensor_buffer),
            'activity': None
        }
