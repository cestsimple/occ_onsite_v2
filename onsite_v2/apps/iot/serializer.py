from django.db import transaction
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import Site, Apsa, Bulk, Variable, Asset, Engineer


class SiteSerializer(ModelSerializer):
    """
    Site序列化器
    """
    class Meta:
        model = Site
        fields = '__all__'


class ApsaSerializer(ModelSerializer):
    """
    APSA序列化器
    """


    class Meta:
        model = Apsa
        fields = '__all__'

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
    class Meta:
        model = Bulk
        fields = '__all__'


class AssetSerializer(ModelSerializer):
    """
    Asset序列化器
    """
    class Meta:
        model = Asset
        exclude = ('uuid', 'status', 'tags', 'variables_num')


class EngineerSerializer(ModelSerializer):
    """
    Enginee序列化器
    """

    class Meta:
        model = Engineer
        exclude = ('uuid', 'status', 'tags', 'variables_num')
