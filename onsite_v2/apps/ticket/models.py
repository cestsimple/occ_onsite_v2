# from django.db import models
#
# # Create your models here.
# class Ticket(models.Model):
#     id = models.AutoField(primary_key=True, verbose_name='����id')
#     type = models.CharField(max_length=50, verbose_name="��������")
#     title = models.CharField(max_length=200, verbose_name="��������")
#     content = models.TextField(verbose_name="��������")
#     user = models.IntegerField(verbose_name="������id")
#     mail = models.CharField("��ϵ����")
#     tel = models.CharField("��ϵ�绰")
#     worker = models.IntegerField(verbose_name="������id")
#     status = models.CharField(verbose_name="����")
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name='����ʱ��')
#     updated_at = models.DateTimeField(auto_now=True, verbose_name='����ʱ��')
#
#     class Meta:
#         ordering = ['id']
#         db_table = 'tb_ticket_ticket'
