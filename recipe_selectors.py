# selectors.py
"""
selectors.py

This module stores CSS selectors and JSON-LD paths for scraping HelloFresh recipe data.
The primary strategy is to parse the JSON-LD data from the <script type="application/ld+json" id="schema-org"> tag.
CSS selectors are used as fallbacks or for data not present in JSON-LD.

***************************************************************************
* CRITICAL NOTE: While JSON-LD is generally stable, website structures    *
* can change. If the JSON-LD structure changes or is removed, this       *
* scraper WILL require updates. Always verify with browser developer tools.*
***************************************************************************
"""
import re

# General Disclaimer
DISCLAIMER = "Important Note: Web scraping can violate the Terms of Service (ToS) of websites, including HelloFresh. This application is developed for educational and demonstrational purposes only. Always review and respect the ToS of any website before attempting to scrape it. Proceed responsibly and at your own risk. This tool does not endorse or encourage activities that violate website ToS."

# --- JSON-LD Path Definitions & CSS Fallbacks ---
# For each field, we'll define a 'json_ld_path' if applicable.
# This path will be a list of keys to navigate the parsed JSON.
# 'css_selectors' will be a list of fallback CSS strategies.

SELECTORS = {
    "json_ld_script_selector": {"type": "css", "selector": "script[type='application/ld+json']#schema-org"},

    "external_id": {
        # The recipe ID is often the last part of the URL slug.
        # Example: "teriyaki-chicken-tenders-5a664231ad1d6c6f007d0d72" -> "5a664231ad1d6c6f007d0d72"
        # This will be handled by custom logic in scraper.py using the 'source_url'.
        "json_ld_path": ["id"], # If the full URL is in 'id', we'll parse the ID from it. Also, the recipe object might have a direct 'id' or 'productID'.
        "css_selectors": [
            {"type": "meta", "selector": "meta[name='page_id']", "attribute_name": "content"},
        ],
        "id_in_url_pattern": r'([a-zA-Z0-9]{24})$' # HelloFresh IDs are typically 24-char alphanumeric
    },
    "name": {
        "json_ld_path": ["name"],
        "css_selectors": [
            {"type": "css", "selector": "h1[data-test-id='recipe-name']"},
            {"type": "css", "selector": "h1[itemprop='name']"},
            {"type": "css", "selector": "h1"},
            {"type": "meta", "selector": "meta[property='og:title']", "attribute_name": "content"},
        ]
    },
    "description": {
        "json_ld_path": ["description"],
        "css_selectors": [
             {"type": "css", "selector": "span[data-test-id='recipe-description']"}, # From previous analysis
             {"type": "css", "selector": "div[data-test-id='recipe-description'] p"}, # From Sample.html structure
             {"type": "meta", "selector": "meta[name='description']", "attribute_name": "content"},
        ]
    },
    "prep_time_minutes": {
        # JSON-LD often uses ISO 8601 duration (e.g., "PT30M") for prepTime, cookTime, totalTime
        "json_ld_path": ["prepTime"], # This will need parsing by parse_duration_to_minutes
        "css_selectors": [
            {"type": "css", "selector": "*[itemprop='prepTime']", "attribute_name": "content"},
            {"type": "css", "selector": "div[data-test-id='recipe-metadata-item-prep-time'] span"},
        ]
    },
    "cook_time_minutes": {
        "json_ld_path": ["cookTime"], # This will need parsing
        "css_selectors": [
            {"type": "css", "selector": "*[itemprop='cookTime']", "attribute_name": "content"},
            {"type": "css", "selector": "div[data-test-id='recipe-metadata-item-cook-time'] span"}, # Might be "Total Time"
        ]
    },
    "total_time_minutes": {
        "json_ld_path": ["totalTime"], # This will need parsing
        "css_selectors": [
            {"type": "css", "selector": "*[itemprop='totalTime']", "attribute_name": "content"},
             # The Sample HTML shows "Total Time" directly:
            {"type": "css", "selector": "div[data-test-id='recipe-description-meta'] div:nth-of-type(1) span:nth-of-type(2)"}, # Example: "35 minutes"
            {"type": "css", "selector": "span:contains('Total Time') + span"}, # More robust if text changes
        ]
    },
    "servings": {
        "json_ld_path": ["recipeYield"], # Usually an integer or string like "2 servings"
        "css_selectors": [
            {"type": "css", "selector": "button[data-test-id='yield-select-button-yield'] span"},
            {"type": "css", "selector": "span[data-test-id='recipe-yield']"},
            {"type": "css", "selector": "*[itemprop='recipeYield']"},
        ]
    },
    "image_url": {
        "json_ld_path": ["image"], # Can be a string or an object with 'url'
        "css_selectors": [
            {"type": "meta", "selector": "meta[property='og:image']", "attribute_name": "content"},
            {"type": "css", "selector": "img[data-test-id='recipe-hero-image']", "attribute_name": "src"},
        ]
    },
    "ingredients": {
        # JSON-LD provides this as an array of strings
        "json_ld_path": ["recipeIngredient"],
        "css_selectors": [
            # Fallback to previous CSS selectors if JSON-LD fails
            {"type": "css_list", "selector": "div[data-test-id='ingredient-item-shipped'] div[data-test-id='ingredient-item-name']"},
            {"type": "css_list", "selector": "div[data-test-id='ingredient-item-not-shipped'] div[data-test-id='ingredient-item-name']"},
            {"type": "css_list", "selector": "*[itemprop='recipeIngredient']"},
        ]
    },
    "steps": {
        # JSON-LD provides this as an array of objects with "@type":"HowToStep" and "text"
        "json_ld_path": ["recipeInstructions"], # This will be a list of HowToStep objects
        "css_selectors": [
            {"type": "css_list", "selector": "div[data-test-id='instruction-step-description']"},
        ]
    },
    "nutrition_info": {
        # JSON-LD provides this as a nested object
        "json_ld_path": ["nutrition"], # This will be an object like {"calories": "640 kcal", ...}
        "css_selectors_parent": "div[data-test-id='nutritions']", # Fallback parent
        "css_fields": { # Sub-selectors relative to the parent_selector
            "calories": {"type": "css", "selector": "div[data-test-id='nutrition-step']:contains('Calories') span:last-child"},
            "fat": {"type": "css", "selector": "div[data-test-id='nutrition-step']:contains('Fat') span:last-child"},
            "saturated_fat": {"type": "css", "selector": "div[data-test-id='nutrition-step']:contains('Saturated Fat') span:last-child"},
            "carbohydrate": {"type": "css", "selector": "div[data-test-id='nutrition-step']:contains('Carbohydrate') span:last-child"},
            "sugar": {"type": "css", "selector": "div[data-test-id='nutrition-step']:contains('Sugar') span:last-child"},
            "protein": {"type": "css", "selector": "div[data-test-id='nutrition-step']:contains('Protein') span:last-child"},
            "fiber": {"type": "css", "selector": "div[data-test-id='nutrition-step']:contains('Dietary Fiber') span:last-child"},
            "cholesterol": {"type": "css", "selector": "div[data-test-id='nutrition-step']:contains('Cholesterol') span:last-child"},
            "sodium": {"type": "css", "selector": "div[data-test-id='nutrition-step']:contains('Sodium') span:last-child"},
        }
    },
    "tags_array": {
        "json_ld_path": ["keywords"], # Often a comma-separated string or an array
        "css_selectors": [
             {"type": "css_list", "selector": "div[data-test-id='recipe-tags-container'] a[data-test-id='tag-link']"}, # From previous analysis
        ]
    },
    "cuisine": { # New field based on JSON-LD
        "json_ld_path": ["recipeCuisine"],
        "css_selectors": [] # Usually in JSON-LD or meta tags if available
    },
    "category": { # New field
        "json_ld_path": ["recipeCategory"],
        "css_selectors": []
    },
     "date_published": {
        "json_ld_path": ["datePublished"],
        "css_selectors": [
            {"type": "meta", "selector": "meta[property='article:published_time']", "attribute_name": "content"}
        ]
    },
    "prep_time_iso": {"json_ld_path": ["prepTime"]}, # Raw ISO duration
    "cook_time_iso": {"json_ld_path": ["cookTime"]}, # Raw ISO duration
    "total_time_iso": {"json_ld_path": ["totalTime"]}, # Raw ISO duration

}

# --- Configuration ---
REQUEST_DELAY_SECONDS = 1
MAX_RETRIES = 2
RETRY_BACKOFF_FACTOR = 0.3

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
]