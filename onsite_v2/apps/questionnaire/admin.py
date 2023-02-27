from django.contrib import admin

# Register your models here.
from .models import Questionnaire, Question

admin.site.register(Questionnaire)
admin.site.register(Question)


class QuestionInline(admin.TabularInline):
    model = Question


class QuestionnaireAdmin(admin.ModelAdmin):
    # 显示字段
    list_display = ['title', 'is_template', 'is_public', 'created_user', 'assigned_role', 'created_at']
    # 省略其他属性和方法
    inlines = [QuestionInline, ]
