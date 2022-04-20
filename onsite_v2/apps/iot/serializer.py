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
    apsa = serializers.SerializerMethodField()

    def get_apsa(self, obj):
        apsa_obj = Apsa.objects.get(asset=obj)
        return {
            'id':apsa_obj.id,
            'onsite_type': apsa_obj.onsite_type,
            'onsite_series': apsa_obj.onsite_series,
            'facility_fin': apsa_obj.facility_fin,
            'daily_js': apsa_obj.daily_js,
            'temperature': apsa_obj.temperature,
            'vap_max': apsa_obj.vap_max,
            'vap_type': apsa_obj.vap_type,
            'norminal_flow': apsa_obj.norminal_flow,
            'daily_bind': apsa_obj.daily_bind,
            'flow_meter': apsa_obj.flow_meter,
            'cooling_fixed': apsa_obj.cooling_fixed
        }

    class Meta:
        model = Asset
        exclude = ('uuid', 'status', 'tags', 'variables_num', 'is_apsa', 'confirm')


class AssetBulkSerializer(ModelSerializer):
    """
    Asset序列化器
    """
    site = SiteSerializer()
    bulk = serializers.SerializerMethodField()

    def get_bulk(self, obj):
        bulk_obj = Bulk.objects.get(asset=obj)
        return {
            'id': bulk_obj.id,
            'tank_size': bulk_obj.tank_size,
            'tank_func': bulk_obj.tank_func,
            'level_a': bulk_obj.level_a,
            'level_b': bulk_obj.level_b,
            'level_c': bulk_obj.level_c,
            'level_d': bulk_obj.level_d,
            'filling_js': bulk_obj.filling_js
        }

    class Meta:
        model = Asset
        exclude = ('uuid', 'status', 'tags', 'variables_num', 'is_apsa', 'confirm')


class VariableSerializer(ModelSerializer):
    """
    Variable序列化器
    """

    class Meta:
        model = Variable
        exclude = ('asset', 'uuid',)
