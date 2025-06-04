# scraper.py
import requests
import time
import random
import logging
import json 
import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from recipe_selectors import SELECTORS, USER_AGENTS, REQUEST_DELAY_SECONDS, MAX_RETRIES, RETRY_BACKOFF_FACTOR, DISCLAIMER
from utils import clean_text, parse_duration_to_minutes, parse_ingredient_strings_list, parse_step_strings_list, extract_allergens_from_text

logger = logging.getLogger(__name__)

def get_json_ld_data(soup):
    script_selector_info = SELECTORS.get("json_ld_script_selector")
    if not script_selector_info:
        logger.warning("JSON-LD script selector not defined in SELECTORS.")
        return None
    script_tag = soup.select_one(script_selector_info['selector'])
    if script_tag and script_tag.string:
        try:
            json_data = json.loads(script_tag.string)
            if isinstance(json_data, list):
                for item in json_data:
                    if isinstance(item, dict) and item.get("@type") == "Recipe":
                        return item
                logger.info("JSON-LD is a list, but no 'Recipe' type found. Taking first item if available.")
                return json_data[0] if json_data else None
            elif isinstance(json_data, dict) and json_data.get("@type") == "Recipe":
                return json_data
            elif isinstance(json_data, dict): # Fallback if @type is not Recipe but it's the main JSON blob
                logger.warning(f"JSON-LD found but @type is '{json_data.get('@type')}', not 'Recipe'. Using it anyway.")
                return json_data

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON-LD: {e}. Content: {script_tag.string[:200]}")
            return None
    else:
        logger.warning(f"JSON-LD script tag not found using selector: {script_selector_info['selector']}")
    return None

def extract_from_json_ld(json_ld_data, path):
    if not json_ld_data or not path: return None
    current_data = json_ld_data
    for key in path:
        if isinstance(current_data, dict) and key in current_data:
            current_data = current_data[key]
        elif isinstance(current_data, list) and isinstance(key, int) and key < len(current_data): # Access list by index
            current_data = current_data[key]
        else: return None
    return current_data

def extract_data_point(soup, strategies, cleaning_func=clean_text):
    if not strategies: return None
    for strategy in strategies:
        try:
            if strategy['type'] == 'css':
                element = soup.select_one(strategy['selector'])
                if element:
                    value = element.get(strategy['attribute_name']) if strategy.get('attribute_name') else element.get_text()
                    return cleaning_func(value) if value and cleaning_func else (value.strip() if value else None)
            elif strategy['type'] == 'meta':
                element = soup.select_one(strategy['selector'])
                if element and strategy.get('attribute_name'):
                    value = element.get(strategy['attribute_name'])
                    return cleaning_func(value) if value and cleaning_func else (value.strip() if value else None)
        except Exception as e:
            logger.warning(f"CSS Selector strategy {strategy} failed: {e}")
            continue
    return None

def extract_list_data(soup, strategies): # Simplified, expects list_item_parser to handle elements
    if not strategies: return []
    for strategy in strategies:
        try:
            if strategy['type'] == 'css_list':
                elements = soup.select(strategy['selector'])
                if elements: return elements
        except Exception as e:
            logger.warning(f"CSS List selector strategy {strategy} failed: {e}")
            continue
    return []


def extract_nutrition_value(value_str):
    if value_str is None: return None
    # Convert to string in case it's a number from JSON-LD
    s = str(value_str).lower()
    match = re.search(r'([\d\.]+)', s)
    return float(match.group(1)) if match else None

def parse_servings_from_json(yield_data):
    if yield_data is None: return None
    if isinstance(yield_data, (int, float)): return int(yield_data)
    if isinstance(yield_data, str):
        match = re.search(r'\d+', yield_data)
        if match: return int(match.group(0))
    logger.warning(f"Could not parse servings from recipeYield: {yield_data}")
    return None
    
# --- Main Scraping Function ---
def scrape_recipe_data(recipe_url):
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    logger.info(f"Scraping URL: {recipe_url}")
    time.sleep(REQUEST_DELAY_SECONDS)

    html_content = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(recipe_url, headers=headers, timeout=15)
            response.raise_for_status()
            html_content = response.text
            logger.info(f"Successfully fetched HTML for {recipe_url}")
            break
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {recipe_url}: {e.response.status_code} {e.response.reason}")
            if e.response.status_code == 404: return {"error": "Recipe not found (404)."}
            if attempt == MAX_RETRIES - 1: return {"error": f"HTTP error after {MAX_RETRIES} attempts: {e.response.status_code}."}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {recipe_url}: {e}")
            if attempt == MAX_RETRIES - 1: return {"error": f"Request error after {MAX_RETRIES} attempts: {e}."}
        time.sleep(RETRY_BACKOFF_FACTOR * (2 ** attempt))

    if not html_content: return {"error": "Could not retrieve HTML content."}

    soup = BeautifulSoup(html_content, "lxml")
    json_ld_data = get_json_ld_data(soup)

    if not json_ld_data:
        logger.warning("JSON-LD data not found or unusable. Relying on CSS selectors.")
    
    scraped_data = {
        "source_url": recipe_url,
        "scraped_at_timestamp": datetime.now(timezone.utc).isoformat(),
        "disclaimer": DISCLAIMER
    }

    def get_value(field_key, cleaning_func=clean_text, is_list=False, 
                  json_list_item_processor=None, # Processes items if data from JSON-LD is a list
                  css_list_item_processor=None,  # Processes BeautifulSoup elements if data from CSS is a list
                  specific_json_parser=None):   # Parses a specific field directly from JSON-LD data
        selector_config = SELECTORS.get(field_key, {})
        json_ld_path = selector_config.get("json_ld_path")
        raw_json_value = None
        
        if json_ld_data and json_ld_path:
            raw_json_value = extract_from_json_ld(json_ld_data, json_ld_path)

        if raw_json_value is not None:
            logger.debug(f"Field '{field_key}': Found in JSON-LD. Raw: {str(raw_json_value)[:100]}")
            if specific_json_parser:
                return specific_json_parser(raw_json_value)
            if is_list:
                return json_list_item_processor(raw_json_value) if json_list_item_processor else \
                       [cleaning_func(item) if cleaning_func else item for item in raw_json_value if item] if isinstance(raw_json_value, list) else []
            return cleaning_func(str(raw_json_value)) if cleaning_func and isinstance(raw_json_value, (str, int, float)) else raw_json_value

        # Fallback to CSS
        css_strategies = selector_config.get("css_selectors")
        if css_strategies:
            logger.debug(f"Field '{field_key}': Not in JSON-LD or parser failed, trying CSS.")
            if is_list:
                elements = extract_list_data(soup, css_strategies) # Returns BS elements
                return css_list_item_processor(elements, cleaning_func=cleaning_func) if css_list_item_processor and elements else []
            else:
                return extract_data_point(soup, css_strategies, cleaning_func)
        
        logger.warning(f"Field '{field_key}': Not found in JSON-LD and no CSS fallbacks or CSS failed.")
        return None


    scraped_data["name"] = get_value("name")
    scraped_data["description"] = get_value("description")

    # External ID
    id_pattern = SELECTORS.get("external_id", {}).get("id_in_url_pattern")
    extracted_id_from_url = None
    if id_pattern:
        match = re.search(id_pattern, recipe_url.split('?')[0].split('/')[-1])
        if match: extracted_id_from_url = match.group(1)
    
    json_ld_id_val = get_value("external_id", cleaning_func=None) # Get raw from JSON-LD
    if json_ld_id_val and isinstance(json_ld_id_val, str) and id_pattern:
        match_json = re.search(id_pattern, json_ld_id_val.split('?')[0].split('/')[-1]) # If it's a URL in id field
        if match_json: scraped_data["external_id"] = match_json.group(1)
        else: scraped_data["external_id"] = json_ld_id_val # If it's already just the ID
    elif extracted_id_from_url:
        scraped_data["external_id"] = extracted_id_from_url
    else:
        scraped_data["external_id"] = None


    # Time fields from JSON-LD (ISO duration) or CSS
    scraped_data["prep_time_minutes"] = get_value("prep_time_minutes", specific_json_parser=parse_duration_to_minutes)
    scraped_data["cook_time_minutes"] = get_value("cook_time_minutes", specific_json_parser=parse_duration_to_minutes)
    scraped_data["total_time_minutes"] = get_value("total_time_minutes", specific_json_parser=parse_duration_to_minutes)

    if scraped_data["total_time_minutes"] is None and scraped_data["prep_time_minutes"] is not None and scraped_data["cook_time_minutes"] is not None:
        scraped_data["total_time_minutes"] = scraped_data["prep_time_minutes"] + scraped_data["cook_time_minutes"]
        logger.info("Calculated total_time_minutes as sum of prep and cook times.")


    scraped_data["servings"] = get_value("servings", specific_json_parser=parse_servings_from_json)
    
    # Image URL: JSON-LD 'image' can be a string URL or an object {"@type": "ImageObject", "url": "..."} or list of these
    raw_image_data = get_value("image_url", cleaning_func=None)
    if isinstance(raw_image_data, list) and raw_image_data:
        img_item = raw_image_data[0]
        scraped_data["image_url"] = img_item.get("url") if isinstance(img_item, dict) else str(img_item)
    elif isinstance(raw_image_data, dict):
        scraped_data["image_url"] = raw_image_data.get("url") or raw_image_data.get("contentUrl")
    elif isinstance(raw_image_data, str):
        scraped_data["image_url"] = raw_image_data
    if scraped_data.get("image_url"): scraped_data["image_url"] = scraped_data["image_url"].strip()


    # Ingredients: JSON-LD path "recipeIngredient" gives a list of strings.
    # parse_ingredient_strings_list is designed for this.
    ingredients_list, allergens_from_ingredients = parse_ingredient_strings_list(
        get_value("ingredients", is_list=True, cleaning_func=None) or [] # Pass raw list of strings
    )
    scraped_data["ingredients"] = ingredients_list
    scraped_data["allergens_extracted_from_ingredients"] = allergens_from_ingredients


    # Steps: JSON-LD path "recipeInstructions" gives a list of HowToStep objects or strings.
    def process_json_steps(step_data_list):
        if not isinstance(step_data_list, list): return []
        processed = []
        for step_item in step_data_list:
            if isinstance(step_item, dict) and step_item.get("@type") == "HowToStep":
                processed.append(clean_text(step_item.get("text")))
            elif isinstance(step_item, str): # If it's just a list of strings
                 processed.append(clean_text(step_item))
        return [s for s in processed if s]
        
    scraped_data["steps"] = get_value("steps", is_list=True, json_list_item_processor=process_json_steps, css_list_item_processor=parse_step_strings_list)


    # Nutrition Info: JSON-LD path "nutrition" gives an object.
    nutrition_json = get_value("nutrition_info", cleaning_func=None) # Get raw dict from JSON-LD
    parsed_nutrition = {}
    if isinstance(nutrition_json, dict):
        for key, value_str in nutrition_json.items():
            # Normalize key: e.g. "fatContent" -> "fat", "calories" -> "calories"
            # Remove "Content", make lowercase, handle "calories" specifically
            clean_key = key.replace("Content", "").lower()
            if "calories" in key.lower(): clean_key = "calories" 
            
            num_value = extract_nutrition_value(str(value_str))
            if num_value is not None:
                parsed_nutrition[clean_key] = num_value
        scraped_data["nutrition_info"] = parsed_nutrition
    
    if not scraped_data["nutrition_info"]: # CSS Fallback for nutrition
        logger.info("Nutrition not fully parsed from JSON-LD, trying CSS fallback.")
        nutrition_css_config = SELECTORS.get("nutrition_info", {})
        parent_selector = nutrition_css_config.get("css_selectors_parent")
        if parent_selector:
            nutrition_parent_el = soup.select_one(parent_selector)
            if nutrition_parent_el:
                css_nutrition_data = {}
                for key, field_strategies in nutrition_css_config.get("css_fields", {}).items():
                    value = extract_data_point(nutrition_parent_el, [field_strategies] if isinstance(field_strategies, dict) else field_strategies, clean_text)
                    if value:
                        num_value = extract_nutrition_value(value)
                        if num_value is not None:
                             css_nutrition_data[key.replace("_schema","")] = num_value
                scraped_data["nutrition_info"] = css_nutrition_data
                if not css_nutrition_data: logger.warning(f"CSS Nutrition parent found, but no fields extracted from {recipe_url}.")
            else: logger.warning(f"CSS Nutrition parent not found via: {parent_selector}")
        

    # Tags (Keywords)
    tags_value = get_value("tags_array", cleaning_func=None) # Get raw data
    if isinstance(tags_value, str):
        scraped_data["tags_array"] = [tag.strip() for tag in tags_value.split(',') if tag.strip()]
    elif isinstance(tags_value, list):
        scraped_data["tags_array"] = [clean_text(str(tag)) for tag in tags_value if tag]
    else: scraped_data["tags_array"] = []
        
    scraped_data["cuisine"] = get_value("cuisine")
    scraped_data["category"] = get_value("category")
    scraped_data["date_published"] = get_value("date_published", cleaning_func=lambda x: x.strip() if x else None)

    # Store raw ISO durations if available from JSON-LD, for potential advanced use
    scraped_data["prep_time_iso"] = get_value("prep_time_iso", cleaning_func=None)
    scraped_data["cook_time_iso"] = get_value("cook_time_iso", cleaning_func=None)
    scraped_data["total_time_iso"] = get_value("total_time_iso", cleaning_func=None)


    # Log missing critical fields
    if not scraped_data.get("name"): logger.error(f"CRITICAL: Recipe Name missing for {recipe_url}")
    if not scraped_data.get("ingredients"): logger.warning(f"Ingredients missing for {recipe_url}")
    if not scraped_data.get("steps"): logger.warning(f"Steps missing for {recipe_url}")

    return scraped_data


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    
    # --- Testing with Sample.html ---
    print("\n--- Testing with Sample.html ---")
    try:
        with open("Sample.html", "r", encoding="utf-8") as f:
            sample_html_content = f.read()
        
        original_requests_get = requests.get
        def mock_requests_get_sample(url, headers, timeout):
            class MockResponse:
                def __init__(self, text, status_code):
                    self.text = text; self.status_code = status_code; self.reason = "OK"
                def raise_for_status(self):
                    if self.status_code >= 400: raise requests.exceptions.HTTPError()
            return MockResponse(sample_html_content, 200)

        requests.get = mock_requests_get_sample
        sample_url = "https://www.hellofresh.com/recipes/teriyaki-chicken-tenders-5a664231ad1d6c6f007d0d72" # Matches Sample.html content
        data = scrape_recipe_data(sample_url)
        requests.get = original_requests_get # Restore
        
        if data and "error" not in data:
            print("\n--- Scraped Data (from Sample.html): ---")
            print(json.dumps(data, indent=2))
            # Basic Assertions based on Sample.html's JSON-LD
            assert data["name"] == "Teriyaki Chicken Tenders with Jasmine Rice and Green Beans"
            assert data["description"].startswith("Soy to the world!")
            assert data["total_time_minutes"] == 35
            assert data["servings"] == 2 
            assert len(data["ingredients"]) == 16 # 12 shipped + 4 not shipped
            assert data["ingredients"][0]["name"] == "Ginger"
            assert data["ingredients"][0]["quantity"] == 1
            assert data["ingredients"][0]["unit"] == "Thumb" # Based on improved parsing
            assert "Soy" in data["allergens_extracted_from_ingredients"]
            assert "Wheat" in data["allergens_extracted_from_ingredients"]
            assert len(data["steps"]) == 6
            assert data["steps"][0].startswith("Wash and dry all produce.")
            assert data["nutrition_info"]["calories"] == 640
            assert data["nutrition_info"]["fat"] == 15
            assert data["cuisine"] == "Asian"
            assert data["category"] == "main course"
            assert data["date_published"] == "2018-01-22T19:57:37+00:00"
            assert data["external_id"] == "5a664231ad1d6c6f007d0d72"
            print("\nSUCCESS: Key data points from Sample.html extracted correctly via JSON-LD!")
        elif data:
            print(f"\n--- Error (from Sample.html): {data['error']} ---")
        else:
            print("Scraping function returned None or unexpected error for Sample.html.")

    except FileNotFoundError:
        print("Sample.html not found. Please ensure it's in the same directory for this test.")
    except Exception as e:
        print(f"An error occurred during Sample.html test: {e}")
        if 'requests' in locals() and 'original_requests_get' in locals() and requests.get != original_requests_get: # type: ignore
            requests.get = original_requests_get # Ensure restoration even on error