from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class CustomUser(AbstractUser):
    USERNAME_FIELD = 'username'
    REQUIRED_FIELD = ['username', 'first_name', 'last_name', 'password']

    username = models.CharField(
        verbose_name='Никнэйм',
        max_length=150,
        unique=True,
        blank=False,
        validators=[
            RegexValidator(r'^[\w.@+-]+\Z')
        ],
    )
    email = models.EmailField(
        verbose_name='Имэйл',
        max_length=256,
        unique=True,
        blank=False,
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=150,
        blank=False,
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=150,
        blank=False,
    )
    password = models.CharField(
        verbose_name='Пароль',
        max_length=150,
        blank=False,
        # validators=[
        #     RegexValidator(r'^[\w.@+-]+\Z')
        # ],
    )

    class Meta:
        ordering = ('username',)

    def __str__(self) -> str:
        return self.username


class Follow(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор рецептов'
    )

    class Meta:
        constraints = (models.UniqueConstraint(fields=['user', 'author'],
                                               name='user_author_unique'),
                       )

    def __str__(self):
        return f'{self.user} follows {self.author}'
