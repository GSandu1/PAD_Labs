# from flask import Flask, request, jsonify
# import requests

# app = Flask(__name__)
# TIMEOUT = 5  # Timeout for requests in seconds

# # Update service URLs to point to Nginx
# NGINX_URL = "http://nginx"

# # ----------- Stock Prediction Service Endpoints -----------

# @app.route('/api/stocks/<symbol>/details', methods=['GET'])
# def get_stock_details(symbol):
#     try:
#         response = requests.get(f"{NGINX_URL}/stock-prediction/api/stocks/{symbol}/details", timeout=TIMEOUT)
#         return jsonify(response.json()), response.status_code
#     except requests.exceptions.Timeout:
#         return jsonify({"error": "Stock Data Service request timed out"}), 504
#     except requests.exceptions.RequestException as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/predict/<symbol>', methods=['GET'])
# def predict_stock(symbol):
#     try:
#         response = requests.get(f"{NGINX_URL}/stock-prediction/api/predict/{symbol}", timeout=TIMEOUT)
#         return jsonify(response.json()), response.status_code
#     except requests.exceptions.Timeout:
#         return jsonify({"error": "Prediction Service request timed out"}), 504
#     except requests.exceptions.RequestException as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/transactions/store', methods=['POST'])
# def store_transaction():
#     try:
#         response = requests.post(f"{NGINX_URL}/stock-prediction/api/transactions/store", json=request.json, timeout=TIMEOUT)
#         return jsonify(response.json()), response.status_code
#     except requests.exceptions.Timeout:
#         return jsonify({"error": "Transaction storage request timed out"}), 504
#     except requests.exceptions.RequestException as e:
#         return jsonify({"error": str(e)}), 500

# # ----------- User Management Service Endpoints -----------

# @app.route('/api/users/register', methods=['POST'])
# def register_user():
#     try:
#         response = requests.post(f"{NGINX_URL}/user-management/api/users/register", json=request.json, timeout=TIMEOUT)
#         return jsonify(response.json()), response.status_code
#     except requests.exceptions.Timeout:
#         return jsonify({"error": "User registration request timed out"}), 504
#     except requests.exceptions.RequestException as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/users/login', methods=['POST'])
# def login_user():
#     try:
#         response = requests.post(f"{NGINX_URL}/user-management/api/users/login", json=request.json, timeout=TIMEOUT)
#         return jsonify(response.json()), response.status_code
#     except requests.exceptions.Timeout:
#         return jsonify({"error": "User login request timed out"}), 504
#     except requests.exceptions.RequestException as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/users/profile', methods=['GET'])
# def get_user_profile():
#     token = request.headers.get('Authorization')
#     if not token:
#         return jsonify({"error": "Token missing"}), 401
#     try:
#         response = requests.get(f"{NGINX_URL}/user-management/api/users/profile", headers={'Authorization': token}, timeout=TIMEOUT)
#         return jsonify(response.json()), response.status_code
#     except requests.exceptions.Timeout:
#         return jsonify({"error": "User profile retrieval request timed out"}), 504
#     except requests.exceptions.RequestException as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/users/profile/update', methods=['POST'])
# def update_user_profile():
#     token = request.headers.get('Authorization')
#     if not token:
#         return jsonify({"error": "Token missing"}), 401
#     try:
#         response = requests.post(
#             f"{NGINX_URL}/user-management/api/users/profile/update",
#             json=request.json,
#             headers={'Authorization': token},
#             timeout=TIMEOUT
#         )
#         return jsonify(response.json()), response.status_code
#     except requests.exceptions.Timeout:
#         return jsonify({"error": "User profile update request timed out"}), 504
#     except requests.exceptions.RequestException as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/users/buy', methods=['POST'])
# def buy_stock():
#     try:
#         response = requests.post(f"{NGINX_URL}/user-management/api/users/buy", json=request.json, timeout=TIMEOUT)
#         return jsonify(response.json()), response.status_code
#     except requests.exceptions.Timeout:
#         return jsonify({"error": "User buy request timed out"}), 504
#     except requests.exceptions.RequestException as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/users/sell', methods=['POST'])
# def sell_stock():
#     try:
#         response = requests.post(f"{NGINX_URL}/user-management/api/users/sell", json=request.json, timeout=TIMEOUT)
#         return jsonify(response.json()), response.status_code
#     except requests.exceptions.Timeout:
#         return jsonify({"error": "User sell request timed out"}), 504
#     except requests.exceptions.RequestException as e:
#         return jsonify({"error": str(e)}), 500

# # ----------- Gateway Status Endpoint -----------

# @app.route('/status', methods=['GET'])
# def status():
#     return jsonify({"message": "API Gateway is running!"})

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=3000)

import time
import logging
from flask import Flask, request, jsonify
import requests
from threading import Lock

app = Flask(__name__)
TIMEOUT = 5 
# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Circuit Breaker Configuration
MAX_RETRIES = 3          # Number of retries per request
FAILURE_THRESHOLD = 2    # Number of failures before opening the circuit
RESET_TIMEOUT = 10       # Time in seconds to wait before attempting to reset the circuit

# Update service URLs to point to Nginx
NGINX_URL = "http://nginx"

class CircuitBreaker:
    def __init__(self, name):
        self.name = name
        self.state = 'CLOSED'
        self.failure_count = 0
        self.last_failure_time = None
        self.lock = Lock()

    def call(self, func, *args, **kwargs):
        with self.lock:
            if self.state == 'OPEN':
                if time.time() - self.last_failure_time > RESET_TIMEOUT:
                    self.state = 'HALF-OPEN'
                    logger.info(f"[{self.name}] Circuit breaker is HALF-OPEN. Testing the service.")
                else:
                    logger.warning(f"[{self.name}] Circuit breaker is OPEN. Failing fast.")
                    raise Exception("Circuit breaker is open.")

        try:
            result = func(*args, **kwargs)
        except Exception as e:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                logger.warning(f"[{self.name}] Failure count: {self.failure_count}")
                if self.failure_count >= FAILURE_THRESHOLD:
                    self.state = 'OPEN'
                    logger.error(f"[{self.name}] Circuit breaker is now OPEN. All requests will fail fast.")
            raise e
        else:
            with self.lock:
                if self.state == 'HALF-OPEN':
                    self.state = 'CLOSED'
                    self.failure_count = 0
                    logger.info(f"[{self.name}] Circuit breaker is now CLOSED. Resuming normal operations.")
            return result

# Initialize Circuit Breakers for each service
stock_cb = CircuitBreaker("StockPredictionService")
user_cb = CircuitBreaker("UserManagementService")

def send_request(url, method="GET", payload=None, headers=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"Attempt {attempt}/{MAX_RETRIES} to {url}")
            if method == "GET":
                response = requests.get(url, timeout=TIMEOUT, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=payload, timeout=TIMEOUT, headers=headers)
            response.raise_for_status()
            logger.info(f"Attempt {attempt}/{MAX_RETRIES} succeeded for {url}")
            return response
        except requests.exceptions.Timeout:
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} timed out for {url}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} failed for {url}: {e}")
    raise Exception(f"All {MAX_RETRIES} retries failed for {url}")

def circuit_breaker_call(circuit_breaker, url, method="GET", payload=None, headers=None):
    try:
        return circuit_breaker.call(send_request, url, method, payload, headers)
    except Exception as e:
        logger.error(f"[{circuit_breaker.name}] {e}")
        raise e

# ----------- Stock Prediction Service Endpoints -----------

@app.route('/api/stocks/<symbol>/details', methods=['GET'])
def get_stock_details(symbol):
    url = f"{NGINX_URL}/stock-prediction/api/stocks/{symbol}/details"
    try:
        response = circuit_breaker_call(stock_cb, url, method="GET")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict/<symbol>', methods=['GET'])
def predict_stock(symbol):
    url = f"{NGINX_URL}/stock-prediction/api/predict/{symbol}"
    try:
        response = circuit_breaker_call(stock_cb, url, method="GET")
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions/store', methods=['POST'])
def store_transaction():
    url = f"{NGINX_URL}/stock-prediction/api/transactions/store"
    payload = request.json
    try:
        response = circuit_breaker_call(stock_cb, url, method="POST", payload=payload)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------- User Management Service Endpoints -----------

@app.route('/api/users/register', methods=['POST'])
def register_user():
    url = f"{NGINX_URL}/user-management/api/users/register"
    payload = request.json
    try:
        response = circuit_breaker_call(user_cb, url, method="POST", payload=payload)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/login', methods=['POST'])
def login_user():
    url = f"{NGINX_URL}/user-management/api/users/login"
    payload = request.json
    try:
        response = circuit_breaker_call(user_cb, url, method="POST", payload=payload)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/profile', methods=['GET'])
def get_user_profile():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Token missing"}), 401
    url = f"{NGINX_URL}/user-management/api/users/profile"
    headers = {'Authorization': token}
    try:
        response = circuit_breaker_call(user_cb, url, method="GET", headers=headers)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/profile/update', methods=['POST'])
def update_user_profile():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Token missing"}), 401
    url = f"{NGINX_URL}/user-management/api/users/profile/update"
    payload = request.json
    headers = {'Authorization': token}
    try:
        response = circuit_breaker_call(user_cb, url, method="POST", payload=payload, headers=headers)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/buy', methods=['POST'])
def buy_stock():
    url = f"{NGINX_URL}/user-management/api/users/buy"
    payload = request.json
    try:
        response = circuit_breaker_call(user_cb, url, method="POST", payload=payload)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/sell', methods=['POST'])
def sell_stock():
    url = f"{NGINX_URL}/user-management/api/users/sell"
    payload = request.json
    try:
        response = circuit_breaker_call(user_cb, url, method="POST", payload=payload)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------- Gateway Status Endpoint -----------

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"message": "API Gateway is running!"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
