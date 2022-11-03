import re
import threading
from datetime import datetime, timedelta

import requests
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from pycognito import Cognito
from rest_framework.generics import ListAPIView

from apps.iot.models import AsyncJob, Asset
from utils import jobs, JResp
from utils.pagination import PageNum
from .models import AssetV2, VariableV2, ApsaV2
from .serializer import AssetV2Serializer

URL = 'https://bos.iot.airliquide.com/api/v1'


def get_cognito():
    """完成验证，返回header"""
    # 设置时间
    time_now = datetime.now()
    time_expire = time_now + timedelta(hours=1)

    # 查询数据库存在有效的token，有则返回
    token_record = AsyncJob.objects.filter(name='IOT_TOKEN').order_by('-start_time')
    if token_record:
        token_record = token_record[0]
        if token_record.finish_time > time_now:
            token = token_record.result
            h = {
                'Host': 'bos.iot.airliquide.com',
                'Authorization': token,
                'business-profile-id': '8e15368e-39c7-437f-9721-e5e54dcd207d',
            }
            return h

    # 申请token
    username = 'xiangzhe.hou@airliquide.com'
    password = 'ZXCzxc1234!'
    user = Cognito(
        user_pool_id='eu-west-1_XxAZFKMzE',
        client_id='oppih8pblveb0qb27sl8k9ubc',
        user_pool_region='eu-west-1',
        username=username,
    )
    user.authenticate(password=password)
    token = 'Bearer ' + user.id_token.strip()

    # 存入数据库
    AsyncJob.objects.create(
        name='IOT_TOKEN',
        result=token,
        start_time=time_now,
        finish_time=time_expire,
    )
    # 返回结果
    h = {
        'Host': 'bos.iot.airliquide.com',
        'Authorization': token,
        'business-profile-id': '8e15368e-39c7-437f-9721-e5e54dcd207d',
    }
    return h


def multi_thread_task(multi_num, target_task, task_args):
    # 设置多线程数
    multi_num = multi_num
    to_add_list, h = task_args
    sub_thread_task = []

    # 为每个线程分配任务列表
    for x in range(multi_num):
        to_add_list_length = range(len(to_add_list))
        # 归类序号取余总线程数等于x的元素
        refresh_list = [to_add_list[i] for i in to_add_list_length if i % multi_num == x]
        # 添加至子线程列表
        sub_thread_task.append(threading.Thread(target=target_task, args=(refresh_list, h)))

    # 循环执行线程列表中的任务
    for task in sub_thread_task:
        task.start()
    # 主线程守护子线程
    for task in sub_thread_task:
        task.join()


class AssetRefresh(View):
    def __init__(self, **kwargs):
        self.uuid: str = ""

    def get(self, request):
        # 获取参数
        try:
            self.uuid = request.GET.get("uuid").strip()
            user = request.GET.get('user')
            # 参数验证
            if not all([self.uuid, user]):
                return JResp("参数不齐全", 400)
            if not re.match(r"^[0-9a-z]{8}(-[0-9a-z]{4}){3}-[0-9a-z]{12}$", self.uuid):
                return JResp("uuid格式错误，请检查", 400)
        except Exception:
            return JResp("参数错误", 400)

        # 检查Job状态
        if jobs.check("IOT_ASSET_MANUEL_v2", user=user, params=f"uuid={self.uuid}"):
            return JResp("任务正在进行中，请稍后刷新", 400)

        # 子线程抓取数据
        threading.Thread(target=self.__refresh_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def __refresh_main(self):
        try:
            # 抓取资产信息
            url: str = f"{URL}/assets/" + self.uuid
            asset = requests.get(url, headers=get_cognito()).json()
            url = f'{URL}/assets/{self.uuid}/variables?limit=1000'
            variables = requests.get(url, headers=get_cognito()).json()["content"]
        except Exception as e:
            print(e)
            jobs.update("IOT_ASSET_MANUEL_v2", "错误：向IOT请求asset或解析失败")
            return

        try:
            # 检查uuid是否存在, 存在则更新数据
            if AssetV2.objects.filter(uuid=self.uuid).count() != 0:
                # 更新asset信息
                self.update_asset(asset)
            else:
                # 创建新asset
                self.create_asset(asset)
            # 更新变量
            self.create_update_variables(variables)
        except Exception as e:
            jobs.update("IOT_ASSET_MANUEL_v2", f"错误：信息失败 -> {e[0:100]}")
            return

        # Job信息更新
        jobs.update("IOT_ASSET_MANUEL_v2", f"成功创建/更新asset和其variables,可以在绑定中选择")

    def create_asset(self, asset):
        AssetV2.objects.create(
            uuid=self.uuid,
            name=asset['name'],
            site_name=asset['site']['name']
        )

    def create_update_variables(self, variables):
        v_list = []
        for v in variables:
            v_list.append(VariableV2(
                uuid=v["id"],
                name=v["name"],
                asset_uuid=self.uuid,
            ))
        with transaction.atomic():
            VariableV2.objects.filter(asset_uuid=self.uuid).delete()
            VariableV2.objects.bulk_create(v_list, batch_size=100)

    def update_asset(self, asset):
        a = AssetV2.objects.get(uuid=self.uuid)
        a.name = asset['name'],
        a.site_name = asset['site']['name']
        a.save()


class ApsaV2View(ListAPIView):
    queryset = ApsaV2.objects.all()
    # 序列化器
    serializer_class = AssetV2Serializer
    # 权限
    # permission_classes = [IsAuthenticated]
    # 分页器
    pagination_class = PageNum

    def get_queryset(self):
        region = self.request.query_params.get('region')
        group = self.request.query_params.get('group')
        name = self.request.query_params.get('name')
        queryset = ApsaV2.objects.all()
        if region:
            queryset = queryset.filter(status=region)
        if group:
            queryset = queryset.filter(status=group)
        if name:
            name = name.strip().upper()
            if "CN_" in name:
                queryset = queryset.filter(Q(rtu_name=name) | Q(name=name))
            else:
                queryset = queryset.filter(Q(rtu_name__contains=name) | Q(name__contains=name))
        return queryset


class AssetV2View(ListAPIView):
    queryset = AssetV2.objects.all()
    # 序列化器
    serializer_class = AssetV2Serializer
    # 权限
    # permission_classes = [IsAuthenticated]
    # 分页器
    pagination_class = PageNum

    def get_queryset(self):
        name = self.request.query_params.get('name')
        status = self.request.query_params.get('status')
        queryset = AssetV2.objects.all()
        if status:
            queryset = queryset.filter(status=status)
        if name:
            name = name.strip()
            queryset = queryset.filter(site_name__contains=name)

        return queryset


def migrate_asset() -> int:
    query_set = Asset.objects.filter(tags='onsite')
    q: Asset
    rows_affected: int = 0
    for q in query_set:
        rows_affected += 1
        AssetV2.objects.create(
            uuid=q.uuid,
            name=q.name,
            site_name=q.site.name,
            status=0
        )
    return rows_affected


def migrate_variable() -> int:
    rows_affected: int = 0

    a: AssetV2
    for a in AssetV2.objects.all():
        url = f'{URL}/assets/{a.uuid}/variables?limit=1000'
        variables = requests.get(url, headers=get_cognito()).json()["content"]
        v_list = []
        for v in variables:
            rows_affected += 1
            v_list.append(VariableV2(
                uuid=v["id"],
                name=v["name"],
                asset_uuid=a.uuid,
            ))
        VariableV2.objects.bulk_create(v_list, batch_size=100)
    return rows_affected


def migrate_apsa() -> int:
    rows_affected: int = 0
    return rows_affected


def migrate(c):
    item: str = c.GET.get('item')
    rows_affected: int = 0
    if item == 'asset':
        rows_affected = migrate_asset()
    elif item == 'variable':
        rows_affected = migrate_variable()
    elif item == 'apsa':
        rows_affected = migrate_apsa()

    return JResp(msg=f"rows_affected: {rows_affected}")
