from django.db import models

from apps.user.models import User


# class SiteV2(models.Model):
#     id = models.AutoField(primary_key=True)
#     name = models.CharField(max_length=50, verbose_name='气站名')
#     region = models.CharField(max_length=20, verbose_name='区域', default='')
#     engineer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
#
#     class Meta:
#         ordering = ['region', 'onsite_series', 'rtu_name']
#         indexes = [
#             models.Index(fields=['uuid'], name='uuid_idx'),
#             models.Index(fields=['name'], name='name_idx'),
#             models.Index(fields=['rtu_name'], name='rtu_name_idx')
#         ]
#         db_table = 'iot_v2_apsa'


class OnsiteSet(models.Model):
    """onsite集合 apsa与bulk的配对关系表"""
    id = models.AutoField(primary_key=True, verbose_name='配对id')
    sid = models.IntegerField(default=0, verbose_name='自身id')
    type = models.CharField(max_length=50, null=False, verbose_name='类型(所属表)')
    pid = models.IntegerField(default=0, verbose_name='父节点id')


class BulkV2(models.Model):
    # 资产字段
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, verbose_name='资产名')
    rtu_name = models.CharField(max_length=50, verbose_name='RTU名', default='')
    comment = models.CharField(max_length=50, verbose_name='备注', default='')
    # bulk字段
    tank_size = models.FloatField(max_length=30, verbose_name='储罐大小', default=0)
    tank_func = models.CharField(max_length=30, verbose_name='储罐功能', default='')
    level_a = models.FloatField(max_length=30, verbose_name='filling标志a', default=1)
    level_b = models.FloatField(max_length=30, verbose_name='filling标志b', default=6)
    level_c = models.FloatField(max_length=30, verbose_name='filling标志c', default=10)
    level_d = models.FloatField(max_length=30, verbose_name='filling标志d', default=0.5)
    filling_js = models.IntegerField(default=0)
    # 变量绑定
    level_cc = models.CharField(max_length=100, default='', verbose_name='level_cc_uuid')
    # 通用字段
    status = models.IntegerField(default=1, verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        indexes = [
            models.Index(fields=['id'], name='id_idx'),
            models.Index(fields=['name'], name='name_idx'),
            models.Index(fields=['rtu_name'], name='rtu_name_idx')
        ]
        db_table = 'iot_v2_bulk'


class ApsaV2(models.Model):
    # 信息字段
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, verbose_name='资产名')
    rtu_name = models.CharField(max_length=50, verbose_name='RTU名', default='')
    region = models.CharField(max_length=20, verbose_name='区域', default='')
    group = models.CharField(max_length=20, verbose_name='分组', default='')
    engineer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    comment = models.CharField(max_length=50, verbose_name='备注', default='')
    # apsa字段
    onsite_type = models.CharField(max_length=30, verbose_name='类型', default='')
    onsite_series = models.CharField(max_length=30, verbose_name='型号', default='')
    facility_fin = models.CharField(max_length=50, verbose_name='项目号', default='')
    temperature = models.FloatField(max_length=30, verbose_name='daily温度', default=0)
    vap_max = models.IntegerField(verbose_name='汽化器最大能力', default=0)
    vap_type = models.CharField(max_length=30, verbose_name='汽化器类型', default='')
    norminal_flow = models.IntegerField(verbose_name='合同产量', default=0)
    daily_bind = models.CharField(max_length=100, verbose_name='daily绑定资产id', default='')
    cooling_fixed = models.FloatField(max_length=10, verbose_name='cooling设定值', default=0)
    mark = models.CharField(max_length=300, default='', verbose_name='额外标识')
    # 计算标识
    daily_js = models.IntegerField(default=0, verbose_name='计算daily')
    # 变量绑定
    m3_q7 = models.CharField(max_length=100, default='', verbose_name='m3_tot_uuid')
    m3_q6 = models.CharField(max_length=100, default='', verbose_name='m3_q6_uuid')
    m3_q5 = models.CharField(max_length=100, default='', verbose_name='m3_q5_uuid')
    m3_q1 = models.CharField(max_length=100, default='', verbose_name='m3_q1_uuid')
    m3_prod = models.CharField(max_length=100, default='', verbose_name='m3_prod_uuid')
    m3_peak = models.CharField(max_length=100, default='', verbose_name='m3_peak_uuid')
    m3_tot = models.CharField(max_length=100, default='', verbose_name='m3_tot_uuid')
    h_stpdft = models.CharField(max_length=100, default='', verbose_name='h_stpdft_uuid')
    h_stpal = models.CharField(max_length=100, default='', verbose_name='h_stpal_uuid')
    h_stp400v = models.CharField(max_length=100, default='', verbose_name='h_stp400v_uuid')
    h_prod = models.CharField(max_length=100, default='', verbose_name='h_prod_uuid')
    flow_meter = models.CharField(max_length=100, default='', verbose_name='flow_meter_uuid')
    # 通用字段
    status = models.IntegerField(default=1, verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ['region', 'onsite_series', 'rtu_name']
        indexes = [
            models.Index(fields=['id'], name='id_idx'),
            models.Index(fields=['name'], name='name_idx'),
            models.Index(fields=['rtu_name'], name='rtu_name_idx')
        ]
        db_table = 'iot_v2_apsa'


class AssetV2(models.Model):
    # 资产字段
    uuid = models.CharField(primary_key=True, max_length=100, verbose_name='uuid')
    name = models.CharField(max_length=50, verbose_name='资产名')
    site_name = models.CharField(max_length=50, verbose_name='气站名')
    # 通用字段
    status = models.IntegerField(default=1, verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ['site_name', 'name']
        indexes = [
            models.Index(fields=['uuid'], name='uuid_idx'),
            models.Index(fields=['site_name', 'name'], name='name_idx')
        ]
        db_table = 'iot_v2_asset'


class VariableV2(models.Model):
    """变量信息表"""
    uuid = models.CharField(primary_key=True, max_length=100, verbose_name='变量uuid')
    asset_uuid = models.CharField(max_length=100, verbose_name='资产uuid')
    name = models.CharField(max_length=50, verbose_name='变量名')
    # 通用字段
    status = models.IntegerField(default=1, verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ['asset_uuid', 'name']
        indexes = [
            models.Index(fields=['uuid'], name='uuid_idx'),
            models.Index(fields=['asset_uuid'], name='asset_uuid_idx'),
        ]
        db_table = 'iot_v2_variable'


class RecordV2(models.Model):
    """变量记录表"""
    id = models.AutoField(primary_key=True)
    variable_uuid = models.CharField(max_length=100, verbose_name='变量uuid')
    datetime = models.DateTimeField(verbose_name='记录时间', null=False)
    value = models.FloatField(max_length=100, verbose_name='记录值', default=0)

    class Meta:
        ordering = ['datetime', 'variable_uuid']
        indexes = [
            models.Index(fields=['id'], name='id_idx'),
            models.Index(fields=['datetime', 'variable_uuid'], name='datetime_uuid_idx'),
        ]
        db_table = 'iot_v2_record'
