from flask import Flask, send_from_directory, jsonify
import json

app = Flask(__name__, static_url_path='')

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')  # Serve as static file

@app.route('/api/data')
def get_data():
    try:
        with open('call_log.json', 'r') as file:
            data = json.load(file)
            return jsonify(data)
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=8100)