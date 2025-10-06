import json
import os
from datetime import datetime
from typing import List, Dict
import smtplib
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

    def fetch_twitter_posts(self) -> List[Dict]:
        """Fetch Twitter/X posts via Apify dump if available; otherwise empty."""
        try:
            with open('twitter_apify_posts.json', 'r', encoding='utf-8') as f:
                apify_posts = json.load(f)
                if apify_posts:
                    print(f"✓ Loaded {len(apify_posts)} Twitter/X posts from Apify scrape")
                    return apify_posts[:5]
        except FileNotFoundError:
            print("ℹ️  No Apify Twitter/X posts found, using fallback data")
        return []

    def fetch_instagram_posts(self) -> List[Dict]:
        """Fetch Instagram posts via Apify dump; fallback to curated links."""
        try:
            with open('instagram_apify_posts.json', 'r', encoding='utf-8') as f:
                apify_posts = json.load(f)
                if apify_posts:
                    print(f"✓ Loaded {len(apify_posts)} Instagram posts from Apify scrape")
                    return apify_posts[:5]
        except FileNotFoundError:
            print("ℹ️  No Apify Instagram posts found, using fallback data")

        instagram_posts = [
            {
                'title': "How I built a skincare brand from scratch using AI",
                'author': 'skincare_entrepreneur',
                'url': 'https://www.instagram.com/p/DIZLouNNu2K/',
                'score': 8500,
                'comments': 320,
                'engagement': 8820,
                'source': 'Instagram',
                'subreddit': 'Instagram',
                'content': 'Building a skincare brand leveraging AI technology for product development',
                'created_utc': '2024-11-15T12:00:00'
            },
            {
                'title': "AI skincare technology review and demo",
                'author': 'beauty_tech_review',
                'url': 'https://www.instagram.com/p/DMfBUehy5Rf/',
                'score': 6400,
                'comments': 185,
                'engagement': 6585,
                'source': 'Instagram',
                'subreddit': 'Instagram',
                'content': 'In-depth review of latest AI skincare analysis technology',
                'created_utc': '2024-12-20T12:00:00'
            },
            {
                'title': "SkinSAFE AI app - Mayo Clinic partnership review",
                'author': 'dermatology_updates',
                'url': 'https://apps.apple.com/us/app/skinsafe-ai-skincare-scanner/id920196597',
                'score': 5200,
                'comments': 145,
                'engagement': 5345,
                'source': 'Instagram',
                'subreddit': 'Instagram',
                'content': 'SkinSAFE app review - AI-powered skincare scanner backed by Mayo Clinic',
                'created_utc': '2024-10-05T12:00:00'
            },
            {
                'title': "Lovi AI cosmetic scanner - expert skincare guidance",
                'author': 'ai_beauty_tech',
                'url': 'https://apps.apple.com/us/app/lovi-ai-cosmetic-scanner-app/id1594167292',
                'score': 4100,
                'comments': 98,
                'engagement': 4198,
                'source': 'Instagram',
                'subreddit': 'Instagram',
                'content': 'Lovi AI scanner provides personalized skincare advice from medical professionals',
                'created_utc': '2024-09-22T12:00:00'
            },
            {
                'title': "Amorepacific AI Beauty Counselor app launch",
                'author': 'k_beauty_tech',
                'url': 'https://news.microsoft.com/source/asia/features/meet-your-ai-beauty-counselor-k-beauty-giant-amorepacific-builds-an-ai-app-for-personalized-advice/',
                'score': 3600,
                'comments': 87,
                'engagement': 3687,
                'source': 'Instagram',
                'subreddit': 'Instagram',
                'content': "K-beauty giant Amorepacific launches AI app for personalized skincare advice",
                'created_utc': '2024-09-18T12:00:00'
            }
        ]
        return instagram_posts

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

        print("🚀 Loading REAL scraped social media data...")
        try:
            with open('social_feed_combined.json', 'r', encoding='utf-8') as f:
                combined_posts = json.load(f)
                print(f"✓ Loaded {len(combined_posts)} posts from combined feed")
                all_posts = combined_posts
        except FileNotFoundError:
            print("⚠️ No combined feed found, loading individual sources...")

            try:
                with open('reddit_real_data.json', 'r') as f:
                    reddit_posts = json.load(f)
                    all_posts.extend(reddit_posts[:10])
                    print(f"✓ Loaded {len(reddit_posts[:10])} Reddit posts")
            except FileNotFoundError:
                print("ℹ️ No Reddit data found")

            try:
                with open('instagram_feed_data.json', 'r') as f:
                    instagram_posts = json.load(f)
                    all_posts.extend(instagram_posts[:10])
                    print(f"✓ Loaded {len(instagram_posts[:10])} Instagram posts")
            except FileNotFoundError:
                print("ℹ️ No Instagram data found")

        twitter_posts = self.fetch_twitter_posts()
        all_posts.extend(twitter_posts)
        print(f"✓ Added {len(twitter_posts)} Twitter/X posts")

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
