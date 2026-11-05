from django.db import models


class HouseholdProfile(models.Model):
    name = models.CharField(max_length=120, default="Desi & Global Rasoi")
    dietary_preferences = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of dietary tags e.g. North Indian, Pan-Asian, Continental, High-Protein, Vegetarian"
    )
    disliked_ingredients = models.TextField(
        blank=True, 
        default="karela, excessive oil",
        help_text="Comma-separated ingredients to exclude"
    )
    available_appliances = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of appliances e.g. Kadai, Wok, Pressure Cooker, Tawa, Air Fryer, Stovetop, Oven"
    )
    default_servings = models.PositiveIntegerField(default=2)

    def __str__(self):
        return self.name

    @classmethod
    def get_solo(cls):
        profile, created = cls.objects.get_or_create(
            id=1,
            defaults={
                "name": "Spice & Wok Kitchen",
                "dietary_preferences": ["North Indian", "Pan-Asian", "Continental & Italian", "High-Protein Vegetarian"],
                "disliked_ingredients": "karela, excessive oil",
                "available_appliances": [
                    "Pressure Cooker",
                    "Kadai / Wok",
                    "Tawa (Flat Griddle)",
                    "Mixer-Grinder (Mixie)",
                    "Stovetop",
                    "Air Fryer"
                ],
                "default_servings": 2,
            }
        )
        return profile

    @property
    def disliked_list(self):
        if not self.disliked_ingredients:
            return []
        return [item.strip() for item in self.disliked_ingredients.split(",") if item.strip()]


class PantryItem(models.Model):
    CATEGORY_CHOICES = [
        ('PRODUCE', 'Fresh Sabzi & Greens (Palak, Veggies, Herbs)'),
        ('DAIRY', 'Dairy & Paneer (Paneer, Dahi, Butter, Ghee, Milk)'),
        ('MEAT', 'Poultry, Meat & Seafood (Chicken, Eggs)'),
        ('PANTRY_STAPLE', 'Dals, Noodles, Pasta, Atta, Rice & Masalas'),
        ('BAKING', 'Spices, Khada Masala & Asian Sauces'),
        ('FROZEN', 'Frozen (Matar, Frozen Corn, Parathas)'),
        ('CANNED', 'Canned & Chutneys/Sauces'),
    ]

    SHELF_LIFE_CHOICES = [
        ('URGENT', 'Urgent (Use ASAP - खराब होने वाला है)'),
        ('THIS_WEEK', 'Fresh (Use This Week - ताज़ा)'),
        ('STAPLE', 'Pantry Staple (Stable - मसाला/अनाज/सॉस)'),
    ]

    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='PRODUCE')
    shelf_life_tier = models.CharField(max_length=20, choices=SHELF_LIFE_CHOICES, default='THIS_WEEK')
    quantity_note = models.CharField(max_length=100, blank=True, default="")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['shelf_life_tier', '-added_at']

    def __str__(self):
        return f"{self.name} ({self.get_shelf_life_tier_display()})"

    @property
    def badge_colors(self):
        if self.shelf_life_tier == 'URGENT':
            return {
                'badge': 'bg-rose-500/15 text-rose-600 border border-rose-300 dark:border-rose-800 dark:text-rose-300',
                'dot': 'bg-rose-500 animate-pulse',
                'label': 'Expiring Soon (जल्दी बनाएं)'
            }
        elif self.shelf_life_tier == 'THIS_WEEK':
            return {
                'badge': 'bg-amber-500/15 text-amber-600 border border-amber-300 dark:border-amber-700 dark:text-amber-300',
                'dot': 'bg-amber-500',
                'label': 'Fresh This Week (ताज़ा)'
            }
        else:
            return {
                'badge': 'bg-emerald-500/15 text-emerald-600 border border-emerald-300 dark:border-emerald-700 dark:text-emerald-300',
                'dot': 'bg-emerald-500',
                'label': 'Staple / Masala / Sauce'
            }

    @property
    def category_icon(self):
        icons = {
            'PRODUCE': '🥬',
            'DAIRY': '🧀',
            'MEAT': '🍗',
            'PANTRY_STAPLE': '🌾',
            'BAKING': '🌶️',
            'FROZEN': '🧊',
            'CANNED': '🥫',
        }
        return icons.get(self.category, '🥕')


class Recipe(models.Model):
    CUISINE_CHOICES = [
        ('INDIAN', '🇮🇳 Indian (Desi Rasoi)'),
        ('PAN_ASIAN', '🥢 Pan-Asian (Wok & Indo-Chinese)'),
        ('CONTINENTAL', '🍝 Continental & Mediterranean'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    prep_time_minutes = models.PositiveIntegerField(default=10)
    cook_time_minutes = models.PositiveIntegerField(default=20)
    servings = models.PositiveIntegerField(default=2)
    appliances_used = models.JSONField(default=list, blank=True)
    image_url = models.CharField(
        max_length=600, 
        blank=True, 
        default="", 
        help_text="Visual culinary photo URL for this dish"
    )
    cuisine = models.CharField(max_length=80, blank=True, default="North Indian")
    cuisine_category = models.CharField(max_length=30, choices=CUISINE_CHOICES, default='INDIAN')
    spice_level = models.CharField(max_length=30, blank=True, default="Medium Spicy 🌶️")
    ingredients = models.JSONField(
        default=list, 
        blank=True,
        help_text='[{"item": "Paneer", "amount": "200g", "is_staple": false, "in_pantry": true}]'
    )
    instructions = models.JSONField(
        default=list, 
        blank=True,
        help_text='[{"step_number": 1, "text": "...", "timer_minutes": 0, "icon": "🔪"}]'
    )
    missing_ingredients = models.JSONField(default=list, blank=True)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_cuisine_category_display()}] {self.title}"

    @property
    def total_time_minutes(self):
        return self.prep_time_minutes + self.cook_time_minutes

    @property
    def is_zero_waste(self):
        return len(self.missing_ingredients) == 0

    @property
    def missing_count(self):
        return len(self.missing_ingredients)

    @property
    def display_image(self):
        if self.image_url:
            return self.image_url
        title_lower = self.title.lower()
        if "chilli paneer" in title_lower or "noodle" in title_lower or "fried rice" in title_lower or "asian" in title_lower:
            return "https://images.unsplash.com/photo-1541696432-82c6da8ce7bf?auto=format&fit=crop&w=800&q=80"
        elif "pasta" in title_lower or "skillet" in title_lower or "continental" in title_lower or "tuscan" in title_lower:
            return "https://images.unsplash.com/photo-1621996346565-e3d5d6281292?auto=format&fit=crop&w=800&q=80"
        elif "paneer" in title_lower or "palak" in title_lower:
            return "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=800&q=80"
        elif "chicken" in title_lower or "murgh" in title_lower or "curry" in title_lower:
            return "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=800&q=80"
        elif "dal" in title_lower or "tadka" in title_lower:
            return "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80"
        return "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=800&q=80"


class MealQueueItem(models.Model):
    PLAN_CHOICES = [
        ('TONIGHT', 'Today / Tonight (आज)'),
        ('TOMORROW', 'Tomorrow (कल)'),
        ('UPCOMING', 'Day 3 / Next Up (परसों)'),
    ]

    MEAL_SLOT_CHOICES = [
        ('LUNCH', '☀️ Lunch (दोपहर का भोजन)'),
        ('DINNER', '🌙 Dinner (रात का खाना)'),
    ]

    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='queue_items')
    planned_for = models.CharField(max_length=20, choices=PLAN_CHOICES, default='TONIGHT')
    meal_slot = models.CharField(max_length=20, choices=MEAL_SLOT_CHOICES, default='DINNER')
    order = models.PositiveIntegerField(default=0)
    is_cooked = models.BooleanField(default=False)

    class Meta:
        ordering = ['planned_for', 'meal_slot', 'order']

    def __str__(self):
        return f"{self.recipe.title} ({self.get_planned_for_display()} - {self.get_meal_slot_display()})"


class ShoppingItem(models.Model):
    CATEGORY_CHOICES = [
        ('PRODUCE', 'Fresh Sabzi & Herbs (सब्जी/धनिया/मिर्च)'),
        ('DAIRY', 'Dairy & Paneer (पनीर/दही/चीज/बटर)'),
        ('MEAT', 'Poultry, Meat & Eggs (अंडे/चिकन)'),
        ('PANTRY_STAPLE', 'Dals, Noodles, Pasta, Atta, Rice & Masalas'),
        ('OTHER', 'Sauces & Asian/Kirana Essentials'),
    ]

    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='PRODUCE')
    quantity_note = models.CharField(max_length=100, blank=True, default="")
    is_bought = models.BooleanField(default=False)
    recipe_source = models.ForeignKey(
        Recipe, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='shopping_items'
    )

    class Meta:
        ordering = ['is_bought', 'category', 'name']

    def __str__(self):
        return f"{self.name} ({'✓' if self.is_bought else '○'})"
