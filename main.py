
import os
import json
import time
import threading
import requests
from flask import Flask

TOKEN = os.environ["BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}/"

app = Flask(__name__)
DATA_FILE = "selected_users.json"
selected = {}
lock = threading.Lock()


def load_data():
    global selected
    try:
        with open(DATA_FILE, "r") as f:
            selected = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        selected = {}


def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(selected, f)


def call_api(method, data=None):
    response = requests.post(
        API + method, json=data or {}, timeout=40
    )
    return response.json()


def is_admin(chat_id, user_id):
    result = call_api("getChatMember", {
        "chat_id": chat_id,
        "user_id": user_id
    })
    if not result.get("ok"):
        return False
    return result["result"]["status"] in ("creator", "administrator")


def handle_message(msg):
    chat_id = str(msg["chat"]["id"])
    user = msg.get("from", {})
    sender_id = user.get("id")

    if not sender_id or user.get("is_bot"):
        return

    text = msg.get("text", "")
    reply = msg.get("reply_to_message")

    if text.startswith("/add"):
        if not is_admin(chat_id, sender_id):
            return
        if not reply or not reply.get("from"):
            return

        target = reply["from"]
        target_id = target["id"]

        with lock:
            selected.setdefault(chat_id, [])
            if target_id not in selected[chat_id]:
                selected[chat_id].append(target_id)
                save_data()

        return

    if text.startswith("/remove"):
        if not is_admin(chat_id, sender_id):
            return
        if not reply or not reply.get("from"):
            return

        target_id = reply["from"]["id"]

        with lock:
            selected.setdefault(chat_id, [])
            if target_id in selected[chat_id]:
                selected[chat_id].remove(target_id)
                save_data()

        return

    if text.startswith("/list"):
        if not is_admin(chat_id, sender_id):
            return

        with lock:
            ids = selected.get(chat_id, [])

        call_api("sendMessage", {
            "chat_id": chat_id,
            "text": "Selected IDs:\n" +
                    ("\n".join(map(str, ids)) if ids else "Empty")
        })
        return

    with lock:
        should_react = sender_id in selected.get(chat_id, [])

    if should_react:
        call_api("setMessageReaction", {
            "chat_id": msg["chat"]["id"],
            "message_id": msg["message_id"],
            "reaction": [
                {"type": "emoji", "emoji": "💘"}
            ]
        })


def polling():
    offset = None

    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset is not None:
                params["offset"] = offset

            result = requests.get(
                API + "getUpdates",
                params=params,
                timeout=40
            ).json()

            if result.get("ok"):
                for update in result["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update:
                        try:
                            handle_message(update["message"])
                        except Exception as error:
                            print("Message error:", error)

        except Exception as error:
            print("Polling error:", error)
            time.sleep(5)


@app.route("/")
def home():
    return "Bot is running!"


if __name__ == "__main__":
    load_data()
    threading.Thread(target=polling, daemon=True).start()
    app.run(host="0.0.0.0",
            port=int(os.environ.get("PORT", 10000)))
