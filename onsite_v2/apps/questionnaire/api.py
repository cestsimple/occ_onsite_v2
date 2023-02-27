# -*- coding:utf-8 -*-
from ninja import Router

from utils.custom_response import json_response
from .models import Questionnaire
from .schema import QuestionnaireOut

"""问卷相关路由"""
questionnaire_router = Router(tags=["问卷相关"])


@questionnaire_router.get("/request", summary="测试")
def request_list(request):
    return json_response()


@questionnaire_router.get("/questionnaires", summary="问卷列表")
def q_list(request, is_template: int = 0):
    # 获取用户名称，默认只能看自己创建的问卷
    user = "admin"
    # 查询问卷
    qs = Questionnaire.objects.filter(created_user=user)
    # 过滤问卷，是否只看模板
    if is_template:
        qs.filter(is_template=is_template)

    data = [QuestionnaireOut.from_orm(x) for x in qs]
    return json_response(200, '问卷列表查询成功', data)
