# -*- coding:utf-8 -*-
from ninja import Router

from utils.custom_response import json_response

"""请求相关路由"""
request_router = Router(tags=["发送请求相关"])


@request_router.get("/request", summary="测试")
def request_list(request):
    return json_response()
