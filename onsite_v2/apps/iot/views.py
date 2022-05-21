import threading
import time
import requests
from django.db import DatabaseError
from django.http import JsonResponse
from django.views import View
from pycognito import Cognito
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from utils.CustomMixins import UpdateListRetrieveViewSet
from utils.pagination import PageNum
from .models import AsyncJob, Site, Asset, Variable, Apsa, Bulk, Record, OriginAssetData
from datetime import datetime, timedelta
from utils import jobs
from .serializer import SiteSerializer, ApsaSerializer, BulkSerializer, VariableSerializer, AssetApsaSerializer, \
    AssetBulkSerializer, AsyncJobSerializer
from ..user.models import User
from django.db.models import Q

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
    password = 'Sunboy27!'
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
        res = requests.get(url, headers=header).json()
        page_max = res['page']['maxPage']
        contents = res['content']
        # 获取全部页数
        if page_max != 0:
            for i in range(1, page_max + 1):
                url = f'{URL}/sites?limit=1000&page={i}'
                res = requests.get(url, headers=header).json()
                contents += res['content']

        # 分类Site
        sites_iot_dic = {}
        for content in contents:
            sites_iot_dic[content['id']] = content
        sites_db_uuid = [x.uuid for x in Site.objects.all()]

        site_new_uuid = [j for j in sites_iot_dic.keys() if j not in sites_db_uuid]
        site_delete_uuid = [k for k in sites_db_uuid if k not in sites_iot_dic.keys()]
        site_update_uuid = [l for l in sites_db_uuid if l in sites_iot_dic.keys()]

        # 创建site
        list_create = []
        for new_site in site_new_uuid:
            list_create.append(
                Site(
                    uuid=new_site,
                    name=sites_iot_dic[new_site]['name'],
                )
            )

        # 更新site
        list_update = []
        for update_site in site_update_uuid:
            site = Site.objects.get(uuid=update_site)
            site.name = sites_iot_dic[update_site]['name']
            if site.confirm == -1:
                site.confirm = 0
            list_update.append(site)

        # 删除site
        list_delete = []
        for delete_site in site_delete_uuid:
            site = Site.objects.get(uuid=delete_site)
            if site.confirm != -1:
                list_delete.append(site)
                site.confirm = -1
                site.save()

        # 批量写入数据库
        try:
            Site.objects.bulk_create(list_create)
            Site.objects.bulk_update(list_update, fields=['name'])
        except Exception as e:
            print(e)
            jobs.update('IOT_SITE', e)

        # console输出
        print(f"更新{len(list_update)}个site资产")
        for x in list_create:
            print(f"新建site资产: {x.name}")
        for x in list_delete:
            print(f"删除site资产: {x.name}")

        # 更新Job状态
        jobs.update('IOT_SITE', 'OK')


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
        res = requests.get(url, headers=header).json()
        page_max = res['page']['maxPage']
        contents = res['content']
        # 获取全部页数
        if page_max != 0:
            for i in range(1, page_max + 1):
                url = f'{URL}/assets?limit=1000&page={i}'
                res = requests.get(url, headers=header).json()
                contents += res['content']

        # 分类
        assets_iot_dic = {}
        for content in contents:
            assets_iot_dic[content['id']] = content
        assets_db_uuid = [x.uuid for x in Asset.objects.all()]

        asset_new_uuid = [j for j in assets_iot_dic.keys() if j not in assets_db_uuid]
        asset_delete_uuid = [k for k in assets_db_uuid if k not in assets_iot_dic.keys()]
        asset_update_uuid = [l for l in assets_db_uuid if l in assets_iot_dic.keys()]

        # 创建
        list_create = []
        for new_asset in asset_new_uuid:
            site = Site.objects.filter(uuid=assets_iot_dic[new_asset]['site']['id'])
            if site:
                site = site[0]
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
        list_delete = []
        for delete_asset in asset_delete_uuid:
            asset = Asset.objects.get(uuid=delete_asset)
            if asset.confirm != -1:
                list_delete.append(asset)
                asset.confirm = -1
                asset.save()

        # 批量写入数据库
        try:
            Asset.objects.bulk_create(list_create)
            Asset.objects.bulk_update(list_update, fields=['name', 'site', 'status', 'variables_num'])
        except Exception as e:
            print(e)
            jobs.update('IOT_ASSET', e)

        # console输出
        print(f"更新{len(list_update)}个asset资产")
        for x in list_create:
            print(f"新建asset资产: {x.name}")
        for x in list_delete:
            print(f"删除asset资产: {x.name}")

        # 更新Job状态
        jobs.update('IOT_ASSET', 'OK')


class TagData(View):
    def __init__(self):
        self.assets = []

    def get(self, request):
        # 检查Job状态
        if jobs.check('IOT_TAG'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 是否强制全部刷新/部分刷新
        force = request.GET.get('force')
        if force:
            self.assets = Asset.objects.filter(confirm__gte=0)
            print(f"强制刷新模式，共刷新{len(self.assets)}个tag")
        else:
            self.assets = Asset.objects.filter(tags='')

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
        for asset in assets:
            url = f'{URL}/assets/{asset.uuid}/tags'
            res = requests.get(url, headers=h).json()
            for tag in res['content']:
                if tag['name'] == 'TECHNO':
                    tag_name = tag['labels'][0]['name']
                    break
            if not tag_name:
                tag_name = 'NULL'
            asset.tags = tag_name
            asset.save()

    def sort_asset(self):
        apsa_name_list = [
            'APSA_T', 'APSA_S', 'MOS', 'EOX', 'PSA',
        ]
        apsa_list = []
        bulk_list = []

        # 过滤ONSITE资产
        for asset in Asset.objects.filter(tags='ONSITE'):
            # 若存在则不操作
            if Bulk.objects.filter(asset=asset).count() == 0 and Apsa.objects.filter(asset=asset).count() == 0:
                name = asset.name
                # 筛选出制氮机
                if any(ele in name for ele in
                       apsa_name_list) and 'WATER' not in name and 'FLOW' not in name and 'BULK' not in name:
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
        Apsa.objects.bulk_create(apsa_list)
        Bulk.objects.bulk_create(bulk_list)

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
            try:
                res = requests.get(url, headers=h).json()

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
                else:
                    site.engineer = User.objects.get(first_name='其他维修')
                site.save()
            except Exception:
                pass

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
        for asset in assets:
            url = f'{URL}/assets/{asset.uuid}/variables?limit=1000'
            res = requests.get(url, headers=h).json()

            # 反序列化
            variable_iot_dic = {}
            for content in res['content']:
                variable_iot_dic[content['id']] = content

            # 计算更新，删除列表
            variable_old_uuid = [x.uuid for x in Variable.objects.filter(asset=asset)]
            variable_new_uuid = [j for j in variable_iot_dic.keys() if j not in variable_old_uuid]
            variable_delete_uuid = [k for k in variable_old_uuid if k not in variable_iot_dic.keys()]
            variable_update_uuid = [l for l in variable_old_uuid if l in variable_iot_dic.keys()]

            # 新建变量
            for variable_create in variable_new_uuid:
                uuid = variable_create
                name = variable_iot_dic[variable_create]['name']
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
                if v.confirm != -1:
                    v.daily_mark = ''
                    v.confirm = -1
                    v.save()
                    # 删除变量记录
                    Record.objects.filter(variable=v).delete()

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

    def get(self, request):
        # 获取部分刷新列表
        self.apsa_list = request.GET.getlist('apsa_list[]', [])

        # 检查Job状态
        if jobs.check('IOT_RECORD'):
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

        total_apsa = 0
        total_bulk = 0
        total_record = 0
        # 获取assets对应变量,去除没有dailymark的
        for asset in self.assets:
            try:
                variables = [x for x in Variable.objects.filter(asset=asset).filter(~Q(daily_mark=''))]
                if asset.is_apsa and Apsa.objects.get(asset=asset).daily_js:
                    length = len(variables)
                    if length == 11 or length == 12:
                        self.variables += variables
                        total_apsa += 1
                        total_record += length * 2
                    else:
                        asset.confirm = 0
                        asset.save()
                        print(f"APSA variables总数验证错误：\n asset:{asset.rtu_name} 变量数:{length} \n: 变量名如下：")
                        for i in variables:
                            print(i.name)
                elif not asset.is_apsa and Bulk.objects.get(asset=asset).filling_js:
                    length = len(variables)
                    if length == 1:
                        self.variables += variables
                        total_bulk += 1
                        total_record += length * 144
                    else:
                        asset.confirm = 0
                        asset.save()
                        print(f"BULK variables总数验证错误：\n asset:{asset.rtu_name}")
            except Exception as e:
                print(e)
                print(f"asset_id={asset.id},is_apsa={asset.is_apsa}")
        print(f"有{total_apsa}个apsa和{total_bulk}个bulk,共:{len(self.variables)}个变量,预计{total_record}条记录")
        # 分发任务至子线程
        multi_thread_task(multi_num=4, target_task=self.refresh_sub, task_args=(self.variables, h))
        # 更新job状态
        jobs.update('IOT_RECORD', 'OK')

    def refresh_sub(self, variables, h):
        # 设置超时时间
        time_now: int = int(time.time())
        max_duration: int = 60 * 30  # secs
        # 设置重试列表
        retry_record = {}
        variables_list = [x for x in variables]
        while len(variables_list) != 0 and (time.time() - time_now < max_duration):
            length = len(variables_list)
            variable = variables_list[0]
            # 设定查询时间
            t = datetime.now()
            # IOT系统时间未UTC，会把我们的时间+8返回
            t_end = (t + timedelta(days=-1)).strftime("%Y-%m-%d") + 'T17:00:00.000Z'
            t_start = (t + timedelta(days=-2)).strftime("%Y-%m-%d") + 'T15:00:00.000Z'
            max_num = 50000
            url = f'{URL}/assets/{variable.asset.uuid}/variables/{variable.uuid}/' \
                  f'timeseries?start={t_start}&end={t_end}&limit={max_num}'
            try:
                res = requests.get(url, headers=h)
                if res.status_code == 401:
                    return
                if res.status_code == 403:
                    pass
                else:
                    res = res.json()['timeseries']
                    daily_mark_list = [
                        'M3_Q1', 'M3_Q5', 'M3_Q6', 'M3_Q7', 'M3_TOT', 'M3_PROD', 'H_PROD', 'H_STPAL',
                        'H_STPDFT', 'H_STP400V', 'M3_PEAK',
                    ]
                    for i in res.keys():
                        time_array = time.localtime(int(i[:-3]))
                        t = time.strftime("%Y-%m-%d %H:%M", time_array)
                        # 过滤
                        value = res[i]
                        if variable.daily_mark == 'LEVEL' and not t.endswith('0'):
                            # 若是level，不要15分钟的点
                            pass
                        elif variable.daily_mark in daily_mark_list and not t.endswith('00:00'):
                            # 若是M3_PEAK，只要零点的
                            pass
                        else:
                            Record.objects.update_or_create(
                                variable=variable, time=t,
                                defaults={
                                    'time': t,
                                    'value': round(value, 2)
                                }
                            )
                variables_list.remove(variable)
            except Exception:
                variables_list.remove(variable)
                if variable.id in retry_record.keys():
                    retry_record[variable.id] += 1
                else:
                    retry_record[variable.id] = 0
                if retry_record[variable.id] < 20:
                    variables_list.insert(length, variable)
                    print(f'redo: {variable.id}')

    def partially_filter(self):
        # 获取所有传入apsa的id
        apsa_id_list = [int(x) for x in self.apsa_list]
        asset_id_list = []
        # 找到每个apsa对应的site下的所有confirm=1的资产id
        for apsa_id in apsa_id_list:
            site_id = Asset.objects.get(apsa=apsa_id).site_id
            asset_id_list += [
                x.id for x in Asset.objects.filter(site=site_id, confirm=1)
            ]
        # 用上面的asset_id进行过滤
        if self.apsa_list:
            self.assets = self.assets.filter(id__in=asset_id_list)


class SiteModelView(UpdateListRetrieveViewSet):
    """自定义SiteMixinView"""
    # 查询集
    queryset = Site.objects.filter(asset__tags='ONSITE').distinct()
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
    queryset = Variable.objects.filter(asset__tags='ONSITE')
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
    queryset = Asset.objects.filter(tags='ONSITE')
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
                elif cal == '0':
                    apsa_id_list = [x.asset_id for x in Apsa.objects.filter(daily_js=0)]
                queryset = queryset.filter(id__in=apsa_id_list)
            elif apsa == '0':
                self.apsa = 0
                bulk_id_list = [x.asset_id for x in Bulk.objects.all()]
                if cal == '1':
                    bulk_id_list = [x.asset_id for x in Bulk.objects.filter(filling_js__gte=1)]
                elif cal == '0':
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
        if comment:
            asset.comment = comment
        site = Site.objects.get(id=site_dic['id'])
        site.engineer = User.objects.get(id=site_dic['engineer']['id'])
        for a in Asset.objects.filter(site=site):
            a.rtu_name = rtu_name
            a.save()
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


class AddOriginDataView(View):
    def get(self, request):
        data = OriginAssetData.objects.all()
        for row in data:
            asset = Asset.objects.filter(uuid=row.uuid)
            if asset.count() != 1:
                print(f'ERROR: UUID错误{row.uuid}')
            else:
                asset = asset[0]
                asset.rtu_name = row.rtu_name
                asset.confirm = 1

                if row.is_bulk:
                    try:
                        bulk = Bulk.objects.get(asset=asset)
                        bulk.tank_size = row.tank_size
                        bulk.level_a = row.levela
                        bulk.level_b = row.levelb
                        bulk.level_c = row.levelc
                        bulk.level_d = row.leveld
                        bulk.filling_js = 1
                    except Exception as e:
                        if 'TOT' not in row.tank_name:
                            print(e)
                            print(asset.id)
                            print('-' * 100)
                        asset.confirm = 0
                else:
                    try:
                        apsa = Apsa.objects.get(asset=asset)
                        apsa.temperature = row.temp
                        if row.vap_max:
                            apsa.vap_max = row.vap_max
                        if row.fin:
                            apsa.facility_fin = row.fin
                        if row.vap_type:
                            apsa.vap_type = row.vap_type
                        apsa.norminal_flow = row.norminal
                        apsa.daily_js = 1
                        variables = Variable.objects.filter(asset=asset, daily_mark='H_STP400V')
                        if variables.count() == 2:
                            for v in variables:
                                if v.name != row.stp_400v:
                                    v.daily_mark = ''
                                    v.save()

                        # 判断变量是否满足11个或者12个
                        daily_mark_list = [
                            'M3_Q1', 'M3_Q5', 'M3_Q6', 'M3_Q7', 'M3_TOT', 'M3_PROD', 'H_PROD', 'H_STPAL',
                            'H_STPDFT', 'H_STP400V', 'M3_PEAK',
                        ]
                        variables = Variable.objects.filter(asset=asset).filter(~Q(daily_mark=''))
                        v_daily_mark_list = [x.daily_mark for x in variables]
                        if variables.count == 11:
                            if daily_mark_list.sort() != v_daily_mark_list.sort():
                                apsa.daily_js = 0
                        elif variables.count == 12:
                            daily_mark_list.append('FLOW_METER')
                            if daily_mark_list.sort() != v_daily_mark_list.sort():
                                apsa.daily_js = 0
                            daily_mark_list.remove('FLOW_METER')
                        else:
                            apsa.daily_js = 0

                    except Exception as e:
                        print(e)
                        print(asset.id)
                        print('-' * 100)
                        asset.confirm = 0
                        apsa.daily_js = 0

                try:
                    asset.save()
                    if row.is_bulk:
                        bulk.save()
                    else:
                        apsa.save()
                except Exception as e:
                    print(e)
                    print(asset.id)
                    print('-' * 100)
        return JsonResponse({'status': 200})


class AsyncJobModelView(ModelViewSet):
    """返回任务"""
    queryset = AsyncJob.objects.all()
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


class RefreshAllAsset(APIView):
    def get(self, request):
        if jobs.check('IOT_SITE', silent=True) or \
                jobs.check('IOT_ASSET', silent=True) or \
                jobs.check('IOT_TAG', silent=True) or \
                jobs.check('IOT_VARIABLE', silent=True) or \
                jobs.check('IOT_ALL'):
            return Response('任务已存在', status=400)

        threading.Thread(target=self.sub, args=(request,)).start()
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新所有iot资产'})

    def sub(self, request):
        # 获取当前时间，设定任务最大时间
        time_now = datetime.now()
        t_start = int(time.time())
        max_duration = 60 * 60  # secs

        # 创建任务实例
        site = SiteData()
        asset = AssetData()
        tag = TagData()
        variable = VariableData()

        site_done = 0
        asset_done = 0
        tag_done = 0
        variable_done = 0

        # 按照顺序执行任务
        while time.time() - t_start < max_duration:
            # 开始site
            if not site_done:
                site.get(request)
                site_done = 1

            # 检测上一个任务完成再做
            job = AsyncJob.objects.filter(name='IOT_SITE', start_time__gt=time_now, result='OK')
            if job.count() == 1 and not asset_done:
                print("IOT_SITE完成")
                asset.get(request)
                asset_done = 1

            job = AsyncJob.objects.filter(name='IOT_ASSET', start_time__gt=time_now, result='OK')
            if job.count() == 1 and not tag_done:
                print("IOT_ASSET完成")
                tag.get(request)
                tag_done = 1

            job = AsyncJob.objects.filter(name='IOT_TAG', start_time__gt=time_now, result='OK')
            if job.count() == 1 and not variable_done:
                print("IOT_TAG完成")
                variable.get(request)
                variable_done = 1

            job = AsyncJob.objects.filter(name='IOT_VARIABLE', start_time__gt=time_now, result='OK')
            if job.count() == 1:
                print("IOT_VARIABLE完成")
                # 任务完成，返回
                jobs.update('IOT_ALL', 'OK')
                return
            time.sleep(5)
        # 刷新超时，计入失败
        jobs.update('IOT_ALL', 'ERROR: TIME OUT')
