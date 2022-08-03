import getpass
import os
from datetime import datetime

import xlrd
from django.shortcuts import render
from xlrd import XLRDError
from django.http import JsonResponse

from .models import ColumnSetting, Car

XLS_FOLDER = fr"C:/users/{getpass.getuser()}/downloads"


def C2I(name: str) -> int:
    n: int = 0
    if not name:
        return -1

    for c in name:
        n = n * 26 + 1 + ord(c) - ord('A')
    return n - 1


def JResponse(status: int, msg: str = '', data: object = None) -> JsonResponse:
    if status == 200:
        if not msg:
            msg = 'ok'

    if status == 400:
        if not msg:
            msg = 'Internal Error'

    return JsonResponse({'status': status, 'msg': msg, 'data': data}, safe=False,
                        json_dumps_params={'ensure_ascii': False})


def selectFile(request):
    # 获取本地所有表格文件
    try:
        files = [x for x in os.listdir(XLS_FOLDER) if x.split('.')[-1] in ['xls', 'xlsx', 'xlsm'] and "~$" not in x]
    except FileNotFoundError:
        return JResponse(404, '获取文件失败，请检查配置中监视文件夹路径是否正确')
    # 返回文件列表
    return JResponse(200, data=files)


def loadFile(request, region):
    # 获取请求参数
    params = request.GET
    file = params.get('file')
    date_chose = params.get('date')

    # 获取所有已注册区域
    regions = [x for x in ColumnSetting.objects.values_list('region', flat=True).distinct()]

    # 读取文件
    try:
        sheet = xlrd.open_workbook(XLS_FOLDER + '/' + file).sheet_by_index(0)
    except FileNotFoundError:
        return JResponse(404, '未找到该文件')
    except XLRDError:
        return JResponse(400, '文件无法打开，格式错误或已损坏')

    # 根据区域处理数据
    rsp = []
    if region in regions:
        # 读取该region配置信息
        setting = ColumnSetting.objects.get(region=region)
        # 获取该区域所有车辆
        cars = [x for x in Car.objects.filter(region=region).values_list('plate', flat=True)]
        # 读取sheet数据
        cars_row_data = {}
        for nrow in range(2, sheet.nrows):
            # 获取单行数据
            row = sheet.row_values(nrow)
            # 有效行过滤条件
            must_have_colomn = [
                row[C2I(setting.plate)],
                row[C2I(setting.driver)],
                row[C2I(setting.driver_super)],
                row[C2I(setting.go_date)]
            ]
            if setting.trip:
                must_have_colomn.append(
                    row[C2I(setting.trip)]
                )
            # 过滤有效行
            if all(must_have_colomn):
                t = datetime(*xlrd.xldate_as_tuple(row[C2I(setting.go_date)], 0)).strftime("%Y-%m-%d")
                plate = ''.join([x for x in row[C2I(setting.plate)] if x.isdigit()])
                # 按照车牌聚合
                if t == date_chose and plate in cars:
                    # 按照车牌进行聚合
                    if plate not in cars_row_data.keys():
                        cars_row_data[plate] = [row]
                    else:
                        cars_row_data[plate].append(row)

        # 对每辆车的数据按照航次&地址进行聚合
        for plate in cars_row_data.keys():
            # 读取车辆配置信息
            car_config = Car.objects.get(plate=plate)
            # 初始化车的信息结构体
            trip = {}
            # 获取车的原始行数据
            data_rows_car = cars_row_data[plate]
            # 对每条数据进行处理聚合
            for raw_row in data_rows_car:
                # 判断是否有航次分组
                if setting.trip:
                    # 判断是否是新的航次
                    if raw_row[C2I(setting.trip)] not in trip.keys():
                        # 新航次肯定也是第一家客户，依次构造(外->内)trip,dest,customer
                        trip[raw_row[C2I(setting.trip)]] = {
                            raw_row[C2I(setting.address)]: {
                                "customer": raw_row[C2I(setting.customer)],
                                "tel": raw_row[C2I(setting.tel)]
                            }
                        }
                    # 已存在该航次
                    else:
                        # 判断客户地址是否存在
                        if raw_row[C2I(setting.address)] not in trip[raw_row[C2I(setting.trip)]].keys():
                            # 新地址在trip的dest中添加customer
                            trip[raw_row[C2I(setting.trip)]][raw_row[C2I(setting.address)]] = {
                                "customer": raw_row[C2I(setting.customer)],
                                "tel": raw_row[C2I(setting.tel)]
                            }
                        else:
                            # 已存在地址跳过该客户
                            pass
                else:
                    # 新地址在trip的dest中添加customer
                    trip[1][raw_row[C2I(setting.address)]] = {
                        "customer": raw_row[C2I(setting.customer)],
                        "tel": raw_row[C2I(setting.tel)]
                    }

            # 地址转化为列表
            trip_dict = []
            ordered_keys = sorted(trip.keys())
            for i in range(len(ordered_keys)):
                t = ordered_keys[i]
                cust_list = []
                cust_dict = trip[t]
                for cust in cust_dict.keys():
                    cust_list.append({
                        "addr": cust.strip(),
                        "comp": cust_dict[cust]["customer"],
                        "tel": cust_dict[cust]["tel"]
                    })
                trip_dict.append({
                    "index": i + 1,
                    "weight": round(car_config.weight / len(cust_list) - 0.05, 1),
                    "cust_list": cust_list
                })

            # 数据加工处理
            if car_config.goods == '氩气,冷冻液体':
                car_config.godos = '氩,冷冻液体'

            # 添加到返回列表中
            rsp.append({
                "plate": plate,
                "driver": data_rows_car[0][C2I(setting.driver)],
                "driver_super": data_rows_car[0][C2I(setting.driver_super)],
                "dispatcher": data_rows_car[0][C2I(setting.dispatcher)],
                "date": date_chose,
                "start_time": f"{date_chose} {car_config.go_time}:00",
                "parking": car_config.parking,
                "ty_comp": car_config.ty_comp,
                "goods": car_config.goods,
                "ship_comp": car_config.ship_comp,
                "car_weight": car_config.weight,
                "trip": trip_dict,
            })

    elif region == 'all':
        # 获取该区域所有车辆
        cars = Car.objects.all()
    else:
        return JResponse(404, '未找到该区域的配置')

    # 返回整理好的路单数据
    return JResponse(200, data=rsp)


def selectFilePage(request):
    return render(request, 'index.html')
