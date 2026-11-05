from django.core.management.base import BaseCommand
from pantry.models import HouseholdProfile, PantryItem, Recipe, MealQueueItem, ShoppingItem


class Command(BaseCommand):
    help = "Seeds realistic multi-cuisine (Indian, Pan-Asian & Continental) pantry, 2 meals/day planner, and visual dishes"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Clearing existing data..."))
        MealQueueItem.objects.all().delete()
        ShoppingItem.objects.all().delete()
        Recipe.objects.all().delete()
        PantryItem.objects.all().delete()
        HouseholdProfile.objects.all().delete()

        self.stdout.write(self.style.NOTICE("Seeding Household Profile..."))
        profile = HouseholdProfile.objects.create(
            id=1,
            name="Spice & Wok Kitchen",
            dietary_preferences=["North Indian", "Pan-Asian", "Continental & Italian", "High-Protein Vegetarian"],
            disliked_ingredients="karela, excessive oil",
            available_appliances=[
                "Pressure Cooker",
                "Kadai / Wok",
                "Tawa (Flat Griddle)",
                "Mixer-Grinder (Mixie)",
                "Stovetop",
                "Air Fryer"
            ],
            default_servings=2
        )

        self.stdout.write(self.style.NOTICE("Seeding Multi-Cuisine Pantry Items..."))
        pantry_seed_data = [
            # 3 URGENT items (Perishable - बना लो जल्दी)
            {
                "name": "Desi Palak (Spinach)",
                "category": "PRODUCE",
                "shelf_life_tier": "URGENT",
                "quantity_note": "1 big bunch - wilting fast! बना लो"
            },
            {
                "name": "Fresh Malai Paneer",
                "category": "DAIRY",
                "shelf_life_tier": "URGENT",
                "quantity_note": "200g soft pack - use in 24 hrs"
            },
            {
                "name": "Fresh Dhaniya & Spring Onion",
                "category": "PRODUCE",
                "shelf_life_tier": "URGENT",
                "quantity_note": "1 bunch herbs - use soon"
            },
            # THIS_WEEK items
            {
                "name": "Desi Tamatar (Tomatoes)",
                "category": "PRODUCE",
                "shelf_life_tier": "THIS_WEEK",
                "quantity_note": "4 ripe juicy red tomatoes"
            },
            {
                "name": "Red Pyaz (Onions)",
                "category": "PRODUCE",
                "shelf_life_tier": "THIS_WEEK",
                "quantity_note": "1 kg fresh pink onions"
            },
            {
                "name": "Green Chillies & Ginger (Adrak)",
                "category": "PRODUCE",
                "shelf_life_tier": "THIS_WEEK",
                "quantity_note": "100g spicy hari mirch & root"
            },
            {
                "name": "Shimla Mirch (Green & Red Peppers)",
                "category": "PRODUCE",
                "shelf_life_tier": "THIS_WEEK",
                "quantity_note": "2 crunchy bell peppers"
            },
            {
                "name": "Button Mushrooms",
                "category": "PRODUCE",
                "shelf_life_tier": "THIS_WEEK",
                "quantity_note": "1 basket fresh"
            },
            {
                "name": "Fresh Dahi (Thick Curd)",
                "category": "DAIRY",
                "shelf_life_tier": "THIS_WEEK",
                "quantity_note": "400g tub"
            },
            # STAPLES (Indian, Pan-Asian & Continental)
            {
                "name": "Aged Basmati Rice",
                "category": "PANTRY_STAPLE",
                "shelf_life_tier": "STAPLE",
                "quantity_note": "5 kg long grain"
            },
            {
                "name": "Organic Toor Dal",
                "category": "PANTRY_STAPLE",
                "shelf_life_tier": "STAPLE",
                "quantity_note": "1 kg unpolished packet"
            },
            {
                "name": "Penne Pasta / Hakka Noodles",
                "category": "PANTRY_STAPLE",
                "shelf_life_tier": "STAPLE",
                "quantity_note": "1 pack dry pasta"
            },
            {
                "name": "Dark Soy Sauce & Chilli Sauce",
                "category": "BAKING",
                "shelf_life_tier": "STAPLE",
                "quantity_note": "Asian sauce bottles"
            },
            {
                "name": "Pure Desi Ghee & Extra Virgin Olive Oil",
                "category": "DAIRY",
                "shelf_life_tier": "STAPLE",
                "quantity_note": "Cooking fats jar"
            },
            {
                "name": "Masala Dabba & Italian Herbs (Oregano/Jeera)",
                "category": "BAKING",
                "shelf_life_tier": "STAPLE",
                "quantity_note": "Spices & herb blends"
            },
        ]

        for item in pantry_seed_data:
            PantryItem.objects.create(**item)

        self.stdout.write(self.style.NOTICE("Seeding Indian, Pan-Asian & Continental Visual Recipes..."))
        
        # Recipe 1: 🇮🇳 Indian (Lunch Favorite)
        r_indian_dal = Recipe.objects.create(
            title="Homestyle Dal Tadka with Jeera Ghee Sizzle & Steamed Basmati",
            description="Soul-satisfying homestyle toor dal cooked to velvety perfection, drenched with a sizzling crackle of cumin, mustard, and hing.",
            prep_time_minutes=8,
            cook_time_minutes=14,
            servings=2,
            cuisine="Homestyle Indian Comfort",
            cuisine_category="INDIAN",
            spice_level="Homestyle Mild-Medium 🌶️",
            image_url="https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80",
            appliances_used=["Pressure Cooker", "Kadai (Deep Wok)", "Stovetop"],
            ingredients=[
                {"item": "Toor / Moong Dal", "amount": "1 cup washed", "is_staple": True, "in_pantry": True},
                {"item": "Aged Basmati Rice", "amount": "1.5 cups aged grains", "is_staple": True, "in_pantry": True},
                {"item": "Desi Tamatar & Hari Mirch", "amount": "2 tomatoes, 2 slit chillies", "is_staple": False, "in_pantry": True},
                {"item": "Jeera, Rai & Hing", "amount": "1 tsp cumin, 1/2 tsp mustard seeds", "is_staple": True, "in_pantry": True},
                {"item": "Desi Ghee & Fresh Dhaniya", "amount": "1.5 tbsp ghee, handful coriander", "is_staple": True, "in_pantry": True},
            ],
            instructions=[
                {"step_number": 1, "text": "Pressure cook toor dal with 3 cups water, 1/2 tsp haldi, and salt for 3 whistles until melt-in-mouth soft.", "timer_minutes": 8, "icon": "♨️"},
                {"step_number": 2, "text": "Wash basmati rice and cook with 2.5 cups water until fragrant, fluffy and separated.", "timer_minutes": 10, "icon": "♨️"},
                {"step_number": 3, "text": "Whisk cooked dal lightly to create a smooth, velvety consistency.", "timer_minutes": 1, "icon": "🍲"},
                {"step_number": 4, "text": "Prepare the iconic tadka: heat desi ghee in a tadka pan, crackle jeera, rai, hing, garlic, and dried red chilli.", "timer_minutes": 2, "icon": "🍳"},
                {"step_number": 5, "text": "Pour the sizzling ghee tadka over the dal with a dramatic hiss! Garnish with fresh dhaniya and serve hot over rice.", "timer_minutes": 1, "icon": "🍽️"},
            ],
            missing_ingredients=[],
            is_favorite=True
        )

        # Recipe 2: 🥢 Pan-Asian (Dinner Favorite)
        r_pan_asian = Recipe.objects.create(
            title="Crispy Wok-Tossed Chilli Paneer & Garlic Fried Rice",
            description="Golden seared paneer cubes tossed in a high-heat wok with crunchy bell peppers, dark soy sauce, and aromatic garlic fried rice.",
            prep_time_minutes=10,
            cook_time_minutes=12,
            servings=2,
            cuisine="Indo-Chinese Pan-Asian",
            cuisine_category="PAN_ASIAN",
            spice_level="Zesty Szechuan Kick 🥢",
            image_url="https://images.unsplash.com/photo-1541696432-82c6da8ce7bf?auto=format&fit=crop&w=800&q=80",
            appliances_used=["Kadai / Wok", "Stovetop"],
            ingredients=[
                {"item": "Fresh Malai Paneer", "amount": "200g cubed", "is_staple": False, "in_pantry": True},
                {"item": "Shimla Mirch (Bell Peppers)", "amount": "1 diced crunchy", "is_staple": False, "in_pantry": True},
                {"item": "Cooked Basmati / Rice", "amount": "2 cups chilled grains", "is_staple": True, "in_pantry": True},
                {"item": "Garlic, Ginger & Green Chillies", "amount": "2 tbsp finely minced", "is_staple": True, "in_pantry": True},
                {"item": "Dark Soy Sauce & Vinegar", "amount": "1.5 tbsp soy, 1 tsp vinegar", "is_staple": True, "in_pantry": True},
            ],
            instructions=[
                {"step_number": 1, "text": "Shallow fry paneer cubes in 1 tbsp oil over high heat until edges turn crisp and golden.", "timer_minutes": 4, "icon": "🍳"},
                {"step_number": 2, "text": "In the same sizzling wok, flash-fry minced garlic, ginger, and diced bell peppers for 2 minutes to keep them crunchy.", "timer_minutes": 2, "icon": "🍳"},
                {"step_number": 3, "text": "Splash in soy sauce, vinegar, chilli flakes, and salt. Toss the golden paneer cubes until coated with a savory glossy glaze.", "timer_minutes": 2, "icon": "🍲"},
                {"step_number": 4, "text": "Toss chilled rice into the wok with garlic and a touch of soy sauce over high flame for smokey wok-hei flavor.", "timer_minutes": 3, "icon": "🍳"},
                {"step_number": 5, "text": "Plate sizzling chilli paneer alongside steaming garlic fried rice and garnish with spring greens.", "timer_minutes": 1, "icon": "🍽️"},
            ],
            missing_ingredients=[],
            is_favorite=True
        )

        # Recipe 3: 🇮🇳 Indian (Palak Paneer)
        r_indian_palak = Recipe.objects.create(
            title="Dhabewala Lasooni Palak Paneer with Desi Ghee Tadka",
            description="Luscious velvety spinach gravy tempered with golden garlic and cumin, folding in soft paneer cubes to rescue wilting palak.",
            prep_time_minutes=10,
            cook_time_minutes=15,
            servings=2,
            cuisine="North Indian Dhaba Style",
            cuisine_category="INDIAN",
            spice_level="Medium Desi Spicy 🌶️",
            image_url="https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=800&q=80",
            appliances_used=["Kadai (Deep Wok)", "Mixer-Grinder (Mixie)", "Stovetop"],
            ingredients=[
                {"item": "Fresh Malai Paneer", "amount": "200g soft cubes", "is_staple": False, "in_pantry": True},
                {"item": "Desi Palak (Spinach)", "amount": "1 big bunch washed", "is_staple": False, "in_pantry": True},
                {"item": "Desi Tamatar & Pyaz", "amount": "1 onion, 2 ripe tomatoes", "is_staple": False, "in_pantry": True},
                {"item": "Garlic (Lahsun) & Green Chillies", "amount": "8 cloves chopped", "is_staple": True, "in_pantry": True},
                {"item": "Desi Ghee & Jeera", "amount": "1.5 tbsp ghee, 1 tsp cumin", "is_staple": True, "in_pantry": True},
            ],
            instructions=[
                {"step_number": 1, "text": "Blanch washed spinach in boiling water for 2 minutes, plunge into ice-cold water, and blitz to a silky puree with green chillies in mixer.", "timer_minutes": 3, "icon": "🔪"},
                {"step_number": 2, "text": "Heat 1 tbsp desi ghee in a kadai. Sauté minced garlic and jeera until nutty and golden.", "timer_minutes": 2, "icon": "🍳"},
                {"step_number": 3, "text": "Add finely diced onions and tomatoes; cook down with haldi, dhaniya powder, and salt until thick and aromatic.", "timer_minutes": 5, "icon": "🍲"},
                {"step_number": 4, "text": "Pour in pureed palak and simmer gently on low heat for 4 minutes to marry flavors.", "timer_minutes": 4, "icon": "🍲"},
                {"step_number": 5, "text": "Gently fold in fresh paneer cubes and crown with a sizzling golden garlic-ghee tadka on top before serving.", "timer_minutes": 1, "icon": "🍽️"},
            ],
            missing_ingredients=[],
            is_favorite=True
        )

        # Recipe 4: 🍝 Continental (Italian Bistro)
        r_continental = Recipe.objects.create(
            title="Creamy Tuscan Garlic Butter Spinach & Mushroom Skillet",
            description="Rich Italian-bistro skillet pairing wilted baby greens with garlic-infused butter, sautéed mushrooms, and tender melted cheese.",
            prep_time_minutes=8,
            cook_time_minutes=12,
            servings=2,
            cuisine="Italian Continental",
            cuisine_category="CONTINENTAL",
            spice_level="Herb Fragrant & Mild 🌿",
            image_url="https://images.unsplash.com/photo-1621996346565-e3d5d6281292?auto=format&fit=crop&w=800&q=80",
            appliances_used=["Kadai (Deep Wok)", "Stovetop"],
            ingredients=[
                {"item": "Desi Palak (Spinach)", "amount": "2 hearty handfuls", "is_staple": False, "in_pantry": True},
                {"item": "Button Mushrooms", "amount": "1 cup sliced", "is_staple": False, "in_pantry": True},
                {"item": "Fresh Paneer / Cheese", "amount": "150g cubed", "is_staple": False, "in_pantry": True},
                {"item": "Garlic Cloves & Butter/Olive Oil", "amount": "5 cloves minced, 2 tbsp butter", "is_staple": True, "in_pantry": True},
                {"item": "Sea Salt & Black Pepper / Oregano", "amount": "To taste", "is_staple": True, "in_pantry": True},
            ],
            instructions=[
                {"step_number": 1, "text": "Melt butter in skillet over medium heat. Sauté minced garlic until golden and intensely fragrant.", "timer_minutes": 2, "icon": "🍳"},
                {"step_number": 2, "text": "Add sliced mushrooms and cook over high heat until caramelized and golden.", "timer_minutes": 4, "icon": "🍳"},
                {"step_number": 3, "text": "Fold in washed spinach leaves and cook gently until wilted into the savory butter mushroom emulsion.", "timer_minutes": 3, "icon": "🍲"},
                {"step_number": 4, "text": "Add cheese/paneer cubes, sprinkle oregano and cracked pepper, covering for 2 minutes to soften.", "timer_minutes": 2, "icon": "♨️"},
            ],
            missing_ingredients=[],
            is_favorite=False
        )

        self.stdout.write(self.style.NOTICE("Seeding 2 Meals/Day in Rolling Meal Queue..."))
        # Day 1 (Today):
        MealQueueItem.objects.create(recipe=r_indian_dal, planned_for="TONIGHT", meal_slot="LUNCH", order=1)
        MealQueueItem.objects.create(recipe=r_pan_asian, planned_for="TONIGHT", meal_slot="DINNER", order=2)

        # Day 2 (Tomorrow):
        MealQueueItem.objects.create(recipe=r_indian_palak, planned_for="TOMORROW", meal_slot="LUNCH", order=1)
        MealQueueItem.objects.create(recipe=r_continental, planned_for="TOMORROW", meal_slot="DINNER", order=2)

        self.stdout.write(self.style.NOTICE("Seeding Multi-Cuisine Shopping List..."))
        shopping_seed = [
            {"name": "Kaju (Cashew Nuts)", "category": "PANTRY_STAPLE", "quantity_note": "100g for rich shahi gravies", "is_bought": False},
            {"name": "Kasuri Methi (Dried Fenugreek)", "category": "PANTRY_STAPLE", "quantity_note": "1 box 50g", "is_bought": False},
            {"name": "Szechuan Pepper Sauce", "category": "OTHER", "quantity_note": "1 bottle for Asian noodles", "is_bought": True},
            {"name": "Parmesan / Cheddar Block", "category": "DAIRY", "quantity_note": "1 block for Continental pasta", "is_bought": False},
        ]

        for s in shopping_seed:
            ShoppingItem.objects.create(**s)

        self.stdout.write(self.style.SUCCESS("✓ Successfully seeded 2 Meals/Day: Indian, Pan-Asian & Continental dishes ready!"))
