#!/usr/bin/env python3
"""
Contact Form Monitor using Selenium to bypass WAF protection
Cross-platform version (Windows + Linux CI)
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time
import os
import requests
import sys
import logging
import platform
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import configuration
try:
    from items import EMAIL, PASSWORD, API_KEY, API_URL, DISCORD_WEBHOOK
    logger.info("Successfully imported configuration")
except ImportError as e:
    logger.error(f"Failed to import configuration: {e}")
    logger.error("Make sure items.py exists with all required variables")
    sys.exit(1)

# Configuration
CONFIG = {
    'API_URL': API_URL,
    'LAST_COUNT_FILE': 'last_message_count.txt',
    'CHECK_INTERVAL': 900,  # 15 minutes
    
    # Email notification
    'SMTP_SERVER': 'smtp.gmail.com',
    'SMTP_PORT': 587,
    'EMAIL_USER': EMAIL,
    'EMAIL_PASS': PASSWORD,
    'NOTIFY_EMAIL': EMAIL,
    
    # API key
    'API_KEY': API_KEY,
    
    # Discord Webhook
    'DISCORD_WEBHOOK': DISCORD_WEBHOOK
}

def is_ci_environment():
    """Check if running in CI environment"""
    return os.getenv('GITHUB_ACTIONS') == 'true' or os.getenv('CI') == 'true'

def setup_driver():
    """Set up Chrome driver with options optimized for both Windows and CI"""
    chrome_options = Options()
    
    # Universal options that work on both platforms
    chrome_options.add_argument('--headless=new')  # Use new headless mode
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--disable-images')  # Speed up loading
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # CI-specific options (these can cause issues on Windows)
    if is_ci_environment():
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--single-process')  # Only in CI
        logger.info("Running in CI environment, using CI-specific Chrome options")
    else:
        # Local development options (more stable on Windows)
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--disable-gpu-logging')
        chrome_options.add_argument('--log-level=3')  # Suppress console logs
        logger.info("Running locally, using local development Chrome options")
    
    try:
        system = platform.system().lower()
        logger.info(f"Detected operating system: {system}")
        
        if system == 'windows':
            # Windows-specific setup
            possible_drivers = [
                'chromedriver.exe',  # In PATH or current directory
                r'C:\chromedriver\chromedriver.exe',
                r'C:\Program Files\chromedriver\chromedriver.exe',
            ]
            
            driver_path = None
            for path in possible_drivers:
                if os.path.exists(path) or path == 'chromedriver.exe':
                    driver_path = path
                    logger.info(f"Found ChromeDriver at: {driver_path}")
                    break
            
            if driver_path and driver_path != 'chromedriver.exe':
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
        
        else:
            # Linux/Unix setup (for CI)
            possible_drivers = [
                '/usr/bin/chromedriver',
                '/usr/bin/chromium-chromedriver',
                '/usr/local/bin/chromedriver',
                '/snap/bin/chromium.chromedriver',
                'chromedriver'
            ]
            
            possible_chrome = [
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                '/usr/bin/google-chrome',
                '/snap/bin/chromium'
            ]
            
            driver_path = None
            chrome_binary = None
            
            # Find ChromeDriver
            for path in possible_drivers:
                if os.path.exists(path):
                    driver_path = path
                    logger.info(f"Found ChromeDriver at: {driver_path}")
                    break
            
            # Find Chrome binary
            for path in possible_chrome:
                if os.path.exists(path):
                    chrome_binary = path
                    logger.info(f"Found Chrome binary at: {chrome_binary}")
                    break
            
            # Set Chrome binary location if found
            if chrome_binary:
                chrome_options.binary_location = chrome_binary
            
            # Create driver
            if driver_path and driver_path != 'chromedriver':
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)
        
        # Set timeouts
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        logger.info("ChromeDriver started successfully")
        return driver
        
    except Exception as e:
        logger.error(f"Error setting up Chrome driver: {e}")
        logger.error("Make sure Chrome/Chromium and ChromeDriver are installed")
        
        # Additional troubleshooting info
        if system == 'windows':
            logger.error("For Windows: Download ChromeDriver from https://chromedriver.chromium.org/")
            logger.error("Make sure ChromeDriver version matches your Chrome version")
        
        return None

def get_current_messages():
    """Fetch messages using Selenium to bypass WAF"""
    driver = setup_driver()
    if not driver:
        return None
    
    try:
        url = f"{CONFIG['API_URL']}?api_key={CONFIG['API_KEY']}"
        logger.info(f"Loading URL: {CONFIG['API_URL']}")
        
        driver.get(url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Get page source
        page_text = driver.page_source
        logger.info(f"Page loaded, content length: {len(page_text)}")
        logger.debug(f"First 200 chars: {page_text[:200]}")
        
        # Look for JSON in the page
        if page_text.startswith('{"') or '{"success"' in page_text:
            try:
                # Extract JSON from page source
                start_idx = page_text.find('{"')
                if start_idx != -1:
                    json_text = page_text[start_idx:]
                    # Find end of JSON
                    brace_count = 0
                    end_idx = 0
                    for i, char in enumerate(json_text):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    
                    if end_idx > 0:
                        json_text = json_text[:end_idx]
                        logger.debug(f"Extracted JSON: {json_text}")
                        data = json.loads(json_text)
                        
                        if data.get('success'):
                            messages = data.get('messages', [])
                            logger.info(f"Successfully fetched {len(messages)} messages")
                            return messages
                        else:
                            logger.error(f"API error: {data.get('error', 'Unknown')}")
                            return None
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
                return None
        
        # Check for common error conditions
        if 'requires Javascript' in page_text:
            logger.warning("Still blocked by JavaScript challenge")
            return None
        elif 'Unauthorized' in page_text:
            logger.error("API key authentication failed")
            return None
        elif 'aes.js' in page_text:
            logger.warning("Encountered WAF challenge page")
            return None
        else:
            logger.warning("Unexpected page content")
            logger.debug(f"Page content: {page_text[:500]}")
            return None
    
    except Exception as e:
        logger.error(f"Selenium error: {e}")
        return None
    finally:
        try:
            driver.quit()
            logger.info("ChromeDriver closed")
        except:
            pass

def get_last_message_count():
    """Get last known count"""
    try:
        with open(CONFIG['LAST_COUNT_FILE'], 'r') as f:
            count = int(f.read().strip())
            logger.info(f"Last known message count: {count}")
            return count
    except FileNotFoundError:
        logger.info("No previous count file found, starting with 0")
        return 0
    except Exception as e:
        logger.warning(f"Error reading count file: {e}, defaulting to 0")
        return 0

def save_message_count(count):
    """Save current count"""
    try:
        with open(CONFIG['LAST_COUNT_FILE'], 'w') as f:
            f.write(str(count))
        logger.info(f"Saved message count: {count}")
    except Exception as e:
        logger.error(f"Error saving count: {e}")

def send_discord_notification(new_messages):
    """Send notification via Discord webhook"""
    if not CONFIG['DISCORD_WEBHOOK']:
        logger.info("No Discord webhook configured, skipping Discord notification")
        return True
    
    try:
        for msg in new_messages:
            data = {
                "content": "🔔 New contact form message!",
                "embeds": [{
                    "title": "New Contact Message",
                    "color": 0x00ff00,
                    "fields": [
                        {"name": "Name", "value": msg.get('name', 'Unknown'), "inline": True},
                        {"name": "Email", "value": msg.get('email', 'Unknown'), "inline": True},
                        {"name": "Message", "value": msg.get('message', '')[:200] + ("..." if len(msg.get('message', '')) > 200 else ""), "inline": False},
                        {"name": "Time", "value": msg.get('timestamp', 'Unknown'), "inline": True}
                    ]
                }]
            }
            response = requests.post(CONFIG['DISCORD_WEBHOOK'], json=data, timeout=10)
            if response.status_code == 204:
                logger.info("Discord notification sent successfully")
            else:
                logger.error(f"Discord notification failed with status: {response.status_code}")
                return False
        return True
    except Exception as e:
        logger.error(f"Discord notification failed: {e}")
        return False

def send_email_notification(new_messages):
    """Send email notification"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        logger.info("Connecting to email server...")
        logger.info(f"Email user: {CONFIG['EMAIL_USER']}")
        logger.info(f"SMTP server: {CONFIG['SMTP_SERVER']}:{CONFIG['SMTP_PORT']}")
        
        server = smtplib.SMTP(CONFIG['SMTP_SERVER'], CONFIG['SMTP_PORT'])
        server.starttls()
        
        # Try to login
        try:
            server.login(CONFIG['EMAIL_USER'], CONFIG['EMAIL_PASS'])
            logger.info("Gmail authentication successful")
        except smtplib.SMTPAuthenticationError as auth_error:
            logger.error(f"Gmail authentication failed: {auth_error}")
            logger.error("Make sure you're using a Gmail App Password, not your regular password")
            logger.error("App Password should be 16 characters like 'abcd efgh ijkl mnop'")
            server.quit()
            return False
        
        for msg in new_messages:
            email_msg = MIMEMultipart()
            email_msg['From'] = CONFIG['EMAIL_USER']
            email_msg['To'] = CONFIG['NOTIFY_EMAIL']
            email_msg['Subject'] = f"WEBSITE: New Contact Message from {msg.get('name', 'Unknown')}"
            
            body = f"""
New contact form message received:

Name: {msg.get('name', 'Unknown')}
Email: {msg.get('email', 'Unknown')}
Time: {msg.get('timestamp', 'Unknown')}

Message:
{msg.get('message', '')}

---
Automated notification from contact monitor
            """
            
            email_msg.attach(MIMEText(body, 'plain'))
            server.send_message(email_msg)
            logger.info(f"Email sent for message from {msg.get('name', 'Unknown')}")
        
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Email notification failed: {e}")
        return False

def check_for_new_messages():
    """Main check function"""
    logger.info(f"Starting message check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    current_messages = get_current_messages()
    if current_messages is None:
        logger.error("Failed to fetch messages")
        return False
    
    current_count = len(current_messages)
    last_count = get_last_message_count()
    
    logger.info(f"Current messages: {current_count}, Last known: {last_count}")
    
    if current_count > last_count:
        new_count = current_count - last_count
        new_messages = current_messages[-new_count:]
        
        logger.info(f"Found {new_count} new message(s)!")
        
        # Send notifications - try both, don't fail if one fails
        email_success = send_email_notification(new_messages)
        discord_success = send_discord_notification(new_messages)
        
        # Success if at least one notification method worked
        if email_success or discord_success:
            if email_success and discord_success:
                logger.info("Both email and Discord notifications sent successfully")
            elif email_success:
                logger.info("Email notification sent successfully (Discord skipped or failed)")
            elif discord_success:
                logger.info("Discord notification sent successfully (Email failed)")
            
            save_message_count(current_count)
            return True
        else:
            logger.error("All notification methods failed")
            return False
    else:
        logger.info("No new messages found")
        save_message_count(current_count)
        return True

if __name__ == "__main__":
    logger.info("Contact Monitor (Selenium) starting...")
    
    try:
        success = check_for_new_messages()
        if success:
            logger.info("Monitor completed successfully")
            sys.exit(0)
        else:
            logger.error("Monitor completed with errors")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)