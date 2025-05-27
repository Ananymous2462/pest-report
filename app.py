# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# --- NEW IMPORTS FOR CLOUDINARY ---
import cloudinary
import cloudinary.uploader

# Load environment variables from .env file (for local testing)
# On Render, these will be set directly in Render's dashboard.
load_dotenv()

app = Flask(__name__)
# Enable CORS for all origins. For production, consider restricting to your frontend domain.
CORS(app)

# --- Email Configuration (using Resend via SMTP) ---
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD') # This is your Resend API Key
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL')
# Set default SMTP_SERVER to Resend's server for robustness
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.resend.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587)) # Standard TLS port

# --- Cloudinary Configuration ---
cloudinary.config(
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key = os.getenv('CLOUDINARY_API_KEY'),
    api_secret = os.getenv('CLOUDINARY_API_SECRET')
)

# Path to store submission data
SUBMISSIONS_FILE = 'data/submissions.json'

# Ensure the 'data' directory exists
os.makedirs('data', exist_ok=True)

def send_email(subject, body, to_email):
    """
    Sends an email using SMTP.
    This function connects to an email server and sends a message.
    Configured for Resend (using SENDER_EMAIL as username and API Key as password).
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

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls() # Upgrade the connection to a secure encrypted SSL/TLS connection
            # For Resend, use the sender email as the username and the API Key as the password
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg) # Send the email
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        print(f"Error details: {e.args}") # Print error arguments for more details
        return False

def save_submission(submission_record):
    """Appends form submission data to a JSON file."""
    try:
        if not os.path.exists(SUBMISSIONS_FILE):
            with open(SUBMISSIONS_FILE, 'w') as f:
                json.dump([], f) # Initialize with an empty list

        with open(SUBMISSIONS_FILE, 'r+') as f:
            file_data = json.load(f)
            file_data.append(submission_record)
            f.seek(0) # Rewind to the beginning of the file
            json.dump(file_data, f, indent=4)
            f.truncate() # Ensure old content is removed if new content is smaller
        print("Submission saved to file.")
        return True
    except Exception as e:
        print(f"Failed to save submission: {e}")
        return False


@app.route('/submit-report', methods=['POST'])
def submit_report():
    """
    Receives form data (including potential file upload),
    uploads image to Cloudinary, saves data, and sends email notification.
    """
    # When frontend sends FormData, text fields are in request.form
    # and files are in request.files.
    # The frontend is sending JSON data as a 'jsonData' field.
    json_data_str = request.form.get('jsonData')
    if not json_data_str:
        return jsonify({"message": "No JSON data found in request.form"}), 400

    try:
        data = json.loads(json_data_str)
    except json.JSONDecodeError:
        return jsonify({"message": "Invalid JSON data provided"}), 400

    # Extract data from the parsed JSON
    your_name = data.get('yourName', 'N/A')
    business_area = data.get('businessArea', 'N/A')
    pests = data.get('pests', [])
    other_pest = data.get('otherPest', '') # Keep as empty string if not provided
    report_date = data.get('reportDate', 'N/A')
    additional_notes = data.get('additionalNotes', 'N/A')

    # --- Handle Image Upload to Cloudinary ---
    image_file = request.files.get('imageFile') # 'imageFile' is the key from frontend FormData
    image_url = "No image uploaded" # Default value if no image or upload fails

    if image_file and image_file.filename:
        try:
            # Upload the image to Cloudinary
            # 'folder' helps organize uploads in your Cloudinary account
            upload_result = cloudinary.uploader.upload(image_file, folder="pest_reports")
            image_url = upload_result.get('secure_url') # Get the secure HTTPS URL of the uploaded image
            print(f"Image uploaded to Cloudinary: {image_url}")
        except Exception as e:
            print(f"Failed to upload image to Cloudinary: {e}")
            image_url = "Image upload failed" # Indicate failure in the report
    else:
        print("No image file provided in submission.")

    # Prepare the complete submission record (including image_url)
    submission_record = {
        "timestamp": datetime.now().isoformat(),
        "yourName": your_name,
        "businessArea": business_area,
        "pests": pests,
        "otherPest": other_pest,
        "reportDate": report_date,
        "additionalNotes": additional_notes,
        "image_url": image_url # Store the Cloudinary URL
    }

    # --- Save data for weekly report ---
    if not save_submission(submission_record):
        return jsonify({"message": "Error saving submission"}), 500

    # --- Send immediate email notification ---
    subject = f"New Pest Report from {your_name}"
    body = (
        f"A new pest report has been submitted:\n\n"
        f"Name: {your_name}\n"
        f"Business Area: {business_area}\n"
        f"Pest(s): {', '.join(pests)}\n"
        + (f"Other Pest: {other_pest}\n" if other_pest else "") + # Only include if other_pest has a value
        f"Date: {report_date}\n"
        f"Notes: {additional_notes}\n"
        f"Image URL: {image_url}\n" # Include the image URL in the email
        f"Submitted At: {submission_record['timestamp']}"
    )

    if send_email(subject, body, RECEIVER_EMAIL):
        return jsonify({"message": "Report submitted and email sent successfully!"}), 200
    else:
        return jsonify({"message": "Report submitted, but email failed to send. Check backend logs."}), 500

@app.route('/')
def home():
    """A simple home route to check if the backend is running."""
    return "Pest Reporting Backend is running!"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
