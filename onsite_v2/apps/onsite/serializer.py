from rest_framework import serializers
from .models import Filling, Daily, DailyMod, Malfunction, FillingMonthly, MonthlyVariable, InvoiceDiff, ReasonDetail
from ..iot.models import Asset, Apsa


class FillingSerializer(serializers.ModelSerializer):
    """
        Filling序列化器
    """
    asset_name = serializers.SerializerMethodField()
    rtu_name = serializers.SerializerMethodField()
    tank_size = serializers.SerializerMethodField()
    nm3 = serializers.SerializerMethodField()

    def get_nm3(self, obj):
        rtu_name = obj.bulk.asset.rtu_name
        try:
            apsa = Apsa.objects.get(asset__rtu_name=rtu_name, asset__confirm=1)
            return round(obj.quantity * 0.65 * (apsa.temperature + 273.15) / 273.15, 2)
        except Exception as e:
            return e[:100]

    def get_asset_name(self, obj):
        return Asset.objects.get(bulk=obj.bulk).name

    def get_rtu_name(self, obj):
        return Asset.objects.get(bulk=obj.bulk).rtu_name

    def get_tank_size(self, obj):
        return obj.bulk.tank_size

    class Meta:
        model = Filling
        fields = '__all__'
        read_only_fields = ['rtu_name', 'asset_name', 'tank_size', 'id']
        write_only_fields = ['bulk']


class DailyModSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMod
        exclude = ['date', 'apsa']
        extra_kwargs = {
            'comment': {'allow_blank': True},
        }


class MalfunctionSerializer(serializers.ModelSerializer):
    asset_name = serializers.SerializerMethodField()
    rtu_name = serializers.SerializerMethodField()
    avg_con = serializers.SerializerMethodField()
    facility_fin = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    reason_detail_1_eng = serializers.SerializerMethodField()
    reason_detail_2_eng = serializers.SerializerMethodField()

    def get_reason_detail_1_eng(self, obj):
        cn_name = obj.reason_detail_1
        if cn_name == "":
            return ""
        results = ReasonDetail.objects.filter(cname=cn_name)
        if not results:
            return "not found"
        else:
            return results[0].ename

    def get_reason_detail_2_eng(self, obj):
        cn_name = obj.reason_detail_2
        if cn_name == "":
            return ""
        results = ReasonDetail.objects.filter(cname=cn_name)
        if not results:
            return "not found"
        else:
            return results[0].ename

    def get_asset_name(self, obj):
        return Asset.objects.get(apsa=obj.apsa).name

    def get_rtu_name(self, obj):
        return Asset.objects.get(apsa=obj.apsa).rtu_name

    def get_avg_con(self, obj):
        if obj.stop_hour:
            return round(obj.stop_consumption / obj.stop_hour, 2)
        return 0

    def get_facility_fin(self, obj):
        return obj.apsa.facility_fin

    def get_region(self, obj):
        return obj.apsa.asset.site.engineer.region

    class Meta:
        model = Malfunction
        fields = '__all__'
        extra_kwargs = {
            'reason_main': {'allow_blank': True},
            'reason_l1': {'allow_blank': True},
            'reason_l2': {'allow_blank': True},
            'reason_l3': {'allow_blank': True},
            'reason_l4': {'allow_blank': True},
            'stop_alarm': {'allow_blank': True},
            'reason_detail_1': {'allow_blank': True},
            'reason_detail_2': {'allow_blank': True},
            'mt_comment': {'allow_blank': True},
            'occ_comment': {'allow_blank': True},
        }


class DailySerializer(serializers.ModelSerializer):
    class Meta:
        model = Daily
        fields = '__all__'


class FillingMonthlySerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    asset_name = serializers.SerializerMethodField()
    rtu_name = serializers.SerializerMethodField()
    tank_size = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    lin_bulk = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    def get_region(self, obj):
        site = obj.bulk.asset.site
        return site.engineer.region if site.engineer else ''

    def get_date(self, obj):
        return str(obj.date)[:10]

    def get_asset_name(self, obj):
        return Asset.objects.get(bulk=obj.bulk).name

    def get_rtu_name(self, obj):
        return Asset.objects.get(bulk=obj.bulk).rtu_name

    def get_tank_size(self, obj):
        return obj.bulk.tank_size

    def get_lin_bulk(self, obj):
        return round((obj.start - obj.end) * obj.bulk.tank_size / 100, 2)

    def get_total(self, obj):
        return round(obj.quantity + (obj.start - obj.end) * obj.bulk.tank_size / 100 ,2)

    class Meta:
        model = FillingMonthly
        exclude = ['bulk']
        read_only_fields = ['rtu_name', 'asset_name', 'id', 'date', 'tank_size']


class InvoiceVariableSerializer(serializers.ModelSerializer):
    rtu_name = serializers.SerializerMethodField()
    variable_name = serializers.SerializerMethodField()

    def get_rtu_name(self, obj):
        return Asset.objects.get(apsa=obj.apsa).rtu_name

    def get_variable_name(self, obj):
        return obj.variable.name

    class Meta:
        model = MonthlyVariable
        fields = '__all__'
        read_only_fields = ['rtu_name', 'id', 'variable_name']


class InvoiceDiffSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    rtu_name = serializers.SerializerMethodField()
    diff = serializers.SerializerMethodField()
    variable_name = serializers.SerializerMethodField()
    variable_id = serializers.SerializerMethodField()

    def get_date(self, obj):
        return str(obj.date)[:10]

    def get_rtu_name(self, obj):
        return Asset.objects.get(apsa=obj.apsa).rtu_name

    def get_variable_name(self, obj):
        return obj.variable.name

    def get_diff(self, obj):
        if obj.variable.name == 'H_PROD':
            return obj.end
        return round(obj.end - obj.start, 2)

    def get_variable_id(self, obj):
        return obj.variable.id

    class Meta:
        model = InvoiceDiff
        exclude = ['apsa', 'variable']
        read_only_fields = ['rtu_name', 'id', 'date', 'usage', 'variable_name', 'get_diff']
