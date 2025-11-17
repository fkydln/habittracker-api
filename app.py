import os
from flask import Flask, render_template, request, jsonify
from pyairtable import Api
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()  # Load environment variables from .env file


app = Flask(__name__)

#get configuration from environment variables
API_TOKEN = os.getenv("AIRTABLE_TOKEN")
BASE_ID =  os.getenv("AIRTABLE_BASE_ID")
TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

#check if any of the required env vars are missing
if not API_TOKEN or not BASE_ID or not TABLE_NAME:
    print("Error: Missing one or more required environment variables. Double check your .env file.")

#initialize Airtable API

api = Api(API_TOKEN)
table = api.table(BASE_ID, TABLE_NAME)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/log", methods=["POST"])
def log_habit():
    data = request.json
    today = datetime.now().strftime("%Y-%m-%d")
    user = data.get('user') # Get the user from the frontend

    if not user:
        return jsonify({"status": "error", "message": "No user specified"}), 400
    
    # Search for row matching BOTH date AND user
    # Formula: AND({date}='2023-XX-XX', {user}='fazkay')
    formula = f"AND({{date}} = '{today}', {{user}} = '{user}')"
    matches = table.all(formula=formula)

    if matches:
        record_id = matches[0]['id']
        current_val = matches[0]['fields'].get('value', 0)
        table.update(record_id, {"value": current_val + 1})
    else:
        # Create new row with user
        table.create({"date": today, "value": 1, "user": user})
    
    return jsonify({"status": "success", "date": today, "user": user})

@app.route("/api/data")
def get_data():
    user = request.args.get('user') # Get user from URL query param
    
    if not user:
        return jsonify([])

    # Filter Airtable to only show records for this user
    formula = f"{{user}} = '{user}'"
    records = table.all(formula=formula)
    
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