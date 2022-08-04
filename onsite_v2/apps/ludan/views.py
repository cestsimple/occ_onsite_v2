from django.http import JsonResponse

from .models import Car, ColumnSetting


def exportCars(request):
    try:
        cars = Car.objects.all()
    except Exception:
        return JsonResponse({
            'status': 400,
            'msg': "数据库读取失败"
        })
    rsp = []
    try:
        for car in cars:
            rsp.append({
                'plate': car.plate,
                'region': car.region,
                'account': car.account,
                'go_time': car.go_time,
                'parking': car.parking,
                'ty_comp': car.ty_comp,
                'goods': car.goods,
                'ship_comp': car.ship_comp,
                'weight': car.weight
            })
    except Exception:
        return JsonResponse({
            'status': 400,
            'msg': "序列化失败"
        })
    return JsonResponse({
            'status': 200,
            'msg': "OK",
            'data': rsp
        })


def exportColumnSettings(request):
    try:
        columns = ColumnSetting.objects.all()
    except Exception:
        return JsonResponse({
            'status': 400,
            'msg': "数据库读取失败"
        })
    rsp = []
    try:
        for c in columns:
            rsp.append({
                'region': c.region,
                'go_date': c.go_date,
                'plate': c.plate,
                'driver': c.driver,
                'driver_super': c.driver_super,
                'dispatcher': c.dispatcher,
                'customer': c.customer,
                'address': c.address,
                'tel': c.tel,
                'trip': c.trip,
            })
    except Exception:
        return JsonResponse({
            'status': 400,
            'msg': "序列化失败"
        })
    return JsonResponse({
            'status': 200,
            'msg': "OK",
            'data': rsp
        })