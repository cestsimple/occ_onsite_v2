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
from rest_framework.viewsets import ModelViewSet

from utils.CustomMixins import UpdateListRetrieveViewSet
from utils.pagination import PageNum
from .models import AsyncJob, Site, Asset, Variable, Apsa, Bulk, Record
from datetime import datetime, timedelta
from utils import jobs
from .serializer import SiteSerializer, ApsaSerializer, BulkSerializer, VariableSerializer, AssetApsaSerializer, \
    AssetBulkSerializer
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

        site_new_uuid = [j for j in sites_iot_dic.keys() if j not in  sites_db_uuid]
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
            list_update.append(site)

        # 删除site
        for delete_site in site_delete_uuid:
            site = Site.objects.get(uuid=delete_site)
            site.confirm = -1
            site.save()

        # 批量写入数据库
        try:
            Site.objects.bulk_create(list_create)
            Site.objects.bulk_update(list_update, fields=['name'])
        except Exception as e:
            print(e)
            jobs.update('IOT_SITE', e)

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
                    variables_num = assets_iot_dic[new_asset]['totalVariables'],
                )
            )

        # 更新
        list_update = []
        for update_asset in asset_update_uuid:
            site = Site.objects.filter(uuid=assets_iot_dic[update_asset]['site']['id'])
            if site:
                site = site[0]
            asset = Asset.objects.get(uuid=update_asset)
            asset.name = assets_iot_dic[update_asset]['name']
            asset.site = site
            asset.status = assets_iot_dic[update_asset]['status']['name']
            asset.variables_num = assets_iot_dic[update_asset]['totalVariables']
            list_update.append(asset)

        # 删除
        for delete_asset in asset_delete_uuid:
            asset = Asset.objects.get(uuid=delete_asset)
            asset.confirm = -1
            asset.save()

        # 批量写入数据库
        try:
            Asset.objects.bulk_create(list_create)
            Asset.objects.bulk_update(list_update, fields=['name', 'site', 'status', 'variables_num'])
        except Exception as e:
            print(e)
            jobs.update('IOT_ASSET', e)

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
            self.assets = Asset.objects.all()
        else:
            self.assets = Asset.objects.filter(tags='')

        # 创建子线程
        threading.Thread(target=self.refresh_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def refresh_main(self):
        #h = get_cognito()
        #multi_thread_task(multi_num=10, target_task=self.refresh_sub, task_args=(self.assets, h))

        # 获取tags后对资产进行分类apsa/bulk
        #self.sort_asset()

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
            'APSA_T3', 'APSA_T4', 'APSA_T5', 'APSA_T6', 'APSA_T7',
            'APSA_S6', 'APSA_S7', 'APSA_S8', 'MOS', 'EOX', 'PSA',
        ]
        apsa_list = []
        bulk_list = []

        # 过滤ONSITE资产
        for asset in Asset.objects.filter(tags='ONSITE'):
            # 若存在则不操作
            if Bulk.objects.filter(asset=asset).count() or Apsa.objects.filter(asset=asset).count():
                name = asset.name
                # 筛选出制氮机
                if name in apsa_name_list:
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
                if 'BULK' in name and 'TOT' not in name:
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
        multi_thread_task(multi_num=10, target_task=self.engineer_sub, task_args=(sites_obj, h))

    def engineer_sub(self, sites, h):
        for site in sites:
            url = f'{URL}/sites/{site.uuid}/tags'
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
                print(engineer_name)
            site.save()

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
        for a in Asset.objects.filter(tags='ONSITE'):
            variables_num_iot = a.variables_num
            variables_num_db = Variable.objects.filter(asset=a).count()
            # 不满足则添加到更新列表更新
            if variables_num_iot != variables_num_db:
                self.assets.append(a)

            # 创建子线程
        threading.Thread(target=self.refresh_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def refresh_main(self):
        h = get_cognito()
        multi_thread_task(multi_num=10, target_task=self.refresh_sub, task_args=(self.assets, h))
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
                v.confirm = -1
                v.save()

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

    def get(self, request):
        # 检查Job状态
        if jobs.check('IOT_RECORD'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 创建子线程
        threading.Thread(target=self.refresh_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def refresh_main(self):
        h = get_cognito()
        # 获取apsa对应变量
        self.variables = [x for x in Variable.objects.filter(asset__apsa__daily_js__gte=1).filter(~Q(daily_mark=''))]
        # 获取bulk对应变量
        self.variables += [j for j in Variable.objects.filter(asset__bulk__filling_js__gte=1).filter(~Q(daily_mark=''))]
        # 分发任务至子线程
        multi_thread_task(multi_num=10, target_task=self.refresh_sub, task_args=(self.variables, h))
        # 更新job状态
        jobs.update('IOT_RECORD', 'OK')

    def refresh_sub(self, variables, h):
        for variable in variables:
            # 设定查询时间
            t = datetime.now()
            # IOT系统时间未UTC，会把我们的时间+8返回
            t_end = (t + timedelta(days=-1)).strftime("%Y-%m-%d") + 'T17:00:00.000Z'
            t_start = (t + timedelta(days=-2)).strftime("%Y-%m-%d") + 'T15:00:00.000Z'
            max_num = 5000
            url = f'{URL}/assets/{variable.asset.uuid}/variables/{variable.uuid}/' \
                  f'timeseries?start={t_start}&end={t_end}&limit={max_num}'

            res = requests.get(url, headers=h).json()['timeseries']

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
                            'value': value,
                        }
                    )


class SiteModelView(UpdateListRetrieveViewSet):
    """自定义SiteMixinView"""
    # 查询集
    queryset = Site.objects.filter(asset__tags='ONSITE').distinct()
    # 序列化器
    serializer_class = SiteSerializer
    # 权限
    permission_classes = [IsAuthenticated]

    def search(self, request):
        query_params = request.GET
        apsa = query_params.get('apsa')
        bulk = query_params.get('bulk')

        query = self.queryset

        if apsa:
            site_id = Apsa.objects.get(id=apsa).asset.site.id
            query = query.get(id=site_id)

        if bulk:
            site_id = Bulk.objects.get(id=bulk).asset.site.id
            query = query.get(id=site_id)

        ser = self.get_serializer(query)

        return Response(ser.data)


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
        flow_meter = request.data.get('flow_meter')
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
            apsa.flow_meter = flow_meter
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
    queryset = Variable.objects.filter(asset__tags='ONSITE').filter(~Q(daily_mark=''))
    # 序列化器
    serializer_class = VariableSerializer
    # 权限
    permission_classes = [IsAuthenticated]

    def search(self, request):
        query_params = request.GET
        apsa = query_params.get('apsa')
        bulk = query_params.get('bulk')

        query = self.queryset

        if apsa:
            query = query.filter(asset__apsa__id=apsa)

        if bulk:
            query = query.filter(asset__bulk__id=bulk)

        ser = self.get_serializer(query, many=True)

        return Response(ser.data)


class AssetModelView(UpdateListRetrieveViewSet):
    """自定义SiteMixinView"""
    # 查询集
    queryset = Asset.objects.filter(tags='ONSITE')
    # 序列化器
    serializer_class = AssetApsaSerializer
    # 权限
    # permission_classes = [IsAuthenticated]

    # 重写方法，添加过滤
    def get_queryset(self):
        # 对关键词进行过滤
        self.apsa = 0
        apsa = self.request.query_params.get('apsa')

        if self.action == 'list':
            if apsa == '1':
                self.apsa = 1
                return self.queryset.filter(is_apsa=1)
            else:
                return self.queryset.filter(is_apsa=0)
        else:
            return self.queryset

    # 根据is_apsa使用不同序列化器
    def get_serializer_class(self):
        if self.action == 'list':
            is_apsa = self.queryset[0].is_apsa
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
        engineer_id = request.data.get('engineer_id')
        asset = Asset.objects.get(id=pk)
        bulk = None
        apsa = None

        if asset.is_apsa:
            # 获取传入参数
            onsite_type = request.data.get('onsite_type')
            onsite_series = request.data.get('onsite_series')
            facility_fin = request.data.get('facility_fin')
            daily_js = request.data.get('daily_js')
            temperature = request.data.get('temperature')
            vap_max = request.data.get('vap_max')
            vap_type = request.data.get('vap_type')
            norminal_flow = request.data.get('norminal_flow')
            daily_bind = request.data.get('daily_bind')
            flow_meter = request.data.get('flow_meter')
            cooling_fixed = request.data.get('cooling_fixed')
            # 验证保存数据
            try:
                # apsa保存
                apsa = Apsa.objects.get(asset=asset)
                apsa.onsite_type = onsite_type
                apsa.onsite_series = onsite_series
                apsa.daily_js = daily_js
                apsa.temperature = temperature
                apsa.norminal_flow = norminal_flow
                if vap_max:
                    apsa.vap_max = vap_max
                if vap_type:
                    apsa.vap_type = vap_type
                if daily_bind:
                    apsa.daily_bind = daily_bind
                    apsa.cooling_fixed = cooling_fixed
                if flow_meter:
                    apsa.flow_meter = flow_meter
                if facility_fin:
                    apsa.facility_fin = facility_fin
            except DatabaseError as e:
                print(e)
                return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)
        else:
            # 获取传入参数
            tank_size = request.data.get('tank_size')
            tank_func = request.data.get('tank_func')
            level_a = request.data.get('level_a')
            level_b = request.data.get('level_b')
            level_c = request.data.get('level_c')
            level_d = request.data.get('level_d')
            filling_js = request.data.get('filling_js')
            # 验证保存数据
            try:
                # bulk保存
                bulk = Bulk.objects.get(asset=asset)
                bulk.tank_size = tank_size
                bulk.tank_func = tank_func
                bulk.level_a = level_a
                bulk.level_b = level_b
                bulk.level_c = level_c
                bulk.level_d = level_d
                bulk.filling_js = filling_js
            except DatabaseError as e:
                print(e)
                return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)

        # 保存asset和site
        if comment:
            asset.comment = comment
        asset.rtu_name = rtu_name
        site = Site.objects.get(asset=asset)
        site.engineer_id = engineer_id
        try:
            if bulk:
                bulk.save()
            if apsa:
                apsa.save()
            asset.save()
            site.save()
        except DatabaseError as e:
            print(e)
            return Response('数据库保存错误', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '保存成功'})
