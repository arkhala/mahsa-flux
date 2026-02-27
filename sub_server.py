"""Token-protected subscription server for Mahsa proxy configs."""

import os

from flask import Flask, Response, request

app = Flask(__name__)
TOKEN = None  # Resolved lazily so ENV set by entrypoint is picked up


def _get_token():
    global TOKEN
    if TOKEN is None:
        TOKEN = os.getenv("SUB_TOKEN", "")
    return TOKEN


@app.route("/sub")
def sub():
    token = _get_token()
    if not token or request.args.get("token") != token:
        return Response("Access denied", status=403)
    try:
        with open("/sub_content.txt") as f:
            content = f.read()
    except FileNotFoundError:
        return Response("Subscription not ready", status=503)
    return Response(content, mimetype="text/plain")


@app.route("/health")
def health():
    return Response("ok", mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)