from flask import Flask, request, jsonify
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests
import json

app = Flask(__name__)

SERVICE_ACCOUNT_FILE = "serviceAccount.json"
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]

with open(SERVICE_ACCOUNT_FILE) as f:
    creds_info = json.load(f)

PROJECT_ID = creds_info["project_id"]

def get_access_token():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    credentials.refresh(Request())
    return credentials.token


@app.route("/send_call", methods=["POST"])
def send_call():
    data = request.json

    required = ["type", "caller", "room_name", "fcm_token"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    message = {
        "message": {
            "token": data["fcm_token"],
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
