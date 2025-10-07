#!/usr/bin/env python3
"""
Unified AI Skincare Feed Aggregator
Web app renders feed; daily aggregation is done by Azure Function.
"""

import json
import os
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from aggregator import UnifiedFeedAggregator

# Configuration
load_dotenv()

# Email config remains for the optional test-email route
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL', 'your-email@gmail.com')
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'sender@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'your-app-password')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = 587

app = Flask(__name__)

# Add custom Jinja2 filter for number formatting
@app.template_filter('format_number')
def format_number(value):
    """Format numbers with commas (e.g., 1000 -> 1,000)"""
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return value

def _get_blob_service_client() -> Optional[BlobServiceClient]:
    """Create a BlobServiceClient via connection string or managed identity.

    Returns None if no configuration found.
    """
    conn_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if conn_str:
        try:
            return BlobServiceClient.from_connection_string(conn_str)
        except Exception:
            pass

    account_url = os.getenv('BLOB_ACCOUNT_URL')  # e.g., https://<account>.blob.core.windows.net
    if account_url:
        try:
            cred = DefaultAzureCredential(exclude_interactive_browser_credential=True)
            return BlobServiceClient(account_url=account_url, credential=cred)
        except Exception:
            pass
    return None


def _read_latest_posts_from_blob() -> Optional[List[Dict[str, Any]]]:
    client = _get_blob_service_client()
    if not client:
        return None
    container_name = os.getenv('FEED_CONTAINER', 'feeds')
    blob_name = os.getenv('FEED_BLOB_NAME', 'latest.json')
    try:
        container_client = client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        data = blob_client.download_blob().readall()
        return json.loads(data)
    except Exception as e:
        print(f"ℹ️ Unable to read blob {container_name}/{blob_name}: {e}")
        return None

def _read_posts_for_date(date_str: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    """Read posts for a specific date (YYYY-MM-DD.json) from Blob. If date_str is None, read latest."""
    if date_str is None:
        return _read_latest_posts_from_blob()
    client = _get_blob_service_client()
    if not client:
        return None
    container_name = os.getenv('FEED_CONTAINER', 'feeds')
    blob_name = f"{date_str}.json"
    try:
        container_client = client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        data = blob_client.download_blob().readall()
        return json.loads(data)
    except Exception as e:
        print(f"ℹ️ Unable to read blob {container_name}/{blob_name}: {e}")
        return None

def _list_available_dates_from_blob(max_items: int = 30) -> List[str]:
    """List available dates from Blob container by enumerating YYYY-MM-DD.json files, sorted desc."""
    client = _get_blob_service_client()
    if not client:
        return []
    container_name = os.getenv('FEED_CONTAINER', 'feeds')
    try:
        container_client = client.get_container_client(container_name)
        dates: List[str] = []
        for blob in container_client.list_blobs():
            name = getattr(blob, 'name', '')
            if name.endswith('.json') and name != os.getenv('FEED_BLOB_NAME', 'latest.json'):
                base = name[:-5]  # strip .json
                # basic validation: expect YYYY-MM-DD
                if len(base) == 10 and base[4] == '-' and base[7] == '-':
                    dates.append(base)
        dates.sort(reverse=True)
        return dates[:max_items]
    except Exception as e:
        print(f"ℹ️ Unable to list blobs in {container_name}: {e}")
        return []

def _today_utc_str() -> str:
    return datetime.utcnow().strftime('%Y-%m-%d')

def generate_html_email(posts: List[Dict]) -> str:
    """Generate beautiful HTML email newsletter"""
    total_engagement = sum(p.get('engagement', 0) for p in posts)
    sources = set(p.get('source', 'Unknown') for p in posts)

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f8f9fa;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 32px;
        }}
        .date {{
            opacity: 0.95;
            margin-top: 10px;
            font-size: 16px;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .stat {{
            text-align: center;
        }}
        .stat-number {{
            font-size: 36px;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #666;
            font-size: 14px;
            margin-top: 5px;
        }}
        .post-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid #667eea;
        }}
        .post-title {{
            font-size: 20px;
            font-weight: 600;
            color: #333;
            margin-bottom: 12px;
        }}
        .source-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }}
        .badge-reddit {{ background: #ff4500; color: white; }}
        .badge-twitter {{ background: #1da1f2; color: white; }}
        .badge-instagram {{ background: #e4405f; color: white; }}
        .post-meta {{
            color: #666;
            font-size: 14px;
            margin-bottom: 12px;
        }}
        .engagement {{
            background: #f0f0f0;
            padding: 6px 12px;
            border-radius: 15px;
            font-size: 13px;
            display: inline-block;
        }}
        .engagement.high {{
            background: #d4edda;
            color: #155724;
        }}
        .post-content {{
            color: #555;
            line-height: 1.6;
            margin: 12px 0;
        }}
        .post-link {{
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }}
        .footer {{
            text-align: center;
            color: #999;
            padding: 30px;
            margin-top: 40px;
            border-top: 2px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 AI Skincare Analysis Daily Digest</h1>
        <div class="date">{datetime.now().strftime('%A, %B %d, %Y')}</div>
    </div>

    <div class="stats">
        <div class="stat">
            <div class="stat-number">{len(posts)}</div>
            <div class="stat-label">Hot Posts</div>
        </div>
        <div class="stat">
            <div class="stat-number">{total_engagement:,}</div>
            <div class="stat-label">Total Engagement</div>
        </div>
        <div class="stat">
            <div class="stat-number">{len(sources)}</div>
            <div class="stat-label">Sources</div>
        </div>
    </div>
"""

        for post in posts[:15]:
            source = post.get('source', 'Unknown')
            source_class = f"badge-{source.lower()}"
            engagement_class = 'high' if post.get('engagement', 0) > 500 else ''

            html += f"""
    <div class="post-card">
        <span class="source-badge {source_class}">{source}</span>
        <div class="post-title">{post.get('title', 'Untitled')}</div>
        <div class="post-meta">
            <span class="engagement {engagement_class}">
                ⬆️ {post.get('score', 0)} • 💬 {post.get('comments', 0)} • 🔥 {post.get('engagement', 0)}
            </span>
            <br>
            👤 {post.get('author', 'Unknown')}
        </div>
        {f'<div class="post-content">{post.get("content", "")[:300]}...</div>' if post.get('content') else ''}
        <a href="{post.get('url', '#')}" class="post-link">Read full discussion →</a>
    </div>
"""

    html += """
    <div class="footer">
        <p><strong>🔬 AI Skincare Analysis Feed</strong></p>
        <p>Your daily digest of trending AI-driven skincare discussions</p>
        <p>Delivered every morning at 8:00 AM</p>
    </div>
</body>
</html>
"""
    return html

# Flask routes
@app.route('/')
def index():
    """Display unified feed webpage"""
    requested_date = request.args.get('date')
    selected_date = requested_date or _today_utc_str()
    posts = _read_posts_for_date(selected_date)
    if posts is None:
        # Fallback to latest
        posts = _read_latest_posts_from_blob()
    if posts is None:
        # Final fallback: local aggregation
        aggregator = UnifiedFeedAggregator()
        posts = aggregator.load_posts_from_sources()

    available_dates = _list_available_dates_from_blob()
    today_str = _today_utc_str()
    from datetime import timedelta
    yesterday_str = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

    # Ensure today's date appears as an option first
    if today_str not in available_dates:
        available_dates = [today_str] + available_dates

    return render_template(
        'feed.html',
        posts=posts,
        selected_date=selected_date,
        available_dates=available_dates,
        today_str=today_str,
        yesterday_str=yesterday_str
    )

@app.route('/api/posts')
def api_posts():
    """API endpoint for posts"""
    date_param = request.args.get('date')
    posts = _read_posts_for_date(date_param)
    if posts is None:
        posts = _read_latest_posts_from_blob()
    if posts is None:
        aggregator = UnifiedFeedAggregator()
        posts = aggregator.load_posts_from_sources()
    return jsonify(posts)

@app.route('/send-test-email')
def send_test_email():
    """Send a test email newsletter"""
    aggregator = UnifiedFeedAggregator()
    posts = aggregator.load_posts_from_sources()
    html_content = generate_html_email(posts)
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🔬 Your Daily AI Skincare Digest - {datetime.now().strftime('%b %d, %Y')}"
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_content, 'html'))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"✅ Newsletter sent to {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")
    return "Test email sent! Check your inbox."

if __name__ == '__main__':
    print("🔬 AI Skincare Feed Aggregator - Unified System")
    print("=" * 60)

    # Note: For local dev only. In Azure App Service use gunicorn.
    port = int(os.getenv('PORT', '5001'))
    print(f"\n🌐 Starting web server at http://localhost:{port}")
    print("🔗 Visit /send-test-email to send a test newsletter")
    print("\nPress Ctrl+C to stop\n")
    app.run(debug=True, host='0.0.0.0', port=port)
