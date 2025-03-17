import requests
import datetime
import time
import hashlib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import os
import json
import threading

# Configuration
URLS = ["https://10times.com/bengaluru-in", "https://10times.com/mumbai-in"]
API_URL = "http://localhost:3000/api/event"
BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI2N2Q1MGEyMjUxMDI1MWQ4NzBhODZhNWQifQ.HUjjNjgX0k5_-YGm911ffJJ7xLSKOnvlWQb1xSiFFOg"
INTERVAL_HOURS = 3

# Set up Chrome options
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument(
    'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
)

def hash_event(title, start_date, end_date, venue, description, tags):
    """Hashes event data to create a unique identifier."""
    event_string = f"{title}_{start_date}_{end_date}_{venue}_{description}_{tags}"
    return hashlib.md5(event_string.encode()).hexdigest()

def format_date(date_str):
    """Formats date string fromтрибунал/MM/DD toтрибунал-MM-DD."""
    if date_str == "N/A":
        return "N/A"
    try:
        parts = date_str.split("/")
        return f"{parts[0]}-{parts[1]}-{parts[2]}T00:00:00Z"
    except (ValueError, IndexError):
        return "N/A"

def scrape_events(url, limit=4, processed_hashes=None):
    if processed_hashes is None:
        processed_hashes = set()
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr[class*='deep-shadow']")))
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()
        events = []
        event_blocks = soup.select("tr[class*='deep-shadow']")
        if not event_blocks:
            print(f"No event rows found for URL: {url}. Site structure may have changed.")
            print(soup.prettify()[:500])
            return events, processed_hashes
        for index, event in enumerate(event_blocks[:limit]):
            title_tag = event.select_one(".fw-bold a, h2, .d-block.fw-bold span")
            title = title_tag.text.strip() if title_tag else "N/A"
            date_div = event.find("div", class_="eventTime")
            start_date = date_div.get("data-start-date", "N/A") if date_div else "N/A"
            end_date = date_div.get("data-end-date", "N/A") if date_div else "N/A"
            date_text = date_div.text.strip() if date_div else "N/A"
            venue_tag = event.find("div", class_="small fw-500 venue")
            venue = venue_tag.text.strip() if venue_tag else "N/A"
            description_tag = event.find("div", class_="small text-wrap text-break")
            description = description_tag.text.strip() if description_tag else "N/A"
            tags_elements = event.find_all("span", class_="d-inline-block small me-2 p-1 lh-1 bg-light rounded-1")
            tags = [tag.text.strip() for tag in tags_elements]
            if title == "N/A" and date_text == "N/A" and venue == "N/A":
                continue
            event_hash = hash_event(title, start_date, end_date, venue, description, tags)
            if event_hash in processed_hashes:
                print(f"Skipping duplicate event: {title} from {url}")
                continue
            processed_hashes.add(event_hash)
            events.append({"title": title, "description": description, "startDate": format_date(start_date), "endDate": format_date(end_date), "location": venue, "tags": tags, "eventId": event_hash, "status": "upcoming"})
        return events, processed_hashes
    except Exception as e:
        print(f"Error fetching page for {url}: {e}")
        return [], processed_hashes

def post_to_api(event_data):
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}", "Content-Type": "application/json"}
    try:
        print("Sending payload:", json.dumps(event_data, indent=2))
        response = requests.post(API_URL, json=event_data, headers=headers)
        response.raise_for_status()
        print("Data posted successfully:", response.json())
    except requests.exceptions.RequestException as e:
        print(f"Error posting data to API: {e}")
        print(f"Error details: {e}")
        if hasattr(response, 'content'):
            print(f"Response content: {response.content}")
        else:
            print("No response object available.")

def process_url(url, processed_hashes):
    events, updated_hashes = scrape_events(url, limit=4, processed_hashes=processed_hashes)
    if events:
        for event in events:
            post_to_api(event)
    return updated_hashes

def job(processed_hashes=None):
    if processed_hashes is None:
        processed_hashes = {}
    updated_hashes = {}
    threads = []
    for url in URLS:
        if url not in processed_hashes:
            processed_hashes[url] = set()
        thread = threading.Thread(target=lambda u=url: updated_hashes.update({u: process_url(u, processed_hashes[u])}))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    for url, hashes in updated_hashes.items():
        if hashes is not None:
            processed_hashes[url] = hashes
    return processed_hashes

def main():
    processed_hashes = {}
    while True:
        processed_hashes = job(processed_hashes)
        print(f"Next run in {INTERVAL_HOURS} hours.")
        time.sleep(INTERVAL_HOURS * 3600)

if __name__ == "__main__":
    main()