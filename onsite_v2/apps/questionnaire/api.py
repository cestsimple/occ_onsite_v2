# -*- coding:utf-8 -*-
from django.db import DatabaseError
from ninja import Router

from utils.custom_response import json_response
from .models import Questionnaire
from .schema import QuestionnaireOut, QuestionnaireIn

"""问卷相关路由"""
questionnaire_router = Router(tags=["问卷相关"])


@questionnaire_router.get("/request", summary="测试")
def request_list(request):
    return json_response()


@questionnaire_router.get("/questionnaires", summary="问卷列表")
def questionnaire_list(request, is_template: int = 0):
    # 获取用户名称，默认只能看自己创建的问卷
    user = "admin"
    # 查询问卷
    qs = Questionnaire.objects.filter(created_user=user)
    # 过滤问卷，是否只看模板
    if is_template:
        qs.filter(is_template=is_template)

    data = [QuestionnaireOut.from_orm(x) for x in qs]
    return json_response(200, '问卷列表查询成功', data)


@questionnaire_router.post("/questionnaire", summary="创建问卷")
def questionnaire_add(request, data: QuestionnaireIn):
    # 问卷是否存在
    if not Questionnaire.objects.filter(title=data.title):
        return json_response(400, '创建问卷失败，问卷标题重复')
    # 保存在数据库
    try:
        q = Questionnaire.objects.create(**data.dict())
    except DatabaseError:
        return json_response(500, '创建问卷失败，数据库错误')

    # 返回
    return json_response(200, '创建问卷成功', QuestionnaireOut.from_orm(q))


@questionnaire_router.put("/questionnaire/{qs_id}", summary="修改问卷")
def questionnaire_edit(request, qs_id: int, data: QuestionnaireIn):
    # 问卷是否存在
    q = Questionnaire.objects.filter(id=qs_id)
    if not q:
        return json_response(404, '修改问卷失败，该问卷不存在')
    # 保存在数据库
    try:
        q.update(**data)
    except DatabaseError:
        return json_response(500, '修改问卷失败，')

    # 返回
    return json_response(200, '修改问卷成功', QuestionnaireOut.from_orm(q))


@questionnaire_router.delete("/questionnaire/{qs_id}", summary="删除问卷")
def questionnaire_del(request, qs_id: int):
    # 问卷是否存在
    q = Questionnaire.objects.filter(id=qs_id)
    if not q:
        return json_response(404, '删除问卷失败，该问卷不存在')
    # 保存在数据库
    try:
        q.delete()
    except DatabaseError:
        return json_response(500, '删除问卷失败，数据库错误')

    # 返回
    return json_response(200, '删除问卷成功')
