from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from djoser.serializers import UserCreateSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredients,
    ShoppingCart,
    Tag,
)
from users.models import Follow

User = get_user_model()


class SetPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_current_password(self, value):
        request = self.context.get("request")
        if request:
            user = self.context["request"].user
            user_password = user.password

            if check_password(value, user_password) is False:
                raise serializers.ValidationError(
                    "Неверно введен старый пароль"
                )
            return value

    def validate_new_password(self, value):
        if not value:
            raise serializers.ValidationError("Укажите новый пароль")
        validate_password(value)
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        if request:
            user = self.context["request"].user
            new_password = validated_data.get("new_password")
            user.set_password(new_password)
            user.save()
            return validated_data


class ProfileForRepresentationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "id", "username", "first_name", "last_name")


class ProfileReadSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ("email",
                  "id",
                  "username",
                  "first_name",
                  "last_name",
                  "is_subscribed"
                  )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and Follow.objects.filter(user=request.user, author=obj).exists()
        )


class ProfileCreateSerializer(UserCreateSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "id",
            "is_subscribed",
            "password",
        )

    def to_representation(self, instance):
        return ProfileForRepresentationSerializer(
            instance, context={"request": self.context.get("request")}
        ).data

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and Follow.objects.filter(user=request.user, author=obj).exists()
        )


class ProfileSerializer(UserCreateSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "id",
            "is_subscribed",
            "password",
        )

    def to_representation(self, instance):
        return ProfileReadSerializer(
            instance, context={"request": self.context.get("request")}
        ).data

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and Follow.objects.filter(user=request.user, author=obj).exists()
        )


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = (
            "id",
            "name",
            "measurement_unit",
        )


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = (
            "id",
            "name",
            "color",
            "slug",
        )


class AddIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=1, max_value=100)

    class Meta:
        model = RecipeIngredients
        fields = ("id", "amount")


class CreateRecipeSerializer(serializers.ModelSerializer):
    ingredients = AddIngredientSerializer(many=True)
    author = ProfileSerializer(read_only=True)
    image = Base64ImageField()
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
    )

    class Meta:
        model = Recipe
        fields = (
            "id",
            "author",
            "name",
            "image",
            "text",
            "ingredients",
            "tags",
            "cooking_time",
        )

    def validate(self, data):
        ingredient_amount = data["ingredients"]
        tags_amount = data["tags"]
        image_amount = data.get('image')
        if not ingredient_amount:
            raise serializers.ValidationError(
                "Рецепт не может быть создан без ингредиентов."
            )
        if not tags_amount:
            raise serializers.ValidationError(
                "Рецепт не может быть создан без тэгов."
            )
        if not image_amount:
            raise serializers.ValidationError(
                "Рецепт не может быть создан без картинки."
            )
        return data

    @staticmethod
    def create_ingredients(ingredients, recipe):
        ingredient_list = []
        for ingredient_data in ingredients:
            ingredient_list.append(
                RecipeIngredients(
                    ingredient=ingredient_data["id"],
                    amount=ingredient_data["amount"],
                    recipe=recipe,
                )
            )
        RecipeIngredients.objects.bulk_create(ingredient_list)

    def create(self, validated_data):
        author = self.context.get("request").user
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def to_representation(self, instance):
        return ReadRecipeSerializer(
            instance, context={"request": self.context.get("request")}
        ).data

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags")
        ingredients = validated_data.pop("ingredients")
        instance = super().update(instance, validated_data)
        instance.tags.clear()
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients(recipe=instance, ingredients=ingredients)
        instance.save
        return instance


class IngredientAmountSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="ingredient.id")
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )

    class Meta:
        model = RecipeIngredients
        fields = ("id", "name", "amount", "measurement_unit")


class ReadRecipeSerializer(serializers.ModelSerializer):
    author = ProfileReadSerializer(read_only=True)
    ingredients = IngredientAmountSerializer(many=True,
                                             source="recipe_ingredients")
    tags = TagSerializer(many=True, read_only=False)
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and Favorite.objects.filter(user=request.user,
                                        recipe=obj.id).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and ShoppingCart.objects.filter(user=request.user,
                                            recipe=obj.id).exists()
        )


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ("user", "recipe")

    def validate(self, data):
        user = data["user"]
        recipe = data["recipe"]
        if Favorite.objects.filter(user=user).filter(recipe=recipe).exists():
            raise serializers.ValidationError("this ricepe already exists!")
        return data

    def to_representation(self, instance):
        return RecipeShortSerializer(
            instance.recipe, context={"request": self.context.get("request")}
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = ("user", "recipe")

    def validate(self, data):
        user = data["user"]
        recipe = data["recipe"]
        if ShoppingCart.objects.filter(user=user).filter(
                recipe=recipe).exists():
            return serializers.ValidationError("This ricepe already exists!")
        return data

    def to_representation(self, instance):
        return RecipeShortSerializer(
            instance.recipe, context={"request": self.context.get("request")}
        ).data


class SubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ("author", "user")
        validators = (
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=("user", "author"),
                message=("Вы уже подписаны на данного автора!"),
            ),
        )

    def validate(self, data):
        user = self.context["request"].user
        author = data["author"]
        if user.id == author.id:
            raise serializers.ValidationError(
                "Нельзя подписаться на самого себя!"
            )
        return data


class SubscribeResponseSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField(read_only=True)
    recipes = ReadRecipeSerializer(many=True, read_only=True)
    recipes_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "id",
            "is_subscribed",
            "recipes",
            "recipes_count",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if request:
            current_user = request.user
            if current_user.is_authenticated:
                return Follow.objects.filter(user=current_user,
                                             author=obj).exists()

        return False

    def get_recipes_count(self, obj):
        recipes = Recipe.objects.filter(author=obj)
        return recipes.count()


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer для модели Follow"""

    email = serializers.ReadOnlyField(source="author.email")
    id = serializers.ReadOnlyField(source="author.id")
    username = serializers.ReadOnlyField(source="author.username")
    first_name = serializers.ReadOnlyField(source="author.first_name")
    last_name = serializers.ReadOnlyField(source="author.last_name")
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Follow
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
        )
        validators = (
            UniqueTogetherValidator(
                queryset=Follow.objects.all(),
                fields=("user", "author"),
                message=("Вы уже подписаны на данного автора!"),
            ),
        )

    def validate(self, data):
        user = self.context["request"].user
        author = data["author"]
        if user.id == author.id:
            raise serializers.ValidationError(
                "Нельзя подписаться на самого себя!"
            )
        return data

    def get_is_subscribed(self, obj):
        user = self.context.get("request").user
        if not user.is_anonymous:
            return Follow.objects.filter(user=obj.user,
                                         author=obj.author).exists()
        return False

    def get_recipes(self, obj):
        request = self.context.get("request")
        limit = request.GET.get("recipes_limit")
        recipes = Recipe.objects.filter(author=obj.author)
        if limit and limit.isdigit():
            recipes = recipes[: int(limit)]
        return RecipeShortSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()
