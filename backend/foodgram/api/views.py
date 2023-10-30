import csv

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.filters import IngredientSearchFilter, RecipeFilter
from api.permissions import IsAuthorAdminOrReadOnly
from api.serializers import (
    CreateRecipeSerializer,
    FavoriteSerializer,
    IngredientSerializer,
    ProfileCreateSerializer,
    ProfileReadSerializer,
    ReadRecipeSerializer,
    SetPasswordSerializer,
    ShoppingCartSerializer,
    SubscribeResponseSerializer,
    SubscribeSerializer,
    SubscriptionSerializer,
    TagSerializer,
)
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


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientSearchFilter
    search_fields = ("^name",)
    pagination_class = None


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("author", "tags")
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return ReadRecipeSerializer
        return CreateRecipeSerializer

    def __post_delete_func(self, request, pk,
                           serializer_param, model, message):
        if request.method == "POST":
            context = {"request": request}
            recipe = get_object_or_404(Recipe, id=pk)
            data = {"user": request.user.id, "recipe": recipe.id}
            serializer = serializer_param(data=data, context=context)
            try:
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            except Exception:
                return Response(serializer.error,
                                status=status.HTTP_400_BAD_REQUEST)
        if request.method == "DELETE":
            recipe = get_object_or_404(Recipe, pk=pk)
            try:
                obj = get_object_or_404(model,
                                        user=request.user.id,
                                        recipe=recipe)
                obj.delete()
                return Response(
                    {"message": {message}},
                    status=status.HTTP_204_NO_CONTENT
                )
            except Exception:
                return Response(
                    {"errors": "Объект не найден"},
                    status=status.HTTP_400_BAD_REQUEST
                )

    @action(
        detail=True,
        permission_classes=(permissions.IsAuthenticated,),
        methods=["POST", "DELETE"],
    )
    def favorite(self, request, pk):
        message = "Рецепт успешно удален из избранного"
        return self.__post_delete_func(
            request, pk, FavoriteSerializer, Favorite, message
        )

    @action(
        detail=True,
        permission_classes=(permissions.IsAuthenticated,),
        methods=["POST", "DELETE"],
    )
    def shopping_cart(self, request, pk):
        message = "Рецепт успешно удален из списка покупок"
        return self.__post_delete_func(
            request, pk, ShoppingCartSerializer, ShoppingCart, message
        )

    @action(
        methods=["GET"],
        detail=False,
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        objects = RecipeIngredients.objects.filter(
            recipe__shopping_cart_recipe__user=request.user
        )
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; " \
                                          "" "filename=shopping_cart.csv"
        writer = csv.writer(response)
        writer.writerow(["Recipe",
                         "Ingredient_name",
                         "Amount",
                         "measurement_unit"])
        object_fields = objects.values_list(
            "recipe__name",
            "ingredient__name",
            "amount",
            "ingredient__measurement_unit"
        )
        for object in object_fields:
            writer.writerow(object)
        return response


class UserViewSet(UserViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ProfileReadSerializer
        return ProfileCreateSerializer

    @action(
        methods=("get",),
        detail=False,
        permission_classes=(permissions.IsAuthenticated,),
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        permission_classes=(permissions.IsAuthenticated,),
        methods=["POST", "DELETE"],
    )
    def subscribe(self, request, id):
        if request.method == "POST":
            context = {"request": request}
            author = get_object_or_404(User, id=id)
            data = {"user": request.user.id, "author": author.id}
            serializer = SubscribeSerializer(data=data, context=context)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            author_serializer = SubscribeResponseSerializer(author)
            return Response(author_serializer.data,
                            status=status.HTTP_201_CREATED)
        if request.method == "DELETE":
            author = get_object_or_404(User, id=id)
            try:
                Follow.objects.get(author=author,
                                   user=request.user.id).delete()
                return Response(
                    {"message": "Вы отписались от этого автора"},
                    status=status.HTTP_204_NO_CONTENT,
                )
            except Exception:
                return Response(
                    {"errors": "Объект не найден"},
                    status=status.HTTP_400_BAD_REQUEST
                )

    @action(
        detail=False,
        permission_classes=(permissions.IsAuthenticated,),
        methods=("get",),
    )
    def subscriptions(self, request):
        user = self.request.user
        queryset = Follow.objects.filter(user=user)
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        permission_classes=(permissions.IsAuthenticated,),
        methods=("get",)
    )
    def users(self, request, pk):
        if request.user.is_authenticated:
            users = User.objects.filter(pk=pk)
            serializer = ProfileReadSerializer(
                user=users,
                context={"request": request})
            return Response(serializer.data,
                            status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=(permissions.IsAuthenticated,),
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(
                {"message": "Пароль успешно изменен"},
                status=status.HTTP_204_NO_CONTENT
            )
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)
