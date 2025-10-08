import json
import os
from datetime import datetime
from typing import List, Dict
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration
MIN_ENGAGEMENT = 100
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL', 'your-email@gmail.com')
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'sender@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'your-app-password')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = 587


class UnifiedFeedAggregator:
    def __init__(self):
        self.all_posts: List[Dict] = []

    def fetch_reddit_posts_via_mcp(self) -> List[Dict]:
        """Placeholder for Reddit fetch via MCP."""
        reddit_posts: List[Dict] = []
        subreddits = ['SkincareAddiction', 'AsianBeauty', 'SkincareAddicts', '30PlusSkinCare']
        for subreddit in subreddits:
            try:
                print(f"📡 Fetching r/{subreddit} via Reddit MCP agent...")
            except Exception as e:
                print(f"⚠️ Error fetching r/{subreddit}: {e}")
        return reddit_posts

    # ---- Real source integrations ----
    def fetch_reddit_posts(self, limit: int = 20) -> List[Dict]:
        """Fetch Reddit posts from selected subreddits using PRAW.

        Supported env vars:
          - REDDIT_CLIENT_ID (required)
          - REDDIT_CLIENT_SECRET (required)
          - REDDIT_USER_AGENT (optional; default constructed if missing)
          - REDDIT_ACCOUNT (optional; Reddit username)
          - REDDIT_PASSWORD (optional; Reddit password for script auth)
        """
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        username = os.getenv('REDDIT_ACCOUNT') or os.getenv('REDDIT_USERNAME')
        password = os.getenv('REDDIT_PASSWORD')
        user_agent = os.getenv('REDDIT_USER_AGENT')
        if not user_agent:
            ua_owner = username or 'ai-skin-feed'
            user_agent = f"ai-skin-feed/1.0 by {ua_owner}"
        if not (client_id and client_secret):
            print("ℹ️ Reddit client credentials not set; skipping Reddit API fetch")
            return []
        try:
            import praw
        except ImportError:
            print("ℹ️ PRAW not installed in this environment; skipping Reddit API fetch")
            return []

        subreddits = ['SkincareAddiction', 'AsianBeauty', 'SkincareAddicts', '30PlusSkinCare']
        keywords = ['ai', 'artificial intelligence', 'skin analysis', 'scanner', 'algorithm', 'personalized']

        # Use script auth if username/password provided; otherwise app-only
        if username and password:
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                username=username,
                password=password,
            )
        else:
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
            )

        out: List[Dict] = []
        for name in subreddits:
            try:
                for s in reddit.subreddit(name).hot(limit=limit):
                    title = s.title or ''
                    text = getattr(s, 'selftext', '') or ''
                    hay = f"{title} {text}".lower()
                    if not any(k in hay for k in keywords):
                        continue
                    out.append({
                        'title': title,
                        'author': str(s.author) if s.author else 'unknown',
                        'url': f"https://www.reddit.com{s.permalink}",
                        'score': int(s.score or 0),
                        'comments': int(s.num_comments or 0),
                        'engagement': int((s.score or 0) + (s.num_comments or 0)),
                        'source': 'Reddit',
                        'subreddit': f"r/{name}",
                        'content': text[:500],
                        'created_utc': datetime.utcfromtimestamp(int(s.created_utc)).isoformat(),
                    })
            except Exception as e:
                print(f"⚠️ Reddit fetch error for r/{name}: {e}")
        print(f"✓ Fetched {len(out)} Reddit posts via API")
        return out

    def fetch_twitter_posts(self, max_results: int = 20) -> List[Dict]:
        """Fetch Twitter/X posts via API v2 recent search using TWITTER_BEARER_TOKEN if provided."""
        bearer = os.getenv('TWITTER_BEARER_TOKEN')
        # Fallback: derive bearer token from API key/secret if available
        if not bearer and os.getenv('TWITTER_API_KEY') and os.getenv('TWITTER_API_KEY_SECRET'):
            try:
                import base64
                key = os.getenv('TWITTER_API_KEY')
                secret = os.getenv('TWITTER_API_KEY_SECRET')
                basic = base64.b64encode(f"{key}:{secret}".encode()).decode()
                tok = requests.post(
                    'https://api.twitter.com/oauth2/token',
                    data={'grant_type': 'client_credentials'},
                    headers={
                        'Authorization': f'Basic {basic}',
                        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
                    },
                    timeout=15,
                )
                tok.raise_for_status()
                bearer = tok.json().get('access_token')
            except Exception as e:
                print(f"ℹ️ Unable to derive bearer token from API key/secret: {e}")
        if not bearer:
            print("ℹ️ No TWITTER_BEARER_TOKEN set; skipping Twitter API fetch")
            return []
        endpoint = 'https://api.twitter.com/2/tweets/search/recent'
        query = '(ai OR "artificial intelligence" OR algorithm OR "machine learning") (skin OR skincare OR dermatology) -is:retweet lang:en'
        params = {
            'query': query,
            'max_results': str(min(max_results, 100)),
            'tweet.fields': 'created_at,public_metrics,author_id',
            'expansions': 'author_id',
            'user.fields': 'username,name',
        }
        headers = {'Authorization': f'Bearer {bearer}'}
        try:
            r = requests.get(endpoint, params=params, headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"⚠️ Twitter API error: {e}")
            return []

        users = {u['id']: u for u in (data.get('includes', {}).get('users', []) or [])}
        out: List[Dict] = []
        for t in data.get('data', []) or []:
            metrics = t.get('public_metrics', {})
            likes = int(metrics.get('like_count', 0))
            replies = int(metrics.get('reply_count', 0))
            retweets = int(metrics.get('retweet_count', 0))
            quotes = int(metrics.get('quote_count', 0))
            author = users.get(t.get('author_id') or '', {})
            url = f"https://x.com/{author.get('username','')}/status/{t.get('id')}"
            out.append({
                'title': (t.get('text') or '')[:120],
                'author': author.get('username') or 'unknown',
                'url': url,
                'score': likes,
                'comments': replies,
                'engagement': likes + replies + retweets + quotes,
                'source': 'Twitter',
                'subreddit': 'Twitter',
                'content': t.get('text') or '',
                'created_utc': t.get('created_at') or '',
            })
        print(f"✓ Fetched {len(out)} Twitter/X posts via API")
        return out

    def fetch_instagram_posts(self, per_hashtag: int = 10) -> List[Dict]:
        """Fetch Instagram posts using Graph API via hashtag search if credentials provided.

        Env vars required:
          - IG_ACCESS_TOKEN (long-lived)
          - IG_BUSINESS_ID (your Instagram Business Account ID)

        Note: Instagram Graph API limitations apply; this queries hashtag recent/top media.
        """
        access_token = os.getenv('IG_ACCESS_TOKEN')
        business_id = os.getenv('IG_BUSINESS_ID')
        if not (access_token and business_id):
            print("ℹ️ Instagram Graph credentials not set; skipping Instagram API fetch")
            return []

        # Allow override via IG_HASHTAGS env (comma-separated)
        env_tags = os.getenv('IG_HASHTAGS')
        if env_tags:
            hashtags = [t.strip().lstrip('#') for t in env_tags.split(',') if t.strip()]
        else:
            hashtags = ['skincare', 'skinanalysis', 'aiskincare', 'dermatology', 'skintech']
        base = 'https://graph.facebook.com/v18.0'
        out: List[Dict] = []
        for tag in hashtags:
            try:
                hs = requests.get(f"{base}/ig_hashtag_search", params={
                    'user_id': business_id,
                    'q': tag,
                    'access_token': access_token,
                }, timeout=15).json()
                if not hs.get('data'):
                    continue
                hid = hs['data'][0]['id']
                media = requests.get(f"{base}/{hid}/recent_media", params={
                    'user_id': business_id,
                    'fields': 'caption,media_url,permalink,like_count,comments_count,timestamp,media_type,username',
                    'access_token': access_token,
                    'limit': per_hashtag,
                }, timeout=20).json()
                for m in media.get('data', []) or []:
                    caption = m.get('caption') or ''
                    out.append({
                        'title': caption[:120] or f"#{tag}",
                        'author': m.get('username', 'unknown'),
                        'url': m.get('permalink'),
                        'score': int(m.get('like_count') or 0),
                        'comments': int(m.get('comments_count') or 0),
                        'engagement': int((m.get('like_count') or 0) + (m.get('comments_count') or 0)),
                        'source': 'Instagram',
                        'subreddit': 'Instagram',
                        'content': caption[:500],
                        'created_utc': m.get('timestamp') or '',
                    })
            except Exception as e:
                print(f"⚠️ Instagram API error for #{tag}: {e}")
        print(f"✓ Fetched {len(out)} Instagram posts via Graph API")
        return out

    def fetch_linkedin_posts(self) -> List[Dict]:
        """Fetch LinkedIn posts via Apify dump; fallback to curated list."""
        try:
            with open('linkedin_apify_posts.json', 'r', encoding='utf-8') as f:
                apify_posts = json.load(f)
                if apify_posts:
                    print(f"✓ Loaded {len(apify_posts)} LinkedIn posts from Apify scrape")
                    return apify_posts[:5]
        except FileNotFoundError:
            print("ℹ️  No Apify LinkedIn posts found, using fallback data")

        linkedin_posts = [
            {
                'title': "AI-powered skincare diagnostics: The future of dermatology",
                'author': 'Dr. Sarah Chen',
                'url': 'https://www.linkedin.com/posts/ai-skincare-tech',
                'score': 1200,
                'comments': 85,
                'engagement': 1285,
                'source': 'LinkedIn',
                'subreddit': 'LinkedIn',
                'content': 'How AI is revolutionizing skin analysis and personalized treatment recommendations in clinical settings.',
                'created_utc': '2024-09-25T12:00:00'
            },
            {
                'title': "Launching our AI skin analysis platform - $5M Series A",
                'author': 'TechVentures',
                'url': 'https://www.linkedin.com/posts/skintech-ai',
                'score': 890,
                'comments': 64,
                'engagement': 954,
                'source': 'LinkedIn',
                'subreddit': 'LinkedIn',
                'content': 'Proud to announce our Series A funding to bring AI-powered skincare diagnostics to consumers worldwide.',
                'created_utc': '2024-09-20T12:00:00'
            },
            {
                'title': "AI vs Dermatologists: Study shows 94% accuracy in melanoma detection",
                'author': 'Medical AI Research',
                'url': 'https://www.linkedin.com/posts/medical-ai-research',
                'score': 756,
                'comments': 123,
                'engagement': 879,
                'source': 'LinkedIn',
                'subreddit': 'LinkedIn',
                'content': 'New peer-reviewed study demonstrates AI matching dermatologist accuracy in skin cancer screening.',
                'created_utc': '2024-09-18T12:00:00'
            },
            {
                'title': "Building AI skincare apps: Lessons from 100K users",
                'author': 'Product Manager Insights',
                'url': 'https://www.linkedin.com/posts/pm-skincare',
                'score': 645,
                'comments': 92,
                'engagement': 737,
                'source': 'LinkedIn',
                'subreddit': 'LinkedIn',
                'content': 'Key learnings from scaling our AI skincare analysis app to 100,000 active users in 6 months.',
                'created_utc': '2024-09-15T12:00:00'
            },
            {
                'title': "Ethical AI in beauty tech: Privacy and bias considerations",
                'author': 'AI Ethics Forum',
                'url': 'https://www.linkedin.com/posts/ai-ethics-beauty',
                'score': 534,
                'comments': 78,
                'engagement': 612,
                'source': 'LinkedIn',
                'subreddit': 'LinkedIn',
                'content': 'Addressing algorithmic bias and data privacy in AI-powered skincare applications.',
                'created_utc': '2024-09-12T12:00:00'
            }
        ]
        return linkedin_posts

    def load_posts_from_sources(self) -> List[Dict]:
        """Load posts from combined JSON and enrich with other sources; filter + sort."""
        all_posts: List[Dict] = []

        print("🚀 Fetching live data from sources where credentials are configured...")
        # Live source calls (each is optional depending on env vars)
        try:
            reddit_posts = self.fetch_reddit_posts(limit=25)
            all_posts.extend(reddit_posts)
        except Exception as e:
            print(f"⚠️ Reddit integration error: {e}")

        try:
            twitter_posts = self.fetch_twitter_posts(max_results=25)
            all_posts.extend(twitter_posts)
        except Exception as e:
            print(f"⚠️ Twitter integration error: {e}")

        # Instagram disabled by request (enable later if needed)

        # If nothing fetched, fallback to packaged combined JSON
        if not all_posts:
            print("ℹ️ No live sources returned posts; using local social_feed_combined.json fallback")
            try:
                with open('social_feed_combined.json', 'r', encoding='utf-8') as f:
                    combined_posts = json.load(f)
                    print(f"✓ Loaded {len(combined_posts)} posts from combined feed")
                    all_posts = combined_posts
            except FileNotFoundError:
                print("⚠️ Fallback combined feed not found; returning empty list")

        print(f"\n🔍 Filtering posts with score > 100...")
        print(f"   Before filter: {len(all_posts)} posts")
        all_posts = [p for p in all_posts if p.get('score', 0) > 100]
        print(f"   After filter: {len(all_posts)} posts")

        all_posts.sort(key=lambda x: x.get('engagement', 0), reverse=True)
        self.all_posts = all_posts
        print(f"\n📊 Total posts in feed: {len(all_posts)}")

        platforms: Dict[str, int] = {}
        for post in all_posts:
            platform = post.get('source', post.get('platform', 'Unknown'))
            platforms[platform] = platforms.get(platform, 0) + 1

        print("📱 Platform breakdown:")
        for platform, count in platforms.items():
            print(f"   - {platform}: {count}")

        return all_posts

    def generate_html_email(self, posts: List[Dict]) -> str:
        total_engagement = sum(p.get('engagement', 0) for p in posts)
        sources = set(p.get('source', 'Unknown') for p in posts)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background: #f8f9fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 15px; text-align: center; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; font-size: 32px; }}
        .date {{ opacity: 0.95; margin-top: 10px; font-size: 16px; }}
        .stats {{ display: flex; justify-content: space-around; background: white; border-radius: 12px; padding: 25px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
        .stat {{ text-align: center; }}
        .stat-number {{ font-size: 36px; font-weight: bold; color: #667eea; }}
        .stat-label {{ color: #666; font-size: 14px; margin-top: 5px; }}
        .post-card {{ background: white; border-radius: 12px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); border-left: 4px solid #667eea; }}
        .post-title {{ font-size: 20px; font-weight: 600; color: #333; margin-bottom: 12px; }}
        .source-badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-right: 8px; }}
        .badge-reddit {{ background: #ff4500; color: white; }}
        .badge-twitter {{ background: #1da1f2; color: white; }}
        .badge-instagram {{ background: #e4405f; color: white; }}
        .post-meta {{ color: #666; font-size: 14px; margin-bottom: 12px; }}
        .engagement {{ background: #f0f0f0; padding: 6px 12px; border-radius: 15px; font-size: 13px; display: inline-block; }}
        .engagement.high {{ background: #d4edda; color: #155724; }}
        .post-content {{ color: #555; line-height: 1.6; margin: 12px 0; }}
        .post-link {{ color: #667eea; text-decoration: none; font-weight: 500; }}
        .footer {{ text-align: center; color: #999; padding: 30px; margin-top: 40px; border-top: 2px solid #eee; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔬 AI Skincare Analysis Daily Digest</h1>
        <div class="date">{datetime.now().strftime('%A, %B %d, %Y')}</div>
    </div>
    <div class="stats">
        <div class="stat"><div class="stat-number">{len(posts)}</div><div class="stat-label">Hot Posts</div></div>
        <div class="stat"><div class="stat-number">{total_engagement:,}</div><div class="stat-label">Total Engagement</div></div>
        <div class="stat"><div class="stat-number">{len(sources)}</div><div class="stat-label">Sources</div></div>
    </div>
"""

        for post in posts[:15]:
            source = post.get('source', 'Unknown')
            source_class = f"badge-{source.lower()}"
            engagement_class = 'high' if post.get('engagement', 0) > 500 else ''
            content_html = ''
            if post.get('content'):
                content_text = post.get('content', '')[:300]
                content_html = f'<div class="post-content">{content_text}...</div>'

            html += f"""
    <div class="post-card">
        <span class="source-badge {source_class}">{source}</span>
        <div class="post-title">{post.get('title', 'Untitled')}</div>
        <div class="post-meta"><span class="engagement {engagement_class}">⬆️ {post.get('score', 0)} • 💬 {post.get('comments', 0)} • 🔥 {post.get('engagement', 0)}</span><br>👤 {post.get('author', 'Unknown')}</div>
        {content_html}
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

    def send_email_newsletter(self):
        posts = self.load_posts_from_sources()
        if not posts:
            print("⚠️ No posts to send in newsletter")
            return
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🔬 Your Daily AI Skincare Digest - {datetime.now().strftime('%b %d, %Y')}"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = RECIPIENT_EMAIL
        html_content = self.generate_html_email(posts)
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.send_message(msg)
            print(f"✅ Newsletter sent to {RECIPIENT_EMAIL}")
        except Exception as e:
            print(f"❌ Error sending email: {e}")
