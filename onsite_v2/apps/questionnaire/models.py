# Create your models here.
from django.db import models

from apps.user.models import User, Role

YES_OR_NO_CHOICE = [
    (1, '是'),
    (0, '否'),
]


class Questionnaire(models.Model):
    """问卷表"""
    id = models.AutoField(primary_key=True, verbose_name='问卷数字id')
    title = models.CharField(max_length=255, verbose_name='问卷标题')
    is_template = models.BooleanField(default=0, verbose_name='设置为模板')
    is_public = models.BooleanField(default=0, verbose_name='仅自己可见')
    created_user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建人')
    assigned_role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name='角色对象')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return f'{self.created_user} 创建了 "{self.title}"'

    class Meta:
        indexes = [
            models.Index(fields=['created_user']),
        ]


class Question(models.Model):
    """问卷问题表"""
    TEXT = 'text'
    NUMBER = 'number'
    BOOLEAN = 'boolean'
    CHOICE = 'choice'
    QUESTION_TYPE_CHOICES = [
        (TEXT, 'Text'),
        (NUMBER, 'Number'),
        (BOOLEAN, 'Boolean'),
        (CHOICE, 'Choice'),
    ]
    id = models.AutoField(primary_key=True, verbose_name='问题数字id')
    order = models.IntegerField(verbose_name="问题序号")
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.CASCADE)
    content = models.CharField(max_length=255)
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default=TEXT)
    required = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.questionnaire.title} 的: "{self.content}"'

    class Meta:
        indexes = [
            models.Index(fields=['questionnaire']),
        ]


class Answer(models.Model):
    """问卷回答表"""
    id = models.AutoField(primary_key=True, verbose_name='问卷回答数字id')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user} answered "{self.question}"'

    class Meta:
        indexes = [
            models.Index(fields=['question', 'user']),
        ]
