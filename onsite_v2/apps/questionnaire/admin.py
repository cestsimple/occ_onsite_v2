from django.contrib import admin

# Register your models here.
from .models import Questionnaire, Question

admin.site.register(Questionnaire)
admin.site.register(Question)
