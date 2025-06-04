# utils.py
import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def clean_text(text):
    """
    Removes HTML tags and normalizes whitespace.
    """
    if text is None:
        return None
    soup = BeautifulSoup(str(text), "lxml") # Ensure text is treated as string for BS
    text_content = soup.get_text(separator=' ', strip=True)
    return ' '.join(text_content.split())

def parse_duration_to_minutes(duration_str):
    """
    Parses ISO 8601 duration strings (e.g., "PT30M", "PT1H30M") or
    simple text like "30 min" or "1 hour 30 minutes" into total minutes.
    Returns an integer or None if parsing fails.
    """
    if not duration_str:
        return None

    # If it's already an int/float (e.g. from direct JSON number), return it
    if isinstance(duration_str, (int, float)):
        return int(duration_str)

    cleaned_duration_str = clean_text(str(duration_str))
    if not cleaned_duration_str:
        return None

    total_minutes = 0
    
    # ISO 8601 format (e.g., PT1H30M, PT45M)
    # Make sure it's a string before regex
    if isinstance(cleaned_duration_str, str) and cleaned_duration_str.startswith("PT"):
        hours_match = re.search(r'(\d+)H', cleaned_duration_str)
        minutes_match = re.search(r'(\d+)M', cleaned_duration_str)
        seconds_match = re.search(r'(\d+)S', cleaned_duration_str) # Handle seconds too
        
        if hours_match:
            total_minutes += int(hours_match.group(1)) * 60
        if minutes_match:
            total_minutes += int(minutes_match.group(1))
        if seconds_match and total_minutes == 0: # Only add seconds if no hours/minutes, or if explicitly needed
             if int(seconds_match.group(1)) >=30 : total_minutes +=1 # round up seconds
        return total_minutes if total_minutes > 0 else (None if not (hours_match or minutes_match or seconds_match) else 0)


    # Text-based format (e.g., "1 hour 30 minutes", "45 min", "1 hr 20 mins")
    if isinstance(cleaned_duration_str, str):
        duration_str_lower = cleaned_duration_str.lower()
        hours = 0
        minutes = 0

        hour_match = re.search(r'(\d+)\s*(?:hour|hr)s?', duration_str_lower)
        if hour_match:
            hours = int(hour_match.group(1))

        minute_match = re.search(r'(\d+)\s*(?:minute|min)s?', duration_str_lower)
        if minute_match:
            minutes = int(minute_match.group(1))
        
        if not hour_match and not minute_match:
            simple_minute_match = re.search(r'(\d+)', duration_str_lower)
            if simple_minute_match:
                minutes = int(simple_minute_match.group(1))
        
        calculated_total_minutes = (hours * 60) + minutes
        return calculated_total_minutes if calculated_total_minutes > 0 else None
    
    logger.warning(f"Could not parse duration: {duration_str}")
    return None

def extract_allergens_from_text(text):
    """
    Extracts allergens mentioned in formats like "(Contains: Soy, Wheat)"
    """
    allergens = set()
    if not text or not isinstance(text, str):
        return list(allergens)
    
    # Regex to find "Contains: Allergen1, Allergen2"
    # It handles one or more allergens separated by commas, optionally followed by 'and'
    match = re.search(r'\((?:Contains|Allergens|Allergen Information):\s*([^)]+)\)', text, re.IGNORECASE)
    if match:
        allergen_string = match.group(1)
        # Split by comma, then 'and', then strip whitespace
        potential_allergens = re.split(r',\s*|\s+and\s+', allergen_string)
        for allergen in potential_allergens:
            cleaned_allergen = allergen.strip().rstrip('.').lower().capitalize() # Normalize
            if cleaned_allergen:
                allergens.add(cleaned_allergen)
    return list(allergens)


def parse_ingredient_strings_list(ingredient_elements_or_strings, cleaning_func=clean_text):
    """
    Parses a list of ingredient elements (BeautifulSoup tags) or simple strings
    into a structured list. Attempts to identify quantity, unit, and name.
    Also extracts allergens if mentioned in the text.
    """
    parsed_ingredients = []
    overall_allergens = set()

    if not ingredient_elements_or_strings:
        return [], []

    for item in ingredient_elements_or_strings:
        if hasattr(item, 'get_text'): # BeautifulSoup element
            full_text_raw = item.get_text()
        elif isinstance(item, str): # Simple string
            full_text_raw = item
        else:
            continue

        full_text = cleaning_func(full_text_raw)
        if not full_text:
            continue
            
        item_allergens = extract_allergens_from_text(full_text_raw) # Use raw text for allergen extraction
        overall_allergens.update(item_allergens)

        # Basic parsing attempt (this is highly dependent on format and may need refinement)
        quantity_str, unit_str, name_str = None, None, full_text
        
        # Refined regex to capture various quantity/unit patterns better
        # Example: "1 thumb", "4 clove", "1.5 cup", "12 ounce", "2 teaspoon", "6 tablespoon", "¼ cup", "Salt"
        # This regex is more comprehensive but still might need adjustments based on edge cases
        pattern = re.compile(
            r"^\s*(?P<quantity>[\d\.\/]+(?:[\s-]\d\/\d)?|\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an|some|pinch(?:es)?|dash(?:es)?|a few|several|to taste)\s*" +
            r"(?P<unit>thumb|clove|unit|cup|ounce|oz|teaspoon|tsp|tablespoon|tbsp|tb|gram|g|kg|ml|l|pinch|can|cans|stalk|head|bunch|slice|slices|packet|pack|box|container|bottle|piece|lb|pound|pounds|qt|quart|pt|pint|gallon|gal|drop|dashes|leaves)?\s*" +
            r"(?P<name>.+)", re.IGNORECASE
        )
        
        match = pattern.match(full_text)
        
        if match:
            gd = match.groupdict()
            quantity_str = gd.get('quantity')
            unit_str = gd.get('unit')
            name_str = gd.get('name', full_text).strip().rstrip(',')
             # If unit is None but quantity implies a count (like "2 Scallions"), name might be better
            if unit_str is None and quantity_str and not any(char.isdigit() for char in name_str.split(' ')[0]): # if "2 Large Onions"
                 pass # name_str should be fine
            elif unit_str is None and quantity_str: # like "1 Lime"
                # Check if the first word of name_str could be the actual unit
                name_parts = name_str.split(' ', 1)
                common_units_check = ['thumb', 'clove', 'unit', 'lime', 'scallions', 'garlic', 'ginger'] # Add more if needed
                if name_parts[0].lower() in common_units_check and len(name_parts) > 1:
                    unit_str = name_parts[0]
                    name_str = name_parts[1]
                elif name_parts[0].lower() in common_units_check and len(name_parts) == 1: # e.g. "1 Lime" becomes Q:1 U:Lime N:""
                    unit_str = name_parts[0]
                    name_str = ""
        else: # No clear quantity/unit, assume full text is the name
            name_str = full_text


        # Normalize common quantity words to numbers
        qty_word_map = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
        if quantity_str and quantity_str.lower() in qty_word_map:
            quantity = qty_word_map[quantity_str.lower()]
        elif quantity_str:
            try:
                if '/' in quantity_str: # Handle fractions like "1/2"
                    if '-' in quantity_str or ' ' in quantity_str: # Mixed fraction like "1 1/2"
                        parts = re.split(r'\s|-', quantity_str)
                        whole = int(parts[0])
                        num, den = map(int, parts[1].split('/'))
                        quantity = whole + (num / den)
                    else: # Simple fraction "1/2"
                        num, den = map(int, quantity_str.split('/'))
                        quantity = num / den
                else:
                    quantity = float(quantity_str) # Handles "0.25", "1.5"
            except ValueError:
                quantity = quantity_str # Keep as string if conversion fails (e.g. "pinch")
        else:
            quantity = None

        # Clean name_str further by removing allergen text if it was part of it.
        if name_str and item_allergens:
             name_str = re.sub(r'\s*\((?:Contains|Allergens|Allergen Information):\s*[^)]+\)', '', name_str, flags=re.IGNORECASE).strip()


        parsed_ingredients.append({
            "name": clean_text(name_str) if name_str else None,
            "quantity": quantity,
            "unit": clean_text(unit_str) if unit_str else None,
            "full_text": full_text,
            "allergens_in_item": item_allergens
        })
        logger.debug(f"Parsed ingredient: Q: {quantity_str}, U: {unit_str}, N: {name_str} from '{full_text}'")

    return parsed_ingredients, list(overall_allergens)


def parse_step_strings_list(step_elements_or_strings, cleaning_func=clean_text):
    """
    Parses a list of step elements (BeautifulSoup tags) or simple strings into a list of strings.
    """
    parsed_steps = []
    if not step_elements_or_strings:
        return []

    for i, item in enumerate(step_elements_or_strings):
        if hasattr(item, 'get_text'): # BeautifulSoup element
            text = cleaning_func(item.get_text())
        elif isinstance(item, str): # Simple string
            text = cleaning_func(item)
        else:
            continue
            
        if text:
            parsed_steps.append(text)
    return parsed_steps