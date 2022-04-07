from pycognito import Cognito
import requests
import datetime
from apps.iot.models import AssetsInfo, VariablesInfo, OnsiteRecords
import time
from django.db.models import Q
import threading

TOKEN = ''
# PLATFORM = 'preprod'
# URL = 'https://preprod.bos.iot.airliquide.com/api/v1'
PLATFORM = 'iot'
URL = 'https://bos.iot.airliquide.com/api/v1'
"""
初始化说明：
step 1  iot/assets/     : assets_refresh 刷新资产列表
step 2  iot/tags/       : tags_refresh 刷新资产tag
step 3  iot/variables/  : variables_refresh_all 刷新资产变量 (call get_variables)
"""


def get_header():
    """return Header"""
    global TOKEN

    h = {
        'Host': 'bos.iot.airliquide.com',
        'Authorization': TOKEN,
        'business-profile-id': '8e15368e-39c7-437f-9721-e5e54dcd207d',
        # '716ecd51-94d1-4962-b761-57657ad9957f' 选择不同业务线
    }
    return h


def get_daily_mark(name):
    """通过变量名匹配daily_mark"""

    # Daily标志列表
    daily_list = [
        'M3_Q1', 'M3_Q5', 'M3_Q6', 'M3_Q7', 'M3_TOT', 'M3_PROD', 'H_PROD', 'H_STPAL',
        'H_STPDFT', 'H_STP400V', 'M3_PEAK',
    ]
    # 自动匹配Daily标志
    if name in daily_list:
        daily_mark = name
        return daily_mark
    if name == 'M3PEAK':
        daily_mark = 'M3_PEAK'
        return daily_mark
    if 'M3_PROD' in name:
        daily_mark = 'M3_PROD'
        return daily_mark
    if name == 'M3PEAK' or name == 'PEAKM3':
        daily_mark = 'M3_PEAK'
        return daily_mark
    if name == 'H_STPCUST':
        daily_mark = 'H_STP400V'
        return daily_mark
    if name == 'LEVEL_CC':
        daily_mark = 'LEVEL'
        return daily_mark

    return ''


def get_cognito():
    """获取Contigo验证"""
    global TOKEN, PLATFORM
    if PLATFORM == 'iot':
        user_pool_id = 'eu-west-1_XxAZFKMzE'
        client_id = 'oppih8pblveb0qb27sl8k9ubc'
    else:
        user_pool_id = 'eu-west-1_WAl0I8YeF'
        client_id = '74u1stbusg97639ejnhuhmt090'

    print('Authorizing>>>')
    username = 'xiangzhe.hou@airliquide.com'
    password = 'Sunboy27!'
    user = Cognito(
        user_pool_id=user_pool_id,
        client_id=client_id,
        user_pool_region='eu-west-1',
        username=username,
    )
    token_old = TOKEN
    user.authenticate(password=password)
    TOKEN = 'Bearer ' + user.id_token.strip()
    if TOKEN != token_old:
        print('Authorized>>>')


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


def assets_refresh_main():
    """获取site列表，检查更新"""
    get_cognito()
    assets_old = AssetsInfo.objects.all()
    assets_old_ids = [x.id for x in assets_old]
    total = 0
    iot_asset_id_list = []
    list_update = []
    list_create = []

    # 抓取IOT资产信息
    max_num = 1000
    url = f'{URL}/assets?limit={max_num}&page=0'
    res = requests.get(url, headers=get_header()).json()
    page_max = res['page']['maxPage']
    contents = res['content']
    if page_max != 0:
        for i in range(1, page_max+1):
            url = f'{URL}/assets?limit={max_num}&page={i}'
            print(f"?page={i}")
            res = requests.get(url, headers=get_header()).json()
            contents += res['content']

    # 序列化属性
    for content in contents:
        uuid = content['id']
        name = content['name']
        site_id = content['site']['id']
        site_cname = content['site']['name']
        status = content['status']['name']
        variables_num = content['totalVariables']
        iot_asset_id_list.append(uuid)
        # is_bulk
        is_bulk = 0
        if 'BULK' in name:
            is_bulk = 1
        asset = AssetsInfo(
            uuid=uuid, name=name, site_id=site_id, site_cname=site_cname,
            status=status, is_deleted=-1, variables_num=variables_num, is_bulk=is_bulk
        )

        # 添加创建或者更新列表
        if uuid in assets_old_ids:
            list_update.append(asset)
        else:
            list_create.append(asset)

        total += 1
    # 写入数据库
    try:
        AssetsInfo.objects.bulk_create(list_create)
        AssetsInfo.objects.bulk_update(list_update, fields=['name', 'site_id', 'site_cname', 'status', 'variables_num'])
    except Exception as e:
        print(e)
        return -1

    # 判断是否有删除
    deleted_list = [x for x in assets_old_ids if x not in iot_asset_id_list]
    for i in deleted_list:
        update = AssetsInfo.objects.filter(id=i)
        update.update(is_deleted=-2)

    return total


def tags_refresh_main():
    """获取tag"""

    get_cognito()

    v_assets = AssetsInfo.objects.all()
    to_refresh_list = [x.uuid for x in v_assets if x.tags == '']
    total = 0

    # 多线程任务
    multi_thread_task(multi_num=20, target_task=tags_refresh_thread, task_args=to_refresh_list)

    return total


def tags_refresh_thread(refresh_list):
    total = 0
    length = len(refresh_list)
    print()
    for i in refresh_list:
        url = f'{URL}/assets/{i}/tags'
        res = requests.get(url, headers=get_header()).json()
        try:
            res = res['content']
            flag = 0
            for j in res:
                if j['name'] == 'TECHNO':
                    tag = j['labels'][0]['name']
                    if tag == '':
                        tag = 'NULL'
                    AssetsInfo.objects.filter(is_deleted=-1, uuid=i).update(tags=tag)
                    flag = 1
            if not flag:
                AssetsInfo.objects.filter(is_deleted=-1, uuid=i).update(tags="NULL")
            total += 1
            print(f'{total}/{length}', end='\r')
        except Exception:
            print(url)
            print(res)
    print('done!')


def variables_refresh_by_asset(asset_id):
    """通过asset_id获取变量"""
    get_cognito()
    return variables_refresh_thread([asset_id])


def variables_refresh_main():
    """刷新所有资产下变量"""
    get_cognito()
    total = 0

    # 只刷新tag为onsite的资产
    assets_id = [x.id for x in AssetsInfo.objects.filter(tags='ONSITE')]

    # 需要更新的资产列表
    to_refresh_list = []
    # 变量判断是否满足登记variables_num满足库中variables_num
    for asset in assets_id:
        asset_object = AssetsInfo.objects.get(id=asset)
        variables_num_iot = VariablesInfo.objects.filter(asset__id=asset).count()
        variables_num_db = asset_object.variables_num

        # 不满足则添加到更新列表更新
        if variables_num_iot != variables_num_db:
            to_refresh_list.append(asset)

    # 多线程任务
    multi_thread_task(multi_num=15, target_task=variables_refresh_thread, task_args=to_refresh_list)

    return total


def variables_refresh_thread(refresh_list):
    """"""
    total = 0
    length = len(refresh_list)
    for asset_id in refresh_list:
        # 查询iot
        # 数字ID转化为UUID
        asset_obj = AssetsInfo.objects.get(id=asset_id)
        asset_uuid = asset_obj.uuid
        url = f'{URL}/assets/{asset_uuid}/variables?limit=800'
        res = requests.get(url, headers=get_header()).json()
        try:
            content = res['content']
            # 序列化，分类
            for i in content:
                uuid = i['id']
                name = i['name']

                # 查询后存在则更新，否则创建
                variables_this_asset = VariablesInfo.objects.filter(uuid=uuid)
                if variables_this_asset.count() == 0:
                    # 匹配获取daily_mark
                    daily_mark = get_daily_mark(name)
                    # 创建变量
                    VariablesInfo.objects.create(uuid=uuid,
                                                 name=name,
                                                 asset=asset_obj,
                                                 is_deleted=-1,
                                                 daily_mark=daily_mark
                                                 )
                else:
                    # 存在变量，则更新名称
                    variables_this_asset.update(
                        name=name,
                    )
            total += 1
            print(f'{total}/{length}', end='\r')
        except Exception as e:
            print(e)
            print(url)
    print('done!')


def records_refresh_main(js_daily_assets):
    """传入需要计算的asset, 查询对应variables后刷新数据"""
    get_cognito()
    to_add_list = []

    # 所有daily_mark被标记(用~Q取补集)且登记完成(is_deleted=1)的变量
    for x in VariablesInfo.objects.filter(~Q(daily_mark='')).filter(is_deleted=1):
        # 计算需要计算的资产
        if x.asset_id in js_daily_assets:
            to_add_list.append([x.asset.uuid, x.uuid])

    # 多线程任务
    multi_thread_task(multi_num=7, target_task=records_refresh_thread, task_args=to_add_list)

    # 返回更新列表的长度
    return len(to_add_list)


def records_refresh_thread(refresh_list):
    """获取记录模组"""
    total = 0
    length = len(refresh_list)
    for asset, variable in refresh_list:
        # 设定查询时间
        t = datetime.datetime.now()
        # IOT系统时间未UTC，会把我们的时间+8返回
        t_end = (t + datetime.timedelta(days=-1)).strftime("%Y-%m-%d") + 'T17:00:00.000Z'
        t_start = (t + datetime.timedelta(days=-2)).strftime("%Y-%m-%d") + 'T16:00:00.000Z'
        max_num = 500
        url = f'{URL}/assets/{asset}/variables/{variable}/' \
              f'timeseries?start={t_start}&end={t_end}&limit={max_num}'
        try:
            # 获取内容
            res = requests.get(url, headers=get_header()).json()
            res = res['timeseries']
            # 格式化查询内容,i为json中的1970的秒数
            v = VariablesInfo.objects.get(uuid=variable)
            daily_mark_list = [
                'M3_Q1', 'M3_Q5', 'M3_Q6', 'M3_Q7', 'M3_TOT', 'M3_PROD', 'H_PROD', 'H_STPAL',
                'H_STPDFT', 'H_STP400V', 'M3_PEAK',
            ]
            for i in res.keys():
                # 将i转换为北京时间
                time_array = time.localtime(int(i[:-3]))
                t = time.strftime("%Y-%m-%d %H:%M", time_array)
                # 过滤
                value = res[i]
                if v.daily_mark == 'LEVEL' and not t.endswith('0'):
                    # 若是level，不要15分钟的点
                    pass
                elif v.daily_mark in daily_mark_list and not t.endswith('00:00'):
                    # 若是M3_PEAK，只要零点的
                    pass
                else:
                    OnsiteRecords.objects.update_or_create(
                        variable=v, time=t,
                        defaults={
                            'time': t,
                            'value': value,
                            'is_deleted': 0,
                        }
                    )
        except Exception as e:
            print(e)
        total += 1
        print(f'{total}/{length}', end='\r')
    print('done')
    return 0
