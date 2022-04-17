from django.db import models
from apps.iot.models import Bulk


class Filling(models.Model):
    """Onsite 充液表"""
    id = models.AutoField(primary_key=True, verbose_name='充液数字id')
    bulk = models.ForeignKey(Bulk, on_delete='CASCADE', max_length=100, verbose_name='充液资产')
    time_1 = models.DateTimeField(verbose_name="Time Before")
    time_2 = models.DateTimeField(verbose_name="Time After")
    level_1 = models.FloatField(max_length=20, verbose_name="Level Before")
    level_2 = models.FloatField(max_length=20, verbose_name="Level After")
    quantity = models.FloatField(max_length=20, verbose_name="Filling Quantity")
    is_deleted = models.IntegerField(default=0)
    confirm = models.IntegerField(verbose_name='确认标志', default=0)
