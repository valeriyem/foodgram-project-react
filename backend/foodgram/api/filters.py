from django_filters.rest_framework import FilterSet, filters

from recipes.models import Ingredient, Recipe, Tag, User


class IngredientSearchFilter(FilterSet):
    name = filters.CharFilter(lookup_expr="startswith")

    class Meta:
        model = Ingredient
        fields = ("name",)


class RecipeFilter(FilterSet):
    is_favorited = filters.NumberFilter(
        method="get_is_favorited")
    is_in_shopping_cart = filters.NumberFilter(
        method="get_is_in_shopping_cart")
    tags = filters.ModelMultipleChoiceFilter(
        field_name="tags__slug",
        to_field_name="slug",
        queryset=Tag.objects.all(),
    )
    author = filters.ModelChoiceFilter(queryset=User.objects.all())

    class Meta:
        model = Recipe
        fields = ("is_favorited", "is_in_shopping_cart", "tags", "author")

    def get_is_favorited(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(
                favoriting__user=self.request.user
            )
        return queryset

    def get_is_in_shopping_cart(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(
                shopping_cart_recipe__user=self.request.user
            )
        return queryset
