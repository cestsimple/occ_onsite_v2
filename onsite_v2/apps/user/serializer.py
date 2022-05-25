from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import User, Role, Permission, RolePermission, UserRole


class UserSerializer(ModelSerializer):
    """
        User序列化器
    """
    roles = serializers.SerializerMethodField()

    def get_roles(self, obj):
        return [x.role_id for x in UserRole.objects.filter(user=obj)]

    class Meta:
        model = User
        exclude = ['last_login', 'is_superuser', 'is_active']

        extra_kwargs = {
            'username': {
                'max_length': 20,
                'min_length': 3
            },
            'password': {
                'max_length': 20,
                'min_length': 3,
                'write_only': True,
                'allow_blank': True
            },
        }

    # 重写create方法
    def create(self, validated_data):
        # 保存用户数据并对密码加密
        user = User.objects.create_user(**validated_data)
        return user


class RoleSerializer(ModelSerializer):
    permIds = serializers.SerializerMethodField()

    def get_permIds(self, obj):
        return [x.permission_id for x in RolePermission.objects.filter(role=obj)]

    class Meta:
        model = Role
        fields = '__all__'


class PermissionSerializer(ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'

        extra_kwargs = {
            'description': {
                'allow_blank': True
            }
        }


class RolePermissionSerializer(ModelSerializer):
    permission = PermissionSerializer()

    class Meta:
        model = RolePermission
        fields = '__all__'
