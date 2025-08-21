# Scraping Configuration
# Modify these settings to adjust scraping behavior

# Timing settings
MIN_DELAY = 3.0  # Minimum delay between requests (seconds)
MAX_DELAY = 6.0  # Maximum delay between requests (seconds)
LONG_BREAK_CHANCE = 0.1  # 10% chance of taking a longer break
LONG_BREAK_MIN = 5.0  # Minimum long break duration
LONG_BREAK_MAX = 15.0  # Maximum long break duration

# Rate limiting settings
RATE_LIMIT_WAIT_MIN = 60  # Minimum wait time when rate limited (seconds)
RATE_LIMIT_WAIT_MAX = 180  # Maximum wait time when rate limited (seconds)

# Human behavior simulation
SCROLL_CHANCE = 0.3  # 30% chance of scrolling
MOUSE_MOVE_CHANCE = 0.2  # 20% chance of mouse movement
SCROLL_MIN = 100  # Minimum scroll amount
SCROLL_MAX = 500  # Maximum scroll amount

# Browser settings
HEADLESS = True  # Set to False to see the browser in action
DISABLE_IMAGES = True  # Disable images to speed up loading
DISABLE_JAVASCRIPT = False  # Set to True if JS is not needed

# Request settings
TIMEOUT = 30000  # Page load timeout (milliseconds)
WAIT_UNTIL = 'networkidle'  # Wait until network is idle

# Error handling
ERROR_WAIT_MIN = 10  # Minimum wait time on errors (seconds)
ERROR_WAIT_MAX = 20  # Maximum wait time on errors (seconds)

# Session management
MAX_RETRIES = 3  # Maximum number of retries for failed requests
RETRY_DELAY = 30  # Delay between retries (seconds)
