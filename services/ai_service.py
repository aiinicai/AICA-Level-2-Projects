import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Check for API Key in environment
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()


def get_gemini_client():
    if not GEMINI_API_KEY:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini client: {e}")
        return None


def parse_grocery_text_or_receipt(text: Optional[str] = None, image_bytes: Optional[bytes] = None) -> List[Dict[str, str]]:
    """
    Parses pasted raw receipt text OR receipt image bytes into Indian & global kitchen items:
    [{"name": "...", "category": "PRODUCE|DAIRY|MEAT|PANTRY_STAPLE|BAKING|FROZEN|CANNED", "shelf_life_tier": "URGENT|THIS_WEEK|STAPLE", "quantity_note": "..."}]
    """
    model = get_gemini_client()
    
    if model and (text or image_bytes):
        prompt = (
            "You are an expert culinary assistant for PantryZero. "
            "Extract grocery ingredients from the following receipt or grocery list. "
            "Recognize Indian, Continental, and Pan-Asian ingredients (Paneer, Dahi, Atta, Dals, Basmati, Soy sauce, Pasta, Olive oil, Palak, Garlic, Chilli, etc.). "
            "For each item, classify it with: "
            "1. 'name': clean ingredient name. "
            "2. 'category': exactly one of ['PRODUCE', 'DAIRY', 'MEAT', 'PANTRY_STAPLE', 'BAKING', 'FROZEN', 'CANNED']. "
            "3. 'shelf_life_tier': 'URGENT' if perishable (paneer, fresh coriander, palak, cut chicken, milk/dahi), "
            "'THIS_WEEK' if fresh vegetables with 4-7 day life, "
            "or 'STAPLE' if dry dals, pasta, noodles, rice, spices, or sauces. "
            "4. 'quantity_note': estimated quantity or package info. "
            "Return ONLY a valid JSON array of objects without markdown formatting or code blocks."
        )

        try:
            if image_bytes:
                import io
                from PIL import Image
                img = Image.open(io.BytesIO(image_bytes))
                response = model.generate_content([prompt, img])
            else:
                response = model.generate_content(f"{prompt}\n\nGrocery text input:\n{text}")

            clean_text = response.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            
            items = json.loads(clean_text.strip())
            if isinstance(items, list) and len(items) > 0:
                return items
        except Exception as e:
            logger.error(f"Gemini receipt parsing failed, falling back to smart parser: {e}")

    # Robust smart fallback parser
    return _mock_parse_grocery(text, bool(image_bytes))


def _mock_parse_grocery(text: Optional[str] = None, is_image: bool = False) -> List[Dict[str, str]]:
    """Heuristic grocery parser for offline/development use."""
    if not text and not is_image:
        return []

    if is_image and (not text or len(text.strip()) < 3):
        return [
            {"name": "Fresh Malai Paneer", "category": "DAIRY", "shelf_life_tier": "URGENT", "quantity_note": "200g pack"},
            {"name": "Desi Palak (Spinach)", "category": "PRODUCE", "shelf_life_tier": "URGENT", "quantity_note": "1 bunch fresh"},
            {"name": "Fresh Dhaniya & Spring Onion", "category": "PRODUCE", "shelf_life_tier": "URGENT", "quantity_note": "1 bunch"},
            {"name": "Desi Tamatar (Tomatoes)", "category": "PRODUCE", "shelf_life_tier": "THIS_WEEK", "quantity_note": "1 kg ripe"},
            {"name": "Bell Peppers (Capsicum)", "category": "PRODUCE", "shelf_life_tier": "THIS_WEEK", "quantity_note": "2 red & green"},
            {"name": "Garlic & Ginger Root", "category": "PRODUCE", "shelf_life_tier": "THIS_WEEK", "quantity_note": "100g each"},
            {"name": "Aged Basmati Rice", "category": "PANTRY_STAPLE", "shelf_life_tier": "STAPLE", "quantity_note": "5 kg bag"},
            {"name": "Dark Soy Sauce & Vinegar", "category": "BAKING", "shelf_life_tier": "STAPLE", "quantity_note": "1 bottle each"},
            {"name": "Penne Pasta & Olive Oil", "category": "PANTRY_STAPLE", "shelf_life_tier": "STAPLE", "quantity_note": "Pantry staple"},
        ]

    lines = [line.strip("-*• 0123456789.₹$£€\t") for line in text.splitlines() if line.strip()]
    extracted = []
    
    category_keywords = {
        'MEAT': ['chicken', 'mutton', 'lamb', 'fish', 'prawn', 'egg', 'eggs', 'murgh'],
        'DAIRY': ['paneer', 'dahi', 'curd', 'ghee', 'milk', 'cream', 'butter', 'cheese', 'mozzarella', 'parmesan'],
        'PRODUCE': ['palak', 'spinach', 'tamatar', 'tomato', 'pyaz', 'onion', 'aloo', 'potato', 'gobi', 'cauliflower', 'bhindi', 'capsicum', 'pepper', 'dhaniya', 'coriander', 'mirch', 'chilli', 'adrak', 'ginger', 'garlic', 'lahsun', 'mushroom', 'spring onion'],
        'FROZEN': ['frozen peas', 'frozen matar', 'frozen corn', 'frozen paratha'],
        'CANNED': ['pickle', 'achar', 'chutney', 'crushed tomato', 'chickpeas', 'corn can'],
        'BAKING': ['haldi', 'turmeric', 'jeera', 'cumin', 'rai', 'mustard', 'garam masala', 'kashmiri mirch', 'kasuri methi', 'hing', 'soy sauce', 'chilli sauce', 'oregano', 'chilli flakes'],
        'PANTRY_STAPLE': ['atta', 'dal', 'rice', 'basmati', 'noodles', 'pasta', 'penne', 'spaghetti', 'poha', 'olive oil', 'sesame oil', 'salt']
    }

    urgent_keywords = ['paneer', 'palak', 'spinach', 'coriander', 'dhaniya', 'curd', 'dahi', 'chicken', 'fish', 'milk', 'cream', 'mushroom']

    for line in lines:
        if len(line) < 2 or line.lower().startswith(('total', 'tax', 'subtotal', 'cash', 'change', 'upi', 'gpay', 'paytm', 'thank')):
            continue

        lower = line.lower()
        matched_category = 'PANTRY_STAPLE'
        for cat, kws in category_keywords.items():
            if any(kw in lower for kw in kws):
                matched_category = cat
                break
        
        tier = 'STAPLE'
        if matched_category in ['PRODUCE', 'DAIRY', 'MEAT']:
            tier = 'THIS_WEEK'
        if any(uk in lower for uk in urgent_keywords):
            tier = 'URGENT'

        clean_name = line.split("₹")[0].split("$")[0].split(" x ")[0].strip().title()
        extracted.append({
            "name": clean_name,
            "category": matched_category,
            "shelf_life_tier": tier,
            "quantity_note": "1 unit"
        })

    return extracted if extracted else [
        {"name": "Fresh Malai Paneer", "category": "DAIRY", "shelf_life_tier": "URGENT", "quantity_note": "200g"},
        {"name": "Desi Palak (Spinach)", "category": "PRODUCE", "shelf_life_tier": "URGENT", "quantity_note": "1 bunch"},
        {"name": "Basmati Rice & Soy Sauce", "category": "PANTRY_STAPLE", "shelf_life_tier": "STAPLE", "quantity_note": "Staple pantry"}
    ]


def suggest_recipes(pantry_items: List[Dict[str, Any]], profile: Optional[Any] = None) -> List[Dict[str, Any]]:
    """
    Generates 4 vibrant visual recipes giving user daily options:
    - Card 1: 🇮🇳 Indian Zero-Waste (e.g. Dhabewala Palak Paneer or Dal Tadka)
    - Card 2: 🥢 Pan-Asian Zero-Waste (e.g. Crispy Indo-Chinese Chilli Paneer & Fried Rice)
    - Card 3: 🍝 Continental Zero-Waste (e.g. Creamy Garlic Butter Spinach & Cheese Skillet)
    - Card 4: 👑 Elevated Fusion Feast (with 1-2 missing flair ingredients)
    """
    model = get_gemini_client()

    urgent_names = [p['name'] for p in pantry_items if p.get('shelf_life_tier') == 'URGENT']
    this_week_names = [p['name'] for p in pantry_items if p.get('shelf_life_tier') == 'THIS_WEEK']
    staple_names = [p['name'] for p in pantry_items if p.get('shelf_life_tier') == 'STAPLE']

    servings = profile.default_servings if profile else 2

    if model:
        prompt = f"""
You are PantryZero's Global Executive Chef specializing in Indian, Pan-Asian, and Continental cuisines.
Given the user's available pantry ingredients, generate EXACTLY 4 visual recipes:
- Recipe 1 MUST be 🇮🇳 INDIAN CUISINE (100% Zero-Waste, missing_ingredients: []).
- Recipe 2 MUST be 🥢 PAN-ASIAN / INDO-CHINESE CUISINE (100% Zero-Waste, missing_ingredients: []). e.g., wok-tossed fried rice, crispy chilli paneer/tofu, hakka noodles, or ginger garlic stir fry.
- Recipe 3 MUST be 🍝 CONTINENTAL / MEDITERRANEAN CUISINE (100% Zero-Waste, missing_ingredients: []). e.g., creamy garlic butter pasta/skillet, sautéed mushroom florentine, or herb roasted skillet.
- Recipe 4 MUST be an ELEVATED FEAST (uses in-stock items + 1-2 missing ingredients listed in 'missing_ingredients').

User's Urgent Items: {urgent_names}
User's Fresh Items: {this_week_names}
User's Staples: {staple_names}
Servings: {servings}

For each recipe, provide:
- "title": Appetizing recipe title
- "description": 2-sentence description
- "cuisine": "North Indian", "Indo-Chinese Pan-Asian", "Italian Continental", etc.
- "cuisine_category": EXACTLY one of ["INDIAN", "PAN_ASIAN", "CONTINENTAL"]
- "spice_level": e.g. "Medium Desi Spicy 🌶️", "Szechuan Zesty 🥢", "Mild & Creamy 🌿"
- "image_url": A direct high-resolution food photo URL from Unsplash
- "prep_time_minutes", "cook_time_minutes", "servings": {servings}
- "appliances_used": list of appliances
- "ingredients": array of {{"item": "...", "amount": "...", "is_staple": bool, "in_pantry": bool}}
- "instructions": array of {{"step_number": 1, "text": "...", "timer_minutes": int, "icon": "🔪|🍳|🍲|♨️|🍽️"}}
- "missing_ingredients": array of strings (empty for cards 1, 2, 3)

Return ONLY a valid JSON array of 4 objects.
"""
        try:
            response = model.generate_content(prompt)
            clean_text = response.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]

            data = json.loads(clean_text.strip())
            if isinstance(data, list) and len(data) >= 3:
                return data
        except Exception as e:
            logger.error(f"Gemini global recipe generation failed, falling back: {e}")

    # Fallback smart multi-cuisine recipes
    return _generate_smart_multicuisine_recipes(pantry_items, profile)


def _generate_smart_multicuisine_recipes(pantry_items: List[Dict[str, Any]], profile: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Generates 4 rich, visual recipes covering Indian, Pan-Asian, and Continental options."""
    names = [p['name'].lower() for p in pantry_items]
    servings = profile.default_servings if profile else 2

    has_paneer = any("paneer" in n for n in names)
    has_chicken = any("chicken" in n or "murgh" in n for n in names)
    has_palak = any("palak" in n or "spinach" in n for n in names)
    has_dal = any("dal" in n for n in names)
    has_rice = any("rice" in n or "basmati" in n for n in names)
    has_capsicum = any("shimla" in n or "capsicum" in n or "pepper" in n for n in names)

    # -------------------------------------------------------------
    # 1. 🇮🇳 INDIAN ZERO-WASTE
    # -------------------------------------------------------------
    recipe_indian = {
        "title": "Dhabewala Lasooni Palak Paneer with Desi Ghee Tadka",
        "description": "Luscious velvety spinach gravy tempered with golden garlic and cumin, folding in soft paneer cubes to rescue wilting palak.",
        "prep_time_minutes": 10,
        "cook_time_minutes": 15,
        "servings": servings,
        "cuisine": "North Indian Dhaba Style",
        "cuisine_category": "INDIAN",
        "spice_level": "Medium Desi Spicy 🌶️",
        "image_url": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=800&q=80",
        "appliances_used": ["Kadai (Deep Wok)", "Mixer-Grinder (Mixie)", "Stovetop"],
        "ingredients": [
            {"item": "Fresh Malai Paneer", "amount": "200g soft cubes", "is_staple": False, "in_pantry": True},
            {"item": "Desi Palak (Spinach)", "amount": "1 big bunch washed", "is_staple": False, "in_pantry": True},
            {"item": "Desi Tamatar & Pyaz", "amount": "1 onion, 2 ripe tomatoes", "is_staple": False, "in_pantry": True},
            {"item": "Garlic (Lahsun) & Green Chillies", "amount": "8 cloves chopped, 2 green chillies", "is_staple": True, "in_pantry": True},
            {"item": "Desi Ghee & Jeera", "amount": "1.5 tbsp ghee, 1 tsp cumin", "is_staple": True, "in_pantry": True},
        ],
        "instructions": [
            {"step_number": 1, "text": "Blanch washed spinach in boiling water for 2 mins, plunge into cold water, and puree with green chillies in mixer.", "timer_minutes": 3, "icon": "🔪"},
            {"step_number": 2, "text": "Heat 1 tbsp desi ghee in a kadai. Sauté half the minced garlic and jeera until nutty and golden.", "timer_minutes": 2, "icon": "🍳"},
            {"step_number": 3, "text": "Add finely diced onions and tomatoes; cook down with haldi, dhaniya powder, and salt until thick and aromatic.", "timer_minutes": 5, "icon": "🍲"},
            {"step_number": 4, "text": "Pour in pureed palak and simmer gently on low heat for 4 minutes to marry flavors.", "timer_minutes": 4, "icon": "🍲"},
            {"step_number": 5, "text": "Gently fold in fresh paneer cubes and crown with a sizzling golden garlic-ghee tadka on top.", "timer_minutes": 1, "icon": "🍽️"},
        ],
        "missing_ingredients": []
    }

    # -------------------------------------------------------------
    # 2. 🥢 PAN-ASIAN ZERO-WASTE
    # -------------------------------------------------------------
    recipe_pan_asian = {
        "title": "Crispy Wok-Tossed Chilli Paneer & Garlic Fried Rice",
        "description": "Golden seared paneer cubes tossed in a high-heat wok with crunchy bell peppers, dark soy sauce, and aromatic garlic fried rice.",
        "prep_time_minutes": 10,
        "cook_time_minutes": 12,
        "servings": servings,
        "cuisine": "Indo-Chinese Pan-Asian",
        "cuisine_category": "PAN_ASIAN",
        "spice_level": "Zesty Szechuan Kick 🥢",
        "image_url": "https://images.unsplash.com/photo-1541696432-82c6da8ce7bf?auto=format&fit=crop&w=800&q=80",
        "appliances_used": ["Kadai / Wok", "Stovetop"],
        "ingredients": [
            {"item": "Fresh Malai Paneer", "amount": "200g cubed", "is_staple": False, "in_pantry": True},
            {"item": "Shimla Mirch (Bell Peppers)", "amount": "1 diced crunchy", "is_staple": False, "in_pantry": True},
            {"item": "Cooked Basmati / Rice", "amount": "2 cups chilled grains", "is_staple": True, "in_pantry": True},
            {"item": "Garlic, Ginger & Green Chillies", "amount": "2 tbsp finely minced", "is_staple": True, "in_pantry": True},
            {"item": "Dark Soy Sauce & Vinegar", "amount": "1.5 tbsp soy, 1 tsp vinegar", "is_staple": True, "in_pantry": True},
            {"item": "Cooking Oil / Sesame", "amount": "1.5 tbsp", "is_staple": True, "in_pantry": True},
        ],
        "instructions": [
            {"step_number": 1, "text": "Shallow fry paneer cubes in 1 tbsp oil over high heat until edges turn crisp and golden.", "timer_minutes": 4, "icon": "🍳"},
            {"step_number": 2, "text": "In the same sizzling wok, flash-fry minced garlic, ginger, and diced bell peppers for 2 minutes to keep them crunchy.", "timer_minutes": 2, "icon": "🍳"},
            {"step_number": 3, "text": "Splash in soy sauce, vinegar, chilli flakes, and salt. Toss the golden paneer cubes until coated with a savory glossy glaze.", "timer_minutes": 2, "icon": "🍲"},
            {"step_number": 4, "text": "Toss chilled rice into the wok with garlic and a touch of soy sauce over high flame for smokey wok-hei flavor.", "timer_minutes": 3, "icon": "🍳"},
            {"step_number": 5, "text": "Plate sizzling chilli paneer alongside steaming garlic fried rice and garnish with spring greens.", "timer_minutes": 1, "icon": "🍽️"},
        ],
        "missing_ingredients": []
    }

    # -------------------------------------------------------------
    # 3. 🍝 CONTINENTAL ZERO-WASTE
    # -------------------------------------------------------------
    recipe_continental = {
        "title": "Creamy Tuscan Garlic Butter Spinach & Cheese Skillet",
        "description": "Rich Italian-bistro skillet pairing wilted baby greens with garlic-infused butter, simmering tomatoes, and tender melted cheese.",
        "prep_time_minutes": 8,
        "cook_time_minutes": 12,
        "servings": servings,
        "cuisine": "Italian Continental",
        "cuisine_category": "CONTINENTAL",
        "spice_level": "Herb Fragrant & Mild 🌿",
        "image_url": "https://images.unsplash.com/photo-1621996346565-e3d5d6281292?auto=format&fit=crop&w=800&q=80",
        "appliances_used": ["Kadai (Deep Wok)", "Stovetop"],
        "ingredients": [
            {"item": "Desi Palak (Spinach)", "amount": "2 hearty handfuls", "is_staple": False, "in_pantry": True},
            {"item": "Fresh Paneer or Cheese", "amount": "150g cubed", "is_staple": False, "in_pantry": True},
            {"item": "Desi Tamatar (Tomatoes)", "amount": "2 diced", "is_staple": False, "in_pantry": True},
            {"item": "Garlic Cloves & Butter/Olive Oil", "amount": "5 cloves minced, 2 tbsp butter", "is_staple": True, "in_pantry": True},
            {"item": "Sea Salt & Black Pepper / Oregano", "amount": "To taste", "is_staple": True, "in_pantry": True},
        ],
        "instructions": [
            {"step_number": 1, "text": "Melt butter in skillet over medium heat. Sauté minced garlic until golden and intensely fragrant.", "timer_minutes": 2, "icon": "🍳"},
            {"step_number": 2, "text": "Add diced tomatoes, oregano, salt, and freshly cracked black pepper; simmer until tomatoes break down into a rustic sauce.", "timer_minutes": 4, "icon": "🍲"},
            {"step_number": 3, "text": "Fold in washed spinach leaves and cook gently until wilted into the savory butter emulsion.", "timer_minutes": 3, "icon": "🍲"},
            {"step_number": 4, "text": "Add paneer/cheese cubes and cover for 2 minutes to allow the cheese to soften and soak up the garlic herb sauce.", "timer_minutes": 2, "icon": "♨️"},
            {"step_number": 5, "text": "Drizzle with extra virgin olive oil and serve with warm bread or fluffy rice.", "timer_minutes": 1, "icon": "🍽️"},
        ],
        "missing_ingredients": []
    }

    # -------------------------------------------------------------
    # 4. 👑 ELEVATED FUSION FEAST (Requires 1-2 missing flair items)
    # -------------------------------------------------------------
    recipe_elevated = {
        "title": "Royal Shahi Makhani Curry with Kasuri Methi Glaze",
        "description": "A regal restaurant-style makhani feast using in-stock paneer and tomatoes, elevated with silky cream and toasted cashews.",
        "prep_time_minutes": 12,
        "cook_time_minutes": 18,
        "servings": servings,
        "cuisine": "Royal Mughlai / North Indian",
        "cuisine_category": "INDIAN",
        "spice_level": "Rich & Mildly Sweet 👑",
        "image_url": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=800&q=80",
        "appliances_used": ["Kadai (Deep Wok)", "Mixer-Grinder (Mixie)", "Stovetop"],
        "ingredients": [
            {"item": "Fresh Malai Paneer", "amount": "250g thick triangles", "is_staple": False, "in_pantry": True},
            {"item": "Desi Tamatar & Pyaz", "amount": "4 ripe tomatoes, 1 onion", "is_staple": False, "in_pantry": True},
            {"item": "Adrak-Lahsun (Ginger-Garlic)", "amount": "1 tbsp freshly minced", "is_staple": True, "in_pantry": True},
            {"item": "Desi Ghee & Butter", "amount": "2 tbsp each", "is_staple": True, "in_pantry": True},
            {"item": "Kaju (Cashew Nuts)", "amount": "10 whole cashews soaked", "is_staple": False, "in_pantry": False},
            {"item": "Kasuri Methi (Dried Fenugreek)", "amount": "1 tbsp toasted", "is_staple": False, "in_pantry": False},
        ],
        "instructions": [
            {"step_number": 1, "text": "Roughly chop tomatoes and onions; boil in 1/2 cup water with cashews and cardamom for 6 minutes, then blend into a silky orange makhani paste.", "timer_minutes": 6, "icon": "🔪"},
            {"step_number": 2, "text": "Melt butter and ghee in kadai. Strain makhani gravy directly into the sizzling pan for that signature mirror-gloss shine.", "timer_minutes": 2, "icon": "🍳"},
            {"step_number": 3, "text": "Add Kashmiri lal mirch for vibrant crimson hue, honey pinch, salt, and simmer until luscious and bubbling.", "timer_minutes": 5, "icon": "🍲"},
            {"step_number": 4, "text": "Gently slide in fresh paneer triangles and let them absorb the rich royal gravy on low flame.", "timer_minutes": 3, "icon": "🍲"},
            {"step_number": 5, "text": "Crush fragrant kasuri methi between palms over the curry and finish with a swirl of fresh cream before plating.", "timer_minutes": 2, "icon": "🍽️"},
        ],
        "missing_ingredients": ["10 Cashew Nuts (Kaju)", "1 tbsp Kasuri Methi"]
    }

    return [recipe_indian, recipe_pan_asian, recipe_continental, recipe_elevated]
