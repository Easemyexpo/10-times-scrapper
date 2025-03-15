from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import datetime

# Config
url = "https://10times.com/bengaluru-in"

# Set up Chrome options
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

def scrape_events(limit=4):
    try:
        # Initialize WebDriver
        driver = webdriver.Chrome(options=options)
        driver.get(url)

        # Wait for event elements to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tr[class*='deep-shadow']"))
        )

        # Parse page source
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()
        events = []

        # Select all event rows
        event_blocks = soup.select("tr[class*='deep-shadow']")
        if not event_blocks:
            print("No event rows found. Site structure may have changed.")
            print(soup.prettify()[:500])  # Debug HTML
            return events

        print(f"Found {len(event_blocks)} event rows. Extracting details...")

        for index, event in enumerate(event_blocks[:limit]):
            # Title extraction
            title_tag = event.select_one(".fw-bold a, h2, .d-block.fw-bold span")
            title = title_tag.text.strip() if title_tag else "N/A"

            # Extract event image
            img_tag = event.find("img", class_="rounded-3")
            image_url = img_tag.get("src", "N/A") if img_tag else "N/A"

            # Extract Start & End Date with better targeting
            date_div = event.find("div", class_="eventTime")
            if date_div:
                start_date = date_div.get("data-start-date", "N/A")
                end_date = date_div.get("data-end-date", "N/A")
                date_text = date_div.text.strip()
            else:
                start_date = end_date = date_text = "N/A"

            # Extract Venue
            venue_tag = event.find("span", class_="fw-600") or event.find("td", class_="text-muted-new")
            venue = venue_tag.text.strip() if venue_tag else "N/A"

            # Skip completely empty events
            if title == "N/A" and date_text == "N/A" and venue == "N/A":
                print(f"Skipping empty event at index {index}:")
                print(event.prettify())  # Debug individual event
                continue

            # Unique event ID
            event_id = f"{title}_{start_date}"
            events.append((event_id, title, image_url, start_date, end_date, date_text, venue))

        if not events:
            print("No valid events extracted.")
        return events

    except Exception as e:
        print(f"Error fetching page: {e}")
        return []

def job():
    events = scrape_events(limit=4)
    if events:
        print(f"Scraped {len(events)} events:")
        for event in events:
            print(event)
    else:
        print("No events scraped.")
    print("Data fetched at", datetime.datetime.now())

# Run the job
job()