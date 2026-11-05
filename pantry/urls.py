from django.urls import path
from . import views

urlpatterns = [
    # Pantry
    path('', views.pantry_list_view, name='pantry_list'),
    path('pantry/add/', views.pantry_add_item_view, name='pantry_add'),
    path('pantry/<int:item_id>/delete/', views.pantry_delete_item_view, name='pantry_delete'),
    path('pantry/bulk-add/', views.pantry_bulk_add_view, name='pantry_bulk_add'),

    # Recipes & Cooking Mode
    path('recipes/', views.recipe_saved_list_view, name='recipe_saved_list'),
    path('recipes/suggest/', views.recipe_suggest_view, name='recipe_suggest'),
    path('recipes/save/', views.recipe_save_view, name='recipe_save'),
    path('recipes/<int:recipe_id>/cook/', views.recipe_cook_view, name='recipe_cook'),
    path('recipes/<int:recipe_id>/finish/', views.recipe_finish_cooking_view, name='recipe_finish_cooking'),
    path('recipes/<int:recipe_id>/missing-to-shopping/', views.recipe_add_missing_to_shopping_view, name='recipe_add_missing_to_shopping'),
    path('recipes/missing-to-shopping/', views.recipe_add_missing_to_shopping_view, name='recipe_add_missing_to_shopping_raw'),
    path('recipes/<int:recipe_id>/favorite/', views.recipe_toggle_favorite_view, name='recipe_toggle_favorite'),

    # Meal Queue & Smart Shopping List
    path('planner/', views.planner_view, name='planner_view'),
    path('planner/queue/add/', views.planner_add_to_queue_view, name='planner_add_to_queue'),
    path('planner/queue/<int:item_id>/move/', views.planner_move_queue_view, name='planner_move_queue'),
    path('planner/queue/<int:item_id>/delete/', views.planner_delete_queue_view, name='planner_delete_queue'),
    path('planner/shopping/add/', views.shopping_add_view, name='shopping_add'),
    path('planner/shopping/<int:item_id>/toggle/', views.shopping_toggle_view, name='shopping_toggle'),
    path('planner/shopping/<int:item_id>/delete/', views.shopping_delete_view, name='shopping_delete'),
    path('planner/shopping/move-to-pantry/', views.shopping_move_bought_to_pantry_view, name='shopping_move_bought_to_pantry'),

    # Settings
    path('settings/', views.household_settings_view, name='household_settings'),
]
