from rest_framework.serializers import ModelSerializer
from .models import Filling


class FillingSerializer(ModelSerializer):
    """
        User序列化器
    """

    class Meta:
        model = Filling
        exclude = ['asset',]
