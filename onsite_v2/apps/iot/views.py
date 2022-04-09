import threading
import requests
from django.http import JsonResponse
from django.views import View
from pycognito import Cognito
from .models import AsyncJob, Site, Asset
from datetime import datetime, timedelta
from utils import jobs

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
    else:
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
            task.setDaemon(True)
            task.start()
        except Exception as e:
            print(f"进程创建失败 - {e}")


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
                    cname=sites_iot_dic[new_site]['name'],
                    ename='',
                )
            )

        # 更新site
        list_update = []
        for update_site in site_update_uuid:
            site = Site.objects.get(uuid=update_site)
            site.cname = sites_iot_dic[update_site]['name']
            list_update.append(site)

        # 删除site
        for delete_site in site_delete_uuid:
            site = Site.objects.get(uuid=delete_site)
            site.confirm = -1
            site.save()

        # 批量写入数据库
        try:
            Site.objects.bulk_create(list_create)
            Site.objects.bulk_update(list_update, fields=['cname'])
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
        multi_thread_task(multi_num=10, target_task=self.refresh_sub, task_args=self.assets)
        jobs.update('IOT_TAG', 'OK')

    def refresh_sub(self, assets):
        header = get_cognito()
        for asset in assets:
            url = f'{URL}/assets/{asset.uuid}/tags'
            res = requests.get(url, headers=header).json()
            for tag in res['content']:
                if tag['name'] == 'TECHNO':
                    tag_name = tag['labels']['name']
            if not tag_name:
                tag_name = 'NULL'
            asset.tags = tag_name
            asset.save()
