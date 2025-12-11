from flask import Flask, request, jsonify
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from database import get_db, init_db
import requests
import json

app = Flask(__name__)

SERVICE_ACCOUNT_FILE = "serviceAccount.json"
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

with open(SERVICE_ACCOUNT_FILE) as f:
    creds_info = json.load(f)

PROJECT_ID = creds_info["project_id"]
init_db()

def get_access_token():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    credentials.refresh(Request())
    return credentials.token


@app.route("/send_call", methods=["POST"])
def send_call():
    data = request.json

    required = ["type", "caller", "room_name", "to_username"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    target_username = data["to_username"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (target_username,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User not registered"}), 404

    user_id = user["id"]

    cursor.execute("""
        SELECT fcm_token FROM devices
        WHERE user_id = ?
        ORDER BY last_update DESC
        LIMIT 1
    """, (user_id,))

    device = cursor.fetchone()

    if not device:
        return jsonify({"error": "No devices registered for user"}), 404

    fcm_token = device["fcm_token"]

    message = {
        "message": {
            "token": fcm_token,
            "data": {
                "type": data["type"],
                "caller": data["caller"],
                "room_name": data["room_name"]
            }
        }
    }

    url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"
    access_token = get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=message)

    return (
        jsonify({"success": True, "response": response.json()})
        if response.status_code == 200
        else jsonify({"error": response.text}), 500
    )


@app.route("/register_device", methods=["POST"])
def register_device():
    data = request.json

    if "username" not in data or "fcm_token" not in data:
        return jsonify({"error": "Missing fields"}), 400

    username = data["username"]
    fcm_token = data["fcm_token"]
    device_id = data.get("device_id")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (username) VALUES (?)", (username,))
        user_id = cursor.lastrowid
    else:
        user_id = user["id"]

    cursor.execute("""
        INSERT INTO devices (user_id, fcm_token, device_id)
        VALUES (?, ?, ?)
    """, (user_id, fcm_token, device_id))

    conn.commit()

    return jsonify({"success": True, "message": "Device registered"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
