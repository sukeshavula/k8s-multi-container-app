import os
import socket

import redis
from flask import Flask, jsonify

app = Flask(__name__)

cache = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    socket_connect_timeout=2,
)


@app.get("/")
def index():
    try:
        visits = cache.incr("visits")
    except redis.exceptions.ConnectionError:
        return jsonify(error="redis unavailable", pod=socket.gethostname()), 503
    return jsonify(
        message=os.environ.get("GREETING", "Hello from Kubernetes"),
        visits=int(visits),
        pod=socket.gethostname(),
    )


@app.get("/healthz")
def healthz():
    # Liveness: the process is up.
    return "ok", 200


@app.get("/readyz")
def readyz():
    # Readiness: only take traffic when Redis is reachable.
    try:
        cache.ping()
        return "ready", 200
    except redis.exceptions.ConnectionError:
        return "redis unavailable", 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
