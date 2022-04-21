from django.db import models
from apps.iot.models import Bulk, Apsa
from apps.user.models import User


class Filling(models.Model):
    """Onsite 充液表"""
    id = models.AutoField(primary_key=True, verbose_name='充液数字id')
    bulk = models.ForeignKey(Bulk, on_delete='CASCADE', max_length=100, verbose_name='充液资产')
    time_1 = models.DateTimeField(verbose_name="Time Before")
    time_2 = models.DateTimeField(verbose_name="Time After")
    level_1 = models.FloatField(max_length=20, verbose_name="Level Before")
    level_2 = models.FloatField(max_length=20, verbose_name="Level After")
    quantity = models.FloatField(max_length=20, verbose_name="Filling Quantity")
    confirm = models.IntegerField(verbose_name='确认标志', default=0)

    class Meta:
        ordering = ['id']


class Daily(models.Model):
    """Daily原始数据表"""
    id = models.AutoField(primary_key=True, verbose_name='日报数字id')
    apsa = models.ForeignKey(Apsa, on_delete='CASCADE', max_length=100, verbose_name='日报资产')
    date = models.DateTimeField(verbose_name="Time")
    h_prod = models.FloatField(verbose_name="生产时间", default='0')
    h_stpal = models.FloatField(max_length=20, verbose_name='手动停机时间', default=0)
    h_stpdft = models.FloatField(max_length=20, verbose_name='故障停机时间', default=0)
    h_stp400v = models.FloatField(max_length=20, verbose_name='电源停机时间', default=0)
    m3_prod = models.FloatField(max_length=20, verbose_name='产量', default=0)
    m3_tot = models.FloatField(max_length=20, verbose_name='客户用量', default=0)
    m3_q1 = models.FloatField(max_length=20, default=0)
    m3_peak = models.FloatField(max_length=20, default=0)
    m3_q5 = models.FloatField(max_length=20, default=0)
    m3_q6 = models.FloatField(max_length=20, default=0)
    m3_q7 = models.FloatField(max_length=20, default=0)
    filling = models.FloatField(max_length=20, default=0)
    lin_tot = models.FloatField(max_length=20, default=0)
    flow_meter = models.FloatField(max_length=20, default=0)
    success = models.IntegerField(default=0)
    confirm = models.IntegerField(default=0)

    class Meta:
        ordering = ['id']


class DailyMod(models.Model):
    """Daily修正数据表"""
    id = models.AutoField(primary_key=True, verbose_name='日报数字id')
    apsa = models.ForeignKey(Apsa, on_delete='CASCADE', max_length=100, verbose_name='日报资产')
    date = models.DateTimeField(verbose_name="Time")
    h_prod_mod = models.FloatField(max_length=50, default=0)
    h_stpal_mod = models.FloatField(max_length=20, default=0)
    h_stpdft_mod = models.FloatField(max_length=20, default=0)
    h_stp400v_mod = models.FloatField(max_length=20, default=0)
    m3_prod_mod = models.FloatField(max_length=20, default=0)
    m3_tot_mod = models.FloatField(max_length=20, default=0)
    m3_q1_mod = models.FloatField(max_length=20, default=0)
    m3_peak_mod = models.FloatField(max_length=20, default=0)
    m3_q5_mod = models.FloatField(max_length=20, default=0)
    m3_q6_mod = models.FloatField(max_length=20, default=0)
    m3_q7_mod = models.FloatField(max_length=20, default=0)
    lin_tot_mod = models.FloatField(max_length=20, default=0)
    flow_meter_mod = models.FloatField(max_length=20, default=0)
    comment = models.CharField(max_length=300, default='')
    user = models.CharField(max_length=100, verbose_name="最后修改用户")


class Malfunction(models.Model):
    """ 停机记录表 """
    id = models.AutoField(primary_key=True, verbose_name='停机数字id')
    apsa = models.ForeignKey(Apsa, on_delete='CASCADE', max_length=100, verbose_name='停机资产')
    t_start = models.DateTimeField(verbose_name="停机开始时间")
    t_end = models.DateTimeField(verbose_name="停机结束时间")
    stop_count = models.IntegerField(verbose_name='停机次数', default=1)
    stop_hour = models.FloatField(max_length=20, default=0)
    stop_consumption = models.FloatField(max_length=20, default=0)
    stop_label = models.CharField(max_length=100, default='')
    stop_alarm = models.CharField(max_length=100, default='')
    reason_main = models.CharField(max_length=100, default='')
    reason_l1 = models.CharField(max_length=100, default='')
    reason_l2 = models.CharField(max_length=100, default='')
    reason_l3 = models.CharField(max_length=100, default='')
    reason_l4 = models.CharField(max_length=100, default='')
    reason_detail_1 = models.CharField(max_length=100, default='')
    reason_detail_2 = models.CharField(max_length=100, default='')
    mt_comment = models.CharField(max_length=200, default='')
    occ_comment = models.CharField(max_length=200, default='')
    change_date = models.DateTimeField(verbose_name="最后修改时间")
    change_user = models.CharField(max_length=100, verbose_name="最后修改用户")
    confirm = models.IntegerField(verbose_name='确认标志', default=0)

    class Meta:
        ordering = ['id']


class Reason(models.Model):
    """ 停机原因表 """
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    cname = models.CharField(max_length=100, default='')
    ename = models.CharField(max_length=100, default='')
    # 默认一对多查询related_name .MalfunctionReason_set.all()
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='subs', blank=True, verbose_name='上级原因')


class ReasonDetail(models.Model):
    """ 停机原因分类表 """
    id = models.AutoField(primary_key=True, verbose_name='数字id')
    cname = models.CharField(max_length=100, default='')
    ename = models.CharField(max_length=100, default='')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='subs', blank=True, verbose_name='上级原因')
