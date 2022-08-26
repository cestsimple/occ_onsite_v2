from django.db import models

REGION_CHOICES = [
    ('qp', '青浦'),
    ('cg', '成功'),
    ('skid', '小罐车'),
    ('med', '医用氧'),
    ('kj', '科举'),
    ('pag', '可燃气'),
]

ACCOUNT_CHOICES = [
    ('ys', '压缩'),
    ('yk', '液空')
]


# Create your models here
class Car(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='车辆id')
    plate = models.CharField(max_length=10, unique=True, null=False, verbose_name='车牌')
    region = models.CharField(max_length=20, choices=REGION_CHOICES, verbose_name='所属区域')
    account = models.CharField(max_length=20, choices=ACCOUNT_CHOICES, verbose_name='路单账号')
    go_time = models.CharField(max_length=20, null=False, verbose_name='出车时间')
    parking = models.CharField(max_length=50, null=False, verbose_name='出场地点')
    ty_comp = models.CharField(max_length=50, null=False, verbose_name='托运业户')
    goods = models.CharField(max_length=50, null=False, verbose_name='物品')
    ship_comp = models.CharField(max_length=100, null=False, verbose_name='装货业户')
    weight = models.FloatField(null=False, verbose_name='车重')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return self.plate

    class Meta:
        verbose_name_plural = "车辆信息表"


class ColumnSetting(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='配置id')
    region = models.CharField(max_length=20, unique=True, choices=REGION_CHOICES, verbose_name='区域')
    go_date = models.CharField(max_length=10, default='', verbose_name='日期列')
    plate = models.CharField(max_length=10, default='', verbose_name='车牌列')
    driver = models.CharField(max_length=10, default='', verbose_name='驾驶员列')
    driver_super = models.CharField(max_length=10, default='', verbose_name='押运员列')
    dispatcher = models.CharField(max_length=10, blank=True, verbose_name='调度列')
    customer = models.CharField(max_length=10, default='', verbose_name='客户名称列')
    address = models.CharField(max_length=10, default='', verbose_name='客户地址列')
    tel = models.CharField(max_length=10, default='', verbose_name='客户电话列')
    trip = models.CharField(max_length=10, blank=True, verbose_name='航次列')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return self.region

    class Meta:
        verbose_name_plural = "区域表格信息列配置表"


# LOCATOR_CHOICE = [
#     ("xpath", "元素Xpath"),
#     ("class", "元素类名"),
#     ("css", "元素CSS"),
#     ("id", "元素ID"),
#     ("name", "元素Name属性"),
#     ("tag", "元素Tag"),
# ]
#
# INTERACTION_CHOICE = [
#     ("click", "点击"),
#     ("send_key", "按键"),
#     ("clear", "清除内容"),
# ]
#
#
# class SeleniumStep(models.Model):
#     id = models.AutoField(primary_key=True, verbose_name="步骤id")
#     task = models.IntegerField(null=False, verbose_name="所属任务")
#     order = models.IntegerField(null=False, verbose_name="执行顺序")
#     locator = models.CharField(max_length=10, choices=LOCATOR_CHOICE, verbose_name="定位方式")
#     interaction = models.CharField(max_length=10, choices=LOCATOR_CHOICE, verbose_name="互动类型")
#     args = models.CharField(max_length=500, verbose_name="参数", null=True)
