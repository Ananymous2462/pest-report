# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS # We need this for security between your website and backend
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file (for local testing)
# On Render, these will be set directly in Render's dashboard.
load_dotenv()

app = Flask(__name__)
CORS(app) # Enable Cross-Origin Resource Sharing for all routes

# --- Configuration (from Environment Variables) ---
# These values will be loaded from your .env file locally,
# and from Render's environment settings when deployed.
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com') # Default for Gmail
SMTP_PORT = int(os.getenv('SMTP_PORT', 587)) # Default for Gmail (TLS)

# Path to store submission data
SUBMISSIONS_FILE = 'data/submissions.json'

# Ensure the 'data' directory exists
os.makedirs('data', exist_ok=True)

def send_email(subject, body, to_email):
    """
    Sends an email using SMTP.
    This function connects to an email server and sends a message.
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("Email sender credentials not set. Cannot send email.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Connect to the SMTP server
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls() # Upgrade the connection to a secure encrypted SSL/TLS connection
            server.login(SENDER_EMAIL, SENDER_PASSWORD) # Log in to your email account
            server.send_message(msg) # Send the email
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def save_submission(data):
    """
    Appends form submission data to a JSON file.
    This is a simple way to store data for the weekly report.
    NOTE: On Render's free tier, this file might be lost if the server restarts.
    For persistent data, a database (like PostgreSQL) is recommended.
    """
    try:
        # Check if the submissions file exists. If not, create it with an empty list.
        if not os.path.exists(SUBMISSIONS_FILE):
            with open(SUBMISSIONS_FILE, 'w') as f:
                json.dump([], f)

        # Read existing data, append new data, and write it back
        with open(SUBMISSIONS_FILE, 'r+') as f:
            file_data = json.load(f) # Load all existing submissions
            file_data.append(data) # Add the new submission
            f.seek(0) # Move cursor to the beginning of the file
            json.dump(file_data, f, indent=4) # Write all data back, formatted nicely
        print("Submission saved to file.")
        return True
    except Exception as e:
        print(f"Failed to save submission: {e}")
        return False

@app.route('/submit-report', methods=['POST'])
def submit_report():
    """
    This is the endpoint that your frontend form will send data to.
    It receives JSON data, saves it, and sends an immediate email.
    """
    # Ensure the incoming request is JSON
    if not request.is_json:
        return jsonify({"message": "Request must be JSON"}), 400

    data = request.get_json() # Get the JSON data sent from the frontend

    # Add a timestamp to the submission data
    data['timestamp'] = datetime.now().isoformat()

    # --- Save data for weekly report ---
    if not save_submission(data):
        return jsonify({"message": "Error saving submission"}), 500

    # --- Send immediate email notification ---
    subject = f"New Pest Report from {data.get('yourName', 'Unknown')}"
    body = (
        f"A new pest report has been submitted:\n\n"
        f"Name: {data.get('yourName', 'N/A')}\n"
        f"Business Area: {data.get('businessArea', 'N/A')}\n"
        f"Pest(s): {', '.join(data.get('pests', []))}\n"
        f"Other Pest: {data.get('otherPest', 'N/A')}\n"
        f"Date: {data.get('reportDate', 'N/A')}\n"
        f"Image File: {data.get('imageFileName', 'No file uploaded')}\n"
        f"Notes: {data.get('additionalNotes', 'N/A')}\n"
        f"Submitted At: {data.get('timestamp')}"
    )

    if send_email(subject, body, RECEIVER_EMAIL):
        return jsonify({"message": "Report submitted and email sent successfully!"}), 200
    else:
        return jsonify({"message": "Report submitted, but email failed to send. Check backend logs."}), 500

@app.route('/')
def home():
    """
    A simple home route to check if the backend is running.
    """
    return "Pest Reporting Backend is running!"

if __name__ == '__main__':
    # This block runs only when you execute app.py directly (e.g., python app.py)
    # It's for local testing. On Render, Gunicorn will run your app.
    app.run(debug=True, port=5000)