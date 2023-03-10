from django.db import models
from apps.user.models import User


class AsyncJob(models.Model):
    """系统设置"""
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    name = models.CharField(max_length=30, verbose_name='储罐大小', null=False, blank=False)
    result = models.CharField(max_length=1024, verbose_name='运行结果', default='')
    start_time = models.DateTimeField(null=False)
    finish_time = models.DateTimeField(null=True)
    params = models.CharField(max_length=500, default="", verbose_name="具体参数")
    user = models.CharField(max_length=50, default="", verbose_name="用户名")
    is_deleted = models.BooleanField(default=False)


class Site(models.Model):
    """气站表"""
    id = models.AutoField(primary_key=True, verbose_name='资产数字id')
    uuid = models.CharField(max_length=100, verbose_name='资产UUID')
    name = models.CharField(max_length=50, verbose_name='气站中文名')
    engineer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    confirm = models.IntegerField(default=0)

    class Meta:
        ordering = ['id']


class Asset(models.Model):
    """资产表"""
    id = models.AutoField(primary_key=True, verbose_name='资产数字id')
    uuid = models.CharField(max_length=100, verbose_name='资产UUID')
    name = models.CharField(max_length=50, verbose_name='资产名')
    rtu_name = models.CharField(max_length=50, verbose_name='RTU名', default='')
    site = models.ForeignKey(Site, on_delete='on_delete=models.SET_NULL', null=True, blank=True)
    status = models.CharField(max_length=20, verbose_name='资产状态', default='')
    variables_num = models.IntegerField(default=-1, verbose_name='变量数')
    tags = models.CharField(max_length=100, verbose_name='标签', default='')
    is_apsa = models.IntegerField(default=0)
    confirm = models.IntegerField(default=0, verbose_name='逻辑删除')
    comment = models.CharField(max_length=50, verbose_name='备注', default='')

    class Meta:
        ordering = ['id']


class Bulk(models.Model):
    """bulk信息单"""
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    asset = models.ForeignKey(Asset, related_name='bulk', on_delete='CASCADE', null=True, blank=True)
    tank_size = models.FloatField(max_length=30, verbose_name='储罐大小', default=0)
    tank_func = models.CharField(max_length=30, verbose_name='储罐功能', default='')
    level_a = models.FloatField(max_length=30, verbose_name='filling标志a', default=1)
    level_b = models.FloatField(max_length=30, verbose_name='filling标志b', default=6)
    level_c = models.FloatField(max_length=30, verbose_name='filling标志c', default=10)
    level_d = models.FloatField(max_length=30, verbose_name='filling标志d', default=0.5)
    filling_js = models.IntegerField(default=0)

    class Meta:
        ordering = ['id']


class Apsa(models.Model):
    """apsa信息单"""
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    asset = models.ForeignKey(Asset, related_name='apsa', on_delete='CASCADE', null=True, blank=True)
    onsite_type = models.CharField(max_length=30, verbose_name='类型', default='')
    onsite_series = models.CharField(max_length=30, verbose_name='型号', default='')
    facility_fin = models.CharField(max_length=50, verbose_name='项目号', default='')
    daily_js = models.IntegerField(default=0, verbose_name='计算daily')
    temperature = models.FloatField(max_length=30, verbose_name='daily温度', default=0)
    vap_max = models.IntegerField(verbose_name='汽化器最大能力', default=0)
    vap_type = models.CharField(max_length=30, verbose_name='汽化器类型', default='')
    norminal_flow = models.IntegerField(verbose_name='合同产量', default=0)
    daily_bind = models.IntegerField(verbose_name='daily绑定资产id', default=-1)
    flow_meter = models.IntegerField(verbose_name='流量计变量id', default=-1)
    cooling_fixed = models.FloatField(max_length=10, verbose_name='cooling设定值', default=0)
    mark = models.CharField(max_length=300, default='', verbose_name='额外标识')

    class Meta:
        ordering = ['id']


class Variable(models.Model):
    """变量信息表"""
    id = models.AutoField(primary_key=True, verbose_name='变量数字id')
    uuid = models.CharField(max_length=100, verbose_name='变量ID')
    name = models.CharField(max_length=50, verbose_name='变量名')
    asset = models.ForeignKey(Asset, on_delete='CASCADE', max_length=100, verbose_name='变量资产')
    confirm = models.IntegerField(default=0, verbose_name='逻辑删除')
    daily_mark = models.CharField(max_length=50, verbose_name='M3标志', default='', blank=True)

    class Meta:
        ordering = ['id']


class Record(models.Model):
    """变量记录表"""
    id = models.AutoField(primary_key=True)
    variable = models.ForeignKey(Variable, on_delete='CASCADE', max_length=100, verbose_name='记录所属变量')
    time = models.DateTimeField(verbose_name='记录时间', null=False)
    value = models.FloatField(max_length=100, verbose_name='记录值', default=0)
    filling_mark = models.IntegerField(verbose_name='充液标志', default=0)


class OriginAssetData(models.Model):
    """老OCC资产登记信息"""
    id = models.AutoField(primary_key=True)
    site_name = models.CharField(max_length=100)
    asset_name = models.CharField(max_length=100)
    uuid = models.CharField(max_length=100)
    rtu_name = models.CharField(max_length=100)
    norminal = models.IntegerField(default=0, null=True)
    temp = models.IntegerField(default=0, null=True)
    fin = models.CharField(max_length=100, null=True)
    file_name = models.CharField(max_length=100, null=True)
    stp_400v = models.CharField(max_length=100, null=True)
    vap_max = models.IntegerField(default=0, null=True)
    vap_type = models.CharField(max_length=100, null=True)
    tank_name = models.CharField(max_length=100, null=True)
    tank_size = models.FloatField(default=0, null=True)
    levela = models.FloatField(default=0, null=True)
    levelb = models.FloatField(default=0, null=True)
    levelc = models.FloatField(default=0, null=True)
    leveld = models.FloatField(default=0, null=True)
    is_bulk = models.IntegerField(default=0, null=True)
