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

def is_today_job(job_data):
    """Check if job was posted today"""
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
            
            return job_date == today
        except (ValueError, AttributeError):
            return False
    
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
            # Check if job matches keywords AND is from today
            text = f"{job['title']} {job['description']}".lower()
            if any(k in text for k in KEYWORDS) and is_today_job(job):
                results.append({
                    "title": job["title"],
                    "company": job["company_name"],
                    "url": job["url"],
                    "source": "Remotive",
                    "date": job.get("publication_date", "Unknown")
                })
        print(f"✅ Remotive: {len(results)} matching jobs from today")
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
                job_date = datetime.fromtimestamp(job_timestamp).date()
                is_today = job_date == date.today()
            else:
                is_today = False
            
            text = f"{job.get('position', '')} {job.get('description', '')}".lower()
            if any(k in text for k in KEYWORDS) and is_today:
                results.append({
                    "title": job.get("position"),
                    "company": job.get("company"),
                    "url": f"https://remoteok.io{job.get('url', '')}",
                    "source": "RemoteOK",
                    "date": job_date.strftime("%Y-%m-%d")
                })
        print(f"✅ RemoteOK: {len(results)} matching jobs from today")
        return results
    except Exception as e:
        print(f"❌ RemoteOK error: {e}")
        return []

# ----------- INDEED SCRAPER (Updated for current jobs) -----------
def fetch_indeed():
    print("🔍 Fetching from Indeed...")
    try:
        # Search for recent jobs (last 1 day)
        url = "https://ng.indeed.com/jobs?q=python+backend+fastapi&l=&fromage=1"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        html = response.text

        # Improved pattern to catch date information
        pattern = r'jobTitle">(.*?)</h2.*?companyName">(.*?)</span.*?date.*?">(.*?)</span.*?href="(\/rc.*?)"'
        matches = re.findall(pattern, html, re.S)
        print(f"📊 Indeed: Found {len(matches)} total jobs")

        results = []
        for title, company, date_str, link in matches:
            # Indeed often shows "Just posted" or "Today" for recent jobs
            if 'today' in date_str.lower() or 'just' in date_str.lower() or '1 day' in date_str.lower():
                full_url = "https://ng.indeed.com" + link
                results.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "url": full_url,
                    "source": "Indeed",
                    "date": "Today"
                })
        print(f"✅ Indeed: {len(results)} matching jobs from today")
        return results
    except Exception as e:
        print(f"❌ Indeed error: {e}")
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
        all_jobs.extend(fetch_indeed())
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