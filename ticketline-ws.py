from playwright.sync_api import sync_playwright, TimeoutError
from dataclasses import dataclass
import datetime

@dataclass
class Event:
    title: str
    date: str
    location: str
    has_multi_sessions: bool

    def __repr__(self):
        return (
            f"Title: {self.title}\n"
            f"Date: {self.date}\n"
            f"Location: {self.location}\n"
            f"Has Multiple Sessions: {self.has_multi_sessions}\n---"
        )

def scrape_events_for_month(page, month, year):
    events = []
    page_number = 1

    while True:
        url = f"https://ticketline.sapo.pt/pesquisa/?category=253&month={month}&year={year}&page={page_number}"
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

            event_obj = Event(
                title.strip(),
                date.strip(),
                location.strip(),
                has_multi
            )
            events.append(event_obj)
            print(f"✅ Event {i}: {title.strip()} on {date.strip()} at {location.strip()} | Multiple Sessions: {has_multi}")

        page_number += 1

    return events

# Main execution
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    today = datetime.date.today()
    all_events = []

    for i in range(3):  # current month + next 2
        month = (today.month + i - 1) % 12 + 1
        year = today.year + ((today.month + i - 1) // 12)
        events = scrape_events_for_month(page, month, year)
        all_events.extend(events)

    browser.close()

    print("\n--- ✅ All Events Found ---")
    for event in all_events:
        print(event)
