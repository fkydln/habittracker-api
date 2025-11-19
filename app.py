import os
from flask import Flask, render_template, request, jsonify
from pyairtable import Api
from datetime import datetime
from dotenv import load_dotenv
import pytz

load_dotenv()

app = Flask(__name__)

# Env variables
API_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID =  os.getenv("AIRTABLE_BASE_ID")
HABIT_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")
USER_TABLE_NAME = os.getenv("AIRTABLE_USER_TABLE_NAME")

api = Api(API_TOKEN)
habit_table = api.table(BASE_ID, HABIT_TABLE_NAME)
user_table = api.table(BASE_ID, USER_TABLE_NAME)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/users")
def get_users():
    try:
        records = user_table.all()
        user_list = []
        for r in records:
            fields = r.get("fields", {})
            user_list.append({
                "username": fields.get("username", ""),
                "displayname": fields.get("displayname", ""),
                "timezone": fields.get("timezone", "UTC")
            })
        return jsonify(user_list)
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify([])

@app.route("/api/log", methods=["POST"])
def log_habit():
    try:
        data = request.json
        username = data.get("user")
        
        if not username:
            return jsonify({"status": "error", "message": "No user specified"}), 400

        # Log UTC timestamp of the click
        utc_now_str = datetime.now(pytz.utc).isoformat()

        # We save to 'timestamp', but if your table still uses 'date', 
        # you should rename the column in Airtable to 'timestamp' for clarity.
        habit_table.create({
            "user": username,
            "timestamp": utc_now_str,
            "value": 1 
        })

        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error logging: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/data")
def get_data():
    try:
        username = request.args.get('user')
        if not username:
            return jsonify([])

        # 1. Get User Timezone
        formula = f"{{username}} = '{username}'"
        user_records = user_table.all(formula=formula)
        
        user_tz_str = "UTC"
        if user_records:
            user_tz_str = user_records[0]["fields"].get("timezone", "UTC")
        
        try:
            user_tz = pytz.timezone(user_tz_str)
        except:
            user_tz = pytz.utc

        # 2. Fetch Records (Safely)
        # We removed fields=['timestamp'] to prevent crashes if the column name is wrong
        habit_records = habit_table.all(formula=f"{{user}} = '{username}'")

        unique_days = set()

        for r in habit_records:
            fields = r.get('fields', {})
            
            # FALLBACK: Check 'timestamp' first, then 'date'
            # This prevents crashes if you haven't renamed the column yet
            ts_str = fields.get('timestamp') or fields.get('date')
            
            if ts_str:
                try:
                    # Scenario A: It's a new Timestamp (contains 'T', e.g., 2025-11-18T14:00...)
                    if 'T' in ts_str:
                        dt_utc = datetime.fromisoformat(ts_str)
                        dt_local = dt_utc.astimezone(user_tz)
                        local_date_str = dt_local.strftime("%Y-%m-%d")
                        unique_days.add(local_date_str)
                    
                    # Scenario B: It's Old Data (Just YYYY-MM-DD)
                    # Trust it as-is, don't convert timezone
                    else:
                        unique_days.add(ts_str)

                except ValueError:
                    continue # Skip bad data

        results = []
        for date_str in unique_days:
            results.append({
                "date": date_str,
                "value": 1 
            })
        
        return jsonify(results)

    except Exception as e:
        print(f"CRITICAL ERROR in /api/data: {e}")
        # Return empty list instead of crashing, so page still loads
        return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)