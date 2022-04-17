import threading
from datetime import datetime, timedelta

from django.db import DatabaseError
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.http import JsonResponse
from django.views import View
from rest_framework.permissions import IsAdminUser

from apps.iot.models import Bulk, Apsa, Variable, Record
from .models import Filling
from .serializer import FillingSerializer
from utils import jobs
from utils.pagination import PageNum


class FillingCalculate(View):
    def __init__(self):
        self.start_date = ''

    def get(self, request):
        # 获取filling日期参数
        query_params = request.GET
        self.start_date = query_params.get('start')

        # 检查Job状态
        if jobs.check('ONSITE_FILLING'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 创建子线程
        threading.Thread(target=self.calculate_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def calculate_main(self):
        # 设置起始时间
        if not self.start_date:
            self.start_date = (datetime.now() + timedelta(days=-2)).strftime("%Y-%m-%d") + ' 00:00'
        t_start = self.start_date
        t_end = (datetime.now() + timedelta(days=-1)).strftime("%Y-%m-%d") + ' 23:59'

        # 获取所有需要计算的bulk的variable
        variables = Variable.objects.filter(asset__bulk__filling_js=True, daily_mark='LEVEL')

        for variable in variables:
            records = {}
            data = Record.objects.filter(variable=variable).filter(time__range=[t_start, t_end]).order_by('time')
            # 对数据按照时间再次排序
            for row in data:
                time_str = row.time.strftime("%Y-%m-%d %H:%M")
                records[time_str] = row.value
                # 对记录字典进行排序
            records_keys = sorted(records.keys())
            records_data = [records[x] for x in records_keys]

            # 计算所有10min间隔差值(斜率)
            diff_list = []
            for i in range(0, len(records_keys) - 1):
                diff_list.append(round(records_data[i] - records_data[i + 1], 1))

            # 获得所有充液段
            filling_intervals = self.get_filling_interval(diff_list)

            # 过滤充液
            final_filling = []
            bulk = Bulk.objects.get(asset__variable=variable)
            for interval in filling_intervals:
                # start = 起始充液点
                start = interval[0]
                # 充液区间长度
                last = interval[-1]
                # 充液差值(百分比) = 充液结束值-充液开始值
                level_diff = round(records_data[start + last] - records_data[start], 2)
                if last == 1:
                    if level_diff > bulk.level_a:
                        final_filling.append(interval)
                elif last == 2:
                    if level_diff > bulk.level_b:
                        final_filling.append(interval)
                elif last == 3:
                    if level_diff > bulk.level_c:
                        final_filling.append(interval)
                elif last == 4:
                    if level_diff > bulk.level_d:
                        final_filling.append(interval)
                else:
                    final_filling.append(interval)

            # 将过滤后的实际充液写入db
            tank_size = bulk.tank_size
            for interval in final_filling:
                start = interval[0]
                last = interval[-1]
                for i in range(start, start + last + 1):
                    try:
                        # 更新records中的filling_mark
                        d = data.get(time=records_keys[i])
                        d.filling_mark = 1
                        d.save()
                    except Exception as e:
                        print(e)

                # filling写入数据库
                quantity = (records_data[start + last] - records_data[start]) / 100 * tank_size * 1000
                Filling.objects.update_or_create(
                    bulk=bulk, time_1=records_keys[start],
                    defaults={
                        'time_2': records_keys[start + last],
                        'level_1': records_data[start],
                        'level_2': records_data[start + last],
                        'quantity': round(quantity, 2),
                        'is_deleted': 0
                    }
                )

        # 更新Job状态
        jobs.update('ONSITE_FILLING', 'OK')

    def get_filling_interval(self, diff_list):
        """ 返回液位上升点及长度 """
        # 结果列表[f1,f2,f3]， f1...3为列表 f1=[充液起始点，充液区间长度]
        result = []
        # 充液区间长度
        fill_len = 0

        # 循环统计长度
        for i in range(len(diff_list)):
            # 液位差<0 是否为上升趋势
            if diff_list[i] < 0:
                # 如果为第一个上升到额点
                if not fill_len:
                    # 长度从0改为1
                    fill_len += 1
                    # 在结果中添加上升点位置，长度为1
                    result.append([i, 1])
                # 如果已经是连续上升点
                else:
                    # 长度+1
                    fill_len += 1
                    # 取出之前的结果(最后一个添加的)，把长度+1后进行保存
                    result[-1][-1] += 1
            else:
                # 也为下降不管，充液长度置零
                fill_len = 0
        return result


class FillingView(ModelViewSet):
    # 查询集
    queryset = Filling.objects.all()
    # 序列化器
    serializer_class = FillingSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAdminUser]

    def search(self, request):
        query_params = request.GET
        engineer = query_params.get('engineer')

        query = self.queryset

        if engineer:
            query = query.filter(~Q(group=''))

        ser = self.get_serializer(query, many=True)

        return Response(ser.data)

    def update(self, request, pk):
        email = request.data.get('email')

        try:
            filling = Filling.objects.get(id=pk)
            filling.save()
        except DatabaseError as e:
            print(e)
            return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '保存成功'})
