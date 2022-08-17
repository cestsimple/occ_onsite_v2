from django.http import JsonResponse


def JResp(msg: str = "ok", status: int = 200, data: object = None) -> JsonResponse:
    """
    @param msg: 返回文字信息,默认ok
    @param status: 返回状态码,默认200
    @param data: 返回数据,默认空
    @return:
    """
    try:
        return JsonResponse({
            "msg": msg,
            "status": status,
            "data": data
        }, safe=False)
    except Exception as e:
        return JsonResponse({
            "msg": e,
            "status": 500,
        })
