from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """自定义用户模型类"""

    level = models.CharField(max_length=3, verbose_name='权限等级')
    region = models.CharField(max_length=20, verbose_name='区域')
    group = models.CharField(max_length=20, verbose_name='分组')
    email = models.CharField(max_length=20, verbose_name='分组', blank=True)

    class Meta:
        ordering = ['id']
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name


class Role(models.Model):
    """角色信息表"""
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    name = models.CharField(max_length=20, verbose_name='名称')
    description= models.CharField(max_length=50, verbose_name='描述')

    class Meta:
        db_table = 'tb_users_role'


class Permission(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    name = models.CharField(max_length=20, verbose_name='名称')
    code = models.CharField(max_length=50, verbose_name='前端view名称')
    description = models.CharField(max_length=50, verbose_name='描述')
    parent = models.IntegerField(null=True, verbose_name='父节点id')

    class Meta:
        db_table = 'tb_users_permission'


class RolePermission(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    role = models.ForeignKey(Role, on_delete='CASCADE')
    permission = models.ForeignKey(Permission, on_delete='CASCADE')

    class Meta:
        db_table = 'tb_users_role_permission'
