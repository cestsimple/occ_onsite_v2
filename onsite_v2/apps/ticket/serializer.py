# -*- coding:utf-8 -*-
from rest_framework import serializers

from .models import Project, Node, NodeContent


# class FillingSerializer(serializers.ModelSerializer):
#     """
#         Filling序列化器
#     """
#     tank_size = serializers.SerializerMethodField()
#
#
#     def get_tank_size(self, obj):
#         return obj.bulk.tank_size
#
#     class Meta:
#         model = Filling
#         exclude = ['created_at', 'updated_at']
#         read_only_fields = ['rtu_name', 'asset_name', 'tank_size', 'id']
#         write_only_fields = ['bulk']


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        exclude = ['created_at', 'updated_at']
        extra_kwargs = {
            'desc': {'allow_blank': True},
        }


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        exclude = ['created_at', 'updated_at']
        extra_kwargs = {
            'desc': {'allow_blank': True},
            'roles': {'allow_blank': True},
            'users': {'allow_blank': True},
        }


class NodeContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeContent
        exclude = ['created_at', 'updated_at']
        extra_kwargs = {
            'type': {'allow_blank': True},
        }
