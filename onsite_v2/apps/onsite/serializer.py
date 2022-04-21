from rest_framework import serializers
from .models import Filling, Daily, DailyMod, Malfunction
from ..iot.models import Site, Asset, Apsa


class FillingSerializer(serializers.ModelSerializer):
    """
        Filling序列化器
    """
    asset_name = serializers.SerializerMethodField()
    rtu_name = serializers.SerializerMethodField()
    tank_size = serializers.SerializerMethodField()

    def get_asset_name(self, obj):
        return Asset.objects.get(bulk=obj.bulk).name

    def get_rtu_name(self, obj):
        return Asset.objects.get(bulk=obj.bulk).rtu_name

    def get_tank_size(self, obj):
        return obj.bulk.tank_size

    class Meta:
        model = Filling
        exclude = ['confirm']
        read_only_fields = ['rtu_name', 'asset_name', 'tank_size', 'id']
        write_only_fields = ['bulk']


class DailySerializer(serializers.ModelSerializer):
    """
        Daily序列化器
    """
    date = serializers.SerializerMethodField()
    region = serializers.SerializerMethodField()
    series = serializers.SerializerMethodField()
    rtu_name = serializers.SerializerMethodField()
    norminal = serializers.SerializerMethodField()
    h_prod = serializers.SerializerMethodField()
    h_missing = serializers.SerializerMethodField()
    h_stop = serializers.SerializerMethodField()
    m3_prod = serializers.SerializerMethodField()
    avg_prod = serializers.SerializerMethodField()
    cus_consume = serializers.SerializerMethodField()
    avg_consume = serializers.SerializerMethodField()
    peak = serializers.SerializerMethodField()
    v_peak = serializers.SerializerMethodField()
    lin_tot = serializers.SerializerMethodField()
    dif_peak = serializers.SerializerMethodField()
    lin_consume = serializers.SerializerMethodField()
    cooling = serializers.SerializerMethodField()
    mod_id = serializers.SerializerMethodField()
    comment = serializers.SerializerMethodField()

    def get_date(self, obj):
        return obj.date.strftime("%Y-%m-%d")

    def get_region(self, obj):
        return Site.objects.get(asset__apsa=obj.apsa).engineer.region

    def get_series(self, obj):
        return obj.apsa.onsite_series

    def get_rtu_name(self, obj):
        return Asset.objects.get(apsa=obj.apsa).rtu_name

    def get_norminal(self, obj):
        return obj.apsa.norminal_flow

    def get_h_prod(self, obj):
        mod = DailyMod.objects.get(date=obj.date, apsa=obj.apsa)
        return round(obj.h_prod + mod.h_prod_mod, 2)

    def get_h_missing(self, obj):
        return round(24 - self.get_h_stop(obj) - self.get_h_prod(obj), 2)

    def get_h_stop(self, obj):
        mod = DailyMod.objects.get(date=obj.date, apsa=obj.apsa)
        return round(
            obj.h_stpal + obj.h_stp400v + obj.h_stpdft + mod.h_stpal_mod + mod.h_stp400v_mod + mod.h_stpdft_mod
            , 2)

    def get_m3_prod(self, obj):
        mod = DailyMod.objects.get(date=obj.date, apsa=obj.apsa)
        return round(obj.m3_prod + mod.m3_prod_mod, 2)

    def get_avg_prod(self, obj):
        return round(self.get_m3_prod(obj) / self.get_h_prod(obj), 2)

    def get_cus_consume(self, obj):
        mod = DailyMod.objects.get(date=obj.date, apsa=obj.apsa)
        return round(obj.m3_tot + mod.m3_tot_mod, 2)

    def get_avg_consume(self, obj):
        return round(self.get_cus_consume(obj) / 24, 2)

    def get_peak(self, obj):
        mod = DailyMod.objects.get(date=obj.date, apsa=obj.apsa)
        return round(obj.m3_peak + mod.m3_peak_mod , 2)

    def get_v_peak(self, obj):
        mod = DailyMod.objects.get(date=obj.date, apsa=obj.apsa)
        return round(obj.m3_q5 + mod.m3_q5_mod , 2)

    def get_lin_tot(self, obj):
        mod = DailyMod.objects.get(date=obj.date, apsa=obj.apsa)
        return round(obj.lin_tot + mod.lin_tot_mod - obj.flow_meter - mod.flow_meter_mod, 2)

    def get_dif_peak(self, obj):
        return round(self.get_v_peak(obj) - self.get_peak(obj) , 2)

    def get_lin_consume(self, obj):
        mod = DailyMod.objects.get(date=obj.date, apsa=obj.apsa)
        return round(obj.m3_q6 + mod.m3_q6_mod + obj.m3_q7 + mod.m3_q7_mod , 2)

    def get_mod_id(self, obj):
        return DailyMod.objects.get(date=obj.date, apsa=obj.apsa).id

    def get_cooling(self, obj):
        """
        规则： 停机cooling记为0， 有固定补冷值则为固定值，计算公式 (lin_tot - lin_consume - peak) / m3_prod * 100
        """
        if obj.apsa.cooling_fixed:
            return obj.apsa.cooling_fixed
        else:
            m3_prod = self.get_m3_prod(obj)
            lin_tot = self.get_lin_tot(obj)
            peak = self.get_peak(obj)
            lin_con = self.get_lin_consume(obj)
            if m3_prod:
                return round((lin_tot - peak - lin_con) / m3_prod * 100, 2)
            else:
                return 0

    def get_comment(self, obj):
        return DailyMod.objects.get(date=obj.date, apsa=obj.apsa).comment

    class Meta:
        model = Daily
        exclude = ['apsa', 'h_stpal', 'h_stpdft', 'h_stp400v', 'm3_tot', 'm3_q1', 'm3_peak', 'm3_q5',
                   'm3_q6', 'm3_q7', 'success', 'confirm']


class DailyModSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMod
        exclude = ['date', 'apsa']


class MalfunctionSerializer(serializers.ModelSerializer):
    asset_name = serializers.SerializerMethodField()
    rtu_name = serializers.SerializerMethodField()
    avg_con = serializers.SerializerMethodField()

    def get_asset_name(self, obj):
        return Asset.objects.get(apsa=obj.apsa).name

    def get_rtu_name(self, obj):
        return Asset.objects.get(apsa=obj.apsa).rtu_name

    def get_avg_con(self, obj):
        return round(obj.stop_consumption / obj.stop_hour, 2)

    class Meta:
        model = Malfunction
        exclude = ['apsa', 'confirm']
        extra_kwargs = {
            'reason_main': {'allow_blank': True},
            'reason_l1': {'allow_blank': True},
            'reason_l2': {'allow_blank': True},
            'reason_l3': {'allow_blank': True},
            'reason_l4': {'allow_blank': True},
            'reason_detail_1': {'allow_blank': True},
            'reason_detail_2': {'allow_blank': True},
            'mt_comment': {'allow_blank': True},
            'occ_comment': {'allow_blank': True},
        }
