from playwright.sync_api import sync_playwright, TimeoutError
from dataclasses import dataclass
import time
import random
import psycopg2
from psycopg2.extras import RealDictCursor
import re
from datetime import datetime, timezone
import os
from scraping_config import *

BASE_URL = "https://ticketline.sapo.pt"

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'giggz',
    'user': 'admin',
    'password': 'admin'
}

# Anti-detection configuration
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
]

# Viewport sizes to rotate
VIEWPORTS = [
    {'width': 1920, 'height': 1080},
    {'width': 1366, 'height': 768},
    {'width': 1440, 'height': 900},
    {'width': 1536, 'height': 864},
    {'width': 1280, 'height': 720}
]

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

def setup_anti_detection(page):
    """Setup anti-detection measures for the browser page."""
    # Set random user agent
    user_agent = random.choice(USER_AGENTS)
    page.set_extra_http_headers({'User-Agent': user_agent})
    
    # Set random viewport
    viewport = random.choice(VIEWPORTS)
    page.set_viewport_size(viewport)
    
    # Set language and timezone
    page.set_extra_http_headers({
        'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    # Add some randomness to make behavior more human-like
    page.add_init_script("""
        // Override webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Add some random mouse movements
        const originalMouseEvent = window.MouseEvent;
        window.MouseEvent = function(type, init) {
            if (init) {
                init.clientX += Math.random() * 2 - 1;
                init.clientY += Math.random() * 2 - 1;
            }
            return new originalMouseEvent(type, init);
        };
    """)
    
    print(f"🕵️ Anti-detection setup: User-Agent: {user_agent[:50]}..., Viewport: {viewport['width']}x{viewport['height']}")

def human_like_delay():
    """Add human-like delays with randomness."""
    # Base delay with some randomness
    base_delay = random.uniform(MIN_DELAY, MAX_DELAY)
    
    # Add occasional longer delays (like a human taking a break)
    if random.random() < LONG_BREAK_CHANCE:
        base_delay += random.uniform(LONG_BREAK_MIN, LONG_BREAK_MAX)
        print(f"⏸️ Taking a longer break: {base_delay:.1f}s")
    
    time.sleep(base_delay)

def check_for_rate_limiting(page):
    """Check if we're being rate limited and handle accordingly."""
    try:
        # Check for common rate limiting indicators
        rate_limit_indicators = [
            "rate limit",
            "too many requests",
            "please wait",
            "temporarily blocked",
            "access denied",
            "captcha"
        ]
        
        page_content = page.content().lower()
        for indicator in rate_limit_indicators:
            if indicator in page_content:
                print(f"🚨 Rate limiting detected: {indicator}")
                return True
        
        # Check HTTP status
        response = page.response_for_request(page.request)
        if response and response.status in [429, 403, 503]:
            print(f"🚨 HTTP {response.status} - Rate limiting detected")
            return True
            
        return False
        
    except Exception as e:
        # If we can't check, assume we're not rate limited
        return False

def handle_rate_limiting():
    """Handle rate limiting by waiting and potentially changing strategy."""
    wait_time = random.uniform(RATE_LIMIT_WAIT_MIN, RATE_LIMIT_WAIT_MAX)
    print(f"⏳ Rate limited. Waiting {wait_time:.0f} seconds...")
    time.sleep(wait_time)

def simulate_human_behavior(page):
    """Simulate human-like behavior on the page."""
    try:
        # Random scroll
        if random.random() < SCROLL_CHANCE:
            scroll_amount = random.randint(SCROLL_MIN, SCROLL_MAX)
            page.mouse.wheel(0, scroll_amount)
            time.sleep(random.uniform(0.5, 1.5))
        
        # Random mouse movement
        if random.random() < MOUSE_MOVE_CHANCE:
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.2, 0.8))
            
    except Exception as e:
        # Ignore errors in human simulation
        pass

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
        human_like_delay()  # Use human-like delays instead of fixed delays
        print(f"\n🔍 Checking: {url}")

        try:
            page.goto(url, wait_until=WAIT_UNTIL, timeout=TIMEOUT)
            simulate_human_behavior(page)  # Add human-like behavior
            
            # Check for rate limiting
            if check_for_rate_limiting(page):
                handle_rate_limiting()
                continue
                
        except Exception as e:
            print(f"⚠️ Error loading page: {e}")
            time.sleep(random.uniform(ERROR_WAIT_MIN, ERROR_WAIT_MAX))
            continue

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
    human_like_delay()  # Use human-like delays
    print(f"🔍 Opening details page for: {event.title}")
    
    try:
        page.goto(event.detailsPageUrl, wait_until=WAIT_UNTIL, timeout=60000)
        simulate_human_behavior(page)  # Add human-like behavior
        
        # Check for rate limiting
        if check_for_rate_limiting(page):
            handle_rate_limiting()
            return []
            
    except Exception as e:
        print(f"⚠️ Error loading details page: {e}")
        return []

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
    # Launch browser with anti-detection settings
    browser_args = [
        '--no-sandbox',
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--disable-extensions',
        '--disable-plugins',
        '--disable-gpu',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-features=TranslateUI',
        '--disable-ipc-flooding-protection'
    ]
    
    if DISABLE_IMAGES:
        browser_args.append('--disable-images')
    
    if DISABLE_JAVASCRIPT:
        browser_args.append('--disable-javascript')
    
    browser = p.chromium.launch(
        headless=HEADLESS,
        args=browser_args
    )
    
    # Create context with additional settings
    context = browser.new_context(
        viewport=None,  # Will be set by setup_anti_detection
        user_agent=None,  # Will be set by setup_anti_detection
        locale='pt-PT',
        timezone_id='Europe/Lisbon',
        permissions=['geolocation'],
        extra_http_headers={
            'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    )
    
    page = context.new_page()
    setup_anti_detection(page)  # Apply anti-detection measures

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
