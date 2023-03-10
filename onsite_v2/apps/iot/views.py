import json
import re
import threading
import time
from datetime import datetime, timedelta
from itertools import chain

import requests
from django.db import DatabaseError
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from pycognito import Cognito
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from utils import jobs, JResp
from utils.CustomMixins import UpdateListRetrieveViewSet
from utils.pagination import PageNum
from .models import AsyncJob, Site, Asset, Variable, Apsa, Bulk, Record
from .serializer import SiteSerializer, ApsaSerializer, BulkSerializer, VariableSerializer, AssetApsaSerializer, \
    AssetBulkSerializer, AsyncJobSerializer
from ..onsite.models import MonthlyVariable
from ..user.models import User

URL = 'https://bos.iot.airliquide.com/api/v1'

# 禁用requests warning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


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
    password = 'ZXCzxc123!'
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


class SiteData(View):
    def get(self, request):
        # 检查Job状态
        if jobs.check('IOT_SITE'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 创建子线程
        threading.Thread(target=self.refresh_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def refresh_main(self):
        # 设置请求信息
        header = get_cognito()
        url = URL + '/sites?limit=1000&page=0'
        res = requests.get(url, headers=header, verify=False).json()
        page_max = res['page']['maxPage']
        contents = res['content']
        # 获取全部页数
        if page_max != 0:
            for i in range(1, page_max + 1):
                url = f'{URL}/sites?limit=1000&page={i}'
                res = requests.get(url, headers=header, verify=False).json()
                contents += res['content']

        # 分类Site
        sites_iot_dic = {}
        for content in contents:
            sites_iot_dic[content['id']] = content
        sites_db_uuid = [x.uuid for x in Site.objects.filter(confirm__gt=-1)]
        site_new_uuid = [j for j in sites_iot_dic.keys() if j not in sites_db_uuid]
        site_delete_uuid = [k for k in sites_db_uuid if k not in sites_iot_dic.keys()]
        site_update_uuid = [l for l in sites_db_uuid if l in sites_iot_dic.keys()]

        # 创建site
        list_create = []
        for new_site in site_new_uuid:
            site = Site.objects.filter(uuid=new_site)
            if site.count() == 0:
                list_create.append(
                    Site(
                        uuid=new_site,
                        name=sites_iot_dic[new_site]['name'],
                    )
                )
            elif site.count() == 1:
                site_update_uuid.append(new_site)

        # 更新site
        list_update = []
        for update_site in site_update_uuid:
            site = Site.objects.get(uuid=update_site)
            site.name = sites_iot_dic[update_site]['name']
            if site.confirm == -1:
                site.confirm = 0
            list_update.append(site)

        # 删除site
        num = 0
        for delete_site in site_delete_uuid:
            site = Site.objects.get(uuid=delete_site)
            site.confirm = -1
            site.save()
            num += 1

        # 批量写入数据库
        try:
            Site.objects.bulk_create(list_create, batch_size=10)
            Site.objects.bulk_update(list_update, fields=['name'])
        except Exception as e:
            print(e)
            jobs.update('IOT_SITE', e)

        # console输出
        print(f"更新{len(list_update)}个site资产")
        for x in list_create:
            print(f"新建site资产: {x.name}")
        print(f"删除site:{len(site_delete_uuid)}个")

        # 更新Job状态
        jobs.update("IOT_SITE", f"新建{len(list_create)}个气站,删除{num}个气站,更新{len(list_update)}个气站")


class AssetData(View):
    def get(self, request):
        # 检查Job状态
        if jobs.check('IOT_ASSET'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 创建子线程
        threading.Thread(target=self.refresh_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def refresh_main(self):
        # 设置请求信息
        header = get_cognito()
        url = URL + '/assets?limit=1000&page=0'
        res = requests.get(url, headers=header, verify=False).json()
        page_max = res['page']['maxPage']
        contents = res['content']
        # 获取全部页数
        if page_max != 0:
            for i in range(1, page_max + 1):
                url = f'{URL}/assets?limit=1000&page={i}'
                res = requests.get(url, headers=header, verify=False).json()
                contents += res['content']

        # 分类
        assets_iot_dic = {}
        for content in contents:
            assets_iot_dic[content['id']] = content
        assets_db_uuid = [x.uuid for x in Asset.objects.filter(confirm__gt=-1)]

        asset_new_uuid = [j for j in assets_iot_dic.keys() if j not in assets_db_uuid]
        asset_delete_uuid = [k for k in assets_db_uuid if k not in assets_iot_dic.keys()]
        asset_update_uuid = [l for l in assets_db_uuid if l in assets_iot_dic.keys()]

        # 创建
        list_create = []
        for new_asset in asset_new_uuid:
            site = Site.objects.filter(uuid=assets_iot_dic[new_asset]['site']['id'])
            if site:
                site = site[0]
            asset = Asset.objects.filter(uuid=new_asset)
            if asset.count() == 0:
                list_create.append(
                    Asset(
                        uuid=new_asset,
                        name=assets_iot_dic[new_asset]['name'],
                        rtu_name='',
                        site=site,
                        status=assets_iot_dic[new_asset]['status']['name'],
                        variables_num=assets_iot_dic[new_asset]['totalVariables'],
                    )
                )
            elif asset.count() == 1:
                asset_update_uuid.append(new_asset)

        # 更新
        list_update = []
        for update_asset in asset_update_uuid:
            asset = Asset.objects.get(uuid=update_asset)
            site = Site.objects.filter(uuid=assets_iot_dic[update_asset]['site']['id'])
            if site:
                site = site[0]
                asset.site = site
            asset.name = assets_iot_dic[update_asset]['name']
            asset.status = assets_iot_dic[update_asset]['status']['name']
            asset.variables_num = assets_iot_dic[update_asset]['totalVariables']
            if asset.confirm == -1:
                asset.confirm = 0
            list_update.append(asset)

        # 删除
        num = 0
        for delete_asset in asset_delete_uuid:
            asset = Asset.objects.get(uuid=delete_asset)
            asset.confirm = -1
            asset.save()
            num += 1

        # 批量写入数据库
        try:
            Asset.objects.bulk_create(list_create, batch_size=10)
            Asset.objects.bulk_update(list_update, batch_size=10, fields=['name', 'site', 'status', 'variables_num'])
        except Exception as e:
            print(e)
            jobs.update('IOT_ASSET', e)

        # console输出
        print(f"更新{len(list_update)}个asset资产")
        for x in list_create:
            print(f"新建asset资产: {x.name}")
        print(f"删除asset资产{len(asset_delete_uuid)}个")

        # 更新Job状态
        jobs.update("IOT_ASSET", f"新建{len(list_create)}个资产,删除{num}个资产,更新{len(list_update)}个资产")


class TagData(View):
    def __init__(self):
        self.assets = []

    def get(self, request):
        # 检查Job状态
        if jobs.check('IOT_TAG'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 是否强制全部刷新/部分刷新
        fast = request.GET.get('fast')
        if fast:
            self.assets = Asset.objects.filter(tags='')
        else:
            self.assets = Asset.objects.filter(confirm__gt=-1)
            print(f"强制刷新模式，共刷新{len(self.assets)}个tag")

        # 创建子线程
        threading.Thread(target=self.refresh_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def refresh_main(self):
        h = get_cognito()
        multi_thread_task(multi_num=8, target_task=self.refresh_sub, task_args=(self.assets, h))

        # 获取tags后对资产进行分类apsa/bulk
        self.sort_asset()

        # 更新site工程师
        self.engineer_main()

        # 更新job状态
        jobs.update('IOT_TAG', 'OK')

    def refresh_sub(self, assets, h):
        # 创建子线程job以便监控
        job = AsyncJob.objects.create(
            name=f'SUB_TAG_{threading.get_ident()}',
            start_time=datetime.now(),
            result='starting,e'
        )

        total = len(assets)
        progress = 0

        for asset in assets:
            try:
                url = f'{URL}/assets/{asset.uuid}/tags'
                res = requests.get(url, headers=h, verify=False).json()
                for tag in res['content']:
                    if tag['name'] == 'TECHNO':
                        tag_name = tag['labels'][0]['name']
                        break
                if not tag_name:
                    tag_name = 'NULL'
                asset.tags = tag_name
                asset.save()

                progress += 1
                job.result = f"done: {progress}/{total}"
                job.save()
            except Exception as e:
                print(url)

        job.delete()

    def sort_asset(self):
        apsa_name_list = [
            'APSA_T', 'APSA_S', 'MOS', 'EOX', 'PSA',
        ]
        apsa_list = []
        bulk_list = []

        # 过滤ONSITE资产
        for asset in Asset.objects.filter(tags='ONSITE', confirm__gt=-1):
            # 若存在则不操作
            if Bulk.objects.filter(asset=asset).count() == 0 and Apsa.objects.filter(asset=asset).count() == 0:
                name = asset.name
                # 筛选出制氮机
                if any(ele in name for ele in
                       apsa_name_list) and 'BULK' not in name:
                    if name.split('_')[0] == 'APSA':
                        onsite_type = 'APSA'
                        onsite_series = name.split('_')[1]
                    else:
                        onsite_type = name
                        onsite_series = name
                    a = Apsa(
                        asset=asset,
                        onsite_type=onsite_type,
                        onsite_series=onsite_series,
                    )
                    apsa_list.append(a)
                    asset.is_apsa = 1
                    asset.save()
                # 筛选出储罐
                elif 'BULK' in name:
                    b = Bulk(
                        asset=asset,
                    )
                    bulk_list.append(b)

        # 写入数据库
        Apsa.objects.bulk_create(apsa_list, batch_size=10)
        Bulk.objects.bulk_create(bulk_list, batch_size=10)

        apsa_result: str = ""
        if apsa_list:
            for a in apsa_list:
                apsa_result += f"{a.asset_id},"
            apsa_result = f"新建{len(apsa_list)}个APSA,asset_id:" + apsa_result[:-1]
        else:
            apsa_result = "本次没有检测到新增APSA，如有需要请手动添加"

        bulk_result: str = ""
        if bulk_list:
            for a in bulk_list:
                bulk_result += f"{a.asset_id},"
            bulk_result = f"新建{len(bulk_list)}个BULK,asset_id:" + bulk_result[:-1]
        else:
            bulk_result = "本次没有检测到新增BULK，如有需要请手动添加"

        AsyncJob.objects.create(
            name='生成 APSA',
            result=apsa_result,
            start_time=datetime.now(),
            finish_time=datetime.now()
        )
        AsyncJob.objects.create(
            name='生成 BULK',
            result=bulk_result,
            start_time=datetime.now(),
            finish_time=datetime.now()
        )

    def engineer_main(self):
        """根据onsite tag获取site的工程师"""
        sites_obj = Site.objects.filter(id__in=[
            x.site_id for x in Asset.objects.filter(tags='ONSITE')
        ]).distinct()
        h = get_cognito()
        multi_thread_task(multi_num=8, target_task=self.engineer_sub, task_args=(sites_obj, h))

    def engineer_sub(self, sites, h):
        for site in sites:
            url = f'{URL}/sites/{site.uuid}/tags'
            site_old_engineer = site.engineer
            try:
                res = requests.get(url, headers=h, verify=False).json()

                for tag in res['content']:
                    if tag['name'] != 'PHASE' and tag['name'] != 'BUSINESS_LINE':
                        try:
                            tag_content = tag['labels'][0]['name']
                        except IndexError:
                            print(f'错误！  {url}')
                            tag_content = ''
                        break

                engineer_name = self.get_engineer_name(tag_content)
                engineer = User.objects.filter(first_name=engineer_name)
                if engineer.count() == 1:
                    site.engineer = engineer[0]
                elif engineer.count() == 2:
                    print(f"有重名:{engineer_name}")
                    if engineer[0].first_name == engineer[1].first_name:
                        if engineer[0].group:
                            site.engineer = engineer[0]
                        else:
                            site.engineer = engineer[1]
                else:
                    print(f"其他情况:{engineer_name}")
                    if not site_old_engineer:
                        site.engineer = User.objects.get(first_name='其他维修')

                site.save()
            except Exception:
                print(engineer_name)

    def get_engineer_name(self, name):
        name = name.replace(' ', '')
        if len(name) > 12:
            if name[-12] == '0':
                name = name[:-12]
            else:
                name = name[:-11]
        if name == '维修公用机':
            return '何祥文'
        if name == '曾立锋':
            return '曾立峰'
        return name


class VariableData(View):
    def __init__(self):
        self.assets = []

    def get(self, request):
        # 检查Job状态
        if jobs.check('IOT_VARIABLE'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 找出需要刷新的资产
        self.assets = Asset.objects.filter(tags='ONSITE')

        # 创建子线程
        threading.Thread(target=self.refresh_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def refresh_main(self):
        h = get_cognito()
        multi_thread_task(multi_num=8, target_task=self.refresh_sub, task_args=(self.assets, h))
        jobs.update('IOT_VARIABLE', 'OK')

    def refresh_sub(self, assets, h):
        # 创建子线程job以便监控
        job = AsyncJob.objects.create(
            name=f'SUB_VARIABLE_{threading.get_ident()}',
            start_time=datetime.now(),
            result='starting,e'
        )

        total = len(assets)
        progress = 0

        for asset in assets:
            url = f'{URL}/assets/{asset.uuid}/variables?limit=1000'
            res = requests.get(url, headers=h, verify=False).json()

            # 反序列化
            variable_iot_dic = {}
            try:
                for content in res['content']:
                    variable_iot_dic[content['id']] = content

                # 计算更新，删除列表
                variable_old_uuid = [x.uuid for x in Variable.objects.filter(asset=asset, confirm__gt=-1)]
                variable_new_uuid = [j for j in variable_iot_dic.keys() if j not in variable_old_uuid]
                variable_delete_uuid = [k for k in variable_old_uuid if k not in variable_iot_dic.keys()]
                variable_update_uuid = [l for l in variable_old_uuid if l in variable_iot_dic.keys()]

                # 新建变量
                for variable_create in variable_new_uuid:
                    uuid = variable_create
                    name = variable_iot_dic[variable_create]['name']
                    if Variable.objects.filter(uuid=uuid).count() == 0:
                        Variable.objects.create(
                            uuid=uuid,
                            name=name,
                            asset=asset,
                            daily_mark=self.get_daily_mark(name, asset.name)
                        )

                # 更新变量
                for variable_update in variable_update_uuid:
                    v = Variable.objects.get(uuid=variable_update)
                    v.name = variable_iot_dic[variable_update]['name']
                    v.save()

                # 删除变量
                for variable_delete in variable_delete_uuid:
                    v = Variable.objects.get(uuid=variable_delete)
                    v.daily_mark = ''
                    v.confirm = -1
                    v.save()

                progress += 1
                job.result = f"done: {progress}/{total}"
                job.save()
            except Exception as e:
                print(url)

        job.delete()

    def get_daily_mark(self, name, asset_name):
        # Daily标志列表
        daily_list = [
            'M3_Q1', 'M3_Q5', 'M3_Q6', 'M3_Q7', 'M3_TOT', 'M3_PROD', 'H_PROD', 'H_STPAL',
            'H_STPDFT', 'H_STP400V', 'M3_PEAK',
        ]
        daily_mark = ''
        # 自动匹配Daily标志
        if name in daily_list:
            daily_mark = name
        if name == 'M3PEAK':
            daily_mark = 'M3_PEAK'
        if 'M3_PROD' in name:
            daily_mark = 'M3_PROD'
        if name == 'M3PEAK' or name == 'PEAKM3':
            daily_mark = 'M3_PEAK'
        if name == 'H_STPCUST':
            daily_mark = 'H_STP400V'
        if name == 'LEVEL_CC':
            daily_mark = 'LEVEL'
        # 检查T系列CUST取消400V
        if 'T' in asset_name and name == 'H_STPCUST':
            daily_mark = ''
        return daily_mark


class RecordData(View):
    def __init__(self):
        self.variables = []
        self.assets = []
        self.apsa_list: list[int] = []
        self.time_list: list[str] = []
        self.start = ''
        self.end = ''

    def get(self, request):
        # 获取部分刷新列表
        self.apsa_list = request.GET.getlist('apsa_list[]', [])
        self.time_list = request.GET.getlist('time_list[]', [])
        user = request.GET.get('user')
        params = ''

        if self.apsa_list:
            params = f"apsa_list={','.join(self.apsa_list)}"
        else:
            params = "apsa_list=all"
        if self.time_list:
            params += f" & time_list={' '.join(self.time_list)}"
        else:
            params += f" & time=yesterday"

        # 检查Job状态
        if jobs.check('IOT_RECORD', user=user, params=params):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 创建子线程
        threading.Thread(target=self.refresh_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def refresh_main(self):
        print("Job started ...")
        # 获取请求头
        h = get_cognito()
        # 遍历asset，获取确认过的再计算
        self.assets = Asset.objects.filter(confirm=1, tags='onsite')

        # 如果是部分请求，则过滤
        self.partially_filter()

        # 设定查询时间
        self.set_time()

        # 删除已有记录保证所有记录都只做插入操作
        self.delete_old_records()

        # 获取assets对应变量,去除没有dailymark的
        for asset in self.assets:
            # 获取所有daily和monthly变量去重
            variables_daily = [x['id'] for x in
                               Variable.objects.filter(asset=asset, confirm__gt=-1).filter(~Q(daily_mark='')).values(
                                   'id')]
            variables_monthly = [x['variable_id'] for x in
                                 MonthlyVariable.objects.filter(apsa__asset=asset).values('variable_id')]
            variables = set(chain(variables_daily, variables_monthly))
            self.variables += variables

        total = len(self.variables)
        print(f"共:{total}个变量,预计{int(total * 11.6)}条记录")
        # 分发任务至子线程
        multi_thread_task(multi_num=15, target_task=self.refresh_sub, task_args=(self.variables, h))
        # 更新job状态
        jobs.update('IOT_RECORD', 'OK')

    def refresh_sub(self, variables, h):
        # 设置超时时间
        time_now = time.time()
        max_duration = 60 * 14.5  # secs

        # 设置重试列表
        error = 0
        retry_record = {}
        variables_list = [Variable.objects.get(id=x) for x in variables]
        ori_len = len(variables_list)

        # 创建子线程job以便监控
        job = AsyncJob.objects.create(
            name=f'SUB_RECORD_{threading.get_ident()}',
            start_time=datetime.now(),
            result='starting,e'
        )

        # 创建列表
        create_list = []

        # 循环任务
        while len(variables_list) != 0 and (time.time() - time_now < max_duration):
            length = len(variables_list)
            variable = variables_list[0]
            url = f'{URL}/assets/{variable.asset.uuid}/variables/{variable.uuid}/' \
                  f'timeseries?start={self.start}&end={self.end}&limit={50000}'
            # 删除此变量，若报错则重新添加
            variables_list.remove(variable)

            # 获取数据
            try:
                res = requests.get(url, headers=h, timeout=3, verify=False)
                if res.status_code == 401:
                    return
                if res.status_code == 403:
                    pass
                else:
                    time_keys = []
                    res = res.json()['timeseries']
                    for i in res.keys():
                        # 时间转化
                        time_array = time.localtime(int(i[:-3]))
                        t = time.strftime("%Y-%m-%d %H:%M", time_array)
                        # 过滤
                        value = res[i]
                        if variable.daily_mark == 'LEVEL' and not t.endswith('0'):
                            # 若是level，不要15分钟的点
                            pass
                        elif variable.daily_mark != 'LEVEL' and not t.endswith('00:00'):
                            # 非level，只要零点的
                            pass
                        else:
                            if t not in time_keys:
                                create_list.append(Record(
                                    variable=variable,
                                    time=t,
                                    value=round(value, 2)
                                ))
                                time_keys.append(t)

                    second_part = job.result.split(",")[1]
                    job.result = f'done:{ori_len - length}/{ori_len},' + second_part
                    job.save()
            except Exception as e:
                print(e)
                error += 1
                # 错误时，若是第一次则创建计数器，否则计数器+1
                if variable.id in retry_record.keys():
                    retry_record[variable.id] += 1
                else:
                    retry_record[variable.id] = 0
                # 最多尝试10次
                if retry_record[variable.id] < 10:
                    variables_list.insert(length, variable)

                first_part = job.result.split(",")[0]
                job.result = first_part + f',retries:{error}'
                job.save()

        # 任务结束,判断结束条件
        if len(variables_list) != 0:
            job.result = 'Error:TimeOut,' + job.result
            job.finish_time = datetime.now()
            job.save()
        else:
            # 新建数据
            Record.objects.bulk_create(create_list, batch_size=100)
            job.delete()

    def set_time(self):
        if self.time_list == [] or self.time_list is None:
            # 设定默认查询时间
            t = datetime.now()
            # IOT系统时间未UTC，会把我们的时间+8返回
            yesterday = (t + timedelta(days=-1)).strftime("%Y-%m-%d")
            self.start = (t + timedelta(days=-2)).strftime("%Y-%m-%d") + 'T15:55:00.000Z'
            self.end = yesterday + 'T16:05:00.000Z'
            self.time_list = [yesterday, yesterday]
        else:
            self.start = (datetime.strptime(self.time_list[0], "%Y-%m-%d") + timedelta(days=-1)).strftime(
                "%Y-%m-%d") + 'T15:55:00.000Z'
            self.end = self.time_list[1] + 'T16:05:00.000Z'

    def partially_filter(self):
        # 如果传入了apsa_id则过滤,否则跳过
        if self.apsa_list:
            # 获取所有传入apsa的id
            apsa_id_list = [int(x) for x in self.apsa_list]
            asset_id_list = []
            # 找到每个apsa对应的site下的所有confirm=1的资产id
            for apsa_id in apsa_id_list:
                site_id = Asset.objects.get(apsa=apsa_id).site_id
                asset_id_list += [
                    x.id for x in Asset.objects.filter(site=site_id, confirm=1)
                ]
            self.assets = self.assets.filter(id__in=asset_id_list)

    def delete_old_records(self):
        end = (datetime.strptime(self.time_list[1], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        time_range = [self.time_list[0], end]
        records = Record.objects.filter(time__range=time_range, variable__asset__in=self.assets)
        if records.count() != 0:
            records.delete()


class SiteModelView(UpdateListRetrieveViewSet):
    """自定义SiteMixinView"""
    # 查询集
    queryset = Site.objects.filter(asset__tags='ONSITE', confirm__gt=-1).distinct()
    # 序列化器
    serializer_class = SiteSerializer
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query_params = self.request.query_params
        apsa = query_params.get('apsa')
        bulk = query_params.get('bulk')

        if apsa:
            return self.queryset.filter(asset__apsa__id=apsa)

        if bulk:
            return self.queryset.filter(asset__bulk__id=bulk)

        return self.queryset

    def update(self, request, pk):
        engineer = request.data.get('engineer')

        try:
            site = Site.objects.get(id=pk)
            if not engineer:
                return Response('请求参数错误', status=status.HTTP_400_BAD_REQUEST)
            site.engineer_id = int(engineer)
            site.save()
        except DatabaseError as e:
            print(e)
            return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '保存成功'})


class ApsaModelView(UpdateListRetrieveViewSet):
    """自定义ApsaMixinView"""
    # 查询集
    queryset = Apsa.objects.all()
    # 序列化器
    serializer_class = ApsaSerializer
    # 权限
    permission_classes = [IsAuthenticated]
    # 分页器
    pagination_class = PageNum

    # 重写方法，添加过滤
    def get_queryset(self):
        # 对关键词进行过滤
        name = self.request.query_params.get('name')

        if name:
            name = name.strip().upper()
            return self.queryset.filter(
                Q(asset__rtu_name__contains=name) | Q(asset__site__name__contains=name)
            )
        else:
            return self.queryset

    def update(self, request, pk):
        rtu_name = request.data.get('rtu_name')
        engineer = request.data.get('engineer')
        onsite_type = request.data.get('onsite_type')
        onsite_series = request.data.get('onsite_series')
        facility_fin = request.data.get('facility_fin')
        daily_js = request.data.get('daily_js')
        temperature = request.data.get('temperature')
        vap_max = request.data.get('vap_max')
        vap_type = request.data.get('vap_type')
        norminal_flow = request.data.get('norminal_flow')
        daily_bind = request.data.get('daily_bind')
        cooling_fixed = request.data.get('cooling_fixed')
        comment = request.data.get('comment')

        try:
            apsa = Apsa.objects.get(id=int(pk))
            apsa.asset.rtu_name = rtu_name
            apsa.asset.site.engineer = engineer['id']
            apsa.onsite_type = onsite_type
            apsa.onsite_series = onsite_series
            apsa.facility_fin = facility_fin
            apsa.daily_js = daily_js
            apsa.temperature = temperature
            apsa.vap_max = vap_max
            apsa.vap_type = vap_type
            apsa.norminal_flow = norminal_flow
            apsa.daily_bind = daily_bind
            apsa.cooling_fixed = cooling_fixed
            apsa.comment = comment
            apsa.save()
        except DatabaseError as e:
            print(e)
            return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '保存成功'})


class BulkModelView(UpdateListRetrieveViewSet):
    """自定义BulkMixinView"""
    # 查询集
    queryset = Bulk.objects.all()
    # 序列化器
    serializer_class = BulkSerializer
    # 权限
    permission_classes = [IsAuthenticated]
    # 分页器
    pagination_class = PageNum

    # 重写方法，添加过滤
    def get_queryset(self):
        # 对关键词进行过滤
        name = self.request.query_params.get('name')

        if name:
            name = name.strip().upper()
            return self.queryset.filter(
                Q(asset__rtu_name__contains=name) | Q(asset__site__name__contains=name)
            )
        else:
            return self.queryset

    def update(self, request, pk):
        tank_size = request.data.get('tank_size')
        tank_func = request.data.get('tank_func')
        filling_js = request.data.get('filling_js')

        try:
            bulk = Bulk.objects.get(id=int(pk))
            if tank_size:
                bulk.tank_size = tank_size
            if tank_func:
                bulk.tank_func = tank_func
            if filling_js:
                bulk.filling_js = filling_js
            bulk.save()
        except DatabaseError as e:
            print(e)
            return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '保存成功'})


class VariableModelView(UpdateListRetrieveViewSet):
    """自定义AssetMixinView"""
    # 查询集
    queryset = Variable.objects.filter(asset__tags='ONSITE', confirm__gt=-1)
    # 序列化器
    serializer_class = VariableSerializer
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query_params = self.request.query_params
        asset = query_params.get('asset')
        apsa = query_params.get('apsa')

        if asset:
            self.queryset = self.queryset.filter(asset__id=asset)
        if apsa:
            self.queryset = self.queryset.filter(asset__apsa__id=apsa)

        return self.queryset

    def update(self, request, pk):
        daily_mark = request.data.get('daily_mark')
        variable = Variable.objects.get(id=pk)

        try:
            variable.daily_mark = daily_mark
            variable.save()
        except Exception:
            return Response('内部错误', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '保存成功'})


class AssetModelView(UpdateListRetrieveViewSet):
    """自定义SiteMixinView"""
    # 查询集
    queryset = Asset.objects.filter(tags='ONSITE').order_by('site__engineer__region', 'rtu_name')
    # 序列化器
    serializer_class = AssetApsaSerializer
    # 分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    # 重写方法，添加过滤
    def get_queryset(self):
        # 对关键词进行过滤
        apsa = self.request.query_params.get('apsa')
        name = self.request.query_params.get('name')
        confirm = self.request.query_params.get('confirm')
        cal = self.request.query_params.get('cal')
        region = self.request.query_params.get('region')
        queryset = self.queryset

        if confirm is not None and confirm != '':
            queryset = queryset.filter(confirm=confirm)

        if self.action == 'list':
            if name:
                name = name.strip().upper()
                queryset = queryset.filter(
                    Q(rtu_name__contains=name) | Q(site__name__contains=name)
                )

            if region:
                queryset = queryset.filter(site__engineer__region=region)

            if apsa == '1':
                self.apsa = 1
                apsa_id_list = [x.asset_id for x in Apsa.objects.all()]
                if cal == '1':
                    apsa_id_list = [x.asset_id for x in Apsa.objects.filter(daily_js__gte=1)]
                if cal == '0':
                    apsa_id_list = [x.asset_id for x in Apsa.objects.filter(daily_js=0)]
                queryset = queryset.filter(id__in=apsa_id_list)
            elif apsa == '0':
                self.apsa = 0
                bulk_id_list = [x.asset_id for x in Bulk.objects.all()]
                if cal == '1':
                    bulk_id_list = [x.asset_id for x in Bulk.objects.filter(filling_js__gte=1)]
                if cal == '0':
                    bulk_id_list = [x.asset_id for x in Bulk.objects.filter(filling_js=0)]
                queryset = queryset.filter(id__in=bulk_id_list)

        return queryset

    # 根据is_apsa使用不同序列化器
    def get_serializer_class(self):
        if self.action == 'list':
            is_apsa = self.apsa
        else:
            pk = self.kwargs.get('pk')
            is_apsa = Asset.objects.get(id=pk).is_apsa

        if is_apsa:
            return AssetApsaSerializer
        else:
            return AssetBulkSerializer

    def update(self, request, pk):
        rtu_name = request.data.get('rtu_name')
        comment = request.data.get('comment')
        apsa_dic = request.data.get('apsa')
        bulk_dic = request.data.get('bulk')
        site_dic = request.data.get('site')
        confirm = request.data.get('confirm')
        asset = Asset.objects.get(id=pk)

        if apsa_dic:
            # 验证保存数据
            try:
                # apsa保存
                apsa = Apsa.objects.get(id=apsa_dic['id'])
                apsa.onsite_type = apsa_dic['onsite_type']
                apsa.onsite_series = apsa_dic['onsite_series']
                apsa.daily_js = apsa_dic['daily_js']
                apsa.temperature = apsa_dic['temperature']
                apsa.norminal_flow = apsa_dic['norminal_flow']
                apsa.mark = apsa_dic['mark']
                if apsa_dic['vap_max']:
                    apsa.vap_max = apsa_dic['vap_max']
                if apsa_dic['vap_type']:
                    apsa.vap_type = apsa_dic['vap_type']
                if apsa_dic['daily_bind']:
                    apsa.daily_bind = apsa_dic['daily_bind']
                    apsa.cooling_fixed = apsa_dic['cooling_fixed']
                if apsa_dic['flow_meter']:
                    apsa.flow_meter = apsa_dic['flow_meter']
                if apsa_dic['facility_fin']:
                    apsa.facility_fin = apsa_dic['facility_fin']
                # 如果常规计算则需要清空bind和fixed
                if apsa.daily_js == 1:
                    apsa.daily_bind = -1
                    apsa.cooling_fixed = 0
            except DatabaseError as e:
                print(e)
                return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)
        else:
            # 验证保存数据
            try:
                # bulk保存
                bulk = Bulk.objects.get(asset=asset)
                bulk.tank_size = bulk_dic['tank_size']
                bulk.tank_func = bulk_dic['tank_func']
                bulk.level_a = bulk_dic['level_a']
                bulk.level_b = bulk_dic['level_b']
                bulk.level_c = bulk_dic['level_c']
                bulk.level_d = bulk_dic['level_d']
                bulk.filling_js = bulk_dic['filling_js']
            except DatabaseError as e:
                print(e)
                return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)

        # 保存asset和site
        if comment is not None:
            asset.comment = comment
        site = Site.objects.get(id=site_dic['id'])
        site.engineer = User.objects.get(id=site_dic['engineer']['id'])
        asset.rtu_name = rtu_name
        asset.confirm = confirm
        try:
            if bulk_dic:
                bulk.save()
            if apsa_dic:
                apsa.save()
            asset.save()
            site.save()
        except DatabaseError as e:
            print(e)
            return Response('数据库保存错误', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '保存成功'})


class AsyncJobModelView(ModelViewSet):
    """返回任务"""
    queryset = AsyncJob.objects.order_by('-start_time')
    # 序列化器
    serializer_class = AsyncJobSerializer
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 获取请求参数
        finish: str = self.request.query_params.get('finish')
        success: str = self.request.query_params.get('success')

        query_set = self.queryset
        # 过滤筛选
        if finish:
            if finish == '1':
                query_set = query_set.filter(~Q(finish_time=None))
            else:
                query_set = query_set.filter(finish_time=None)

        if success:
            if success == '1':
                query_set = query_set.filter(result='OK')
            else:
                query_set = query_set.filter(~Q(result='OK'))

        return query_set.filter(~Q(name='IOT_TOKEN'))

    def clear(self, request):
        try:
            day: int = int(self.request.query_params.get("day"))
            # 设置最小预留天数
            if day <= 1:
                day = 1
            # 转化为日期
            dt = (datetime.now() + timedelta(days=-day)).strftime("%Y-%m-%d")
        except Exception:
            return JResp("缺少参数或类型错误", 400)

        try:
            # 删除数据库文件
            AsyncJob.objects.filter(start_time__lte=dt).delete()
        except Exception:
            return JResp("数据库内部错误", 400)

        # 返回成功
        return JResp()


class KillRecordTaskView(View):
    def get(self, request):
        sub_jobs = AsyncJob.objects.filter(name__contains='SUB_RECORD')
        for j in sub_jobs:
            j.delete()
        main_jobs = AsyncJob.objects.filter(name__contains='RECORD', finish_time=None)
        for job in main_jobs:
            job.result = 'ERROR: killed by api questionnaire'
            job.finish_time = datetime.now()
            job.save()
        return JsonResponse({"status": 200, 'msg': 'ok', 'affected rows': len(sub_jobs + 1)})


class GetUUID(View):
    def get(self, request):
        key = request.GET.get("key")
        if not key:
            return JResp("关键字不能为空", 400)

        assets = Asset.objects.filter(rtu_name=key.upper())

        if assets.count() == 0:
            return JResp("未找到该RTU", 404)

        rsp = []
        for asset in assets:
            variables = Variable.objects.filter(asset=asset).filter(~Q(daily_mark=''))
            v_rsp = []
            for v in variables:
                v_rsp.append({
                    "variable_name": v.name,
                    "variable_id": v.id
                })
            rsp.append({
                "asset_name": f"{asset.rtu_name}-{asset.name}",
                "asset_id": asset.id,
                "variables": v_rsp
            })

        return JResp(data=rsp)


class CreateRecord(View):
    def post(self, request):
        body = json.loads(request.body.decode('utf-8'))
        v_id = body.get("variable_id")
        dt = body.get("dt")
        value = body.get("value")

        if not all([v_id, dt, value]):
            return JResp("参数不齐全", 400)

        try:
            r = Record.objects.filter(variable_id=v_id, time=dt)
            if r.count() == 0:
                Record.objects.create(
                    variable_id=v_id,
                    value=round(float(value), 2),
                    time=dt
                )
            else:
                r.delete()
                Record.objects.create(
                    variable_id=v_id,
                    value=round(float(value), 2),
                    time=dt
                )
        except Exception as e:
            print(e)
            return JResp("创建失败，数据格式类型错误", 400)

        return JResp()


class ApsaInfo(View):
    def get(self, rqeuest):
        rsp = {}
        for apsa in Apsa.objects.all():
            rtu_name = apsa.asset.rtu_name
            rsp[rtu_name] = apsa.id

        return JResp(data=rsp)


class ManuelCreateAsset(View):
    def __init__(self):
        self.uuid: str = ""
        self.is_apsa: int = 0
        self.user: str = ""
        self.res: dict = {}

    def get(self, request):
        # 获取参数
        try:
            self.uuid = request.GET.get("uuid").strip()
            self.is_apsa = int(request.GET.get("is_apsa"))
            self.user = request.GET.get('user')
            # 参数验证
            if not all([self.uuid, self.user]):
                return JResp("参数不齐全", 400)
            if not re.match(r"[0-9a-z]{8}(-[0-9a-z]{4}){3}-[0-9a-z]{12}", self.uuid):
                return JResp("uuid格式错误，请检查", 400)
        except Exception:
            return JResp("参数错误", 400)

        # 检查Job状态
        if jobs.check("IOT_ASSET_MANUEL", user=self.user, params=f"uuid={self.uuid}&is_apsa={self.is_apsa}"):
            return JResp("任务正在进行中，请稍后刷新", 400)

        # 子线程抓取数据
        threading.Thread(target=self.refresh_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def refresh_main(self):
        # 检查uuid是否存在
        if Asset.objects.filter(uuid=self.uuid).count() != 0:
            jobs.update("IOT_ASSET_MANUEL", "错误：该UUID已存在")
            return

        # 抓取资产信息
        url: str = f"{URL}/assets/{self.uuid}"
        try:
            self.res = requests.get(url, headers=get_cognito(), verify=False).json()
        except Exception as e:
            print(e)
            jobs.update("IOT_ASSET_MANUEL", "错误：向IOT请求asset或解析失败")
            return

        # 判断气站uuid是否存在,创建气站
        try:
            site_dic: dict = self.res["site"]
            if Site.objects.filter(uuid=site_dic["id"]).count() == 0:
                Site.objects.create(uuid=site_dic["id"], name=site_dic["name"])
        except Exception as e:
            jobs.update("IOT_ASSET_MANUEL", f"错误：Site创建失败|{e}")
            return

        # 创建资产
        try:
            Asset.objects.create(
                uuid=self.uuid,
                name=self.res["name"],
                rtu_name="",
                is_apsa=self.is_apsa,
                site=Site.objects.get(uuid=site_dic["id"]),
                status=self.res['status']['name'],
                variables_num=self.res['totalVariables'],
                tags="ONSITE"
            )
        except Exception:
            jobs.update("IOT_ASSET_MANUEL", "错误：Asset创建失败")
            return

        # 创建Bulk/Apsa
        try:
            if self.is_apsa:
                Apsa.objects.create(
                    asset=Asset.objects.get(uuid=self.uuid),
                )
            else:
                Bulk.objects.create(
                    asset=Asset.objects.get(uuid=self.uuid),
                )
        except Exception:
            jobs.update("IOT_ASSET_MANUEL", "错误：Apsa/Bulk创建失败")
            return

        # 检查变量uuid是否存在，并创建
        try:
            asset = Asset.objects.get(uuid=self.uuid)
            asset_name = asset.name
            url = f'{URL}/assets/{self.uuid}/variables?limit=1000'
            res = requests.get(url, headers=get_cognito(), verify=False).json()["content"]
            for c in res:
                variable_name = c["name"]
                if Variable.objects.filter(uuid=c["id"]).count() == 0:
                    Variable.objects.create(
                        uuid=c["id"],
                        name=variable_name,
                        asset=asset,
                        daily_mark=self.get_daily_mark(variable_name, asset_name),
                    )
        except Exception:
            jobs.update("IOT_ASSET_MANUEL", "错误：Variables创建失败")
            return

        # Job信息更新
        asset_type: str = "apsa" if self.is_apsa else "bulk"
        jobs.update("IOT_ASSET_MANUEL", f"成功创建{asset_type},请在资产管理中查看")

    def get_daily_mark(self, name, asset_name):
        # Daily标志列表
        daily_list = [
            'M3_Q1', 'M3_Q5', 'M3_Q6', 'M3_Q7', 'M3_TOT', 'M3_PROD', 'H_PROD', 'H_STPAL',
            'H_STPDFT', 'H_STP400V', 'M3_PEAK',
        ]
        daily_mark = ''
        # 自动匹配Daily标志
        if name in daily_list:
            daily_mark = name
        if name == 'M3PEAK':
            daily_mark = 'M3_PEAK'
        if 'M3_PROD' in name:
            daily_mark = 'M3_PROD'
        if name == 'M3PEAK' or name == 'PEAKM3':
            daily_mark = 'M3_PEAK'
        if name == 'H_STPCUST':
            daily_mark = 'H_STP400V'
        if name == 'LEVEL_CC':
            daily_mark = 'LEVEL'
        # 检查T系列CUST取消400V
        if 'T' in asset_name and name == 'H_STPCUST':
            daily_mark = ''
        return daily_mark
