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
from .models import Filling, Daily, DailyMod, Malfunction
from .serializer import FillingSerializer, DailySerializer
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
            self.start_date = (datetime.now() + timedelta(days=-1)).strftime("%Y-%m-%d") + ' 00:00'
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


class DailyCalculate(View):
    def __init__(self):
        self.t_start = ''
        self.t_end = ''
        self.apsa = None
        self.error = 0
        self.error_variables = []
        self.daily_res = {
            'h_prod': -1,
            'h_stpal': -1,
            'h_stpdft': -1,
            'h_stp400v': -1,
            'm3_prod': -1,
            'm3_tot': -1,
            'm3_q1': -1,
            'm3_peak': -1,
            'm3_q5': -1,
            'm3_q6': -1,
            'm3_q7': -1,
            'filling': 0,
            'lin_tot': 0,
            'flow_meter': 0,
        }

    def get(self, request):
        # 获取daily日期参数
        query_params = request.GET
        start = query_params.get('start')
        end = query_params.get('end')

        # 检查Job状态
        if jobs.check('ONSITE_DAILY'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 设置需要计算的日期, 完成类型转换
        if not end:
            end = datetime.now().date()
        else:
            end = datetime.strptime(end, "%Y-%m-%d").date()

        if not start:
            start = datetime.now().date()
        else:
            start = datetime.strptime(start, "%Y-%m-%d").date()

        # 创建子线程
        for d in self.set_date(start, end):
            threading.Thread(target=self.calculate_main, args=(d,)).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def calculate_main(self, c_date):
        # 设定时间(参数：时间字符串)
        self.set_time(c_date)
        t_start = self.t_start

        # 查询所有需要计算的Apsa
        apsas = Apsa.objects.filter(daily_js__gte=1).order_by('daily_js')

        for apsa in apsas:
            # 传递apsa全局使用
            self.apsa = apsa

            # 获取daily参数
            self.get_daily_res()
            d_res = self.daily_res

            # 如果数据源错误，可以计算lin_tot的继续计算
            if d_res['m3_prod'] >= 0 and d_res['m3_q6'] >= 0 and d_res['m3_q7'] >= 0 and d_res['m3_peak'] >= 0:
                # 单机apsa计算
                if apsa.daily_js == 1:
                    self.get_lin_tot_simple()
                # 共用apsa计算(该机器固定补冷)
                if apsa.daily_js == 2:
                    self.get_lin_tot_complex()

            # 若有停机写入停机
            self.generate_malfunction()
            # 写入daily
            self.generate_daily()

            # 写入daily_mod表
            self.generate_daily_mod()

        # 更新Job状态
        jobs.update('ONSITE_DAILY', 'OK')

    def set_time(self, date):
        # 设置起始时间 eg.计算9号数据 应该设置查询8，9两天数据
        self.t_start = (date + timedelta(days=-1)).strftime("%Y-%m-%d")
        self.t_end = (date + timedelta(days=0)).strftime("%Y-%m-%d")

    def get_daily_res(self):
        # 对于每个需要计算的variable
        variables = Variable.objects.filter(asset__apsa=self.apsa).filter(~Q(daily_mark=''))
        for v in variables:
            try:
                # 查询其所有record
                data_today = Record.objects.get(variable__id=v.id, time=self.t_end).value
                data_yesterday = Record.objects.get(variable__id=v.id, time=self.t_start).value
                # 根据时间，计算该daily_mark的值
                self.daily_res[v.daily_mark.lower()] = round(data_today - data_yesterday, 2)
            except Exception as e:
                # 若查数据缺失，错误标志置1
                self.error = 1
                self.error_variables.append(v.name)

    def get_lin_tot_simple(self):
        """
        单机apsa的lin_tot
        公式：(充液量+储罐液位首尾差量)/1000*650*(合同温度/273.15)
        """
        t_start = self.t_start
        t_end = self.t_end

        # 获取所有计算filling的罐子资产 fiiling_js=1表示filling记入daily，fiiling_js=2表示只计算filling，被过滤排除
        bulks = Bulk.objects.filter(asset__site=self.apsa.asset.site, filling_js=1)

        filling_quantity = 0
        lin_bulks = 0
        for bulk in bulks:
            # 计算充液量 单位:升(液态)
            filling_quantity += sum([
                x.quantity for x in Filling.objects.filter(bulk=bulk, time_1__range=[t_start, t_end])
            ])
            # 计算储罐首尾液位差量
            l_0 = Record.objects.filter(variable__asset__bulk=bulk).get(time=t_start + ' 00:00:00').value
            l_1 = Record.objects.filter(variable__asset__bulk=bulk).get(time=t_end + ' 00:00:00').value
            lin_bulks += (l_0 - l_1) / 100 * bulk.tank_size * 1000  # 单位:升(液态)

        # 计算lin_tot,单位标立 = 储罐消耗 + 充液
        lin_tot = round((filling_quantity + lin_bulks) / 1000 * 650 * (273.15 + self.apsa.temperature) / 273.15, 2)

        # 保存数据
        self.daily_res['lin_tot'] = lin_tot
        self.daily_res['filling'] = filling_quantity

    def get_lin_tot_complex(self):
        """
            共用储罐的apsa的lin_tot
            公式：(m3产量*补冷值/100)+m3_q6+m3_q7+m3_peak
        """
        # 获取设定的cooling值
        cooling_fixed = self.apsa.cooling_fixed

        # 根据cooling反推lin_tot，再加上停机用液和Peak
        lin_tot = round(self.res['m3_prod'] * cooling_fixed / 100, 2)
        lin_tot += self.res['m3_q6'] + self.res['m3_q7'] + self.res['m3_peak']

        # 保存数据
        self.daily_res['lin_tot'] = lin_tot

    def generate_daily(self):
        # 生成成功daily
        d_res = self.daily_res
        if not self.error:
            # 添加成功标志位, 更新备注信息
            d_res['success'] = 1
            d_res['comment'] = ''

            # Daily写入数据库
            Daily.objects.update_or_create(
                apsa=self.apsa, date=self.t_start,
                defaults=d_res,
            )
        else:
            # 添加错误变量信息
            d_res['comment'] = '报错变量:' + f"{'|'.join(self.error_variables)}"
            Daily.objects.update_or_create(
                apsa=self.apsa, date=self.t_start,
                defaults=d_res
            )

    def generate_daily_mod(self):
        res = {
            'user': 'SYSTEM'
        }
        apsa = self.apsa
        if self.apsa.daily_js == 2:
            res['lin_tot_mod'] = self.daily_res['lin_tot']
            apsa = Apsa.objects.filter(id=self.apsa.daily_bind)
        DailyMod.objects.update_or_create(
            apsa=apsa, date=self.t_start,
            defaults=res
        )

    def generate_malfunction(self):
        """生成停机Malfunction"""
        d_res = self.daily_res

        if d_res['h_stpal'] or d_res['h_stpdft'] or d_res['h_stp400v']:
            if d_res['h_stpal']:
                default = {
                    'stop_label': 'AL',
                    'stop_consumption': d_res['m3_q6'],
                    'stop_time': d_res['h_stpal'],
                }
            elif d_res['h_stpdft']:
                default = {
                    'stop_label': 'DFT',
                    'stop_consumption': 0,
                    'stop_time': d_res['h_stpdft'],
                }
            elif d_res['h_stp400v']:
                default = {
                    'stop_label': '400V',
                    'stop_consumption': d_res['m3_q7'],
                    'stop_time': d_res['h_stp400v'],
                }
            # 添加停机信息
            default['t_end'] = self.t_start

            # 生成记录
            default['change_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            default['change_user'] = 'system'
            Malfunction.objects.update_or_create(
                apsa=self.apsa, t_start=self.t_start, stop_label=default['stop_label'],
                defaults=default
            )

    def set_date(self, start, end):
        res = [start]
        if start == end:
            return res
        for i in range(15):
            new_date = start + timedelta(days=i + 1)
            if new_date == end:
                res.append(end)
                return res
            res.append(new_date)
