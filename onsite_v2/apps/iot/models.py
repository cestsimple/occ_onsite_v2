from django.db import models


class Site(models.Model):
    """气站表"""
    id = models.AutoField(primary_key=True, verbose_name='资产数字id')
    uuid = models.CharField(max_length=100, verbose_name='资产UUID')
    cname = models.CharField(max_length=50, verbose_name='气站中文名')
    ename = models.CharField(max_length=50, verbose_name='气站英文名')

    status = models.BooleanField(default=True)


class asset(models.Model):
    """资产信息表"""

    id = models.AutoField(primary_key=True, verbose_name='资产数字id')
    uuid = models.CharField(max_length=100, verbose_name='资产UUID')
    name = models.CharField(max_length=50, verbose_name='资产名')
    site = models.ForeignKey(Site, on_delete='CASCADE', blank=True)
    confirm = models.IntegerField(default=0, verbose_name='逻辑删除')
    status = models.CharField(max_length=20, verbose_name='资产状态', default='')



    facility_fin = models.CharField(max_length=50, verbose_name='项目号', default='')
    vap_max = models.CharField(max_length=30, verbose_name='汽化器最大能力', default='')
    vap_type = models.CharField(max_length=30, verbose_name='汽化器类型', default='')
    tank_size = models.FloatField(max_length=30, verbose_name='储罐大小', default=0)
    norminal_flow = models.IntegerField(verbose_name='合同产量', default=0)
    tags = models.CharField(max_length=100, verbose_name='标签', default='')
    temperature = models.FloatField(max_length=30, verbose_name='daily温度', default=0)

    daily_js = models.IntegerField(default=0, verbose_name='计算daily')
    daily_bind = models.CharField(max_length=100, verbose_name='daily绑定资产id', default='')
    flow_meter = models.CharField(max_length=100, verbose_name='流量计变量id', default='')
    cooling_fixed = models.FloatField(max_length=10, verbose_name='cooling设定值', default=0)
    filling_js = models.IntegerField(default=0, verbose_name='计算filling')
    variables_num = models.IntegerField(default=-1, verbose_name='变量数')
    comment = models.CharField(max_length=50, verbose_name='备注', default='')
    is_bulk = models.IntegerField(null=False, verbose_name='变量数')

    class Meta:
        db_table = 'onsite_assets'
        verbose_name = 'List for all assets'


class Region(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='资产数字id')

class Engineer(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='资产数字id')

class BulkSpec(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='资产数字id')
    tank_func = models.CharField(max_length=30, verbose_name='储罐功能', default='')
    level_a = models.FloatField(max_length=30, verbose_name='filling标志a', default=1)
    level_b = models.FloatField(max_length=30, verbose_name='filling标志b', default=6)
    level_c = models.FloatField(max_length=30, verbose_name='filling标志c', default=10)
    level_d = models.FloatField(max_length=30, verbose_name='filling标志d', default=0.5)


class ApsaSpec(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='资产数字id')
    onsite_type = models.CharField(max_length=30, verbose_name='类型', default='')
    onsite_series = models.CharField(max_length=30, verbose_name='型号', default='')
    region = models.CharField(max_length=30, verbose_name='区域', default='')
    mtgroup = models.CharField(max_length=30, verbose_name='维修组别', default='')