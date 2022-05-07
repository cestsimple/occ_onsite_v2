import threading
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.db import DatabaseError
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.http import JsonResponse
from django.views import View
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from apps.iot.models import Bulk, Apsa, Variable, Record, Site, Asset
from utils.CustomMixins import ListViewSet, RetrieveUpdateViewSet, ListUpdateViewSet
from .models import Filling, Daily, DailyMod, Malfunction, Reason, ReasonDetail, FillingMonthly, MonthlyVariable
from .serializer import FillingSerializer, DailySerializer, DailyModSerializer, MalfunctionSerializer, \
    FillingMonthlySerializer, MonthlyVariableSerializer
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
        variables = Variable.objects.filter(asset__bulk__filling_js__gte=1, daily_mark='LEVEL')

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


class DailyCalculate(View):
    def __init__(self):
        self.t_start = ''
        self.t_end = ''
        self.apsa = None
        self.error = 0
        self.error_variables = []
        self.daily_res = {
            'h_prod': 0,
            'h_stpal': 0,
            'h_stpdft': 0,
            'h_stp400v': 0,
            'm3_prod': 0,
            'm3_tot': 0,
            'm3_q1': 0,
            'm3_peak': 0,
            'm3_q5': 0,
            'm3_q6': 0,
            'm3_q7': 0,
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
        apsas = Apsa.objects.filter(daily_js__gte=1, asset__confirm=1).order_by('daily_js')

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

            # 清空全局变量
            self.error = 0
            self.error_variables = []
            self.daily_res = {
                'h_prod': 0,
                'h_stpal': 0,
                'h_stpdft': 0,
                'h_stp400v': 0,
                'm3_prod': 0,
                'm3_tot': 0,
                'm3_q1': 0,
                'm3_peak': 0,
                'm3_q5': 0,
                'm3_q6': 0,
                'm3_q7': 0,
                'filling': 0,
                'lin_tot': 0,
                'flow_meter': 0,
            }

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
                # 查询其所有daily_mark数据
                data_today = Record.objects.get(variable__id=v.id, time=self.t_end).value
                data_yesterday = Record.objects.get(variable__id=v.id, time=self.t_start).value
                # 根据时间，计算该daily_mark的值
                self.daily_res[v.daily_mark.lower()] = round(data_today - data_yesterday, 2)
            except Exception as e:
                # 若查数据缺失，错误标志置1
                self.error = 1
                self.error_variables.append(v.name.replace('M3_', '').replace('H_', ''))

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
            try:
                l_0 = Record.objects.filter(variable__asset__bulk=bulk).get(time=t_start + ' 00:00:00').value
                l_1 = Record.objects.filter(variable__asset__bulk=bulk).get(time=t_end + ' 00:00:00').value
                lin_bulks += (l_0 - l_1) / 100 * bulk.tank_size * 1000  # 单位:升(液态)
            except Exception:
                l_0 = l_1 = lin_bulks = 0
                self.error = 1
                self.error_variables.append('lin_bulk')
            # 添加液位差数据至res中，以便计入数据库

        # 计算lin_tot,单位标立 = 储罐消耗 + 充液
        lin_tot = round((filling_quantity + lin_bulks) / 1000 * 650 * (273.15 + self.apsa.temperature) / 273.15, 2)

        # 保存数据
        self.daily_res['lin_tot'] = lin_tot
        self.daily_res['filling'] = round(filling_quantity, 2)

    def get_lin_tot_complex(self):
        """
            共用储罐的apsa的lin_tot
            公式：(m3产量*补冷值/100)+m3_q6+m3_q7+m3_peak
        """
        # 获取设定的cooling值
        cooling_fixed = self.apsa.cooling_fixed

        # 根据cooling反推lin_tot，再加上停机用液和Peak
        lin_tot = round(self.daily_res['m3_prod'] * cooling_fixed / 100, 2)
        lin_tot += self.daily_res['m3_q6'] + self.daily_res['m3_q7'] + self.daily_res['m3_peak']

        # 保存数据
        self.daily_res['lin_tot'] = lin_tot

    def generate_daily(self):
        # 生成成功daily
        d_res = self.daily_res
        d_res['success'] = 0

        # 添加成功标志位
        if not self.error:
            d_res['success'] = 1

        # Daily写入数据库
        Daily.objects.update_or_create(
            apsa=self.apsa, date=self.t_start,
            defaults=d_res
        )

    def generate_daily_mod(self):
        res = {
            'user': 'SYSTEM'
        }
        if self.error:
            # 获取报错变量信息，并对数据长度进行检查
            comment = '报错变量:' + f"{'|'.join(self.error_variables)}"
            if len(comment) > 300:
                comment = comment[:300]
            res['comment'] = comment

        try:
            # 创建APSA自己的MOD数据
            DailyMod.objects.update_or_create(
                apsa=self.apsa, date=self.t_start,
                defaults=res
            )

            # 若为从气站，需要创建第两条mod数据，更新主机的mod数据
            if self.apsa.daily_js == 2:
                apsa = Apsa.objects.get(id=self.apsa.daily_bind)
                DailyMod.objects.update_or_create(
                    apsa=apsa, date=self.t_start,
                    defaults={
                        'lin_tot_mod': -self.daily_res['lin_tot']
                    }
                )
        except Exception as e:
            print(e)

    def generate_malfunction(self):
        """生成停机Malfunction"""
        d_res = self.daily_res

        if d_res['h_stpal'] or d_res['h_stpdft'] or d_res['h_stp400v']:
            if d_res['h_stpal']:
                default = {
                    'stop_label': 'AL',
                    'stop_consumption': d_res['m3_q6'],
                    'stop_hour': d_res['h_stpal'],
                }
            elif d_res['h_stpdft']:
                default = {
                    'stop_label': 'DFT',
                    'stop_consumption': 0,
                    'stop_hour': d_res['h_stpdft'],
                }
            elif d_res['h_stp400v']:
                default = {
                    'stop_label': '400V',
                    'stop_consumption': d_res['m3_q7'],
                    'stop_hour': d_res['h_stp400v'],
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


class FillMonthlyCalculate(View):
    """计算月充液报表"""
    def __init__(self):
        self.start = ''
        self.end = ''
        self.bulk = None

    def get(self, request):
        # 检查Job状态
        if jobs.check('ONSITE_FILLING_MONTHLY'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 检查日期是否在21号之后，并设置日期
        if datetime.today().day < 6:
            jobs.update('ONSITE_FILLING_MONTHLY', 'ERROR: RequestTooEarly')
            return JsonResponse({'status': 400, 'msg': '请在21号或以后生成数据'})
        try:
            month = datetime.today().month
            year = datetime.today().year
            self.end = datetime(year, month, 6)
            self.start = self.end + relativedelta(months=-1)
        except Exception:
            jobs.update('ONSITE_FILLING_MONTHLY', 'ERROR: QueryDateSetError')
            return JsonResponse({'status': 400, 'msg': '查询时间设置错误'})

        # 创建子线程
        threading.Thread(target=self.calculate_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def calculate_main(self):
        # 获取所有储罐
        bulks = Bulk.objects.filter(filling_js__gte=1)

        # 异常处理
        try:
            # 对储罐循环
            for bulk in bulks:
                # 设置全局变量,设置过程变量
                self.bulk = bulk
                f_quantity = 0

                # 抓取开头结尾液位
                l_start = self.get_level(self.start)
                l_end = self.get_level(self.end)

                # 抓取时间范围内所有Filling记录(液态L)
                f_quantity += sum([
                    x.quantity for x in Filling.objects.filter(bulk=bulk, time_1__range=[self.start, self.end])
                ])

                # 公式计算汇总记录(液态立方米) f = 始末液位*容积(M3) + 月度充液量(M3)
                quantity = (l_start - l_end) * bulk.tank_size / 100 + f_quantity / 1000

                # 数据库保存或更新
                FillingMonthly.objects.update_or_create(
                    bulk=bulk, date=self.end,
                    defaults={
                        'start': l_start,
                        'end': l_end,
                        'quantity': round(quantity, 2),
                    }
                )
        except Exception as e:
            # 更新Job状态
            jobs.update('ONSITE_FILLING_MONTHLY', f'calculate_main(): {e}')
        else:
            jobs.update('ONSITE_FILLING_MONTHLY', 'OK')

    def get_level(self, date):
        try:
            r = Record.objects.get(variable__asset__bulk=self.bulk, time=date)
            if r.value != 0 and date == self.start:
                print(r.id)
            return Record.objects.get(variable__asset__bulk=self.bulk, time=date).value
        except Exception:
            return 0


class FillingModelView(ModelViewSet):
    # 查询集
    queryset = Filling.objects.order_by('confirm', 'bulk__asset__rtu_name', 'time_1')
    # 序列化器
    serializer_class = FillingSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 重写，添加条件过滤功能
        querry = self.request.query_params
        start = querry.get('start')
        end = querry.get('end')
        name = querry.get('name')
        region = querry.get('region')
        group = querry.get('group')

        if region:
            self.queryset = self.queryset.filter(bulk__asset__site__engineer__region=region)
        if group:
            self.queryset = self.queryset.filter(bulk__asset__site__engineer__group=group)
        if name:
            name = name.strip().upper()
            self.queryset = self.queryset.filter(
                Q(bulk__asset__rtu_name__contains=name) | Q(bulk__asset__site__name__contains=name)
            )
        if start and end:
            start = start.replace('+', '')
            end = end.replace('+', '')
            self.queryset = self.queryset.filter(time_1__range=[start, end])

        return self.queryset

    def create(self, request, *args, **kwargs):
        bulk = request.data.get('bulk')
        time_1 = request.data.get('time_1')
        time_2 = request.data.get('time_2')
        level_1 = float(request.data.get('level_1'))
        level_2 = float(request.data.get('level_2'))

        # 验证是否存在充液记录
        if Filling.objects.filter(bulk=bulk, time_1=time_1).count() != 0:
            return Response(f'创建失败，储罐和时间冲突，已存在该记录', status=status.HTTP_400_BAD_REQUEST)

        try:
            tank_size = float(Bulk.objects.get(id=bulk).tank_size)
            quantity = round((level_2 - level_1) / 100 * tank_size * 1000, 2)
            filling = Filling(
                bulk_id=int(bulk),
                time_1=time_1,
                time_2=time_2,
                level_1=level_1,
                level_2=level_2,
                quantity=quantity,
                confirm=1
            )
            self.update_lin_tot(filling, quantity)
            filling.save()
        except DatabaseError as e:
            return Response(f'数据库操作异常: {e}', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '充液记录创建成功'})

    def update(self, request, pk):
        # 查询记录
        filling = Filling.objects.get(id=pk)
        # 获取参数
        bulk = request.data.get('bulk')
        time_1 = request.data.get('time_1')
        time_2 = request.data.get('time_2')
        level_1 = float(request.data.get('level_1'))
        level_2 = float(request.data.get('level_2'))
        tank_size = float(Bulk.objects.get(id=bulk).tank_size)
        quantity = round((level_2 - level_1) / 100 * tank_size * 1000, 2)  # 液体L
        # 保存数据
        try:
            filling.time_1 = time_1
            filling.time_2 = time_2
            filling.level_1 = level_1
            filling.level_2 = level_2
            self.update_lin_tot(filling, quantity - filling.quantity)
            filling.quantity = quantity
            filling.confirm = 1
            filling.save()
        except DatabaseError as e:
            return Response(f'数据库操作异常: {e}', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '修改充液记录成功'})

    def destroy(self, request, *args, **kwargs):
        filling = self.get_object()
        diff = filling.quantity
        try:
            self.update_lin_tot(filling, -diff)
            filling.delete()
        except Exception as e:
            print(e)
            return Response(f'数据库操作异常: {e}', status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 200, 'msg': '删除充液记录成功'})

    def update_lin_tot(self, filling, diff):
        if isinstance(filling.time_1, str):
            t = filling.time_1.split(' ')[0]
        else:
            t = filling.time_1.strftime('%Y-%m-%d')
        bulk = filling.bulk
        site = Site.objects.get(asset__bulk=bulk)
        apsa = Apsa.objects.get(asset__site=site, asset__is_apsa=1)
        try:
            daily = Daily.objects.get(apsa=apsa, date=t)
        except Exception:
            return
        lin_tot = round(diff / 1000 * 650 * (273.15 + apsa.temperature) / 273.15, 2)
        daily.lin_tot = round(daily.lin_tot + lin_tot, 2)
        daily.filling = round(daily.filling + diff)
        daily.save()


class FillMonthlyView(ListUpdateViewSet):
    # 查询集
    queryset = FillingMonthly.objects.order_by('bulk__asset__site__engineer_region')
    # 序列化器
    serializer_class = FillingMonthlySerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 重写，添加条件过滤功能
        querry = self.request.query_params
        date = querry.get('date')
        region = querry.get('region')

        if region:
            self.queryset = self.queryset.filter(bulk__asset__site__engineer__region=region)

        if date:
            self.queryset = self.queryset.filter(date=date+'-6')

        return self.queryset


class DailyModelView(ListUpdateViewSet):
    # 查询集
    queryset = Daily.objects.order_by('confirm', 'apsa__asset__site__engineer__region', 'apsa__onsite_series', 'apsa__asset__rtu_name')
    # 序列化器
    serializer_class = DailySerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 重写，添加条件过滤功能
        querry = self.request.query_params
        start = querry.get('start')
        end = querry.get('end')
        name = querry.get('name')
        region = querry.get('region')
        group = querry.get('group')

        if region:
            self.queryset = self.queryset.filter(apsa__asset__site__engineer__region=region)
        if group:
            self.queryset = self.queryset.filter(apsa__asset__site__engineer__group=group)
        if name:
            name = name.strip().upper()
            self.queryset = self.queryset.filter(
                Q(apsa__asset__rtu_name__contains=name) | Q(apsa__asset__site__name__contains=name)
            )
        if start and end:
            start = start.replace('+', '')
            end = end.replace('+', '')
            self.queryset = self.queryset.filter(date__range=[start, end])

        return self.queryset

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            res = self.generate_daily_data(serializer.data)
            return self.get_paginated_response(res)

        serializer = self.get_serializer(queryset, many=True)
        res = self.generate_daily_data(serializer.data)
        return Response(res)

    def update(self, request, pk):
        daily = Daily.objects.get(id=pk)
        daily.confirm = 1
        daily.success = 1
        daily.save()
        return Response({'status': 200, 'msg': '修改Daily记录成功'})

    def generate_daily_data(self, daily_origin_list):
        res_list = []
        for d in daily_origin_list:
            # 获取资产，气站
            site = Site.objects.get(asset__apsa__id=d['apsa'])
            asset = Asset.objects.get(apsa__id=d['apsa'])
            apsa = Apsa.objects.get(id=d['apsa'])
            mod = DailyMod.objects.get(date=d['date'], apsa__id=d['apsa'])
            # 创建内容
            h_prod = d['h_prod'] + mod.h_prod_mod
            h_stop = d['h_stpal']+d['h_stp400v']+d['h_stpdft']+ mod.h_stpal_mod + mod.h_stpdft_mod + mod.h_stp400v_mod
            h_missing = 24 - h_stop - h_prod
            m3_prod = d['m3_prod'] + mod.m3_prod_mod
            avg_prod = m3_prod / h_prod if h_prod else 0
            cus_consume = d['m3_tot'] + mod.m3_tot_mod
            avg_consume = cus_consume / 24
            peak = d['m3_peak'] + mod.m3_peak_mod
            v_peak = d['m3_q5'] + mod.m3_q5_mod
            lin_tot = d['lin_tot'] + mod.lin_tot_mod + d['flow_meter'] + mod.flow_meter_mod
            dif_peak = v_peak - peak
            lin_consume = d['m3_q6'] + mod.m3_q6_mod + d['m3_q7'] + mod.m3_q7_mod
            mod_id = mod.id
            if apsa.cooling_fixed:
                cooling = apsa.cooling_fixed
            else:
                cooling = ((lin_tot - peak - lin_consume) / m3_prod * 100) if m3_prod else 0

            # 添加数据
            res_list.append({
                'id': d['id'],
                'date': d['date'].split(' ')[0],
                'region': site.engineer.region,
                'series': apsa.onsite_series,
                'rtu_name': asset.rtu_name,
                'norminal': apsa.norminal_flow,
                'h_prod': round(h_prod, 2),
                'h_stop': round(h_stop, 2),
                'h_missing': round(h_missing, 2),
                'm3_prod': int(m3_prod),
                'avg_prod': round(avg_prod, 2),
                'cus_consume': round(cus_consume, 2),
                'avg_consume': int(avg_consume),
                'peak': round(peak, 2),
                'v_peak': round(v_peak, 2),
                'lin_tot': round(lin_tot, 2),
                'dif_peak': round(dif_peak, 2),
                'lin_consume': round(lin_consume, 2),
                'mod_id': round(mod_id, 2),
                'cooling': round(cooling, 2),
                'filling': round(d['filling'], 2),
                'vap_max': int(apsa.vap_max),
                'success': d['success'],
                'confirm': d['confirm'],
                'comment': mod.comment,
            })

        return res_list


class DailyOriginView(View):
    def get(self, request, pk):
        daily = Daily.objects.get(id=pk)
        return JsonResponse({
            'h_prod': daily.h_prod,
            'h_stpal': daily.h_stpal,
            'h_stpdft': daily.h_stpdft,
            'h_stp400v': daily.h_stp400v,
            'm3_prod': daily.m3_prod,
            'm3_tot': daily.m3_tot,
            'm3_q1': daily.m3_q1,
            'm3_peak': daily.m3_peak,
            'm3_q5': daily.m3_q5,
            'm3_q6': daily.m3_q6,
            'm3_q7': daily.m3_q7,
            'lin_tot': daily.lin_tot,
            'flow_meter': daily.flow_meter
        })


class DailyModModelView(RetrieveUpdateViewSet):
    # 查询集
    queryset = DailyMod.objects.all()
    # 序列化器
    serializer_class = DailyModSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]


class MalfunctionModelView(ModelViewSet):
    # 查询集
    queryset = Malfunction.objects.all().order_by('apsa__asset__site__engineer__region', 'apsa__onsite_series')
    # 序列化器
    serializer_class = MalfunctionSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 重写，添加条件过滤功能
        querry = self.request.query_params
        start = querry.get('start')
        end = querry.get('end')
        name = querry.get('name')
        region = querry.get('region')
        group = querry.get('group')

        if region:
            self.queryset = self.queryset.filter(apsa__asset__site__engineer__region=region)
        if group:
            self.queryset = self.queryset.filter(apsa__asset__site__engineer__group=group)
        if name:
            name = name.strip().upper()
            self.queryset = self.queryset.filter(
                Q(apsa__asset__rtu_name__contains=name) | Q(apsa__asset__site__name__contains=name)
            )
        if start and end:
            start = start.replace('+', '')
            end = end.replace('+', '')
            self.queryset = self.queryset.filter(t_start__range=[start, end])

        return self.queryset

    def create(self, request, *args, **kwargs):
        apsa_id = request.data.get('apsa_id')
        t_start = request.data.get('t_start')
        t_end = request.data.get('t_end')
        stop_label = request.data.get('stop_label')
        stop_alarm = request.data.get('stop_alarm')
        reason_main = request.data.get('reason_main')
        reason_l1 = request.data.get('reason_l1')
        reason_l2 = request.data.get('reason_l2')
        reason_l3 = request.data.get('reason_l3')
        reason_l4 = request.data.get('reason_l4')
        reason_detail_1 = request.data.get('reason_detail_1')
        reason_detail_2 = request.data.get('reason_detail_2')
        mt_comment = request.data.get('mt_comment')
        occ_comment = request.data.get('occ_comment')
        change_user = request.data.get('change_user')
        stop_count = int(request.data.get('stop_count'))
        stop_hour = float(request.data.get('stop_hour'))
        stop_consumption = float(request.data.get('stop_consumption'))

        # 验证是否存在充液记录
        if Malfunction.objects.filter(apsa=apsa_id, t_start=t_start).count() != 0:
            return Response(f'创建失败，气站时间冲突，已存在该记录', status=status.HTTP_400_BAD_REQUEST)

        try:
            Malfunction.objects.create(
                apsa_id=int(apsa_id),
                t_start=t_start,
                t_end=t_end,
                stop_consumption=stop_consumption,
                stop_count=stop_count,
                stop_hour=stop_hour,
                stop_label=stop_label,
                stop_alarm=stop_alarm,
                reason_main=reason_main,
                reason_l1=reason_l1,
                reason_l2=reason_l2,
                reason_l3=reason_l3,
                reason_l4=reason_l4,
                reason_detail_1=reason_detail_1,
                reason_detail_2=reason_detail_2,
                mt_comment=mt_comment,
                occ_comment=occ_comment,
                change_user=change_user,
                change_date=datetime.now()
            )
        except DatabaseError as e:
            return Response(f'数据库操作异常: {e}', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '充液记录创建成功'})


class ReasonModelView(ListViewSet):
    # 查询集
    queryset = Malfunction.objects.all()
    # 序列化器
    serializer_class = MalfunctionSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def list(self, request):
        query = request.query_params
        parent = query.get('parent')

        if not parent:
            try:
                # 查询一级原因
                reason_level_1 = Reason.objects.filter(parent=None)
                # 序列化一级原因
                reason_list = []
                for reason in reason_level_1:
                    reason_list.append({'id': reason.id, 'cname': reason.cname})
            except Exception as e:
                print(e)
                return JsonResponse({'code': 400, 'errmsg': '一级原因数据错误'})
            # 响应一级原因数据
            return JsonResponse({'code': 200, 'errmsg': 'OK', 'reason_list': reason_list})
        else:
            # 提供下级原因
            try:
                parent_model = Reason.objects.get(id=parent)  # 查询下级原因的父级
                sub_model_list = parent_model.subs.all()

                # 序列化下级原因数据
                sub_list = []
                for sub_model in sub_model_list:
                    sub_list.append({'id': sub_model.id, 'cname': sub_model.cname})

                sub_data = {
                    'id': parent_model.id,  # 父级pk
                    'cname': parent_model.cname,  # 父级name
                    'subs': sub_list  # 父级的子集
                }
            except Exception as e:
                print(e)
                return JsonResponse({'code': 400, 'errmsg': '下级原因数据错误'})

            return JsonResponse({'code': 200, 'errmsg': 'OK', 'sub_data': sub_data})


class ReasonDetailModelView(ListViewSet):
    # 查询集
    queryset = Malfunction.objects.all()
    # 序列化器
    serializer_class = MalfunctionSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def list(self, request):
        query = request.query_params
        parent = query.get('parent')

        if not parent:
            try:
                # 查询一级原因
                reason_level_1 = ReasonDetail.objects.filter(parent=None)
                # 序列化一级原因
                reason_list = []
                for reason in reason_level_1:
                    reason_list.append({'id': reason.id, 'cname': reason.cname})
            except Exception as e:
                print(e)
                return JsonResponse({'code': 400, 'errmsg': '一级原因数据错误'})
            # 响应一级原因数据
            return JsonResponse({'code': 200, 'errmsg': 'OK', 'reason_list': reason_list})
        else:
            # 提供下级原因
            try:
                parent_model = ReasonDetail.objects.get(id=parent)  # 查询下级原因的父级
                sub_model_list = parent_model.subs.all()

                # 序列化下级原因数据
                sub_list = []
                for sub_model in sub_model_list:
                    sub_list.append({'id': sub_model.id, 'cname': sub_model.cname})

                sub_data = {
                    'id': parent_model.id,  # 父级pk
                    'cname': parent_model.cname,  # 父级name
                    'subs': sub_list  # 父级的子集
                }
            except Exception as e:
                print(e)
                return JsonResponse({'code': 400, 'errmsg': '下级原因数据错误'})

            return JsonResponse({'code': 200, 'errmsg': 'OK', 'sub_data': sub_data})


class MonthlyVariableModelView(ModelViewSet):
    # 查询集
    queryset = MonthlyVariable.objects.order_by('apsa__asset__site__engineer_region')
    # 序列化器
    serializer_class = MonthlyVariableSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 条件过滤功能
        querry = self.request.query_params
        name = querry.get('name')
        region = querry.get('region')
        group = querry.get('group')

        if region:
            self.queryset = self.queryset.filter(apsa__asset__site__engineer__region=region)
        if group:
            self.queryset = self.queryset.filter(apsa__asset__site__engineer__group=group)
        if name:
            name = name.strip().upper()
            self.queryset = self.queryset.filter(
                Q(apsa__asset__rtu_name__contains=name) | Q(apsa__asset__site__name__contains=name)
            )

        return self.queryset
