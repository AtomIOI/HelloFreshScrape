# HelloFresh Recipe Scraper

This application scrapes recipe data from HelloFresh recipe URLs. It consists of a Python Flask backend for scraping and a simple HTML/JavaScript frontend for interaction.

**Important Note: Web scraping can violate the Terms of Service (ToS) of websites, including HelloFresh. This application is developed for educational and demonstrational purposes only. Always review and respect the ToS of any website before attempting to scrape it. Proceed responsibly and at your own risk. This tool does not endorse or encourage activities that violate website ToS.**

## Technology Stack

* **Backend**: Python, Flask, Requests, BeautifulSoup4 (with lxml)
* **Frontend**: HTML, CSS, Vanilla JavaScript

## Features

* Input a HelloFresh recipe URL.
* Scrape data like name, description, times, servings, ingredients, steps, etc.
* Display structured recipe data.
* Show raw JSON output with a "Copy JSON" button.
* User-Agent rotation and configurable request delay.
* Basic error handling and retries.

## Project Structure

hellofresh_scraper/
├── app.py              # Flask application, API routes
├── scraper.py          # Core scraping logic
├── selectors.py        # CSS selectors and configuration
├── utils.py            # Helper functions (data cleaning, parsing)
├── templates/
│   └── index.html      # Frontend HTML
├── static/
│   ├── script.js       # Frontend JavaScript
│   └── style.css       # Frontend CSS
└── README.md           # This file

## Setup and Installation

1.  **Clone the repository (or create the files manually as described).**
2.  **Ensure Python 3.x is installed.**
3.  **Install dependencies:**
    Open your terminal in the project's root directory (`hellofresh_scraper/`) and run:
    ```bash
    pip install Flask requests beautifulsoup4 lxml flask-cors
    ```
    *(Optional for dynamic scraping, if you extend `scraper.py`):*
    ```bash
    # pip install playwright
    # python -m playwright install
    # or
    # pip install selenium
    ```

## How to Run the Application

1.  Navigate to the project's root directory in your terminal:
    ```bash
    cd path/to/hellofresh_scraper
    ```
2.  Run the Flask application:
    ```bash
    python app.py
    ```
3.  Open your web browser and go to: `http://127.0.0.1:5000/`

## How to Use

1.  Open the application in your browser.
2.  Find a HelloFresh recipe URL you want to scrape (e.g., `https://www.hellofresh.com/recipes/some-recipe-slug-xxxxxxxxxxxxxxxx`).
3.  Paste the URL into the input field.
4.  Click the "Scrape Recipe" button.
5.  View the scraped data displayed on the page and the raw JSON output.

## Maintaining the Scraper

**Website Structure Changes:**
Websites, including HelloFresh, frequently update their HTML structure. This can break the scraper. If the scraper stops working or extracts incorrect data:

1.  **Identify Failing Selectors:** Check the console logs from the Flask application (`app.py`). The `scraper.py` module logs warnings when specific data fields cannot be found.
2.  **Inspect the Website:** Open a HelloFresh recipe page in your browser. Use your browser's Developer Tools (usually by right-clicking on an element and selecting "Inspect" or "Inspect Element") to examine the HTML structure of the data you want to extract.
3.  **Update `selectors.py`:**
    * Locate the relevant selector entry in the `SELECTORS` dictionary in `selectors.py`.
    * Modify the CSS selector string (e.g., `selector: "h1.recipe-title"`) to match the new HTML structure you found.
    * Prioritize robust selectors: unique IDs, `data-*` attributes, Schema.org `itemprop` attributes, or stable class names. Avoid highly generic or dynamically generated class names.
    * Test thoroughly after changes.

**Configuration:**
You can adjust settings like `REQUEST_DELAY_SECONDS`, `MAX_RETRIES`, and `USER_AGENTS` at the bottom of `selectors.py`.

## Potential Next Steps & Advanced Topics (for the user)

* **Dynamic Content Handling**: If HelloFresh relies heavily on JavaScript to load recipe data not present in the initial HTML, you might need to integrate `Playwright` or `Selenium`. The `scraper.py` file has comments indicating where this logic could be added. This is more resource-intensive.
* **Inspecting XHR/Fetch Requests**: For some sites, data is loaded via background API calls (XHR/Fetch). You can use browser developer tools (Network tab) to find these. If HelloFresh uses such an API for recipe data, directly calling that API with `requests` might be more efficient and reliable than parsing HTML (but these private APIs can change without notice).
* **Proxy Use**: If you encounter IP blocking or rate limiting for extensive scraping (not recommended for single URL scraping), using proxies could be a solution. This adds complexity.
* **Database Ingestion**: The output JSON can be used to populate a database. For example, with a SQL database or a NoSQL database like Supabase/Firebase:
    * The keys in the JSON output (e.g., `name`, `prep_time_minutes`, `ingredients`) can directly map to column names in a database table or fields in a document.
    * You would write a separate script or extend this application to take the JSON and insert it into your chosen database.
* **Error Monitoring & Alerting**: For a production scraper, you'd want more robust error monitoring (e.g., Sentry) and alerting for failures.
* **Robust Ingredient Parsing**: The current ingredient parsing in `utils.py` is very basic. For more accurate separation of quantity, unit, and name, consider using more advanced regex, NLP libraries (like spaCy), or dedicated ingredient parsing libraries.

**Remember to scrape responsibly and respect website Terms of Service.**