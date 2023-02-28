# -*- coding:utf-8 -*-
from django.db import DatabaseError
from ninja import Router

from utils.custom_response import json_response
from .models import Questionnaire, Question
from .schema import QuestionnaireOut, QuestionnaireIn, QuestionIn, QuestionOut
from ..user.models import User, Role

"""问卷相关路由"""
questionnaire_router = Router(tags=["问卷相关"])


@questionnaire_router.get("/questionnaires", summary="问卷列表")
def questionnaire_list(request, is_template: bool = False):
    # 获取用户名称，默认只能看自己创建的问卷
    user = "admin"
    # 查询问卷
    qs = Questionnaire.objects.filter(created_user__username=user)
    # 过滤问卷，是否只看模板
    if is_template:
        qs.filter(is_template=is_template)

    data = [QuestionnaireOut.from_orm(x) for x in qs]
    return json_response(200, '问卷列表查询成功', data)


@questionnaire_router.post("/questionnaire", summary="创建问卷")
def questionnaire_add(request, data: QuestionnaireIn):
    # 问卷是否存在
    if Questionnaire.objects.filter(title=data.title):
        return json_response(400, '创建问卷失败，问卷标题重复')

    # 验证创建人和角色
    user = User.objects.filter(username=data.created_user)
    role = Role.objects.filter(name=data.assigned_role)
    if not all([user, role]):
        return json_response(400, '创建问卷失败，创建人或授权角色不存在')

    # 保存在数据库
    data.assigned_role = role[0]
    data.created_user = user[0]
    try:
        qs = Questionnaire.objects.create(**data.dict())
    except DatabaseError:
        return json_response(500, '创建问卷失败，数据库错误')

    # 返回
    return json_response(200, '创建问卷成功', QuestionnaireOut.from_orm(qs))


@questionnaire_router.put("/questionnaire/{qs_id}", summary="修改问卷")
def questionnaire_edit(request, qs_id: int, data: QuestionnaireIn):
    # 问卷是否存在
    qs = Questionnaire.objects.filter(id=qs_id)
    if not qs:
        return json_response(404, '修改问卷失败，该问卷不存在')

    # 验证创建人和角色
    user = User.objects.filter(username=data.created_user)
    role = Role.objects.filter(name=data.assigned_role)
    if not all([user, role]):
        return json_response(400, '创建问卷失败，创建人或授权角色不存在')

    # 保存在数据库
    try:
        data.assigned_role = role[0]
        data.created_user = user[0]
        qs.update(**data.dict())
        qs[0].save()
    except DatabaseError:
        return json_response(500, '修改问卷失败，')
    print()
    # 返回
    return json_response(200, '修改问卷成功', QuestionnaireOut.from_orm(qs[0]))


@questionnaire_router.delete("/questionnaire/{qs_id}", summary="删除问卷")
def questionnaire_del(request, qs_id: int):
    # 问卷是否存在
    qs = Questionnaire.objects.filter(id=qs_id)
    if not qs:
        return json_response(404, '删除问卷失败，该问卷不存在')
    # 保存在数据库
    try:
        qs.delete()
    except DatabaseError:
        return json_response(500, '删除问卷失败，数据库错误')

    # 返回
    return json_response(200, '删除问卷成功')


@questionnaire_router.post("/question", summary="创建问题")
def question_add(request, data: QuestionIn):
    # 查询问卷
    qs = Questionnaire.objects.filter(id=data.questionnaire)
    if not qs:
        return json_response(404, '创建问题失败，该问卷不存在')
    qs = qs[0]
    # 验证order为正
    if data.order <= 0:
        return json_response(400, '创建问题失败，序号需为正')
    # 查询问卷和id是否唯一
    if Question.objects.filter(questionnaire=qs, order=data.order):
        return json_response(400, '创建问题失败，序号重复')
    # 保存问题
    data.questionnaire = qs
    q = Question.objects.create(**data.dict())
    return json_response(200, '创建问题成功', QuestionOut.from_orm(q))


@questionnaire_router.put("/question/{qid}", summary="修改问题")
def question_edit(request, qid: int, data: QuestionIn):
    # 查询问题
    q = Question.objects.filter(id=qid)
    if not q:
        return json_response(404, '修改问题失败，该问题不存在')
    # 查询问卷
    qs = Questionnaire.objects.filter(id=data.questionnaire)
    if not qs:
        return json_response(404, '修改问题失败，该问卷不存在')
    qs = qs[0]
    # 验证order为正
    if data.order <= 0:
        return json_response(400, '修改问题失败，序号需为正')
    # 查询问卷和id是否唯一
    if Question.objects.filter(questionnaire=qs, order=data.order) and data.order != q[0].order:
        return json_response(400, '修改问题失败，序号重复')
    # 保存问题
    data.questionnaire = qs
    q.update(**data.dict())
    q[0].save()
    return json_response(200, '修改问题成功', QuestionOut.from_orm(q[0]))


@questionnaire_router.delete("/question/{qid}", summary="删除问题")
def question_del(request, qid: int):
    # 查询问题
    q = Question.objects.filter(id=qid)
    if not q:
        return json_response(404, '删除问题失败，该问题不存在')
    # 保存在数据库
    try:
        q.delete()
    except DatabaseError:
        return json_response(500, '删除问题失败，数据库错误')

    # 返回
    return json_response(200, '删除问题成功')
