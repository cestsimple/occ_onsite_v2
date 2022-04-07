from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.


class User(AbstractUser):
    """自定义用户模型类"""

    level = models.CharField(max_length=3, verbose_name='权限等级')
    region = models.CharField(max_length=20, verbose_name='区域')
    group = models.CharField(max_length=20, verbose_name='分组')

    class Meta:
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
