from django.db import models
from apps.user.models import User


class AsyncJob(models.Model):
    """系统设置"""
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    job = models.CharField(max_length=30, verbose_name='储罐大小', null=False, blank=False)
    finished = models.BooleanField(default=False)
    create_time = models.DateTimeField()
    finish_time = models.DateTimeField()


class Region(models.Model):
    """地区表"""
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    name = models.CharField(max_length=30, verbose_name='地区名', default='')
    is_deleted = models.BooleanField(default=False)


class Engineer(models.Model):
    """维修工程师表"""
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    region = models.ForeignKey(Region, on_delete='on_delete=models.SET_NULL', null=True, blank=True)
    mtgroup = models.CharField(max_length=30, verbose_name='维修分组', default='')
    name = models.CharField(max_length=30, verbose_name='姓名', default='')
    user = models.ForeignKey(User, on_delete='on_delete=models.SET_NULL', null=True, blank=True)
    is_deleted = models.BooleanField(default=False)


class BulkSpec(models.Model):
    """bulk信息单"""
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    tank_size = models.FloatField(max_length=30, verbose_name='储罐大小', default=0)
    tank_func = models.CharField(max_length=30, verbose_name='储罐功能', default='')
    level_a = models.FloatField(max_length=30, verbose_name='filling标志a', default=1)
    level_b = models.FloatField(max_length=30, verbose_name='filling标志b', default=6)
    level_c = models.FloatField(max_length=30, verbose_name='filling标志c', default=10)
    level_d = models.FloatField(max_length=30, verbose_name='filling标志d', default=0.5)
    filling_js = models.IntegerField(default=0, verbose_name='计算filling')


class ApsaSpec(models.Model):
    """apsa信息单"""
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    onsite_type = models.CharField(max_length=30, verbose_name='类型', default='')
    onsite_series = models.CharField(max_length=30, verbose_name='型号', default='')
    facility_fin = models.CharField(max_length=50, verbose_name='项目号', default='')
    daily_js = models.IntegerField(default=0, verbose_name='计算daily')
    temperature = models.FloatField(max_length=30, verbose_name='daily温度', default=0)
    vap_max = models.CharField(max_length=30, verbose_name='汽化器最大能力', default='')
    vap_type = models.CharField(max_length=30, verbose_name='汽化器类型', default='')
    norminal_flow = models.IntegerField(verbose_name='合同产量', default=0)
    daily_bind = models.CharField(max_length=100, verbose_name='daily绑定资产id', default='')
    flow_meter = models.CharField(max_length=100, verbose_name='流量计变量id', default='')
    cooling_fixed = models.FloatField(max_length=10, verbose_name='cooling设定值', default=0)


class Site(models.Model):
    """气站表"""
    id = models.AutoField(primary_key=True, verbose_name='资产数字id')
    uuid = models.CharField(max_length=100, verbose_name='资产UUID')
    cname = models.CharField(max_length=50, verbose_name='气站中文名')
    ename = models.CharField(max_length=50, verbose_name='气站英文名')
    engineer = models.ForeignKey(Engineer, on_delete='on_delete=models.SET_NULL', null=True, blank=True)
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'site'
        verbose_name = 'List for all assets'


class Asset(models.Model):
    """资产表"""
    id = models.AutoField(primary_key=True, verbose_name='资产数字id')
    uuid = models.CharField(max_length=100, verbose_name='资产UUID')
    name = models.CharField(max_length=50, verbose_name='资产名')
    site = models.ForeignKey(Site, on_delete='on_delete=models.SET_NULL', null=True, blank=True)
    bulk_spec = models.ForeignKey(BulkSpec, on_delete='on_delete=models.SET_NULL', null=True, blank=True)
    apsa_spec = models.ForeignKey(ApsaSpec, on_delete='on_delete=models.SET_NULL', null=True, blank=True)
    status = models.CharField(max_length=20, verbose_name='资产状态', default='')
    variables_num = models.IntegerField(default=-1, verbose_name='变量数')
    tags = models.CharField(max_length=100, verbose_name='标签', default='')
    comment = models.CharField(max_length=50, verbose_name='备注', default='')
    confirm = models.IntegerField(default=0, verbose_name='逻辑删除')
    class Meta:
        db_table = 'asset'
        verbose_name = 'List for all assets'
