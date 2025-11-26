import requests
import re
import time
from datetime import datetime

TELEGRAM_TOKEN = "<TELEGRAM_BOT_TOKEN>"
CHAT_ID = "<YOUR_TELEGRAM_CHAT_ID>"

KEYWORDS = ["python", "fastapi", "backend", "software engineer", "backend engineer"]

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=payload)


# ----------- REMOTIVE JOBS API -----------
def fetch_remotive():
    url = "https://remotive.com/api/remote-jobs"
    data = requests.get(url).json()
    jobs = data["jobs"]

    results = []
    for job in jobs:
        text = f"{job['title']} {job['description']}".lower()
        if any(k in text for k in KEYWORDS):
            results.append({
                "title": job["title"],
                "company": job["company_name"],
                "url": job["url"],
                "source": "Remotive"
            })
    return results


# ----------- REMOTEOK API -----------
def fetch_remoteok():
    url = "https://remoteok.com/api"
    data = requests.get(url).json()

    results = []
    for job in data[1:]:
        text = f"{job.get('position', '')} {job.get('description', '')}".lower()
        if any(k in text for k in KEYWORDS):
            results.append({
                "title": job.get("position"),
                "company": job.get("company"),
                "url": job.get("url"),
                "source": "RemoteOK"
            })
    return results


# ----------- INDEED SCRAPER (simple) -----------
def fetch_indeed():
    url = "https://ng.indeed.com/jobs?q=python+backend+fastapi&l="
    html = requests.get(url).text

    pattern = r'jobTitle">(.*?)</h2.*?companyName">(.*?)</span.*?href="(\/rc.*?)"'
    matches = re.findall(pattern, html, re.S)

    results = []
    for title, company, link in matches:
        full_url = "https://ng.indeed.com" + link
        results.append({
            "title": title,
            "company": company,
            "url": full_url,
            "source": "Indeed"
        })
    return results


# ----------- MAIN PIPELINE -----------
def run():
    print(f"Started job check at {datetime.now()}")

    all_jobs = []

    try:
        all_jobs.extend(fetch_remotive())
        all_jobs.extend(fetch_remoteok())
        all_jobs.extend(fetch_indeed())
    except Exception as e:
        send_telegram(f"⚠️ Job bot error: {str(e)}")
        return

    if not all_jobs:
        send_telegram("No new Python/FastAPI jobs found.")
        return

    # Send results
    for job in all_jobs[:10]:
        msg = (
            f"💼 <b>{job['title']}</b>\n"
            f"🏢 {job['company']}\n"
            f"🔗 {job['url']}\n"
            f"🌍 Source: {job['source']}"
        )
        send_telegram(msg)
        time.sleep(1)


if __name__ == "__main__":
    run()
