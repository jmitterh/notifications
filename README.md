# Contact Form Monitor & Notification System

A robust Python-based monitoring system that automatically checks for new contact form submissions on your website and sends notifications via multiple channels (email, Discord, etc.). Designed to bypass common WAF (Web Application Firewall) protections that might block API requests.

## 🚀 Features

- **Multiple monitoring approaches**: API requests, admin panel scraping, and Selenium-based browser automation
- **WAF bypass capabilities**: Uses browser-like headers and Selenium to circumvent protection mechanisms
- **Multi-channel notifications**: Email (Gmail SMTP) and Discord webhook support
- **Automated monitoring**: GitHub Actions integration for continuous monitoring every 15 minutes
- **Persistent state**: Tracks message counts to detect only new submissions
- **Error handling**: Robust retry mechanisms and fallback strategies

## 📋 Components

### Core Scripts

1. **`selenium_contact_monitor.py`** *(Recommended - Working)*
   - Uses Selenium WebDriver to bypass JavaScript challenges and WAF protection
   - Most reliable for protected endpoints
   - Supports both email and Discord notifications

2. **`contact_monitor.py`**
   - Direct API approach with browser-like headers
   - Faster but may be blocked by WAF
   - Good for unprotected endpoints

3. **`admin_scraper_contact_monitor.py`**
   - Scrapes admin panel directly instead of using API
   - Bypass API-level WAF restrictions
   - Currently not working for original purpose

### Configuration

- **`items.py`** *(Not included - you need to create this)*
  ```python
  # Your configuration file
  EMAIL = "your-email@gmail.com"
  PASSWORD = "your-app-password"  # Gmail app password
  API_KEY = "your-api-key"
  API_URL = "https://your-site.com/api/messages"
  ADMIN_URL = "https://your-site.com/admin.php"
  ADMIN_PASSWORD = "your-admin-password"
  DISCORD_WEBHOOK = "https://discord.com/api/webhooks/..."
  ```

## 🛠️ Setup

### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# For Selenium (recommended approach)
# Download ChromeDriver from https://chromedriver.chromium.org/
# Or install via package manager:
# Ubuntu/Debian: sudo apt-get install chromium-chromedriver
# macOS: brew install chromedriver
```

### Local Setup

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd python-notification-system
   ```

2. Create your `items.py` configuration file with your credentials

3. Test the monitor:
   ```bash
   python selenium_contact_monitor.py
   ```

### GitHub Actions Setup

The repository includes automated monitoring via GitHub Actions that runs every 15 minutes.

#### Required Secrets

Add these secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

- `EMAIL`: Your Gmail address
- `EMAIL_PASSWORD`: Your Gmail app password ([How to get app password](https://support.google.com/accounts/answer/185833))
- `API_KEY`: Your website's API key
- `API_URL`: Your contact form API endpoint
- `DISCORD_WEBHOOK`: Discord webhook URL (optional)

#### Workflow Configuration

The workflow is already configured in `.github/workflows/monitor.yml` and will:
- Run every 15 minutes
- Install dependencies
- Execute the monitoring script
- Send notifications for new messages

## 📧 Notification Channels

### Email (Gmail)
- Uses SMTP with app passwords for security
- Sends detailed message information
- Includes direct links to admin panel

### Discord Webhook
- Rich embed notifications with message preview
- Instant notifications to your Discord server
- Color-coded alerts

## 🔧 Technical Details

### WAF Bypass Strategies

1. **Browser Simulation**: Uses realistic User-Agent strings and headers
2. **Selenium WebDriver**: Executes JavaScript and handles dynamic content
3. **Retry Logic**: Implements exponential backoff for failed requests
4. **Session Management**: Maintains cookies and connection state

### Security Considerations

- Credentials stored as GitHub Secrets (encrypted)
- API keys masked in logs
- SSL certificate verification enabled by default
- No sensitive data committed to repository

## 🚦 Usage

### Manual Run
```bash
python selenium_contact_monitor.py
```

### Continuous Monitoring
The GitHub Actions workflow handles continuous monitoring automatically. Check the Actions tab in your repository to see run history and logs.

### Customization

- Modify `CONFIG` dictionary in scripts to adjust timing, notification preferences
- Update `.github/workflows/monitor.yml` to change monitoring frequency
- Add new notification channels by extending the notification functions

## 📊 Monitoring

- Check GitHub Actions logs for monitoring status
- Message counts are tracked in `last_message_count.txt`
- Failed notifications are logged with error details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

## 🛟 Troubleshooting

### Common Issues

1. **ChromeDriver not found**: Install ChromeDriver and ensure it's in your PATH
2. **Gmail authentication**: Use app passwords, not regular passwords
3. **WAF blocking**: Try the Selenium approach instead of direct API calls
4. **GitHub Actions failing**: Check that all required secrets are set

### Debug Mode

Enable verbose logging by modifying the scripts to include more detailed output for troubleshooting.

---

*This system is designed for personal use to monitor your own website's contact forms. Ensure you comply with the terms of service of all platforms you're monitoring.*