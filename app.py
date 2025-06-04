# app.py
import logging
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS # For allowing frontend requests from a different port during development

# Assuming scraper.py is in the same directory
from scraper import scrape_recipe_data 
from recipe_selectors import DISCLAIMER # Import disclaimer to pass to template

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# --- Logging Configuration ---
# It's good practice to configure logging for your application.
# You can make this more sophisticated (e.g., logging to a file, different levels).
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(name)s - %(threadName)s - %(message)s')
logger = logging.getLogger(__name__)

# --- General Disclaimer (already in selectors.py, also good to have here) ---
# This is also passed to the frontend template.
APP_DISCLAIMER = DISCLAIMER 

# --- Routes ---
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html', disclaimer=APP_DISCLAIMER)

@app.route('/scrape-recipe', methods=['POST'])
def handle_scrape_recipe():
    """
    API endpoint to scrape a recipe.
    Expects a JSON payload with a "url" key.
    """
    logger.info("Received request for /scrape-recipe")
    if not request.is_json:
        logger.warning("Request is not JSON")
        return jsonify({"error": "Invalid request: payload must be JSON."}), 400

    data = request.get_json()
    recipe_url = data.get('url')

    if not recipe_url:
        logger.warning("URL is missing from request")
        return jsonify({"error": "URL is required."}), 400

    # Basic URL validation (can be improved)
    if not recipe_url.startswith(('http://', 'https://')):
        logger.warning(f"Invalid URL format: {recipe_url}")
        return jsonify({"error": "Invalid URL format. Must start with http:// or https://"}), 400
    
    # Optional: Add more specific validation for HelloFresh URLs if desired
    # if "hellofresh.com" not in recipe_url:
    #     return jsonify({"error": "URL does not seem to be a HelloFresh domain."}), 400

    logger.info(f"Starting scrape for URL: {recipe_url}")
    try:
        scraped_data = scrape_recipe_data(recipe_url)
        if "error" in scraped_data:
            logger.error(f"Scraping failed for {recipe_url}: {scraped_data['error']}")
            # Return a 500 for server-side scraping issues, or 400/404 if it's client related
            # Based on error content, status code might change.
            # e.g. if scraper_data['error'] contains "404", maybe return 404
            return jsonify(scraped_data), 500 # Or a more specific error code
        
        logger.info(f"Successfully scraped data for {recipe_url}")
        return jsonify(scraped_data), 200
    except Exception as e:
        logger.critical(f"An unexpected error occurred during scraping process for {recipe_url}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected server error occurred. Please check server logs."}), 500

# --- How to run the Flask application (for README or comments) ---
# 1. Make sure you have Python and pip installed.
# 2. Install dependencies: pip install Flask requests beautifulsoup4 lxml flask-cors
# 3. Save app.py, scraper.py, selectors.py, utils.py in the same directory.
# 4. Create a 'templates' folder and put 'index.html' inside it.
# 5. Create a 'static' folder and put 'script.js' (and 'style.css' if used) inside it.
# 6. Open your terminal, navigate to the directory containing app.py.
# 7. Run the Flask app: python app.py
#    (For development, Flask's built-in server is fine. For production, use a WSGI server like Gunicorn.)
# 8. Open your browser and go to http://127.0.0.1:5000/

if __name__ == '__main__':
    # Note: debug=True is useful for development but should be False in production.
    app.run(debug=True, port=5000)