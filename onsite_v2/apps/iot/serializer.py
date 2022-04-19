from django.db import transaction
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Site, Apsa, Bulk, Variable, Asset
from apps.user.models import User


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'region', 'group', 'email']


class SiteSerializer(ModelSerializer):
    """
    Site序列化器
    """
    engineer = UserSerializer()

    class Meta:
        model = Site
        exclude = ('uuid',)


class ApsaSerializer(ModelSerializer):
    """
    APSA序列化器
    """
    class Meta:
        model = Apsa
        exclude = ('asset',)


class BulkSerializer(ModelSerializer):
    """
    Bulk序列化器
    """

    class Meta:
        model = Bulk
        exclude = ('asset',)


class AssetApsaSerializer(ModelSerializer):
    """
    Asset序列化器
    """
    site = SiteSerializer()
    apsa = ApsaSerializer()

    class Meta:
        model = Asset
        exclude = ('uuid', 'status', 'tags', 'variables_num')


class AssetBulkSerializer(ModelSerializer):
    """
    Asset序列化器
    """
    site = SiteSerializer()

    class Meta:
        model = Asset
        exclude = ('uuid', 'status', 'tags', 'variables_num')


class VariableSerializer(ModelSerializer):
    """
    Variable序列化器
    """

    class Meta:
        model = Variable
        exclude = ('asset', 'uuid',)


