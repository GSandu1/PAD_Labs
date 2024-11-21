from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
STOCK_PREDICTION_URL = "http://stock-prediction-service:5000"
USER_MANAGEMENT_URL = "http://user-management-service:5002"
TIMEOUT = 5  # Timeout for requests in seconds

# ----------- Stock Prediction Service Endpoints -----------

@app.route('/api/stocks/<symbol>/details', methods=['GET'])
def get_stock_details(symbol):
    try:
        response = requests.get(f"{STOCK_PREDICTION_URL}/api/stocks/{symbol}/details", timeout=TIMEOUT)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "Stock Data Service request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/predict/<symbol>', methods=['GET'])
def predict_stock(symbol):
    try:
        response = requests.get(f"{STOCK_PREDICTION_URL}/api/predict/{symbol}", timeout=TIMEOUT)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "Prediction Service request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/transactions/store', methods=['POST'])
def store_transaction():
    try:
        response = requests.post(f"{STOCK_PREDICTION_URL}/api/transactions/store", json=request.json, timeout=TIMEOUT)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "Transaction storage request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

# ----------- User Management Service Endpoints -----------

@app.route('/api/users/register', methods=['POST'])
def register_user():
    try:
        response = requests.post(f"{USER_MANAGEMENT_URL}/api/users/register", json=request.json, timeout=TIMEOUT)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "User registration request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/users/login', methods=['POST'])
def login_user():
    try:
        response = requests.post(f"{USER_MANAGEMENT_URL}/api/users/login", json=request.json, timeout=TIMEOUT)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "User login request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/users/profile', methods=['GET'])
def get_user_profile():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Token missing"}), 401
    try:
        response = requests.get(f"{USER_MANAGEMENT_URL}/api/users/profile", headers={'Authorization': token}, timeout=TIMEOUT)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "User profile retrieval request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/users/profile/update', methods=['POST'])
def update_user_profile():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Token missing"}), 401
    try:
        response = requests.post(
            f"{USER_MANAGEMENT_URL}/api/users/profile/update",
            json=request.json,
            headers={'Authorization': token},
            timeout=TIMEOUT
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "User profile update request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/users/buy', methods=['POST'])
def buy_stock():
    try:
        response = requests.post(f"{USER_MANAGEMENT_URL}/api/users/buy", json=request.json, timeout=TIMEOUT)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "User buy request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/users/sell', methods=['POST'])
def sell_stock():
    try:
        response = requests.post(f"{USER_MANAGEMENT_URL}/api/users/sell", json=request.json, timeout=TIMEOUT)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.Timeout:
        return jsonify({"error": "User sell request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

# ----------- Gateway Status Endpoint -----------

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"message": "API Gateway is running!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
