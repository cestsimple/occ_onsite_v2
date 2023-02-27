# -*- coding:utf-8 -*-
from ninja import Router

from utils.custom_response import json_response

"""问卷相关路由"""
questionnaire_router = Router(tags=["问卷相关"])


@questionnaire_router.get("/request", summary="测试")
def request_list(request):
    return json_response()


@questionnaire_router.get("/questionnaires", summary="问卷列表")
def q_list(request, is_template: int = 0, role: str = ""):
    return json_response()
