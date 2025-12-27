import os
import requests
import re
import time
from datetime import datetime, date
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

# Get from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

print(f"🚀 Bot started at {datetime.now()}")
print(f"📝 TELEGRAM_TOKEN exists: {bool(TELEGRAM_TOKEN)}")
print(f"📝 CHAT_ID exists: {bool(CHAT_ID)}")

KEYWORDS = ["python", "fastapi", "backend", "software engineer", "backend engineer"]

def send_telegram(message: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Missing Telegram credentials")
        return False
        
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print(f"✅ Telegram message sent: {message[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        return False

def is_recent_job(job_data, days_limit=3):
    """Check if job was posted within the last N days"""
    today = date.today()
    
    # Handle different date formats from different APIs
    publication_date = job_data.get('publication_date', '') or job_data.get('date', '')
    
    if not publication_date:
        return False
    
    # Convert to date object if it's a string
    if isinstance(publication_date, str):
        try:
            # Handle various date formats
            if 'T' in publication_date:
                # ISO format: "2023-11-26T10:30:00"
                job_date = datetime.fromisoformat(publication_date.replace('Z', '+00:00')).date()
            else:
                # Simple date format: "2023-11-26"
                job_date = datetime.strptime(publication_date, "%Y-%m-%d").date()
            
            delta = (today - job_date).days
            return 0 <= delta <= days_limit
        except (ValueError, AttributeError) as e:
            # print(f"Date parse error: {e} for {publication_date}")
            return False
            
    # If it's already a date/datetime object
    if isinstance(publication_date, (date, datetime)):
        if isinstance(publication_date, datetime):
            publication_date = publication_date.date()
        delta = (today - publication_date).days
        return 0 <= delta <= days_limit
    
    return False

# ----------- REMOTIVE JOBS API -----------
def fetch_remotive():
    print("🔍 Fetching from Remotive...")
    try:
        url = "https://remotive.com/api/remote-jobs"
        data = requests.get(url).json()
        jobs = data["jobs"]
        print(f"📊 Remotive: Found {len(jobs)} total jobs")

        results = []
        for job in jobs:
            # Check if job matches keywords AND is recent
            text = f"{job['title']} {job['description']}".lower()
            if any(k in text for k in KEYWORDS) and is_recent_job(job):
                results.append({
                    "title": job["title"],
                    "company": job["company_name"],
                    "url": job["url"],
                    "source": "Remotive",
                    "date": job.get("publication_date", "Unknown")
                })
        print(f"✅ Remotive: {len(results)} matching recent jobs")
        return results
    except Exception as e:
        print(f"❌ Remotive error: {e}")
        return []

# ----------- REMOTEOK API -----------
def fetch_remoteok():
    print("🔍 Fetching from RemoteOK...")
    try:
        url = "https://remoteok.io/api"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers)
        data = response.json()
        print(f"📊 RemoteOK: Found {len(data)-1} total jobs")

        results = []
        for job in data[1:]:  # Skip first element (metadata)
            # RemoteOK uses timestamp in seconds
            job_timestamp = job.get('epoch', job.get('date'))
            if job_timestamp:
                try:
                    job_date = datetime.fromtimestamp(int(job_timestamp)).date()
                    # Check if recent
                    delta = (date.today() - job_date).days
                    is_recent = 0 <= delta <= 3
                except:
                    is_recent = False
            else:
                is_recent = False
            
            text = f"{job.get('position', '')} {job.get('description', '')}".lower()
            if any(k in text for k in KEYWORDS) and is_recent:
                results.append({
                    "title": job.get("position"),
                    "company": job.get("company"),
                    "url": f"https://remoteok.io{job.get('url', '')}",
                    "source": "RemoteOK",
                    "date": job_date.strftime("%Y-%m-%d")
                })
        print(f"✅ RemoteOK: {len(results)} matching recent jobs")
        return results
    except Exception as e:
        print(f"❌ RemoteOK error: {e}")
        return []

# ----------- WE WORK REMOTELY (RSS) -----------
def fetch_wwr():
    print("🔍 Fetching from WeWorkRemotely...")
    try:
        # We Work Remotely has an RSS feed which is easier to parse than scraping HTML
        url = "https://weworkremotely.com/remote-jobs.rss"
        response = requests.get(url) 
        # Simple XML parsing using string manipulation to avoid complex dependencies
        # In a production app, use 'feedparser' or 'xml.etree.ElementTree'
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            print(f"📊 WWR: Found {len(items)} total jobs in feed")
            
            results = []
            for item in items:
                title = item.find('title').text if item.find('title') is not None else ""
                description = item.find('description').text if item.find('description') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                # WWR format: "Mon, 27 Dec 2025 10:00:00 +0000"
                try:
                    # Parse simplified date
                    job_dt = datetime.strptime(pubDate.split('+')[0].strip(), "%a, %d %b %Y %H:%M:%S")
                    job_data = {'date': job_dt.date()}
                    is_recent = is_recent_job(job_data)
                    date_str = job_dt.strftime("%Y-%m-%d")
                except:
                    is_recent = True # Only most recent 50 are in RSS usually, so assume recent
                    date_str = "Recent"

                text = f"{title} {description}".lower()
                if any(k in text for k in KEYWORDS) and is_recent:
                    results.append({
                        "title": title,
                        "company": "WeWorkRemotely Job", # WWR RSS often puts company in title "Company: Role"
                        "url": link,
                        "source": "WeWorkRemotely",
                        "date": date_str
                    })
            
            print(f"✅ WWR: {len(results)} matching recent jobs")
            return results
            
        except ET.ParseError:
            print("❌ WWR XML Parse Error")
            return []
            
    except Exception as e:
        print(f"❌ WWR error: {e}")
        return []

# ----------- HACKER NEWS (WHO IS HIRING) -----------
def fetch_hackernews():
    print("🔍 Fetching from Hacker News...")
    try:
        # Fetch top job stories
        url = "https://hacker-news.firebaseio.com/v0/jobstories.json"
        job_ids = requests.get(url).json()[:50] # Check top 50
        print(f"📊 Hacker News: Checking top {len(job_ids)} job posts")
        
        results = []
        for jid in job_ids:
            item_url = f"https://hacker-news.firebaseio.com/v0/item/{jid}.json"
            job = requests.get(item_url).json()
            
            if not job or 'title' not in job:
                continue
                
            # HN jobs are usually just a title/text, sometimes url
            title = job.get('title', 'Unknown')
            text = job.get('text', '') or title
            
            # Check date
            job_time = job.get('time')
            if job_time:
                job_date = datetime.fromtimestamp(job_time).date()
                if not is_recent_job({'date': job_date}):
                    continue
                date_str = job_date.strftime("%Y-%m-%d")
            else:
                date_str = "Recent"
            
            content_to_check = f"{title} {text}".lower()
            
            if any(k in content_to_check for k in KEYWORDS):
                results.append({
                    "title": title,
                    "company": "Hacker News",
                    "url": job.get('url', f"https://news.ycombinator.com/item?id={jid}"),
                    "source": "Hacker News",
                    "date": date_str
                })
                
        print(f"✅ Hacker News: {len(results)} matching recent jobs")
        return results
    except Exception as e:
        print(f"❌ Hacker News error: {e}")
        return []

# ----------- MAIN PIPELINE -----------
def run():
    start_time = datetime.now()
    today = date.today().strftime("%Y-%m-%d")
    print(f"⏰ Started job check at {start_time}")
    print(f"📅 Looking for jobs from: {today}")

    # Send start notification
    start_msg = f"🤖 Job Bot Started\n📅 Date: {today}\n⏰ Time: {start_time.strftime('%H:%M:%S')}"
    send_telegram(start_msg)

    all_jobs = []

    try:
        all_jobs.extend(fetch_remotive())
        all_jobs.extend(fetch_remoteok())
        all_jobs.extend(fetch_wwr())
        all_jobs.extend(fetch_hackernews())
        # Indeed is disabled due to high failure rate
        # all_jobs.extend(fetch_indeed())
    except Exception as e:
        error_msg = f"⚠️ Job bot error: {str(e)}"
        print(error_msg)
        send_telegram(error_msg)
        return

    print(f"📈 Total today's jobs found: {len(all_jobs)}")

    if not all_jobs:
        message = f"📭 No new Python/FastAPI jobs found for {today}."
        print(message)
        send_telegram(message)
        return

    # Send results (limit to avoid spam)
    success_count = 0
    jobs_to_send = all_jobs[:15]  # Increased limit since we're filtering by date
    
    for job in jobs_to_send:
        msg = (
            f"💼 <b>{job['title']}</b>\n"
            f"🏢 {job['company']}\n"
            f"📅 {job.get('date', 'Today')}\n"
            f"🔗 {job['url']}\n"
            f"🌍 Source: {job['source']}"
        )
        if send_telegram(msg):
            success_count += 1
        time.sleep(1)  # Avoid rate limiting

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    summary = f"✅ Bot completed in {duration:.1f}s\n📅 Date: {today}\n📊 Found: {len(all_jobs)} jobs\n📤 Sent: {success_count} notifications"
    print(summary)
    send_telegram(summary)


if __name__ == "__main__":
    run()