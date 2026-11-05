import json
from django.test import TestCase, Client
from django.urls import reverse
from pantry.models import HouseholdProfile, PantryItem, Recipe, MealQueueItem, ShoppingItem
from services import ai_service


class PantryModelTests(TestCase):
    def test_household_profile_get_solo(self):
        profile = HouseholdProfile.get_solo()
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "Spice & Wok Kitchen")
        self.assertIn("North Indian", profile.dietary_preferences)
        self.assertIn("Pan-Asian", profile.dietary_preferences)

    def test_pantry_item_badge_colors(self):
        urgent_item = PantryItem.objects.create(
            name="Fresh Chicken",
            category="MEAT",
            shelf_life_tier="URGENT"
        )
        self.assertIn("rose", urgent_item.badge_colors['badge'])
        self.assertEqual(urgent_item.category_icon, "🍗")

        fresh_item = PantryItem.objects.create(
            name="Desi Palak",
            category="PRODUCE",
            shelf_life_tier="THIS_WEEK"
        )
        self.assertIn("amber", fresh_item.badge_colors['badge'])
        self.assertEqual(fresh_item.category_icon, "🥬")

        staple_item = PantryItem.objects.create(
            name="Haldi Masala",
            category="BAKING",
            shelf_life_tier="STAPLE"
        )
        self.assertIn("emerald", staple_item.badge_colors['badge'])
        self.assertEqual(staple_item.category_icon, "🌶️")

    def test_recipe_properties(self):
        recipe_zero = Recipe.objects.create(
            title="Zero Waste Palak Paneer",
            prep_time_minutes=10,
            cook_time_minutes=20,
            servings=2,
            cuisine_category="INDIAN",
            missing_ingredients=[]
        )
        self.assertEqual(recipe_zero.total_time_minutes, 30)
        self.assertTrue(recipe_zero.is_zero_waste)
        self.assertEqual(recipe_zero.missing_count, 0)
        self.assertEqual(recipe_zero.cuisine_category, "INDIAN")

        recipe_asian = Recipe.objects.create(
            title="Wok Chilli Paneer",
            prep_time_minutes=10,
            cook_time_minutes=15,
            servings=2,
            cuisine_category="PAN_ASIAN",
            missing_ingredients=["Cashews"]
        )
        self.assertFalse(recipe_asian.is_zero_waste)
        self.assertEqual(recipe_asian.missing_count, 1)

    def test_shopping_item_and_meal_queue(self):
        recipe = Recipe.objects.create(
            title="Dal Tadka",
            prep_time_minutes=5,
            cook_time_minutes=10,
            servings=2
        )
        queue_item = MealQueueItem.objects.create(
            recipe=recipe,
            planned_for="TONIGHT",
            meal_slot="LUNCH"
        )
        self.assertEqual(queue_item.planned_for, "TONIGHT")
        self.assertEqual(queue_item.meal_slot, "LUNCH")
        self.assertFalse(queue_item.is_cooked)

        shopping = ShoppingItem.objects.create(
            name="Kasuri Methi",
            category="PANTRY_STAPLE",
            recipe_source=recipe
        )
        self.assertFalse(shopping.is_bought)
        self.assertEqual(shopping.recipe_source, recipe)


class AIServiceTests(TestCase):
    def test_parse_grocery_text_fallback(self):
        raw_text = """
        - Fresh Malai Paneer 200g
        - Desi Palak 1 bunch
        - Organic Toor Dal 1kg
        - Dark Soy Sauce 1 bottle
        """
        parsed = ai_service.parse_grocery_text_or_receipt(text=raw_text)
        self.assertTrue(len(parsed) >= 3)
        names = [item['name'].lower() for item in parsed]
        self.assertTrue(any("paneer" in n for n in names))
        self.assertTrue(any("palak" in n for n in names))

    def test_suggest_recipes_fallback_structure(self):
        pantry_data = [
            {"name": "Fresh Malai Paneer", "shelf_life_tier": "URGENT", "category": "DAIRY"},
            {"name": "Desi Palak (Spinach)", "shelf_life_tier": "URGENT", "category": "PRODUCE"},
            {"name": "Toor Dal", "shelf_life_tier": "STAPLE", "category": "PANTRY_STAPLE"},
            {"name": "Basmati Rice", "shelf_life_tier": "STAPLE", "category": "PANTRY_STAPLE"},
        ]
        profile = HouseholdProfile.get_solo()
        recipes = ai_service.suggest_recipes(pantry_data, profile)

        # Must return 4 multi-cuisine recipes
        self.assertEqual(len(recipes), 4)

        # Indian, Pan-Asian, Continental are 100% Zero-Waste
        self.assertEqual(len(recipes[0]['missing_ingredients']), 0)
        self.assertEqual(len(recipes[1]['missing_ingredients']), 0)
        self.assertEqual(len(recipes[2]['missing_ingredients']), 0)

        # Elevated recipe has missing ingredients
        self.assertTrue(len(recipes[3]['missing_ingredients']) > 0)
        self.assertTrue(recipes[0]['image_url'].startswith("http"))


class PantryViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.profile = HouseholdProfile.get_solo()
        self.pantry_item = PantryItem.objects.create(
            name="Desi Palak",
            category="PRODUCE",
            shelf_life_tier="URGENT",
            quantity_note="1 bunch"
        )
        self.recipe = Recipe.objects.create(
            title="Dhabewala Palak Paneer",
            prep_time_minutes=5,
            cook_time_minutes=15,
            servings=2,
            ingredients=[{"item": "Desi Palak", "amount": "1 bunch", "is_staple": False, "in_pantry": True}],
            instructions=[{"step_number": 1, "text": "Blanch palak in boiling water", "timer_minutes": 2, "icon": "🔪"}],
            missing_ingredients=[]
        )

    def test_pantry_list_view(self):
        response = self.client.get(reverse('pantry_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Desi Palak")
        self.assertContains(response, "Kitchen Inventory")

    def test_pantry_add_item(self):
        response = self.client.post(reverse('pantry_add'), {
            'name': 'Fresh Malai Paneer',
            'category': 'DAIRY',
            'shelf_life_tier': 'URGENT',
            'quantity_note': '200g'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PantryItem.objects.filter(name='Fresh Malai Paneer').exists())

    def test_pantry_delete_item(self):
        response = self.client.post(reverse('pantry_delete', args=[self.pantry_item.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(PantryItem.objects.filter(id=self.pantry_item.id).exists())

    def test_recipe_suggest_view(self):
        response = self.client.get(reverse('recipe_suggest'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Smart Daily Recipes')
        self.assertContains(response, 'Indian Desi Rasoi')
        self.assertContains(response, 'Pan-Asian')

    def test_recipe_cook_view(self):
        response = self.client.get(reverse('recipe_cook', args=[self.recipe.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dhabewala Palak Paneer")
        self.assertContains(response, "Distraction-Free Rasoi")

    def test_planner_view(self):
        response = self.client.get(reverse('planner_view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2 Meals Per Day Planner")
        self.assertContains(response, "Lunch")
        self.assertContains(response, "Dinner")

    def test_shopping_toggle(self):
        shop_item = ShoppingItem.objects.create(name="Kasuri Methi", category="PANTRY_STAPLE")
        response = self.client.post(reverse('shopping_toggle', args=[shop_item.id]))
        self.assertEqual(response.status_code, 302)
        shop_item.refresh_from_db()
        self.assertTrue(shop_item.is_bought)

    def test_move_bought_to_pantry(self):
        shop_item = ShoppingItem.objects.create(name="Hari Mirch", category="PRODUCE", is_bought=True)
        response = self.client.post(reverse('shopping_move_bought_to_pantry'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ShoppingItem.objects.filter(id=shop_item.id).exists())
        self.assertTrue(PantryItem.objects.filter(name="Hari Mirch").exists())

    def test_pwa_manifest_and_sw(self):
        res_manifest = self.client.get('/manifest.json')
        self.assertEqual(res_manifest.status_code, 200)
        self.assertIn('application/manifest+json', res_manifest['Content-Type'])
        self.assertIn("What's cooking today?", res_manifest.content.decode())

        res_sw = self.client.get('/sw.js')
        self.assertEqual(res_sw.status_code, 200)
        self.assertEqual(res_sw['Service-Worker-Allowed'], '/')
        self.assertIn('application/javascript', res_sw['Content-Type'])
