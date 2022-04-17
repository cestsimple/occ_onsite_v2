from rest_framework.serializers import ModelSerializer
from .models import User


class UserSerializer(ModelSerializer):
    """
        User序列化器
    """

    class Meta:
        model = User
        fields = ['id',]

        extra_kwargs = {
            'username': {
                'max_length': 20,
                'min_length': 3
            },
        }

    # 重写create方法
    def create(self, validated_data):
        # 保存用户数据并对密码加密
        user = User.objects.create_user(**validated_data)
        return user
