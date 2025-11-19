import os
from flask import Flask, render_template, request, jsonify
from pyairtable import Api
from datetime import datetime
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()  # Load environment variables from .env file

app = Flask(__name__)

# Environment variables for two Airtable tables
API_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID =  os.getenv("AIRTABLE_BASE_ID")
HABIT_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")  # e.g., 'habits'
USER_TABLE_NAME = os.getenv("AIRTABLE_USER_TABLE_NAME")  # e.g., 'users'

if not API_TOKEN or not BASE_ID or not HABIT_TABLE_NAME or not USER_TABLE_NAME:
    print("Error: Missing env variables.")

api = Api(API_TOKEN)
habit_table = api.table(BASE_ID, HABIT_TABLE_NAME)
user_table = api.table(BASE_ID, USER_TABLE_NAME)


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/users")
def get_users():
    records = user_table.all()
    user_list = []
    for r in records:
        fields = r["fields"]
        user_list.append({
            "username": fields.get("username", ""),
            "displayname": fields.get("displayname", ""),
            "timezone": fields.get("timezone", "")
        })
    return jsonify(user_list)

@app.route("/api/log", methods=["POST"])
def log_habit():
    data = request.json
    username = data.get("user")
    user_date = data.get("date")  # Local date - sent from frontend (YYYY-MM-DD)

    if not username:
        return jsonify({"status": "error", "message": "No user specified"}), 400

    # Lookup user record to get timezone
    formula = f"{{username}} = '{username}'"
    user_records = user_table.all(formula=formula)
    if not user_records:
        return jsonify({"status": "error", "message": "User not found in database"}), 400

    user_info = user_records[0]["fields"]
    user_timezone = user_info.get("timezone", "UTC")

    # If frontend provided a local date, use it; otherwise, fall back to user's local time at server
    if user_date:
        today_str = user_date
    else:
        tzinfo = pytz.timezone(user_timezone)
        today_str = datetime.now(tzinfo).strftime("%Y-%m-%d")

    # Search for row matching BOTH date AND user
    formula = f"AND({{date}} = '{today_str}', {{user}} = '{username}')"
    matches = habit_table.all(formula=formula)

    if matches:
        record_id = matches[0]['id']
        current_val = matches[0]['fields'].get('value', 0)
        habit_table.update(record_id, {"value": current_val + 1})
    else:
        habit_table.create({"date": today_str, "value": 1, "user": username})

    return jsonify({"status": "success", "date": today_str, "user": username})

@app.route("/api/data")
def get_data():
    username = request.args.get('user')
    if not username:
        return jsonify([])

    formula = f"{{user}} = '{username}'"
    records = habit_table.all(formula=formula)

    results = []
    for r in records:
        fields = r['fields']
        if 'date' in fields and 'value' in fields:
            results.append({
                "date": fields['date'],
                "value": fields['value']
            })
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)