#!/usr/bin/env python3
"""
Simple admin panel scraper - bypasses API WAF issues entirely
Currently does not work for its original purpose.
"""

import requests
import re
import time
from datetime import datetime
from items import EMAIL, PASSWORD, ADMIN_PASSWORD, ADMIN_URL

# Configuration
CONFIG = {
    'ADMIN_URL': ADMIN_URL,
    'ADMIN_PASSWORD': ADMIN_PASSWORD,  # Your admin panel password
    'LAST_COUNT_FILE': 'last_message_count.txt',
    'CHECK_INTERVAL': 900,
    
    'EMAIL_USER': EMAIL,
    'EMAIL_PASS': PASSWORD,
    'NOTIFY_EMAIL': EMAIL
}

def create_session():
    """Create session with retry adapter"""
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    session = requests.Session()
    
    # Add retry strategy
    retry = Retry(
        total=3, connect=3, read=3, backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"])
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    
    # Browser headers
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })
    
    return session

def handle_waf_challenge(session, url):
    """Handle the WAF JavaScript challenge by waiting and retrying"""
    max_attempts = 3
    
    for attempt in range(max_attempts):
        print(f"Attempt {attempt + 1} to access {url}")
        
        response = session.get(url, timeout=15, allow_redirects=True)
        
        if response.status_code == 200:
            # Check if we got the JavaScript challenge
            if 'requires Javascript' in response.text or 'aes.js' in response.text:
                print("Got WAF challenge, waiting and retrying...")
                time.sleep(5)  # Wait for potential redirect
                continue
            else:
                # Successfully bypassed or no challenge
                return response
    
    print("Could not bypass WAF challenge")
    return None

def login_to_admin(session):
    """Login to admin panel"""
    try:
        print("Accessing admin panel...")
        response = handle_waf_challenge(session, CONFIG['ADMIN_URL'])
        
        if not response:
            return False
        
        # Check if login form is present
        if 'password' in response.text.lower() and 'login' in response.text.lower():
            print("Submitting login...")
            login_data = {'password': CONFIG['ADMIN_PASSWORD']}
            response = session.post(CONFIG['ADMIN_URL'], data=login_data, timeout=15)
            
            if response.status_code == 200 and 'Contact Form Messages' in response.text:
                print("Successfully logged in")
                return True
            else:
                print("Login failed - check password")
                return False
        elif 'Contact Form Messages' in response.text:
            print("Already logged in")
            return True
        else:
            print("Unexpected admin page content")
            return False
            
    except Exception as e:
        print(f"Login error: {e}")
        return False

def get_message_count_from_admin(session):
    """Get message count from admin panel"""
    try:
        response = session.get(CONFIG['ADMIN_URL'], timeout=15)
        
        if response.status_code != 200:
            return None
        
        # Look for "Total Messages: X"
        match = re.search(r'Total Messages:\s*(\d+)', response.text)
        if match:
            return int(match.group(1))
        
        # Alternative: count message divs
        message_count = response.text.count('<div class="message">')
        if message_count >= 0:
            return message_count
        
        return None
    except Exception as e:
        print(f"Error getting count: {e}")
        return None

def send_email_notification(new_message_count):
    """Send simple email notification"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(CONFIG['EMAIL_USER'], CONFIG['EMAIL_PASS'])
        
        subject = f"New Contact Messages ({new_message_count})"
        body = f"""
You have {new_message_count} new contact form messages.

View them at: {CONFIG['ADMIN_URL']}

Automated notification from your website monitor.
        """
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = CONFIG['EMAIL_USER']
        msg['To'] = CONFIG['NOTIFY_EMAIL']
        
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

def check_messages():
    """Main function"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking messages...")
    
    session = create_session()
    
    # Login to admin
    if not login_to_admin(session):
        return False
    
    # Get current count
    current_count = get_message_count_from_admin(session)
    if current_count is None:
        print("Could not get message count")
        return False
    
    # Compare with last count
    try:
        with open(CONFIG['LAST_COUNT_FILE'], 'r') as f:
            last_count = int(f.read().strip())
    except:
        last_count = 0
    
    print(f"Current: {current_count}, Last: {last_count}")
    
    if current_count > last_count:
        new_count = current_count - last_count
        print(f"Found {new_count} new messages!")
        
        if send_email_notification(new_count):
            print("Email notification sent")
            # Save new count
            with open(CONFIG['LAST_COUNT_FILE'], 'w') as f:
                f.write(str(current_count))
        else:
            return False
    else:
        print("No new messages")
        # Update count anyway
        with open(CONFIG['LAST_COUNT_FILE'], 'w') as f:
            f.write(str(current_count))
    
    return True

if __name__ == "__main__":
    print("Contact Monitor (Admin Scraper) starting...")
    
    # Update your admin password here
    CONFIG['ADMIN_PASSWORD'] = input("Enter your admin panel password: ")
    
    # Run check
    check_messages()