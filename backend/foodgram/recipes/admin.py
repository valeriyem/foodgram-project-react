from django.contrib import admin

from .models import Favorite, Ingredient, Recipe, ShoppingCart, Tag

admin.site.register(Ingredient)
admin.site.register(Tag)
admin.site.register(Recipe)
admin.site.register(Favorite)
admin.site.register(ShoppingCart)
# Register your models here.
