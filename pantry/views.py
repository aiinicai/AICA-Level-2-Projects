import os
import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import HouseholdProfile, PantryItem, Recipe, MealQueueItem, ShoppingItem
from services import ai_service

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# PANTRY VIEWS
# -----------------------------------------------------------------------------

def pantry_list_view(request):
    tier_filter = request.GET.get('tier', 'ALL')
    category_filter = request.GET.get('category', 'ALL')
    search_query = request.GET.get('q', '').strip()

    items = PantryItem.objects.all()

    if tier_filter in ['URGENT', 'THIS_WEEK', 'STAPLE']:
        items = items.filter(shelf_life_tier=tier_filter)

    if category_filter and category_filter != 'ALL':
        items = items.filter(category=category_filter)

    if search_query:
        items = items.filter(Q(name__icontains=search_query) | Q(quantity_note__icontains=search_query))

    urgent_items = PantryItem.objects.filter(shelf_life_tier='URGENT')
    this_week_items = PantryItem.objects.filter(shelf_life_tier='THIS_WEEK')
    staple_items = PantryItem.objects.filter(shelf_life_tier='STAPLE')

    context = {
        'items': items,
        'urgent_items': urgent_items,
        'this_week_items': this_week_items,
        'staple_items': staple_items,
        'current_tier': tier_filter,
        'current_category': category_filter,
        'search_query': search_query,
        'categories': PantryItem.CATEGORY_CHOICES,
    }

    if request.headers.get('HX-Request') and request.GET.get('partial'):
        return render(request, 'pantry/partials/item_list_grid.html', context)

    return render(request, 'pantry/pantry_list.html', context)


@require_POST
def pantry_add_item_view(request):
    name = request.POST.get('name', '').strip()
    category = request.POST.get('category', 'PRODUCE')
    shelf_life_tier = request.POST.get('shelf_life_tier', 'THIS_WEEK')
    quantity_note = request.POST.get('quantity_note', '').strip()

    if not name:
        return HttpResponse('<div class="text-rose-500 text-xs">Name is required</div>', status=400)

    item = PantryItem.objects.create(
        name=name,
        category=category,
        shelf_life_tier=shelf_life_tier,
        quantity_note=quantity_note
    )

    if request.headers.get('HX-Request'):
        # Return full updated items grid along with out-of-band badge updates
        urgent_count = PantryItem.objects.filter(shelf_life_tier='URGENT').count()
        total_count = PantryItem.objects.count()
        
        items = PantryItem.objects.all()
        return render(request, 'pantry/partials/item_list_grid.html', {
            'items': items,
            'new_item_id': item.id,
            'urgent_count': urgent_count,
            'total_count': total_count,
            'just_added': item,
        })

    messages.success(request, f"Added '{item.name}' to your pantry.")
    return redirect('pantry_list')


@require_POST
def pantry_delete_item_view(request, item_id):
    item = get_object_or_404(PantryItem, id=item_id)
    item_name = item.name
    item.delete()

    if request.headers.get('HX-Request'):
        urgent_count = PantryItem.objects.filter(shelf_life_tier='URGENT').count()
        total_count = PantryItem.objects.count()
        
        # Return empty response for the card delete with out-of-band badge counter updates
        html = f"""
        <div id="urgent-badge-desktop" hx-swap-oob="true">
            {f'<span class="px-1.5 py-0.5 text-xs font-bold rounded-full bg-urgent text-white shadow-sm shadow-urgent/30 animate-pulse">{urgent_count}</span>' if urgent_count > 0 else ''}
        </div>
        <div id="urgent-badge-mobile" hx-swap-oob="true">
            {f'<span class="absolute -top-1 -right-2 px-1.5 py-0.2 text-[10px] font-black rounded-full bg-urgent text-white animate-pulse shadow-sm">{urgent_count}</span>' if urgent_count > 0 else ''}
        </div>
        <span id="pantry-total-count" hx-swap-oob="true" class="font-bold text-slate-800">{total_count} items</span>
        <span id="pantry-urgent-count" hx-swap-oob="true" class="font-bold text-rose-600">{urgent_count} urgent</span>
        """
        return HttpResponse(html)

    messages.info(request, f"Removed '{item_name}' from pantry.")
    return redirect('pantry_list')


@require_POST
def pantry_bulk_add_view(request):
    grocery_text = request.POST.get('grocery_text', '').strip()
    receipt_image = request.FILES.get('receipt_image')

    image_bytes = None
    if receipt_image:
        image_bytes = receipt_image.read()

    if not grocery_text and not image_bytes:
        messages.error(request, "Please paste grocery text or select a receipt photo.")
        return redirect('pantry_list')

    try:
        extracted = ai_service.parse_grocery_text_or_receipt(text=grocery_text, image_bytes=image_bytes)
        count = 0
        valid_cats = dict(PantryItem.CATEGORY_CHOICES).keys()
        valid_tiers = dict(PantryItem.SHELF_LIFE_CHOICES).keys()

        for raw in extracted:
            name = raw.get('name', '').strip()
            if not name:
                continue
            cat = raw.get('category', 'PRODUCE')
            if cat not in valid_cats:
                cat = 'PRODUCE'
            tier = raw.get('shelf_life_tier', 'THIS_WEEK')
            if tier not in valid_tiers:
                tier = 'THIS_WEEK'
            qty = raw.get('quantity_note', '1 unit')

            PantryItem.objects.create(
                name=name,
                category=cat,
                shelf_life_tier=tier,
                quantity_note=qty
            )
            count += 1

        messages.success(request, f"✨ Successfully parsed and added {count} items to your pantry!")
    except Exception as e:
        logger.error(f"Bulk parse error: {e}")
        messages.error(request, f"Could not parse items: {e}")

    return redirect('pantry_list')


# -----------------------------------------------------------------------------
# RECIPE & COOKING ENGINE VIEWS
# -----------------------------------------------------------------------------

def recipe_suggest_view(request):
    profile = HouseholdProfile.get_solo()
    urgent_items = PantryItem.objects.filter(shelf_life_tier='URGENT')
    this_week_items = PantryItem.objects.filter(shelf_life_tier='THIS_WEEK')
    staples = PantryItem.objects.filter(shelf_life_tier='STAPLE')

    all_pantry_dicts = [
        {'name': i.name, 'shelf_life_tier': i.shelf_life_tier, 'category': i.category, 'quantity': i.quantity_note}
        for i in PantryItem.objects.all()
    ]

    force_regenerate = request.GET.get('refresh') == '1'
    cached_recipes = request.session.get('suggested_recipes')

    if not cached_recipes or force_regenerate:
        recipes_data = ai_service.suggest_recipes(all_pantry_dicts, profile)
        # Store in session
        request.session['suggested_recipes'] = recipes_data
    else:
        recipes_data = cached_recipes

    context = {
        'recipes': recipes_data,
        'profile': profile,
        'urgent_count': urgent_items.count(),
        'fresh_count': this_week_items.count(),
        'urgent_names': [i.name for i in urgent_items[:4]],
    }
    return render(request, 'recipes/recipe_suggest.html', context)


@require_POST
def recipe_save_view(request):
    """
    Saves a generated recipe from the suggest view into the database.
    Can also directly add it to the tonight meal queue.
    """
    title = request.POST.get('title')
    description = request.POST.get('description', '')
    prep_time = int(request.POST.get('prep_time_minutes', 10))
    cook_time = int(request.POST.get('cook_time_minutes', 15))
    servings = int(request.POST.get('servings', 2))
    
    appliances_raw = request.POST.get('appliances_used', '[]')
    ingredients_raw = request.POST.get('ingredients', '[]')
    instructions_raw = request.POST.get('instructions', '[]')
    missing_raw = request.POST.get('missing_ingredients', '[]')
    
    appliances = json.loads(appliances_raw) if isinstance(appliances_raw, str) else appliances_raw
    ingredients = json.loads(ingredients_raw) if isinstance(ingredients_raw, str) else ingredients_raw
    instructions = json.loads(instructions_raw) if isinstance(instructions_raw, str) else instructions_raw
    missing_ingredients = json.loads(missing_raw) if isinstance(missing_raw, str) else missing_raw

    image_url = request.POST.get('image_url', '').strip()
    cuisine = request.POST.get('cuisine', 'North Indian').strip()
    cuisine_category = request.POST.get('cuisine_category', 'INDIAN').strip()
    spice_level = request.POST.get('spice_level', 'Medium Spicy 🌶️').strip()

    action = request.POST.get('action', 'save')  # 'save', 'cook_lunch', 'cook_dinner'

    recipe = Recipe.objects.create(
        title=title,
        description=description,
        prep_time_minutes=prep_time,
        cook_time_minutes=cook_time,
        servings=servings,
        image_url=image_url,
        cuisine=cuisine,
        cuisine_category=cuisine_category,
        spice_level=spice_level,
        appliances_used=appliances,
        ingredients=ingredients,
        instructions=instructions,
        missing_ingredients=missing_ingredients,
        is_favorite=(action == 'save')
    )

    if action in ['cook_lunch', 'cook_dinner', 'cook_tonight']:
        slot = 'LUNCH' if action == 'cook_lunch' else 'DINNER'
        MealQueueItem.objects.create(
            recipe=recipe,
            planned_for='TONIGHT',
            meal_slot=slot,
            order=0,
            is_cooked=False
        )
        messages.success(request, f"Scheduled '{recipe.title}' for Today's {slot.title()}! Let's cook!")
        return redirect('recipe_cook', recipe_id=recipe.id)

    messages.success(request, f"Saved '{recipe.title}' to your Cookbook!")
    return redirect('recipe_saved_list')


def recipe_cook_view(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    # Match recipe ingredients against available pantry items
    pantry_names = set(p.name.lower() for p in PantryItem.objects.all())
    
    ingredient_status = []
    for ing in recipe.ingredients:
        name = ing.get('item', '')
        in_stock = any(p_name in name.lower() or name.lower() in p_name for p_name in pantry_names)
        ingredient_status.append({
            'item': name,
            'amount': ing.get('amount', ''),
            'in_stock': in_stock or ing.get('is_staple', False),
            'is_staple': ing.get('is_staple', False)
        })

    context = {
        'recipe': recipe,
        'ingredient_status': ingredient_status,
        'instructions': recipe.instructions,
    }
    return render(request, 'recipes/cooking_mode.html', context)


@require_POST
def recipe_finish_cooking_view(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    consume_pantry = request.POST.get('consume_pantry') == 'on'

    consumed_count = 0
    if consume_pantry:
        # Find pantry items matching ingredients and delete/consume them
        for ing in recipe.ingredients:
            item_name = ing.get('item', '')
            if ing.get('is_staple'):
                continue  # don't delete staples like salt/pepper
            matched = PantryItem.objects.filter(name__icontains=item_name).first()
            if not matched:
                words = item_name.split()
                for w in words:
                    if len(w) > 3:
                        matched = PantryItem.objects.filter(name__icontains=w).first()
                        if matched:
                            break
            if matched:
                matched.delete()
                consumed_count += 1

    # Mark corresponding meal queue items as cooked
    MealQueueItem.objects.filter(recipe=recipe).update(is_cooked=True)

    msg = f"🎉 Great job cooking '{recipe.title}'!"
    if consumed_count > 0:
        msg += f" {consumed_count} pantry ingredients marked as consumed."
    messages.success(request, msg)
    return redirect('pantry_list')


@require_POST
def recipe_add_missing_to_shopping_view(request, recipe_id=None):
    """
    Adds missing ingredients from a recipe (or form list) to the shopping list.
    """
    recipe = None
    if recipe_id:
        recipe = get_object_or_404(Recipe, id=recipe_id)
        missing_list = recipe.missing_ingredients
    else:
        missing_raw = request.POST.get('missing_json', '[]')
        try:
            missing_list = json.loads(missing_raw)
        except Exception:
            missing_list = []

    added = 0
    for item_str in missing_list:
        clean_name = item_str.strip()
        if not clean_name:
            continue
        
        # Categorize
        cat = 'PRODUCE'
        lower = clean_name.lower()
        if any(w in lower for w in ['cheese', 'milk', 'cream', 'yogurt', 'butter']):
            cat = 'DAIRY'
        elif any(w in lower for w in ['chicken', 'beef', 'pork', 'fish', 'salmon', 'meat']):
            cat = 'MEAT'
        elif any(w in lower for w in ['oil', 'spice', 'capers', 'vinegar', 'sauce', 'pasta', 'flour']):
            cat = 'PANTRY_STAPLE'

        ShoppingItem.objects.create(
            name=clean_name,
            category=cat,
            quantity_note="For recipe",
            is_bought=False,
            recipe_source=recipe
        )
        added += 1

    if request.headers.get('HX-Request'):
        return HttpResponse(f"""
        <div class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-100 text-emerald-800 text-xs font-bold shadow-sm">
            <span>✓</span>
            <span>Added {added} missing items to Shopping List</span>
        </div>
        """)

    messages.success(request, f"Added {added} missing items to your Shopping List!")
    return redirect('planner_view')


def recipe_saved_list_view(request):
    recipes = Recipe.objects.all().order_by('-is_favorite', '-created_at')
    context = {
        'recipes': recipes,
    }
    return render(request, 'recipes/saved_list.html', context)


@require_POST
def recipe_toggle_favorite_view(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    recipe.is_favorite = not recipe.is_favorite
    recipe.save()

    if request.headers.get('HX-Request'):
        heart = "❤️" if recipe.is_favorite else "🤍"
        return HttpResponse(f"""
        <button hx-post="/recipes/{recipe.id}/favorite/" hx-swap="outerHTML" 
                class="p-2 rounded-full hover:bg-rose-50 text-lg transition-transform active:scale-125"
                title="Toggle favorite">
            {heart}
        </button>
        """)

    return redirect('recipe_saved_list')


# -----------------------------------------------------------------------------
# PLANNER & SHOPPING LIST VIEWS
# -----------------------------------------------------------------------------

def planner_view(request):
    queue_tonight = MealQueueItem.objects.filter(planned_for='TONIGHT', is_cooked=False)
    queue_tomorrow = MealQueueItem.objects.filter(planned_for='TOMORROW', is_cooked=False)
    queue_upcoming = MealQueueItem.objects.filter(planned_for='UPCOMING', is_cooked=False)

    # 2 Meals Per Day Slots (Lunch & Dinner)
    day_plans = [
        {
            'key': 'TONIGHT',
            'title': 'Today (आज)',
            'badge': 'Day 1 &bull; Active Plan',
            'lunch_items': queue_tonight.filter(meal_slot='LUNCH'),
            'dinner_items': queue_tonight.filter(meal_slot='DINNER'),
            'border_color': 'border-amber-300',
            'bg_gradient': 'from-amber-500/10 via-amber-500/5',
            'dot_color': 'bg-amber-500 animate-pulse',
        },
        {
            'key': 'TOMORROW',
            'title': 'Tomorrow (कल)',
            'badge': 'Day 2',
            'lunch_items': queue_tomorrow.filter(meal_slot='LUNCH'),
            'dinner_items': queue_tomorrow.filter(meal_slot='DINNER'),
            'border_color': 'border-indigo-200',
            'bg_gradient': 'from-indigo-500/10 via-indigo-500/5',
            'dot_color': 'bg-indigo-500',
        },
        {
            'key': 'UPCOMING',
            'title': 'Day 3 / Next Up (परसों)',
            'badge': 'Day 3',
            'lunch_items': queue_upcoming.filter(meal_slot='LUNCH'),
            'dinner_items': queue_upcoming.filter(meal_slot='DINNER'),
            'border_color': 'border-teal-200',
            'bg_gradient': 'from-teal-500/10 via-teal-500/5',
            'dot_color': 'bg-teal-500',
        },
    ]

    # Shopping list grouped by aisle
    shopping_items = ShoppingItem.objects.all()
    shopping_by_category = {}
    for cat_key, cat_label in ShoppingItem.CATEGORY_CHOICES:
        items = shopping_items.filter(category=cat_key)
        if items.exists():
            shopping_by_category[cat_label] = items

    all_recipes = Recipe.objects.all()

    context = {
        'day_plans': day_plans,
        'queue_tonight': queue_tonight,
        'queue_tomorrow': queue_tomorrow,
        'queue_upcoming': queue_upcoming,
        'shopping_items': shopping_items,
        'shopping_by_category': shopping_by_category,
        'all_recipes': all_recipes,
        'shopping_categories': ShoppingItem.CATEGORY_CHOICES,
        'bought_count': shopping_items.filter(is_bought=True).count(),
        'pending_count': shopping_items.filter(is_bought=False).count(),
    }
    return render(request, 'planner/planner_view.html', context)


@require_POST
def planner_add_to_queue_view(request):
    recipe_id = request.POST.get('recipe_id')
    planned_for = request.POST.get('planned_for', 'TONIGHT')
    meal_slot = request.POST.get('meal_slot', 'DINNER')
    recipe = get_object_or_404(Recipe, id=recipe_id)

    MealQueueItem.objects.create(
        recipe=recipe,
        planned_for=planned_for,
        meal_slot=meal_slot,
        order=MealQueueItem.objects.filter(planned_for=planned_for, meal_slot=meal_slot).count() + 1
    )
    messages.success(request, f"Added '{recipe.title}' to {planned_for.title()} {meal_slot.title()}.")
    return redirect('planner_view')


@require_POST
def planner_move_queue_view(request, item_id):
    queue_item = get_object_or_404(MealQueueItem, id=item_id)
    new_plan = request.POST.get('planned_for')
    new_slot = request.POST.get('meal_slot')
    if new_plan in ['TONIGHT', 'TOMORROW', 'UPCOMING']:
        queue_item.planned_for = new_plan
    if new_slot in ['LUNCH', 'DINNER']:
        queue_item.meal_slot = new_slot
    queue_item.save()

    return redirect('planner_view')

    return redirect('planner_view')


@require_POST
def planner_delete_queue_view(request, item_id):
    queue_item = get_object_or_404(MealQueueItem, id=item_id)
    queue_item.delete()

    if request.headers.get('HX-Request'):
        return HttpResponse("")

    return redirect('planner_view')


@require_POST
def shopping_add_view(request):
    name = request.POST.get('name', '').strip()
    category = request.POST.get('category', 'PRODUCE')
    quantity_note = request.POST.get('quantity_note', '').strip()

    if name:
        ShoppingItem.objects.create(
            name=name,
            category=category,
            quantity_note=quantity_note,
            is_bought=False
        )

    return redirect('planner_view')


@require_POST
def shopping_toggle_view(request, item_id):
    item = get_object_or_404(ShoppingItem, id=item_id)
    item.is_bought = not item.is_bought
    item.save()

    if request.headers.get('HX-Request'):
        # Return updated shopping row partial
        return render(request, 'planner/partials/shopping_item_row.html', {'item': item})

    return redirect('planner_view')


@require_POST
def shopping_delete_view(request, item_id):
    item = get_object_or_404(ShoppingItem, id=item_id)
    item.delete()

    if request.headers.get('HX-Request'):
        return HttpResponse("")

    return redirect('planner_view')


@require_POST
def shopping_move_bought_to_pantry_view(request):
    """
    Converts all checked shopping items (is_bought=True) into PantryItem records in one click!
    """
    bought_items = ShoppingItem.objects.filter(is_bought=True)
    count = 0

    cat_map = {
        'PRODUCE': 'PRODUCE',
        'DAIRY': 'DAIRY',
        'MEAT': 'MEAT',
        'PANTRY_STAPLE': 'PANTRY_STAPLE',
        'OTHER': 'PANTRY_STAPLE',
    }

    tier_map = {
        'PRODUCE': 'THIS_WEEK',
        'DAIRY': 'THIS_WEEK',
        'MEAT': 'THIS_WEEK',
        'PANTRY_STAPLE': 'STAPLE',
        'OTHER': 'STAPLE',
    }

    for item in bought_items:
        pantry_cat = cat_map.get(item.category, 'PRODUCE')
        tier = tier_map.get(item.category, 'THIS_WEEK')
        
        PantryItem.objects.create(
            name=item.name,
            category=pantry_cat,
            shelf_life_tier=tier,
            quantity_note=item.quantity_note or "Purchased from list"
        )
        count += 1

    bought_items.delete()
    messages.success(request, f"🎉 Moved {count} purchased groceries directly into your In-Stock Pantry!")
    return redirect('pantry_list')


# -----------------------------------------------------------------------------
# SETTINGS & HOUSEHOLD PROFILE
# -----------------------------------------------------------------------------

def manifest_json_view(request):
    from django.conf import settings
    manifest_path = os.path.join(settings.BASE_DIR, 'static', 'manifest.json')
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/manifest+json')
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        return response
    except Exception as e:
        return HttpResponse('{}', content_type='application/manifest+json')


def service_worker_view(request):
    from django.conf import settings
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/javascript; charset=utf-8')
        response['Service-Worker-Allowed'] = '/'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        return response
    except Exception as e:
        return HttpResponse('// SW load error', content_type='application/javascript; charset=utf-8')


def household_settings_view(request):
    profile = HouseholdProfile.get_solo()

    all_dietary_options = [
        "North Indian (Dhaba & Homestyle)",
        "South Indian (Tiffin & Curries)",
        "Indian Vegetarian (Shakahari)",
        "Jain (No Onion & No Garlic)",
        "High-Protein Desi",
        "Sattvic (Pure Ayurvedic)",
        "Mughlai & Non-Veg (Chicken/Mutton)",
        "Low-Oil Healthy Desi",
        "Keto / Low-Carb",
        "Vegan"
    ]

    all_appliances_options = [
        "Pressure Cooker (सीटी कुकर)",
        "Kadai (Deep Wok / कड़ाही)",
        "Tawa (Flat Griddle / तवा)",
        "Mixer-Grinder (Mixie / मिक्सी)",
        "Stovetop (गैस चूल्हा)",
        "Air Fryer (Crispy Tikki / Samosa)",
        "Oven / OTG (Tandoori & Baking)",
        "Hand Blender / Churner (मथानी)"
    ]

    if request.method == 'POST':
        profile.name = request.POST.get('name', 'My Kitchen').strip()
        profile.default_servings = int(request.POST.get('default_servings', 2))
        profile.disliked_ingredients = request.POST.get('disliked_ingredients', '').strip()
        profile.dietary_preferences = request.POST.getlist('dietary_preferences')
        profile.available_appliances = request.POST.getlist('available_appliances')
        profile.save()

        # Invalidate recipe suggestion cache so new preferences apply immediately
        if 'suggested_recipes' in request.session:
            del request.session['suggested_recipes']

        messages.success(request, "Kitchen Profile & AI preferences saved successfully!")
        return redirect('household_settings')

    context = {
        'profile': profile,
        'all_dietary_options': all_dietary_options,
        'all_appliances_options': all_appliances_options,
    }
    return render(request, 'settings/settings_view.html', context)
