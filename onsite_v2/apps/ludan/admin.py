from django.contrib import admin

# Register your models here.
from .models import Car, ColumnSetting

admin.site.register(Car)
admin.site.register(ColumnSetting)