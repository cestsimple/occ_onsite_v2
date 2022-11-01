import re
import threading
from datetime import datetime, timedelta

import requests
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from pycognito import Cognito

from apps.iot.models import AsyncJob
from utils import jobs, JResp, pagination
from .models import AssetV2, VariableV2, ApsaV2

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


def apsa_list(c):
    if c.method == 'GET':
        page = c.GET.get('page')
        pagesize = c.GET.get('pagesize')
        region = c.GET.get('region')
        group = c.GET.get('group')
        name = c.GET.get('name')

        # 过滤
        query_set = ApsaV2.objects.all()
        if region:
            query_set = query_set.filter(region=region)
        if group:
            query_set = query_set.filter(group=group)
        if name:
            name = name.strip().upper()
            if "CN_" in name:
                query_set = query_set.filter(Q(rtu_name=name) | Q(name=name))
            else:
                query_set = query_set.filter(Q(rtu_name__contains=name) | Q(name__contains=name))
        # 分页
        if not all([page, pagesize]):
            page = 1
            pagesize = 10
        else:
            page = int(page)
            pagesize = int(pagesize)
        p = pagination.paginator(page, pagesize, query_set)
        # 序列化
        res = []
        q: ApsaV2
        for q in p['list']:
            res.append({
                'id': q.id,
                'name': q.name,
                'rtu_name': q.rtu_name,
                'region': q.region,
                'group': q.group,
                'engineer': q.engineer.first_name,
                'comment': q.comment,
                'onsite_type': q.onsite_type,
                'onsite_series': q.onsite_series,
                'facility_fin': q.facility_fin,
                'temperature': q.temperature,
                'vap_max': q.vap_max,
                'vap_type': q.vap_type,
                'norminal_flow': q.norminal_flow,
                'daily_bind': q.daily_bind,
                'cooling_fixed': q.cooling_fixed,
                'mark': q.mark,
                'daily_js': q.daily_js,
                'm3_q7': q.m3_q7,
                'm3_q6': q.m3_q6,
                'm3_q5': q.m3_q5,
                'm3_q1': q.m3_q1,
                'm3_prod': q.m3_prod,
                'm3_peak': q.m3_peak,
                'm3_tot': q.m3_tot,
                'h_stpdft': q.h_stpdft,
                'h_stpal': q.h_stpal,
                'h_stp400v': q.h_stp400v,
                'h_prod': q.h_prod,
                'flow_meter': q.flow_meter,
                'status': q.status,
                'created_at': q.created_at,
                'updated_at': q.updated_at,
            })
        # 返回响应
        p['list'] = res
        return JResp('ok', 200, p)
