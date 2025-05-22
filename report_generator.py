# report_generator.py
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file (for local testing)
# On Render, these will be set directly in Render's dashboard.
load_dotenv()

# --- Configuration (from Environment Variables) ---
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL') # The email to send the report TO
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))

# Path to the file where form submissions are stored
SUBMISSIONS_FILE = 'data/submissions.json'

def send_email(subject, body, to_email):
    """
    Sends an email using SMTP.
    This function is reused from app.py to send the weekly report.
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
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"Report email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send report email: {e}")
        return False

def generate_weekly_report():
    """
    Generates a text-based report from submissions recorded in the last 7 days.
    """
    # Check if the submissions file exists
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
                # Skip this submission if timestamp is invalid
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
        if sub.get('otherPest'): # Only include if 'otherPest' has a value
            report_lines.append(f"  Other Pest: {sub.get('otherPest')}")
        report_lines.append(f"  Date of Incident: {sub.get('reportDate', 'N/A')}")
        report_lines.append(f"  Image File: {sub.get('imageFileName', 'No file uploaded')}")
        report_lines.append(f"  Notes: {sub.get('additionalNotes', 'N/A')}")
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
    # For a more robust solution, consider moving old data to an archive or using a database.
    try:
        # Re-read the file to ensure we don't accidentally clear new submissions
        # that might have come in while the report was being generated.
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