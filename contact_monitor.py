#!/usr/bin/env python3
"""
Contact Form Monitor - With proper browser headers
"""

import requests
import json
import time
import os
from datetime import datetime
from items import EMAIL, PASSWORD, API_KEY, API_URL

# Configuration
CONFIG = {
    'API_URL': API_URL,
    'LAST_COUNT_FILE': 'last_message_count.txt',
    'CHECK_INTERVAL': 900,  # 15 minutes
    
    # Email notification settings
    'SMTP_SERVER': 'smtp.gmail.com',
    'SMTP_PORT': 587,
    'EMAIL_USER': EMAIL,
    'EMAIL_PASS': PASSWORD,
    'NOTIFY_EMAIL': EMAIL,
    
    # API key for your endpoint
    'API_KEY': API_KEY
}

# Browser-like headers to avoid blocking
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0'
}


def get_last_message_count():
    """Get the last known message count from file"""
    try:
        if os.path.exists(CONFIG['LAST_COUNT_FILE']):
            with open(CONFIG['LAST_COUNT_FILE'], 'r') as f:
                return int(f.read().strip())
        return 0
    except:
        return 0

def save_message_count(count):
    """Save the current message count to file"""
    try:
        with open(CONFIG['LAST_COUNT_FILE'], 'w') as f:
            f.write(str(count))
    except Exception as e:
        print(f"Error saving count: {e}")

def get_current_messages():
    """Fetch current messages from the API endpoint with proper headers"""
    try:
        print("Fetching messages from API...")
        
        # Create a session for better connection handling
        session = requests.Session()
        session.headers.update(HEADERS)
        
        params = {'api_key': CONFIG['API_KEY']}
        print(f"Using API key: {CONFIG['API_KEY'][:20]}...")  # Only show first 20 chars for security
        
        # Make the request with headers and session
        response = session.get(
            CONFIG['API_URL'], 
            params=params, 
            timeout=30,
            stream=False,
            allow_redirects=True
            # verify=True  # Verify SSL certificates
        )
        
        print(f"API Response Status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print(f"Raw response (first 200 chars): {response.text[:200]}")
            
            try:
                data = response.json()
                print(f"JSON parsed successfully: {data}")
                
                if data.get('success'):
                    messages = data.get('messages', [])
                    print(f"Found {len(messages)} messages")
                    return messages
                else:
                    print(f"API error: {data.get('error', 'Unknown error')}")
                    return None
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Raw response: {response.text}")
                return None
        else:
            print(f"HTTP error: {response.status_code}")
            print(f"Response text: {response.text}")
            return None
            
    except requests.exceptions.SSLError as e:
        print(f"SSL error: {e}")
        print("Trying again without SSL verification...")
        
        try:
            # Retry without SSL verification as fallback
            session = requests.Session()
            session.headers.update(HEADERS)
            
            response = session.get(
                CONFIG['API_URL'], 
                params={'api_key': CONFIG['API_KEY']}, 
                timeout=30,
                verify=False  # Disable SSL verification
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('messages', [])
            return None
            
        except Exception as retry_e:
            print(f"Retry also failed: {retry_e}")
            return None
            
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        return None
    except requests.exceptions.Timeout as e:
        print(f"Timeout error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def send_email_notification(new_messages):
    """Send notification via email"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        print("Connecting to email server...")
        server = smtplib.SMTP(CONFIG['SMTP_SERVER'], CONFIG['SMTP_PORT'])
        server.starttls()
        server.login(CONFIG['EMAIL_USER'], CONFIG['EMAIL_PASS'])
        
        for msg in new_messages:
            email_msg = MIMEMultipart()
            email_msg['From'] = CONFIG['EMAIL_USER']
            email_msg['To'] = CONFIG['NOTIFY_EMAIL']
            email_msg['Subject'] = f"New Contact Message from {msg.get('name', 'Unknown')}"
            
            body = f"""
New contact form message received on your website:

Name: {msg.get('name', 'Unknown')}
Email: {msg.get('email', 'Unknown')}
Time: {msg.get('timestamp', 'Unknown')}

Message:
{msg.get('message', 'No message content')}

---
View admin panel.

This is an automated notification from your contact form monitor.
            """
            
            email_msg.attach(MIMEText(body, 'plain'))
            server.send_message(email_msg)
            print(f"Email sent for message from {msg.get('name', 'Unknown')}")
        
        server.quit()
        return True
    except Exception as e:
        print(f"Email notification failed: {e}")
        return False

def send_desktop_notification(new_messages):
    """Send desktop notification (Windows)"""
    try:
        # Try Windows toast notifications
        import win10toast
        toaster = win10toast.ToastNotifier()
        
        for msg in new_messages:
            toaster.show_toast(
                "New Contact Message",
                f"From: {msg.get('name', 'Unknown')}\nEmail: {msg.get('email', 'Unknown')}",
                duration=10,
                icon_path=None
            )
        return True
    except ImportError:
        print("win10toast not installed. Install with: pip install win10toast")
        return False
    except Exception as e:
        print(f"Desktop notification failed: {e}")
        return False

def check_for_new_messages():
    """Main function to check for new messages and notify"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for new messages...")
    
    # Get current messages
    current_messages = get_current_messages()
    if current_messages is None:
        print("Could not fetch messages - API might be down")
        return False
    
    current_count = len(current_messages)
    last_count = get_last_message_count()
    
    print(f"Current messages: {current_count}, Last known: {last_count}")
    
    if current_count > last_count:
        new_message_count = current_count - last_count
        print(f"Found {new_message_count} new message(s)!")
        
        # Get the new messages (last N messages)
        new_messages = current_messages[-new_message_count:]
        
        # Send notifications
        email_success = send_email_notification(new_messages)
        desktop_success = send_desktop_notification(new_messages)
        
        if email_success or desktop_success:
            print("Notifications sent!")
            save_message_count(current_count)
        else:
            print("All notifications failed")
            return False
    else:
        print("No new messages")
    
    save_message_count(current_count)
    return True

if __name__ == "__main__":
    print("Contact Form Monitor Starting...")
    print("Press Ctrl+C to stop")
    
    try:
        # Run once for testing
        check_for_new_messages()
        
        # Uncomment below for continuous monitoring
        # while True:
        #     success = check_for_new_messages()
        #     if not success:
        #         print("Check failed, retrying in 5 minutes...")
        #         time.sleep(300)
        #     else:
        #         print(f"Next check in {CONFIG['CHECK_INTERVAL']//60} minutes...")
        #         time.sleep(CONFIG['CHECK_INTERVAL'])
            
    except KeyboardInterrupt:
        print("\nMonitor stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")