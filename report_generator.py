# report_generator.py
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# --- Email Configuration (using SendGrid via SMTP) ---
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD') # This is now your SendGrid API Key
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL') # The email to send the report TO
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.sendgrid.net') # SendGrid's SMTP server
SMTP_PORT = int(os.getenv('SMTP_PORT', 587)) # SendGrid's SMTP port (TLS)

SUBMISSIONS_FILE = 'data/submissions.json'

def send_email(subject, body, to_email):
    """
    Sends an email using SMTP.
    Updated to use SendGrid's specific login (username 'apikey').
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("Email sender credentials not set. Cannot send report email.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            # For SendGrid, the username is 'apikey', and password is the API Key
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"Report email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send report email: {e}")
        print(f"Error details: {e.args}") # Print error arguments for more details
        return False

def generate_weekly_report():
    """Generates a text-based report from submissions recorded in the last 7 days."""
    if not os.path.exists(SUBMISSIONS_FILE):
        print("No submissions file found. No report generated.")
        return "No submissions data available for the weekly report."

    try:
        with open(SUBMISSIONS_FILE, 'r') as f:
            submissions = json.load(f) # Load all recorded submissions
    except json.JSONDecodeError:
        print("Error decoding JSON from submissions file. It might be empty or corrupted.")
        return "Error reading submissions data. Report cannot be generated."
    except Exception as e:
        print(f"An unexpected error occurred while reading submissions: {e}")
        return "An error occurred while preparing the report."

    # Calculate the timestamp for 7 days ago
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_submissions = []

    # Filter submissions that occurred within the last 7 days
    for s in submissions:
        if 'timestamp' in s:
            try:
                submission_time = datetime.fromisoformat(s['timestamp'])
                if submission_time >= seven_days_ago:
                    recent_submissions.append(s)
            except ValueError:
                print(f"Warning: Invalid timestamp format found: {s['timestamp']}")
                continue

    if not recent_submissions:
        return "No new pest reports in the last week."

    # Build the report content
    report_lines = [
        f"Weekly Pest Report - Last 7 Days ({seven_days_ago.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')})\n",
        "="*60 + "\n" # A separator line
    ]

    for i, sub in enumerate(recent_submissions):
        report_lines.append(f"--- Report #{i+1} ---")
        report_lines.append(f"  Name: {sub.get('yourName', 'N/A')}")
        report_lines.append(f"  Business Area: {sub.get('businessArea', 'N/A')}")
        report_lines.append(f"  Pest(s): {', '.join(sub.get('pests', []))}")
        if sub.get('otherPest') and sub.get('otherPest').strip() != 'N/A' and sub.get('otherPest').strip() != '': # Check if it's not empty or default 'N/A'
            report_lines.append(f"  Other Pest: {sub.get('otherPest')}")
        report_lines.append(f"  Date of Incident: {sub.get('reportDate', 'N/A')}")
        report_lines.append(f"  Notes: {sub.get('additionalNotes', 'N/A')}")
        report_lines.append(f"  Image URL: {sub.get('image_url', 'No image uploaded')}") # Include image URL
        report_lines.append(f"  Submitted On: {datetime.fromisoformat(sub['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n")

    return "\n".join(report_lines)

if __name__ == '__main__':
    print("Starting weekly pest report generation process...")
    report_content = generate_weekly_report()
    subject = f"Weekly Pest Report - {datetime.now().strftime('%Y-%m-%d')}"

    if send_email(subject, report_content, RECEIVER_EMAIL):
        print("Weekly report sent successfully.")
    else:
        print("Failed to send weekly report. Check logs for details.")

    # Optional: Clear old data after reporting to prevent the file from growing indefinitely.
    try:
        if os.path.exists(SUBMISSIONS_FILE):
            with open(SUBMISSIONS_FILE, 'r') as f:
                all_submissions = json.load(f)

            # Keep only submissions newer than 7 days ago
            seven_days_ago_for_clearing = datetime.now() - timedelta(days=7)
            submissions_to_keep = [
                s for s in all_submissions
                if 'timestamp' in s and datetime.fromisoformat(s['timestamp']) >= seven_days_ago_for_clearing
            ]

            with open(SUBMISSIONS_FILE, 'w') as f:
                json.dump(submissions_to_keep, f, indent=4)
            print("Submissions file updated (old entries cleared).")
        else:
            print("Submissions file not found during clearing process.")
    except Exception as e:
        print(f"Failed to clear old submissions from file: {e}")
