from flask import Flask, request, jsonify
import requests
from pybreaker import CircuitBreaker
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import os

app = Flask(__name__)

REQUEST_COUNT = Counter(
    'api_gateway_request_count_total',
    'Total Request Count',
    ['method', 'endpoint', 'http_status']
)

REQUEST_LATENCY = Histogram(
    'api_gateway_request_latency_seconds',
    'Request latency',
    ['endpoint'],
    buckets=[0.1, 0.5, 1, 2, 5]
)


# Middleware for capturing metrics
@app.before_request
def start_timer():
    request.start_time = request.environ.get('werkzeug.request_started_at', 0)


@app.after_request
def record_metrics(response):
    latency = request.environ.get('werkzeug.request_started_at', 0)
    endpoint = request.path
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        http_status=response.status_code
    ).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)
    return response


# Expose `/metrics` endpoint
@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
# metrics = PrometheusMetrics(app)

# Circuit breaker configuration
FAIL_MAX = 3
RESET_TIMEOUT = 30

STOCK_PREDICTION_REPLICAS = [
    {"host": "stock-prediction-service-1", "port": "5000"},
    {"host": "stock-prediction-service-2", "port": "5000"}
]

USER_MANAGEMENT_REPLICAS = [
    {"host": "user-management-service-1", "port": "5002"},
    {"host": "user-management-service-2", "port": "5002"}
]

stock_circuit_breakers = {
    f"{replica['host']}:{replica['port']}": CircuitBreaker(fail_max=FAIL_MAX, reset_timeout=RESET_TIMEOUT)
    for replica in STOCK_PREDICTION_REPLICAS
}

user_circuit_breakers = {
    f"{replica['host']}:{replica['port']}": CircuitBreaker(fail_max=FAIL_MAX, reset_timeout=RESET_TIMEOUT)
    for replica in USER_MANAGEMENT_REPLICAS
}

def make_request_with_circuit_breaker(url, method, headers=None, data=None, replicas=None, circuit_breakers=None):
    """
    Makes a request to a service replica using circuit breakers. Switches replicas after retries fail.
    """
    for replica in replicas:
        replica_key = f"{replica['host']}:{replica['port']}"
        service_url = f"http://{replica['host']}:{replica['port']}/{url}"
        circuit_breaker = circuit_breakers[replica_key]

        if circuit_breaker.current_state == "open":
            app.logger.warning(f"[CIRCUIT BREAKER] Skipping {replica_key} as it is OPEN.")
            continue

        app.logger.info(f"[CIRCUIT BREAKER] Attempting requests to replica: {replica_key}")
        for attempt in range(1, 4):  
            try:
                # Perform the request
                if method == "GET":
                    response = circuit_breaker.call(requests.get, service_url, headers=headers, timeout=10)
                elif method == "POST":
                    response = circuit_breaker.call(requests.post, service_url, headers=headers, json=data, timeout=10)

                # Success: Log and return the response
                app.logger.info(f"[SUCCESS] Request succeeded for {replica_key} on attempt {attempt}.")
                return response.json(), response.status_code

            except Exception as e:
                # Log failure and retry
                app.logger.error(f"[ERROR] Attempt {attempt} failed for {replica_key}: {str(e)}")

        # Log that the replica is exhausted
        app.logger.error(f"[CIRCUIT BREAKER] Replica {replica_key} failed all retries. Moving to the next replica...")

    # If all replicas fail
    app.logger.error("[CIRCUIT BREAKER] All replicas failed. Circuit breakers are now OPEN.")
    return {"error": "All replicas failed. Circuit breakers tripped."}, 503


# API Gateway Endpoints
@app.route('/api/stocks/<symbol>/details', methods=['GET'])
def get_stock_details(symbol):
    url = f"api/stocks/{symbol}/details"
    headers = {"Content-Type": "application/json"}
    response, status_code = make_request_with_circuit_breaker(
        url, "GET", headers=headers,
        replicas=STOCK_PREDICTION_REPLICAS,
        circuit_breakers=stock_circuit_breakers
    )
    return jsonify(response), status_code

@app.route('/api/predict/<symbol>', methods=['GET'])
def predict_stock(symbol):
    url = f"api/predict/{symbol}"
    headers = {"Content-Type": "application/json"}
    response, status_code = make_request_with_circuit_breaker(
        url, "GET", headers=headers,
        replicas=STOCK_PREDICTION_REPLICAS,
        circuit_breakers=stock_circuit_breakers
    )
    return jsonify(response), status_code

@app.route('/api/transactions/store', methods=['POST'])
def store_transaction():
    url = "api/transactions/store"
    data = request.json
    headers = {"Content-Type": "application/json"}
    response, status_code = make_request_with_circuit_breaker(
        url, "POST", headers=headers, data=data,
        replicas=STOCK_PREDICTION_REPLICAS,
        circuit_breakers=stock_circuit_breakers
    )
    return jsonify(response), status_code

@app.route('/api/users/register', methods=['POST'])
def register_user():
    url = "api/users/register"
    data = request.json
    headers = {"Content-Type": "application/json"}
    response, status_code = make_request_with_circuit_breaker(
        url, "POST", headers=headers, data=data,
        replicas=USER_MANAGEMENT_REPLICAS,
        circuit_breakers=user_circuit_breakers
    )
    return jsonify(response), status_code

@app.route('/api/users/login', methods=['POST'])
def login_user():
    url = "api/users/login"
    data = request.json
    headers = {"Content-Type": "application/json"}
    response, status_code = make_request_with_circuit_breaker(
        url, "POST", headers=headers, data=data,
        replicas=USER_MANAGEMENT_REPLICAS,
        circuit_breakers=user_circuit_breakers
    )
    return jsonify(response), status_code

@app.route('/api/users/profile', methods=['GET'])
def get_user_profile():
    url = "api/users/profile"
    headers = {"Authorization": request.headers.get('Authorization')}
    response, status_code = make_request_with_circuit_breaker(
        url, "GET", headers=headers,
        replicas=USER_MANAGEMENT_REPLICAS,
        circuit_breakers=user_circuit_breakers
    )
    return jsonify(response), status_code

@app.route('/api/users/profile/update', methods=['POST'])
def update_user_profile():
    url = "api/users/profile/update"
    data = request.json
    headers = {"Authorization": request.headers.get('Authorization')}
    response, status_code = make_request_with_circuit_breaker(
        url, "POST", headers=headers, data=data,
        replicas=USER_MANAGEMENT_REPLICAS,
        circuit_breakers=user_circuit_breakers
    )
    return jsonify(response), status_code

# Gateway Status Endpoint
@app.route('/status', methods=['GET'])
def status():
    return jsonify({"message": "API Gateway is running!"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
