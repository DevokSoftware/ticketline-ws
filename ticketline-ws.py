from playwright.sync_api import sync_playwright, TimeoutError
from dataclasses import dataclass
import time
import random
import psycopg2
from psycopg2.extras import RealDictCursor
import re
from datetime import datetime, timezone

BASE_URL = "https://ticketline.sapo.pt"

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'giggz',
    'user': 'admin',
    'password': 'admin'
}

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

def parse_date_to_offset_datetime(date_str):
    """
    Parse the date string from the website and convert it to OffsetDateTime format.
    The date format from the website appears to be in ISO format or similar.
    """
    try:
        # Try to parse as ISO format first
        if 'T' in date_str:
            # ISO format with time
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            # Date only format, assume midnight UTC
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            dt = dt.replace(tzinfo=timezone.utc)
        
        return dt
    except ValueError as e:
        print(f"⚠️ Could not parse date '{date_str}': {e}")
        # Return current time as fallback
        return datetime.now(timezone.utc)

def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except psycopg2.Error as e:
        print(f"❌ Database connection failed: {e}")
        return None

def get_standups_from_db():
    """Fetch all standups from the database."""
    conn = get_db_connection()
    if not conn:
        print("❌ Cannot fetch standups - no database connection")
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM standup")
        standups = cursor.fetchall()
        print(f"📋 Found {len(standups)} standups in database")
        return standups
    except psycopg2.Error as e:
        print(f"❌ Error fetching standups: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def find_matching_standup(event_title, standups):
    """
    Find a standup whose name is contained in the event title (case-insensitive).
    Returns (standup_id, standup_name) if found, None otherwise.
    """
    event_title_lower = event_title.lower()
    
    for standup_id, standup_name in standups:
        if standup_name.lower() in event_title_lower:
            print(f"🎯 Event '{event_title}' matches standup '{standup_name}' (ID: {standup_id})")
            return standup_id, standup_name
    
    return None

def get_locations_from_db():
    """Fetch all locations from the database."""
    conn = get_db_connection()
    if not conn:
        print("❌ Cannot fetch locations - no database connection")
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM location")
        locations = cursor.fetchall()
        print(f"📍 Found {len(locations)} locations in database")
        return locations
    except psycopg2.Error as e:
        print(f"❌ Error fetching locations: {e}")
        return []
    finally:
        cursor.close()
        conn.close()
        print("\n")

def find_matching_location(event_location, locations):
    """
    Find a location whose name is contained in the event location (case-insensitive).
    Returns (location_id, location_name) if found, None otherwise.
    """
    event_location_lower = event_location.lower()
    
    for location_id, location_name in locations:
        if location_name.lower() in event_location_lower:
            print(f"📍 Event location '{event_location}' matches location '{location_name}' (ID: {location_id})")
            return location_id, location_name
    
    return None

def save_events_to_db(events):
    """Save events to the database."""
    # First, fetch all standups and locations from the database
    standups = get_standups_from_db()
    if not standups:
        print("❌ No standups found in database. Cannot save events.")
        return
    
    locations = get_locations_from_db()
    if not locations:
        print("❌ No locations found in database. Cannot save events.")
        return
    
    conn = get_db_connection()
    if not conn:
        print("❌ Cannot save events - no database connection")
        return
    
    try:
        cursor = conn.cursor()
        
        # Create table if it doesn't exist (matching your JPA entity)
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS event_script (
            id SERIAL PRIMARY KEY,
            name VARCHAR(500) NOT NULL,
            date TIMESTAMP WITH TIME ZONE NOT NULL,
            url VARCHAR(1000) NOT NULL,
            location INT NULL,
            standup_id INT NOT NULL,
            UNIQUE(name, date)
        );
        """
        cursor.execute(create_table_sql)
        
        # Insert events
        insert_sql = """
        INSERT INTO event_script (name, date, url, location, standup_id) 
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (name, date) DO NOTHING
        """
        
        saved_count = 0
        skipped_standup_count = 0
        skipped_location_count = 0
        unmatched_locations = set()
        
        for event in events:
            # Check if event matches any standup
            matching_standup = find_matching_standup(event.title, standups)
            
            if matching_standup:
                standup_id, standup_name = matching_standup
                
                # Check if event location matches any location
                matching_location = find_matching_location(event.location, locations)
                
                if matching_location:
                    location_id, location_name = matching_location
                    
                    try:
                        # Parse the date string to OffsetDateTime
                        parsed_date = parse_date_to_offset_datetime(event.date)
                        
                        # Map fields: title -> name, detailsPageUrl -> url
                        cursor.execute(insert_sql, (
                            event.title,
                            parsed_date,
                            event.detailsPageUrl,
                            location_id,
                            standup_id
                        ))
                        
                        if cursor.rowcount > 0:
                            saved_count += 1
                            print(f"💾 Saved: {event.title} (Standup: {standup_name}, Location: {location_name})")
                        else:
                            print(f"⏭️ Skipped (duplicate): {event.title}")
                            
                    except psycopg2.Error as e:
                        print(f"❌ Error saving event '{event.title}': {e}")
                        continue
                else:
                    skipped_location_count += 1
                    unmatched_locations.add(event.location)
                    print(f"🚫 Skipped (no matching location): {event.title} - Location: {event.location}")
            else:
                skipped_standup_count += 1
                print(f"🚫 Skipped (no matching standup): {event.title}")
        
        conn.commit()
        print(f"\n✅ Successfully saved {saved_count} new events to database")
        print(f"🚫 Skipped {skipped_standup_count} events (no matching standup)")
        print(f"🚫 Skipped {skipped_location_count} events (no matching location)")
        
        # Print unmatched locations for manual addition
        if unmatched_locations:
            print(f"\n📋 Unmatched locations that need to be added to the database:")
            for location in sorted(unmatched_locations):
                print(f"   - {location}")
        else:
            print(f"\n✅ All event locations matched existing locations in database")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def scrape_events_for_month(page, month, year):
    events = []
    page_number = 1

    while True:
        url = f"{BASE_URL}/pesquisa/?category=253&month={month}&year={year}&page={page_number}" #253 is the stand up comedy's category
        time.sleep(random.uniform(4.5, 7.5)) #added a sleeper to avoid rate-limits or bans  
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
        if session.locator('.date').count() == 0:
            print("⚠️ Session is no longer available.")
            continue
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

    today = datetime.today().date()
    main_events = []
    all_events = []
    
    for i in range(1):
    # for i in range(3):  # current month + next 2
        month = (today.month + i - 1) % 12 + 1
        year = today.year + ((today.month + i - 1) // 12)
        main_events = scrape_events_for_month(page, month, year)
        
    # It checks multi-sessions events
    for event in main_events[:]:  # iterate over a copy so we can extend the list
        if event.has_multi_sessions:
            extra = scrape_additional_sessions(page, event)
            all_events.extend(extra)
        else:
            all_events.append(event)

    browser.close()

    print("\n--- ✅ All Events Found ---")
    for event in all_events:
        print(event)

    # Save events to database
    print(f"\n💾 Saving {len(all_events)} events to database...")
    save_events_to_db(all_events)
