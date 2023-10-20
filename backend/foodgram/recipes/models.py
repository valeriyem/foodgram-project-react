from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(
        verbose_name="название Тэга",
        max_length=150,
        unique=True,
    )
    color = models.CharField(
        verbose_name="Цвет",
        max_length=50,
        unique=True,
    )
    slug = models.SlugField(
        verbose_name="Слаг",
        max_length=150,
        unique=True,
    )


class Ingredient(models.Model):
    name = models.CharField(
        verbose_name="название ингридиента",
        max_length=150,
        blank=False,
    )
    measurement_unit = models.CharField(
        verbose_name="еденица измерения",
        max_length=50,
        blank=False,
    )

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        verbose_name="Автор",
        on_delete=models.CASCADE,
        blank=False,
        related_name="recipes",
    )
    name = models.CharField(
        verbose_name="Название рецепта",
        max_length=150,
        blank=False,
    )
    image = models.ImageField(
        verbose_name="фото рецепта",
        blank=False,
        upload_to="recipes/",
    )
    text = models.TextField(
        verbose_name="описание рецепта",
        blank=False,
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        blank=False,
        through="RecipeIngredients",
    )
    tags = models.ManyToManyField(Tag, blank=False, null=True, through="RecipeTags")
    cooking_time = models.PositiveIntegerField(
        verbose_name="время приготовления(мин)",
        blank=False,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )

    def __str__(self):
        return self.name


class RecipeIngredients(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients"
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
    )
    amount = models.PositiveIntegerField(
        verbose_name="Количество",
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        null=True,
    )


class RecipeTags(models.Model):
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        verbose_name="тэг",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name="рецепт",
    )

    def __str__(self):
        return f"{self.tag} + {self.recipe}"


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
        related_name="favoriting",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name="Рецепт",
        related_name="favoriting",
    )

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"

    def __str__(self):
        return f"{self.user} добавил {self.recipe} в избранное!"


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
        related_name="shopping_cart",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="shopping_cart_recipe",
        verbose_name="Рецепт",
    )

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"

    def __str__(self):
        return f"{self.user} добавил {self.recipe} в списки покупок!"
