from django.shortcuts import render
from rest_framework import viewsets, status
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse
import io
from django.db.models import Sum
from djoser.views import UserViewSet
import csv
from rest_framework.response import Response
from api.filters import IngredientSearchFilter, RecipeFilter
from rest_framework import filters
from recipes.models import Ingredient, Tag, Recipe, Favorite, ShoppingCart, RecipeIngredients
from users.models import Follow
from api.serializers import IngredientSerializer, ProfileReadSerializer, \
    TagSerializer, CreateRecipeSerializer, SetPasswordSerializer, \
    ReadRecipeSerializer, FavoriteSerializer,\
    ShoppingCartSerializer, SubscribeSerializer, ProfileSerializer,\
    SubscribeResponseSerializer, ProfileCreateSerializer, SubscriptionSerializer
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from api.permissions import IsAdminOrReadOnly, IsAuthorAdminOrReadOnly

User = get_user_model()


class IngredientsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend, )
    filterset_class = IngredientSearchFilter
    # filter_backends = (filters.SearchFilter,)
    search_fields = ('^name',)
    # permission_classes = [IsAdminOrReadOnly]
    pagination_class = None


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    # permission_classes = [IsAdminOrReadOnly]
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    #анонимный GET-запрос на получение cписка рецептов будет обработан успешно
    #запрос на изменение или создание информации без токена не сработает
    # permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    permission_classes = (IsAuthorAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('author', 'tags')
    filterset_class = RecipeFilter

    # def get_queryset(self):
    #     queryset = Recipe.objects.all().select_related('author')
    #     return queryset

    def get_serializer_class(self):
        # if self.action in ('retrieve', 'list'):
        if self.request.method in permissions.SAFE_METHODS:
            return ReadRecipeSerializer
        return CreateRecipeSerializer

    @action(detail=True,
            permission_classes=(permissions.IsAuthenticated,),
            methods=['POST', 'DELETE']
            )
    def favorite(self, request, pk):
        if request.method == 'POST':
            context = {'request': request}
            recipe = get_object_or_404(Recipe, id=pk)
            data = {
                'user': request.user.id,
                'recipe': recipe.id
            }
            serializer = FavoriteSerializer(data=data, context=context)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            recipe = get_object_or_404(Recipe, pk=pk)
            try:
                obj = get_object_or_404(Favorite, user=request.user.id, recipe=recipe)
                obj.delete()
                return Response({'message':'Рецепт успешно удален из избранного'}, status=status.HTTP_204_NO_CONTENT)
            except:
                return Response({'errors': 'Объект не найден'},
                                status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True,
            permission_classes=(permissions.IsAuthenticated,),
            methods=['POST', 'DELETE']
            )
    def shopping_cart(self,request,pk):
        if request.method == 'POST':
            context = {'request':request}
            recipe = get_object_or_404(Recipe, id=pk)
            data={
                'user': request.user.id,
                'recipe': recipe.id
            }
            serializer = ShoppingCartSerializer(data=data,context=context)
            try:
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data,status=status.HTTP_201_CREATED)
            except:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'DELETE':
            try:
                recipe = get_object_or_404(Recipe, pk=pk)
                obj = get_object_or_404(ShoppingCart, user = request.user.id,recipe = recipe)
                obj.delete()
                return Response({'message': 'Рецепт успешно удален из списка покупок'},
                                status=status.HTTP_204_NO_CONTENT)
            except:
                return Response({'errors': 'Объект не найден'},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(
        methods=['GET'],
        detail=False,
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        objects = RecipeIngredients.objects.filter(recipe__shopping_cart_recipe__user=request.user)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=shopping_cart.csv'
        writer = csv.writer(response)
        writer.writerow(['Recipe', 'Ingredient_name','Amount','measurement_unit'])
        object_fields = objects.values_list('recipe__name', 'ingredient__name','amount','ingredient__measurement_unit')
        for object in object_fields:
            writer.writerow(object)
        return response


class UserViewSet(UserViewSet):
    queryset = User.objects.all()
    # serializer_class = ProfileSerializer
    # pagination_class = PageNumberPagination
    #permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProfileReadSerializer
        return ProfileCreateSerializer

    @action(
        methods=('get',),
        detail=False,
        permission_classes=(permissions.IsAuthenticated,)
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True,
            permission_classes=(permissions.IsAuthenticated,),
            methods=['POST', 'DELETE']
            )
    def subscribe(self, request, id):
        if request.method == 'POST':
            context = {'request': request}
            author = get_object_or_404(User, id=id)
            data = {
                'user': request.user.id,
                'author': author.id
            }
            serializer = SubscribeSerializer(data=data, context=context)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            author_serializer = SubscribeResponseSerializer(author)
            return Response(author_serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            author = get_object_or_404(User, id=id)
            # if Follow.objects.filter(author=author,user=self.request.user).exists():
            #     Follow.objects.get(author=author,user=request.user.id).delete()
            #     # get_object_or_404(Follow, user=request.user.id, author=get_object_or_404(User, id=id)).delete()
            #     return Response({'message': 'Вы отписались от этого автора'},
            #                     status=status.HTTP_204_NO_CONTENT
            #                     )
            # else:
            #     return Response({'errors': 'Объект не найден'},
            #                     status=status.HTTP_400_BAD_REQUEST)
            try:
                    Follow.objects.get(author=author,user=request.user.id).delete()
                    return Response({'message': 'Вы отписались от этого автора'},
                                    status=status.HTTP_204_NO_CONTENT
                                    )
            except:
                return Response({'errors': 'Объект не найден'},
                                status=status.HTTP_400_BAD_REQUEST)



    @action(detail=False,
            permission_classes=(permissions.IsAuthenticated,),
            methods=('get',)
            )
    # def subscriptions(self, request):
    #     user = request.user
    #     # page = self.paginate_queryset(Follow.objects.filter(user=user))
    #     page = self.paginate_queryset(user.follower.all())
    #     # serializer = SubscribeSerializer(page, many=True, context={'request': request})
    #     # return self.get_paginated_response(serializer.data)
    #     serializer = SubscribeResponseSerializer(page, many=True, context={'request': request})
    #     return self.get_paginated_response(serializer.data)

    def subscriptions(self, request):
        user = self.request.user
        queryset = Follow.objects.filter(user=user)
        print(f'query{queryset}')
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)



    @action(detail=True,
            permission_classes=(permissions.IsAuthenticated,),
            methods=('get',)
            )
    def users(self, request, pk):
        user = request.user
        if request.user.is_authenticated:
            users = User.objects.filter(pk=pk)
            serializer = ProfileReadSerializer(user = users,context=context)
            return Response(serializer.data,
                            status=status.HTTP_204_NO_CONTENT
                            )

    @action(
        detail = False,
        methods = ['post'],
        permission_classes = (permissions.IsAuthenticated,),
    )
    def set_password(self,request):
        serializer = SetPasswordSerializer(data=request.data,
                                           context ={'request':request})
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({'message':'Пароль успешно изменен'},
                            status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)