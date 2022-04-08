import threading

from django.shortcuts import render
# Create your views here
from pycognito import Cognito
from .models import AsyncJob
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, timedelta


def get_cognito():
    """完成验证，返回token"""
    # 设置时间
    time_now = datetime.now()
    time_expire = time_now +timedelta(hours=1)
    token = ''

    # 查询数据库存在有效的token，有则返回
    token_record = AsyncJob.objects.filter(name='IOT_TOKEN').order_by('-start_time')[0]
    if token_record.count():
        if token_record.finish_time > time_now:
            token = token_record.result
            return token

    # 申请token
    username = 'xiangzhe.hou@airliquide.com'
    password = 'Sunboy27!'
    user = Cognito(
        user_pool_id='eu-west-1_XxAZFKMzE',
        client_id='oppih8pblveb0qb27sl8k9ubc',
        user_pool_region='eu-west-1',
        username=username,
    ).authenticate(password=password)
    token = 'Bearer ' + user.id_token.strip()

    # 存入数据库
    AsyncJob.objects.create(
        name='IOT_TOKEN',
        result=token,
        start_time=time_now,
        finish_time=time_expire,
    )

    # 返回结果
    return token


def multi_thread_task(multi_num, target_task, task_args):
    # 设置多线程数
    multi_num = multi_num
    to_add_list = task_args
    sub_thread_task = []

    # 为每个线程分配任务列表
    for x in range(multi_num):
        to_add_list_length = range(len(to_add_list))
        # 归类序号取余总线程数等于x的元素
        refresh_list = [to_add_list[i] for i in to_add_list_length if i % multi_num == x]
        # 添加至子线程列表
        sub_thread_task.append(threading.Thread(target=target_task, args=(refresh_list,)))

    # 循环执行线程列表中的任务
    for task in sub_thread_task:
        try:
            task.start()
        except Exception as e:
            print(f"进程创建失败 - {e}")


class SiteData(APIView):
    def get(self, request):
        # 检查Job状态
        job = AsyncJob.objects.filter(name='IOT_SITE').order_by('-start_time')[0]
        if job.count and not job.finished:
            return Response({'status': 400, 'msg': '有未完成任务正在执行,请稍后尝试'})

        # 添加Job状态
        job = AsyncJob.objects.create(
            name='IOT_SITE',
            start_time=datetime.now(),
        )

        # 创建子线程

        # 返回相应结果
        return Response({'status': 200, 'msg': '请求成功，正在刷新中'})

    def refresh_sub(self):
        pass