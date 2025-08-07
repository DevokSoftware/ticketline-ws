from playwright.sync_api import sync_playwright, TimeoutError

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, slow_mo=200)
    page = browser.new_page()
    page.goto("https://ticketline.sapo.pt/pesquisa?category=253")


    try:
        page.wait_for_selector("#eventos", timeout=10000)
        print("✅ '#eventos' container found.")

        # Get all event elements
        event_elements =  page.locator('#eventos ul.events_list li').all()
        print(f"Found {len(event_elements)} total events")

        for i, event in enumerate(event_elements, start=1):
            classes =  event.get_attribute('class') or ''
            has_multi = 'has_multiple_sessions' in classes
            title =  event.locator('.title').text_content()
            date =  event.locator('.date').get_attribute('data-date')
            location =  event.locator('.venues').text_content()
            print(f"Event {i}: {title} on {date} at {location} - Multiple Sessions: {has_multi}")

    except TimeoutError:
        print("❌ Timeout: '#eventos' container not found.")

    browser.close()


