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


class AssetSerializer(ModelSerializer):
    """
    Asset序列化器
    """
    site = SiteSerializer()

    class Meta:
        model = Asset
        exclude = ('uuid', 'status', 'tags', 'variables_num')


class ApsaSerializer(ModelSerializer):
    """
    APSA序列化器
    """
    engineer = serializers.SerializerMethodField()
    rtu_name = serializers.SerializerMethodField()
    # region = serializers.SerializerMethodField()
    # group = serializers.SerializerMethodField()
    site_name = serializers.SerializerMethodField()

    def get_rtu_name(self, obj):
        return obj.asset.rtu_name

    def get_engineer(self, obj):
        res = {
            'id': '',
            'region': '',
            'group': '',
        }
        if obj.asset.site.engineer is not None:
            res['id'] = obj.asset.site.engineer.id
            res['region'] = obj.asset.site.engineer.region
            res['group'] = obj.asset.site.engineer.group
            return res
        return res
        # def get_region(self, obj):
        #     if obj.asset.site.engineer is not None:
        #         return obj.asset.site.engineer.region
        #     return ''
        #
        # def get_group(self, obj):
        #     if obj.asset.site.engineer is not None:
        #         return obj.asset.site.engineer.group
        return ''

    def get_site_name(self, obj):
        return obj.asset.site.name

    class Meta:
        model = Apsa
        exclude = ('asset',)

    # def update(self, instance, validated_data):
    #     site = self.context['request'].data.get('site')
    #     # 开启事务
    #     with transaction.atomic():
    #         # 设置保存点
    #         save_point = transaction.savepoint()
    #         try:
    #             # 更新asset信息
    #             Asset.objects.filter(id=instance.id).update(validated_data)
    #             # 更新site信息
    #             Asset.objects.filter(id=instance.id).site(**site)
    #         except:
    #             # 回滚
    #             transaction.savepoint_rollback(save_point)
    #             raise serializers.ValidationError('保存失败')
    #         else:
    #             # 提交
    #             transaction.savepoint_commit(save_point)
    #             return instance


class BulkSerializer(ModelSerializer):
    """
    Bulk序列化器
    """

    rtu_name = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    group = serializers.SerializerMethodField()
    site_name = serializers.SerializerMethodField()

    def get_rtu_name(self, obj):
        return obj.asset.rtu_name

    def get_region(self, obj):
        if obj.asset.site.engineer is not None:
            return obj.asset.site.engineer.region
        return ''

    def get_group(self, obj):
        if obj.asset.site.engineer is not None:
            return obj.asset.site.engineer.group
        return ''

    def get_site_name(self, obj):
        return obj.asset.site.name

    class Meta:
        model = Bulk
        exclude = ('asset',)


class VariableSerializer(ModelSerializer):
    """
    Variable序列化器
    """

    class Meta:
        model = Variable
        exclude = ('asset', 'uuid',)


