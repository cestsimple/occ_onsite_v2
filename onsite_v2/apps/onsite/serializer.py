from rest_framework.serializers import ModelSerializer
from .models import Filling


class FillingSerializer(ModelSerializer):
    """
        Filling序列化器
    """
    class Meta:
        model = Filling
        exclude = ['Bulk',]


class DailySerializer(ModelSerializer):
    """
        Daily序列化器
    """
    class Meta:
        model = Filling
        exclude = ['Apsa',]