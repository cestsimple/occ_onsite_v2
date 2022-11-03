from rest_framework.serializers import ModelSerializer

from .models import AssetV2, ApsaV2, BulkV2, VariableV2, RecordV2


class AssetV2Serializer(ModelSerializer):
    class Meta:
        model = AssetV2
        fields = ['uuid', 'name', 'site_name', 'status']


class ApsaV2Serializer(ModelSerializer):
    class Meta:
        model = ApsaV2
        exclude = ('created_at', 'updated_at')


class BulkV2Serializer(ModelSerializer):
    class Meta:
        model = BulkV2
        exclude = ('created_at', 'updated_at')


class VariableV2Serializer(ModelSerializer):
    class Meta:
        model = VariableV2
        exclude = ('created_at', 'updated_at')


class RecordV2Serializer(ModelSerializer):
    class Meta:
        model = RecordV2
        fields = '__all__'
