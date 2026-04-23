from flask import Flask, render_template, jsonify, request
import json
import os
import time

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data.json')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
STATUS_FILE = os.path.join(BASE_DIR, 'status.json')
REFRESH_FLAG = os.path.join(BASE_DIR, 'refresh.flag')

DEFAULT_BRANDS = [
    "Roland", "Korg", "Yamaha", "Waldorf", "Kawai", "E-mu", "Akai", 
    "Ensoniq", "Oberheim", "Casio", "Alesis", "Sequential", "Moog", 
    "Nord", "Arturia", "Novation", "Elektron", "Access",
    "Quasimidi", "Kurzweil", "Hohner", "Crumar", "Vermona", "Simmons"
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    if os.path.exists(DATA_FILE):
        for _ in range(3): # Retry logic para lectura
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return jsonify({"status": "success", "data": data})
            except json.JSONDecodeError:
                time.sleep(0.2)
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500
                
    return jsonify({"status": "error", "message": "No data available yet."}), 404

@app.route('/api/status')
def get_status():
    if os.path.exists(STATUS_FILE):
        for _ in range(3):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                    return jsonify({"status": "success", "data": status_data})
            except json.JSONDecodeError:
                time.sleep(0.2)
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "success", "data": {"state": "idle", "progress": 0}}), 200

@app.route('/api/trigger_search', methods=['POST'])
def trigger_search():
    try:
        with open(REFRESH_FLAG, 'w') as f:
            f.write('1')
        return jsonify({"status": "success", "message": "Search triggered."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def manage_config():
    if request.method == 'POST':
        # Save new configuration
        new_config = request.json
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=4)
            return jsonify({"status": "success", "config": new_config})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        # Get configuration
        if not os.path.exists(CONFIG_FILE):
            try:
                default_config = {"brands": {b: True for b in DEFAULT_BRANDS}}
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=4)
            except Exception as e:
                pass # let it fall through and try to read
                
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return jsonify({"status": "success", "config": config})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500
        else:
            return jsonify({"status": "error", "message": "Could not read or create config."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
