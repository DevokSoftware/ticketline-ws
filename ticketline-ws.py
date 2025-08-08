from playwright.sync_api import sync_playwright, TimeoutError
from dataclasses import dataclass
import datetime
import time
import random

BASE_URL = "https://ticketline.sapo.pt"

@dataclass
class Event:
    title: str
    date: str
    location: str
    has_multi_sessions: bool
    detailsPageUrl: str

    def __repr__(self):
        return (
            f"Title: {self.title}\n"
            f"Date: {self.date}\n"
            f"Location: {self.location}\n"
            f"Has Multiple Sessions: {self.has_multi_sessions}\n"
            f"Details Page URL: {self.detailsPageUrl}\n---"
        )

def scrape_events_for_month(page, month, year):
    events = []
    page_number = 1

    while True:
        url = f"{BASE_URL}/pesquisa/?category=253&month={month}&year={year}&page={page_number}" #253 is the stand up comedy's category
        time.sleep(random.uniform(2.5, 3.5)) #added a sleeper to avoid rate-limits or bans  
        print(f"\n🔍 Checking: {url}")

        page.goto(url)

        try:
            page.wait_for_selector("#eventos", timeout=10000)
            print("✅ '#eventos' container found.")
        except TimeoutError:
            print("⛔ Timeout: '#eventos' not found. Skipping.")
            break

        event_elements = page.locator('#eventos ul.events_list li')
        # If only one <li> and it has class "empty" → no events
        if event_elements.count() == 1 and event_elements.first.get_attribute("class") == "empty":
            print("⚠️ No events found (empty class detected). Moving to next month.")
            break

        print(f"📦 Found {event_elements.count()} events.")

        for i, event in enumerate(event_elements.all(), start=1):
            classes = event.get_attribute('class') or ''
            has_multi = 'has_multiple_sessions' in classes
            title = event.locator('.title').text_content() or 'N/A'
            date = event.locator('.date').get_attribute('data-date') or 'N/A'
            location = event.locator('.venues').text_content() or 'N/A'
            href = event.locator('a').get_attribute('href') or ''
            full_url = BASE_URL + href if href.startswith('/') else href

            event_obj = Event(
                title.strip(),
                date.strip(),
                location.strip(),
                has_multi,
                full_url
            )
            events.append(event_obj)
            print(f"✅ Event {i}: {title.strip()} on {date.strip()} at {location.strip()} | Multiple Sessions: {has_multi}")

        page_number += 1

    return events

def scrape_additional_sessions(page, event: Event):
    time.sleep(random.uniform(2.5, 3.5)) #added a sleeper to avoid rate-limits or bans  
    print(f"🔍 Opening details page for: {event.title}")
    page.goto(event.detailsPageUrl, timeout=60000)

    session_elements = page.locator('#sessoes ul.sessions_list li')
    if session_elements.count() == 0:
        print(f"⚠️ No sessions found for {event.title}")
        return []

    extra_events = []
    for session in session_elements.all():
        date_attr = session.locator('.date').get_attribute('content') or ''
        title_text = session.locator('.details').get_attribute('content') or event.title
        venue_text = session.locator('.venue').text_content() or ''
        district_text = session.locator('.district').text_content() or ''

        # Build the location string same as in main scrape
        location_str = f"{venue_text.strip()} - {district_text.strip()}".strip(" -")

        href = session.locator('a').get_attribute('href') or ''
        full_url = BASE_URL + href if href.startswith('/') else href

        extra_events.append(Event(
            title=title_text.strip(),
            date=date_attr.strip(),
            location=location_str,
            has_multi_sessions=False,  # detail page sessions don't need further expansion
            detailsPageUrl=full_url
        ))

    print(f"➕ Found {len(extra_events)} extra sessions for {event.title}")
    return extra_events


# Main execution
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    today = datetime.date.today()
    all_events = []
    
    for i in range(1):
        print(f"Index:  {i}")
    # for i in range(3):  # current month + next 2
        month = (today.month + i - 1) % 12 + 1
        year = today.year + ((today.month + i - 1) // 12)
        events = scrape_events_for_month(page, month, year)
        all_events.extend(events)

    # It checks multi-sessions events
    for event in all_events[:]:  # iterate over a copy so we can extend the list
        if event.has_multi_sessions:
            extra = scrape_additional_sessions(page, event)
            all_events.extend(extra)

    browser.close()

    print("\n--- ✅ All Events Found ---")
    for event in all_events:
        print(event)
