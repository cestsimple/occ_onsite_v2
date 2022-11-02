# from django.db import models
#
# # Create your models here.
# class Ticket(models.Model):
#     id = models.AutoField(primary_key=True, verbose_name='工单id')
#     type = models.CharField(max_length=50, verbose_name="工单类型")
#     title = models.CharField(max_length=200, verbose_name="工单标题")
#     content = models.TextField(verbose_name="工单内容")
#     user = models.IntegerField(verbose_name="发起人id")
#     mail = models.CharField("联系邮箱")
#     tel = models.CharField("联系电话")
#     worker = models.IntegerField(verbose_name="负责人id")
#     status = models.CharField(verbose_name="进度")
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
#     updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
#
#     class Meta:
#         ordering = ['id']
#         db_table = 'tb_ticket_ticket'
