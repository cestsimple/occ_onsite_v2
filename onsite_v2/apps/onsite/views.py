import threading
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from django.db import DatabaseError
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from django.http import JsonResponse
from django.views import View
from rest_framework.permissions import IsAuthenticated

from apps.iot.models import Bulk, Apsa, Variable, Record, Site, Asset
from utils.CustomMixins import ListViewSet, RetrieveUpdateViewSet, ListUpdateViewSet
from .models import Filling, Daily, DailyMod, Malfunction, Reason, ReasonDetail, FillingMonthly, MonthlyVariable, \
    InvoiceDiff
from .serializer import FillingSerializer, DailySerializer, DailyModSerializer, MalfunctionSerializer, \
    FillingMonthlySerializer, InvoiceVariableSerializer, InvoiceDiffSerializer
from utils import jobs
from utils.pagination import PageNum


class FillingCalculate(View):
    def __init__(self):
        self.date_list = []
        self.apsa_list = []
        self.t_start = ''
        self.t_end = ''

    def get(self, request):
        # 获取filling日期参数
        self.date_list = request.GET.getlist('date_list[]', [])
        self.apsa_list = request.GET.getlist('apsa_list[]', [])

        # 检查Job状态
        if jobs.check('ONSITE_FILLING'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 创建子线程
        threading.Thread(target=self.calculate_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def calculate_main(self):
        # 设置起始时间
        self.set_date()

        # 按照apsa过滤,获取所有需要计算的bulk的variable
        self.set_variables()

        # 对每个储罐进行计算
        for variable in self.variables:
            records = {}
            data = Record.objects.filter(variable=variable).filter(time__range=[self.t_start, self.t_end]).order_by(
                'time')
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
            if diff_list[i] < -0.01:
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

    def set_date(self):
        if self.date_list is not None and self.date_list != []:
            self.t_start = self.date_list[0] + ' 00:00'
            d = (datetime.strptime(self.date_list[1], '%Y-%m-%d') + timedelta(days=1))
            self.t_end = d.strftime("%Y-%m-%d") + ' 00:00'
        else:
            self.t_start = (datetime.now() + timedelta(days=-1)).strftime("%Y-%m-%d") + ' 00:00'
            self.t_end = datetime.now().strftime("%Y-%m-%d") + ' 00:00'

    def set_variables(self):
        # 按照apsa过滤
        if self.apsa_list:
            sites = [x for x in Site.objects.filter(asset__apsa__id__in=self.apsa_list)]
            assets = [x for x in Asset.objects.filter(site__in=sites, bulk__filling_js__gte=1)]
            self.variables = [x for x in Variable.objects.filter(asset__in=assets, daily_mark='LEVEL', confirm__gt=-1)]
        else:
            self.variables = Variable.objects.filter(asset__bulk__filling_js__gte=1, daily_mark='LEVEL', confirm__gt=-1)


class DailyCalculate(View):
    def __init__(self):
        self.t_start = ''
        self.t_end = ''
        self.date_range = []
        self.date_list = []
        self.apsa_list = []
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
        self.date_range = request.GET.getlist('date_list[]', [])
        self.apsa_list = request.GET.getlist('apsa_list[]', [])

        # 检查Job状态
        if jobs.check('ONSITE_DAILY'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 创建子线程
        threading.Thread(target=self.calculate_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def calculate_main(self):
        # 设定时间(参数：时间字符串)
        self.set_date()

        # 查询所有需要计算的Apsa
        apsas = Apsa.objects.filter(daily_js__gte=1, asset__confirm=1).order_by('daily_js')

        # 过滤参数中传入的气站
        if self.apsa_list:
            self.apsa_list = [int(x) for x in self.apsa_list]
            apsas = apsas.filter(id__in=self.apsa_list)

        for date in self.date_list:
            # 设置起始日期
            self.set_time(date)

            # 计算每个apsa
            for apsa in apsas:
                # 传递apsa全局使用
                self.apsa = apsa

                # 获取daily参数
                self.get_daily_res()
                d_res = self.daily_res

                # 如果数据源错误，可以计算lin_tot的继续计算 (设备有可能会抖动，导致累积量出现小的负值)
                if apsa.daily_js == 1 or apsa.daily_js == 5:
                    # 单机apsa计算
                    self.get_lin_tot_simple()
                else:
                    if d_res['m3_prod'] >= -0.99 and d_res['m3_q6'] >= -0.99 and d_res['m3_q7'] >= -0.99 and d_res[
                        'm3_peak'] >= -0.99:
                        # 共用apsa计算(该机器固定补冷)
                        self.get_lin_tot_complex()
                    else:
                        self.error = 1
                        self.error_variables.append('M3出现负数')

                # 若有停机写入停机
                self.generate_malfunction()

                # 若daily存在且确认则跳过daily和mod
                d = Daily.objects.filter(apsa=self.apsa, date=self.t_start)
                if not (d.count() == 1 and d[0].confirm == 1):
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
        self.t_start = date
        self.t_end = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=1)).strftime("%Y-%m-%d")

    def get_daily_res(self):
        # 对于每个需要计算的variable
        variables = Variable.objects.filter(asset__apsa=self.apsa, confirm__gt=-1).filter(~Q(daily_mark=''))
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
            variable = Variable.objects.get(asset=bulk.asset, daily_mark='LEVEL')
            try:
                l_0 = Record.objects.filter(variable=variable).get(time=t_start + ' 00:00:00').value
                l_1 = Record.objects.filter(variable=variable).get(time=t_end + ' 00:00:00').value
                lin_bulks += (l_0 - l_1) / 100 * bulk.tank_size * 1000  # 单位:升(液态)
            except Exception:
                lin_bulks = 0
                self.error = 1
                self.error_variables.append('bulk_level')
            # 添加液位差数据至res中，以便计入数据库

        # 计算lin_tot,单位标立 = 储罐消耗 + 充液
        lin_tot = round((filling_quantity + lin_bulks) / 1000 * 650 * (273.15 + self.apsa.temperature) / 273.15, 2)

        # 保存数据
        self.daily_res['lin_tot'] = round(lin_tot, 2)
        self.daily_res['filling'] = round(filling_quantity, 2)

    def get_lin_tot_complex(self):
        """
            共用储罐的apsa的lin_tot
            公式：(m3产量*补冷值/100)+m3_q6+m3_q7+m3_peak
        """
        # 获取设定的cooling值
        cooling_fixed = self.apsa.cooling_fixed

        # 根据cooling反推lin_tot，再加上停机用液和Peak
        lin_tot = self.daily_res['m3_prod'] * cooling_fixed / 100
        lin_tot += self.daily_res['m3_q6'] + self.daily_res['m3_q7'] + self.daily_res['m3_peak']

        # 保存数据
        self.daily_res['lin_tot'] = round(lin_tot, 2)

    def generate_daily(self):
        # 生成成功daily
        d_res = self.daily_res
        d_res['success'] = 0

        # 添加成功标志位
        if not self.error:
            d_res['success'] = 1

        # 若为从气站，且已有数据(重跑)，先恢复主气站lin_tot_mod
        record = Daily.objects.filter(apsa=self.apsa, date=self.t_start)
        if self.apsa.daily_js == 2 and record.count() == 1:
            apsa = Apsa.objects.get(id=self.apsa.daily_bind)
            bind_daily_mod = DailyMod.objects.get(apsa=apsa, date=self.t_start)
            bind_daily_mod.lin_tot_mod += round(record[0].lin_tot, 2)
            bind_daily_mod.save()

        # Daily写入数据库
        Daily.objects.update_or_create(
            apsa=self.apsa, date=self.t_start,
            defaults=d_res
        )

    def generate_daily_mod(self):
        comment = ''
        if self.error:
            # 获取报错变量信息，并对数据长度进行检查
            comment = '报错变量:' + f"{'|'.join(self.error_variables)}"
            if len(comment) > 300:
                comment = comment[:300]

        try:
            # 创建自己的MOD数据
            daily_mod = DailyMod.objects.filter(apsa=self.apsa, date=self.t_start)
            if daily_mod.count() == 1:
                # 若已存在daily_mod说明是重跑，则先删除mod
                daily_mod[0].delete()

            DailyMod.objects.create(
                apsa=self.apsa,
                date=self.t_start,
                comment=comment,
                user='SYSTEM'
            )

            # 若为从气站，需要创建第两条mod数据，更新主气站lin_tot_mod数据
            if self.apsa.daily_js == 2:
                apsa = Apsa.objects.get(id=self.apsa.daily_bind)
                bind_daily_mod = DailyMod.objects.get(apsa=apsa, date=self.t_start)
                bind_daily_mod.lin_tot_mod -= round(self.daily_res['lin_tot'], 2)
                bind_daily_mod.save()
        except Exception as e:
            print(e)

    def generate_malfunction(self):
        """生成停机Malfunction"""
        d_res = self.daily_res
        has_al = 0

        # 循环三次，判断三种停机是否出现
        for i in range(3):
            # 是否停机标志位
            has_stopped = 0

            # 获取停机时常信息
            if i == 0 and d_res['h_stpal']:
                has_stopped = 1
                has_al = 1
                consumption = d_res['m3_q6']
                default = {'stop_label': 'AL',
                           'stop_consumption': consumption,
                           'stop_hour': d_res['h_stpal']}

            if i == 1 and d_res['h_stpdft']:
                has_stopped = 1
                # 如果已经记过AL则DFT的用液不计
                if has_al:
                    consumption = 0
                else:
                    consumption = d_res['m3_q6']

                default = {'stop_label': 'DFT',
                           'stop_consumption': consumption,
                           'stop_hour': d_res['h_stpdft']}

            if i == 2 and d_res['h_stp400v']:
                has_stopped = 1
                default = {'stop_label': '400V',
                           'stop_consumption': d_res['m3_q7'],
                           'stop_hour': d_res['h_stp400v']}

            # 判断标志位创建停机记录
            if has_stopped:
                default['t_end'] = self.t_start

                # 判断是否存在且确认，是则跳过
                m = Malfunction.objects.filter(apsa=self.apsa, t_start=self.t_start, stop_label=default['stop_label'])
                if not (m.count() == 1 and m[0].confirm == 1):
                    # 生成或更新记录
                    default['change_date'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    default['change_user'] = 'system'
                    Malfunction.objects.update_or_create(
                        apsa=self.apsa, t_start=self.t_start, stop_label=default['stop_label'],
                        defaults=default
                    )

    def set_date(self):
        if not self.date_range:
            yesterday = (datetime.now() + timedelta(days=-1)).strftime("%Y-%m-%d")
            self.date_list.append(yesterday)
        else:
            t_start = self.date_range[0]
            t_end = self.date_range[1]
            while t_start != t_end:
                self.date_list.append(t_start)
                t_start = (datetime.strptime(t_start, '%Y-%m-%d') + timedelta(days=1)).strftime("%Y-%m-%d")
            self.date_list.append(t_end)


class FillMonthlyCalculate(APIView):
    """计算月充液报表"""

    def __init__(self):
        self.start = ''
        self.end = ''
        self.bulk = None

    def get(self, request):
        query_params = request.GET
        start = query_params.get('start')
        self.region = query_params.get('region')

        # 检查Job状态
        if jobs.check('ONSITE_FILLING_MONTHLY'):
            return Response('任务正在进行中，请稍后刷新', status=status.HTTP_400_BAD_REQUEST)

        # 设置时间
        try:
            # day = int(start.split('-')[-1])
            month = datetime.today().month
            year = datetime.today().year
            self.end = datetime(year, month, 21)
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

        if self.region:
            bulks = bulks.filter(asset__site__engineer__region=self.region)

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
                    x.quantity for x in
                    Filling.objects.filter(confirm=1, bulk=bulk, time_1__range=[self.start, self.end])
                ])

                # 公式计算汇总记录(液态立方米) f = 始末液位*容积(M3) + 月度充液量(M3)
                quantity = f_quantity / 1000

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
            return Record.objects.get(variable__asset__bulk=self.bulk, time=date).value
        except Exception:
            return 0


class InvoiceDiffCalculate(APIView):
    """计算月报表变量差值"""

    def __init__(self):
        self.start = ''
        self.end = ''
        self.region = ''
        self.variable = None

    def get(self, request):
        # 获取计算日期
        query_params = request.GET
        date = query_params.getlist('date[]')
        self.region = query_params.get('region')

        # 检查Job状态
        if jobs.check('ONSITE_INVOICE_DIFF'):
            return Response('任务正在进行中，请稍后刷新', status=status.HTTP_400_BAD_REQUEST)

        # 设置时间
        try:
            self.end = date[-1]
            self.start = date[0]
        except Exception:
            jobs.update('ONSITE_INVOICE_DIFF', 'ERROR: SetQueryDateError')
            return JsonResponse({'status': 400, 'msg': '查询时间设置错误'})

        # 创建子线程
        threading.Thread(target=self.calculate_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def calculate_main(self):
        # 获取所有需要计算的variables
        monthly_variable_matches = MonthlyVariable.objects.filter(usage='INVOICE')
        if self.region:
            monthly_variable_matches = monthly_variable_matches.filter(apsa__asset__site__engineer__region=self.region)

        # 异常处理
        try:
            # 对记录循环
            for match in monthly_variable_matches:
                # 设置全局变量
                self.variable = match.variable

                # 抓取开头结尾液位
                v_start = self.get_value(self.start)
                v_end = self.get_value(self.end)

                # 数据库保存或更新
                InvoiceDiff.objects.update_or_create(
                    apsa=match.apsa,
                    date=self.end,
                    variable=match.variable,
                    defaults={
                        'usage': 'INVOICE',
                        'start': v_start,
                        'end': v_end,
                    }
                )
        except Exception as e:
            # 更新Job状态
            jobs.update('ONSITE_INVOICE_DIFF', f'calculate_main(): {e}')
        else:
            jobs.update('ONSITE_INVOICE_DIFF', 'OK')

    def get_value(self, date):
        try:
            return Record.objects.get(variable=self.variable, time=date).value
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
        confirm = float(request.data.get('confirm'))

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
                confirm=confirm
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
        confirm = float(request.data.get('confirm'))
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
            filling.confirm = confirm
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
        # 有可能有两台apsa
        apsa = Apsa.objects.get(asset__rtu_name=bulk.asset.rtu_name, asset__is_apsa=1, asset__confirm=1)
        try:
            daily = Daily.objects.get(apsa=apsa, date=t)
        except Exception:
            return
        lin_tot = round(diff / 1000 * 650 * (273.15 + apsa.temperature) / 273.15, 2)
        daily.lin_tot = round(daily.lin_tot + lin_tot, 2)
        daily.filling = round(daily.filling + diff)
        daily.save()


class FillingMonthlyView(ListUpdateViewSet):
    # 查询集
    queryset = FillingMonthly.objects.all()
    # 序列化器
    serializer_class = FillingMonthlySerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 重写，添加条件过滤功能
        query = self.request.query_params
        date = query.get('date')
        region = query.get('region')
        self.aggr = query.get('aggr')

        if date:
            self.queryset = self.queryset.filter(date=date + '-21')

        if region:
            self.queryset = self.queryset.filter(bulk__asset__site__engineer__region=region)

        return self.queryset

    def list(self, request):
        queryset = self.get_queryset()
        # ordered_queryset = {}
        # for q in self.get_queryset():
        #     if e := q.bulk.asset.site.engineer:
        #         region = e.region
        #     else:
        #         region = '11'
        #     ordered_queryset[region+q.bulk.asset.rtu_name] = q
        #
        # queryset = []
        # keys = sorted([i for i in ordered_queryset.keys()])
        #
        # for x in keys:
        #     queryset.append(ordered_queryset[x])
        #
        # for x in queryset:
        #     print(x.bulk.asset.rtu_name)

        sites = [x['bulk__asset__rtu_name'] for x in queryset.values('bulk__asset__rtu_name').distinct()]

        page_sites = self.paginate_queryset(sites)

        if page_sites is not None:
            q = queryset.filter(bulk__asset__rtu_name__in=page_sites)

            if self.aggr == '1':
                rsp = self.aggregate(page_sites, q)
            else:
                serializer = self.get_serializer(q, many=True)
                rsp = serializer.data

            return self.get_paginated_response(rsp)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def aggregate(self, sites, q):
        rsp = []
        for site in sites:
            engineer = None
            total = 0
            date = ''

            for i in q.filter(bulk__asset__rtu_name=site):
                lin_bulk = (i.start - i.end) * i.bulk.tank_size / 100
                date = i.date
                total += i.quantity + lin_bulk
                engineer = i.bulk.asset.site.engineer

            rsp.append({
                "date": date.strftime('%Y-%m-%d'),
                "region": engineer.region if engineer else '',
                "rtu_name": site,
                "total": round(total, 2)
            })
        return rsp


class FillingMonthlyDetailView(APIView):
    def get(self, request):
        query = request.query_params
        date = query.get('date')
        region = query.get('region')

        if not date:
            return Response('缺少参数', status=status.HTTP_400_BAD_REQUEST)

        try:
            filling_query = Filling.objects.filter(confirm=1)
            if region:
                filling_query = filling_query.filter(bulk__asset__site__engineer__region=region.upper())

            if date:
                month = int(date.split('-')[-1])
                year = int(date.split('-')[0])
                end = datetime(year, month, 1)
                start = end + relativedelta(months=-1)
                filling_query = filling_query.filter(time_1__range=[start, end])

            res = []
            for record in filling_query.order_by('bulk__asset__rtu_name'):
                res.append({
                    'rtu_name': record.bulk.asset.rtu_name,
                    'asset_name': record.bulk.asset.name,
                    'time_1': record.time_1.strftime("%Y-%m-%d %H:%M"),
                    'time_2': record.time_2.strftime("%Y-%m-%d %H:%M"),
                    'level_1': record.level_1,
                    'level_2': record.level_2,
                    'quantity': round(record.quantity / 1000, 2)
                })
        except Exception as e:
            print(e)
            return Response('数据库错误', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(res)


class DailyModelView(ListUpdateViewSet):
    # 查询集
    queryset = Daily.objects.order_by('confirm', 'apsa__asset__site__engineer__region', '-apsa__onsite_series',
                                      'apsa__asset__rtu_name')
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
            h_stop = d['h_stpal'] + d['h_stp400v'] + d[
                'h_stpdft'] + mod.h_stpal_mod + mod.h_stpdft_mod + mod.h_stp400v_mod
            h_missing = 24 - h_stop - h_prod
            m3_prod = d['m3_prod'] + mod.m3_prod_mod
            avg_prod = m3_prod / h_prod if h_prod else 0
            cus_consume = d['m3_tot'] + mod.m3_tot_mod
            avg_consume = cus_consume / 24
            peak = d['m3_peak'] + mod.m3_peak_mod
            v_peak = d['m3_q5'] + mod.m3_q5_mod
            lin_tot = d['lin_tot'] + mod.lin_tot_mod - d['flow_meter'] - mod.flow_meter_mod
            dif_peak = v_peak - peak
            lin_consume = d['m3_q6'] + mod.m3_q6_mod + d['m3_q7'] + mod.m3_q7_mod
            mod_id = mod.id
            if apsa.cooling_fixed and apsa.daily_js == 2:
                cooling = apsa.cooling_fixed
            else:
                cooling = ((lin_tot - peak - lin_consume) / m3_prod * 100) if m3_prod else 0
            filling = d['filling'] * 0.65 * (apsa.temperature + 273.15) / 273.15

            # 添加数据
            res_list.append({
                'id': d['id'],
                'date': d['date'].split(' ')[0],
                'region': site.engineer.region if site.engineer else '',
                'series': apsa.onsite_series,
                'rtu_name': asset.rtu_name,
                'norminal': apsa.norminal_flow,
                'h_prod': round(h_prod, 2),
                'h_stop': round(h_stop, 2),
                'h_missing': round(h_missing, 2),
                'm3_prod': round(m3_prod, 2),
                'avg_prod': round(avg_prod, 2),
                'cus_consume': round(cus_consume, 2),
                'avg_consume': round(avg_consume, 2),
                'peak': round(peak, 2),
                'v_peak': round(v_peak, 2),
                'lin_tot': round(lin_tot, 2),
                'dif_peak': round(dif_peak, 2),
                'lin_consume': round(lin_consume, 2),
                'mod_id': round(mod_id, 2),
                'cooling': round(cooling, 2),
                'filling': round(filling, 2),
                'vap_max': round(apsa.vap_max, 2),
                'success': d['success'],
                'confirm': d['confirm'],
                'mark': apsa.mark,
                'comment': mod.comment,
            })

        return res_list


class DailyModModelView(RetrieveUpdateViewSet):
    # 查询集
    queryset = DailyMod.objects.all()
    # 序列化器
    serializer_class = DailyModSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def update(self, request, pk):
        daily_mod = DailyMod.objects.get(id=pk)
        apsa = daily_mod.apsa
        # 如果是从设备，需要联动更新LIN_TOT和主设备的LIN_TOT
        if apsa.daily_js > 1:
            # 获取旧数据
            old_prod = daily_mod.m3_prod_mod
            old_peak = daily_mod.m3_peak_mod
            old_q6 = daily_mod.m3_q6_mod
            old_q7 = daily_mod.m3_q7_mod
            old_lin_tot = daily_mod.lin_tot_mod

            # 判断是否更新了q6, q7, peak, prod
            if request.data.get('lin_tot_mod') == old_lin_tot:
                if request.data.get('m3_prod_mod') != old_prod or request.data.get(
                        'm3_peak_mod') != old_peak or request.data.get('m3_q6_mod') != old_q6 or request.data.get(
                    'm3_q7_mod') != old_q7:
                    # 如果更新了其中的任何一个，重新计算lin_tot
                    lin_tot = request.data.get('m3_prod_mod') * apsa.cooling_fixed / 100
                    lin_tot += request.data.get('m3_q6_mod') + request.data.get('m3_q7_mod') + request.data.get(
                        'm3_peak_mod')

                    # 获取主设备
                    main_apsa_id = apsa.daily_bind

                    # 将新老lin_tot差值更新到主设备中
                    diff_lin_tot = lin_tot - old_lin_tot
                    main_daily_mod = DailyMod.objects.get(date=daily_mod.date, apsa_id=main_apsa_id)
                    main_daily_mod.lin_tot_mod = round(main_daily_mod.lin_tot_mod - diff_lin_tot, 2)
                    main_daily_mod.save()

                    # 更新从设备lin_tot
                    daily_mod.lin_tot_mod = lin_tot
            else:
                # 获取主设备
                main_apsa_id = apsa.daily_bind
                # 若手动填写了lin_tot则不再重新计算，默认已计算过
                lin_tot = request.data.get('lin_tot_mod')
                diff_lin_tot = lin_tot - old_lin_tot
                main_daily_mod = DailyMod.objects.get(date=daily_mod.date, apsa_id=main_apsa_id)
                main_daily_mod.lin_tot_mod = round(main_daily_mod.lin_tot_mod - diff_lin_tot, 2)
                main_daily_mod.save()

                # 更新从设备lin_tot
                daily_mod.lin_tot_mod = lin_tot
        else:
            daily_mod.lin_tot_mod = request.data.get('lin_tot_mod')
        daily_mod.h_prod_mod = request.data.get('h_prod_mod')
        daily_mod.h_stpal_mod = request.data.get('h_stpal_mod')
        daily_mod.h_stpdft_mod = request.data.get('h_stpdft_mod')
        daily_mod.h_stp400v_mod = request.data.get('h_stp400v_mod')
        daily_mod.m3_prod_mod = request.data.get('m3_prod_mod')
        daily_mod.m3_tot_mod = request.data.get('m3_tot_mod')
        daily_mod.m3_q1_mod = request.data.get('m3_q1_mod')
        daily_mod.m3_peak_mod = request.data.get('m3_peak_mod')
        daily_mod.m3_q5_mod = request.data.get('m3_q5_mod')
        daily_mod.m3_q6_mod = request.data.get('m3_q6_mod')
        daily_mod.m3_q7_mod = request.data.get('m3_q7_mod')
        daily_mod.flow_meter_mod = request.data.get('flow_meter_mod')
        daily_mod.user = request.data.get('user')
        daily_mod.comment = request.data.get('comment')
        daily_mod.save()
        return Response({'status': 200, 'msg': '修改DailyMod成功'})


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


class DailyLintotView(View):
    def get(self, request, pk):
        rsp = []
        daily = Daily.objects.get(id=pk)
        apsa = daily.apsa
        if apsa.daily_js == 0:
            return JsonResponse([{
                "error": 1,
                "msg": "该APSA不计算daily"
            }], safe=False)
        elif apsa.daily_js == 2:
            main_apsa = Apsa.objects.get(id=apsa.daily_bind)
            return JsonResponse([{
                "error": 1,
                "msg": f"该APSA从属于{main_apsa.asset.rtu_name}，LINTOT为固定值"
            }], safe=False)
        t_start = daily.date
        t_end = (t_start + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        bulks = Bulk.objects.filter(asset__site=apsa.asset.site, filling_js=1)
        for bulk in bulks:
            filling_quantity = sum([
                x.quantity for x in Filling.objects.filter(bulk=bulk, time_1__range=[t_start, t_end])
            ])
            # 计算储罐首尾液位差量
            variable = Variable.objects.get(asset=bulk.asset, daily_mark='LEVEL')
            try:
                l_0 = Record.objects.filter(variable=variable).get(time=t_start).value
                l_1 = Record.objects.filter(variable=variable).get(time=t_end).value
                lin_bulk = (l_0 - l_1) / 100 * bulk.tank_size * 1000  # 单位:升(液态)
            except Exception as e:
                print(e)
                l_0 = l_1 = lin_bulk = 0

            rsp.append({
                "bulk_id": bulk.id,
                "bulk_name": bulk.asset.name,
                "tank_size": bulk.tank_size,
                "l1": round(l_0, 2),
                "l2": round(l_1, 2),
                "lin_bulk": round(lin_bulk / 1000 * 650 * (273.15 + apsa.temperature) / 273.15, 2),
                "filling_quantity": round(filling_quantity / 1000 * 650 * (273.15 + apsa.temperature) / 273.15, 2),
                "lin_tot": round((filling_quantity + lin_bulk) / 1000 * 650 * (273.15 + apsa.temperature) / 273.15, 2)
            })

        return JsonResponse(rsp, safe=False)


class MalfunctionModelView(ModelViewSet):
    # 查询集
    queryset = Malfunction.objects.order_by('confirm', 'apsa__asset__site__engineer__region', 'apsa__onsite_series',
                                            't_start', )
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
        reason = querry.getlist('reason[]')
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
        if reason is not None and isinstance(reason, list) and reason != []:
            self.queryset = self.queryset.filter(reason_main__in=reason)

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
                change_date=datetime.now(),
                confirm=1
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
        all = query.get('all')

        if all:
            reason_list = []
            for reason in Reason.objects.all():
                reason_list.append({'id': reason.id, 'cname': reason.cname, 'ename': reason.ename})
            return JsonResponse({'code': 200, 'errmsg': 'OK', 'reason_list': reason_list})

        if not parent:
            try:
                # 查询一级原因
                reason_level_1 = Reason.objects.filter(parent=None)
                # 序列化一级原因
                reason_list = []
                for reason in reason_level_1:
                    reason_list.append({'id': reason.id, 'cname': reason.cname, 'ename': reason.ename})
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
                    sub_list.append({'id': sub_model.id, 'cname': sub_model.cname, 'ename': sub_model.ename})

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
    queryset = MonthlyVariable.objects.order_by('apsa__asset__site__engineer__region', 'apsa', 'variable')
    # 序列化器
    serializer_class = InvoiceVariableSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 条件过滤功能
        query = self.request.query_params
        name = query.get('name')
        usage = query.get('usage')
        region = query.get('region')

        queryset = self.queryset
        if region:
            queryset = queryset.filter(apsa__asset__site__engineer__region=region)
        if name:
            name = name.strip().upper()
            queryset = queryset.filter(
                Q(apsa__asset__rtu_name__contains=name) | Q(apsa__asset__site__name__contains=name)
            )
        if usage:
            queryset = queryset.filter(usage=usage.upper())

        return queryset

    def update(self, request):
        # 获取参数
        variable_id: int = request.data.get('variable')
        apsa_id: int = request.data.get('apsa')
        usage: list[str] = request.data.get('usage')
        order_invoice: int = request.data.get('order_invoice')
        order_monthly: int = request.data.get('order_monthly')

        old_usage = [x.usage for x in MonthlyVariable.objects.filter(variable=variable_id) if x.usage != '']
        if not old_usage:
            MonthlyVariable.objects.filter(variable=variable_id).delete()

        delete_item = [x for x in old_usage if x not in usage]
        update_item = [x for x in old_usage if x in usage]
        create_item = [x for x in usage if x not in old_usage if x != '']

        variable = Variable.objects.get(id=variable_id)
        apsa = Apsa.objects.get(id=apsa_id)

        # 保存数据
        try:
            # 若为usage不选时，删除后必须重新创建一个usage为空的记录
            if not usage:
                MonthlyVariable.objects.filter(variable=variable).delete()
                MonthlyVariable.objects.create(
                    variable=variable,
                    apsa=apsa
                )
            else:
                for usage in delete_item:
                    MonthlyVariable.objects.get(variable=variable_id, usage=usage).delete()

                for usage in update_item:
                    m = MonthlyVariable.objects.get(variable=variable_id, usage=usage)
                    if usage == 'MONTHLY':
                        m.order = order_monthly
                    elif usage == 'INVOICE':
                        m.order = order_invoice
                    m.save()

                for usage in create_item:
                    if not MonthlyVariable.objects.filter(variable=variable, apsa=apsa, usage=usage).count():
                        m = MonthlyVariable.objects.create(variable=variable, apsa=apsa, usage=usage)
                        if usage == 'MONTHLY':
                            m.order = order_monthly
                        elif usage == 'INVOICE':
                            m.order = order_invoice
                        m.save()

        except DatabaseError as e:
            return Response(f'数据库操作异常: {e}', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '修改月报变量成功'})

    def create(self, request, *args, **kwargs):
        try:
            apsa: int = request.data.get('apsa')
            variable: int = request.data.get('variable')
            usage: list[str] = request.data.get('usage')
            order_invoice: int = request.data.get('order_invoice')
            order_monthly: int = request.data.get('order_monthly')
            apsa_obj = Apsa.objects.get(id=apsa)
            variable_obj = Variable.objects.get(id=variable)
        except Exception:
            return Response("参数错误", status=status.HTTP_400_BAD_REQUEST)

        try:
            if usage:
                MonthlyVariable.objects.filter(variable=variable).delete()
                for u in usage:
                    if not MonthlyVariable.objects.filter(variable=variable, usage=u).count():
                        m = MonthlyVariable.objects.create(
                            apsa=apsa_obj,
                            variable=variable_obj,
                            usage=u.upper()
                        )
                        if u == 'MONTHLY':
                            m.order = order_monthly
                        elif u == 'INVOICE':
                            m.order = order_invoice
                        m.save()
            else:
                if not MonthlyVariable.objects.filter(variable=variable).count():
                    m = MonthlyVariable.objects.create(
                        apsa=apsa_obj,
                        variable=variable_obj,
                    )
                    m.save()
        except Exception:
            return Response("内部错误", status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': 'ok'})

    def destroy(self, request, *args, **kwargs):
        pk = kwargs['pk']
        try:
            for x in MonthlyVariable.objects.filter(variable=pk):
                x.delete()
        except Exception as e:
            print(e)
            return Response(f'数据库操作异常: {e}', status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 200, 'msg': '删除权限成功'})

    def list(self, request):
        queryset = self.filter_queryset(self.get_queryset()).values('variable').distinct()
        page = self.paginate_queryset(queryset)

        if page is not None:
            res = self.aggregate(page)
            return self.get_paginated_response(res)

        res = self.aggregate(queryset)
        return Response(res)

    def aggregate(self, querySet):
        res = []
        for v in querySet:
            id = v['variable']
            usage = []
            order_monthly = None
            order_invoice = None
            for q in MonthlyVariable.objects.filter(variable=id):
                usage.append(q.usage)
                if q.usage == 'MONTHLY' and q.order != -1:
                    order_monthly = q.order
                if q.usage == 'INVOICE' and q.order != -1:
                    order_invoice = q.order
            res.append({
                'variable': q.variable_id,
                'apsa': q.apsa_id,
                'rtu_name': q.apsa.asset.rtu_name,
                'variable_name': q.variable.name,
                'usage': usage,
                'order_monthly': order_monthly,
                'order_invoice': order_invoice
            })
        return res


class InvoiceDiffModelView(ModelViewSet):
    # 查询集
    queryset = InvoiceDiff.objects.all()
    # 序列化器
    serializer_class = InvoiceDiffSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def list(self, request):
        query = self.request.query_params
        usage = query.get('usage')
        region = query.get('region')
        name = query.get('name')
        t_start = query.getlist('date[]')[0] + " 00:00:00"
        t_end = query.getlist('date[]')[1] + " 00:00:00"

        queryset = MonthlyVariable.objects.filter(usage=usage)
        if region:
            queryset = queryset.filter(apsa__asset__site__engineer__region=region)
        if name:
            name = name.strip().upper()
            queryset = queryset.filter(
                Q(apsa__asset__rtu_name__contains=name) | Q(apsa__asset__site__name__contains=name)
            )
        queryset = queryset.order_by('apsa__asset__rtu_name', 'order')
        page = self.paginate_queryset(queryset)

        if page is not None:
            rsp = []
            for q in page:
                v = q.variable

                r1 = Record.objects.filter(variable=v, time=t_start)
                if r1.count() == 1:
                    l_start = r1[0].value
                else:
                    l_start = 0

                r2 = Record.objects.filter(variable=v, time=t_end)
                if r2.count() == 1:
                    l_end = r2[0].value
                else:
                    l_end = 0

                # H_PROD不需要计算差值，只要去截至值即可
                if v.daily_mark == 'H_PROD' and usage == 'MONTHLY':
                    diff = l_end
                else:
                    diff = round(l_end-l_start, 2)

                rsp.append({
                    "date": t_end.split(' ')[0],
                    "rtu_name": v.asset.rtu_name,
                    "variable_name": v.name,
                    "variable_id": v.id,
                    "order": MonthlyVariable.objects.get(variable=v, usage=usage).order,
                    "start": round(l_start, 2),
                    "end": round(l_end, 2),
                    "diff": diff
                })
            return self.get_paginated_response(rsp)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class MonthlyMalfunction(ModelViewSet):
    # 查询集
    queryset = Malfunction.objects.all()
    # 序列化器
    serializer_class = InvoiceDiffSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def list(self, request):
        query = self.request.query_params
        region = query.get('region')
        name = query.get('name')
        t_start = query.getlist('date[]')[0] + " 00:00:00" if query.getlist('date[]') else ""
        t_end = query.getlist('date[]')[1] + " 23:59:59" if query.getlist('date[]') else ""

        # 若无时间参数则默认未前一天的一个月周期
        if not t_start or not t_end:
            yesterday = datetime.now() + timedelta(days=-1)
            t_end = yesterday.strftime("%Y-%m-%d") + " 00:00:00"
            t_start = (yesterday + relativedelta(months=-1)).strftime("%Y-%m-%d") + " 00:00:00"

        # 条件过滤
        queryset = Apsa.objects.filter(daily_js__gte=1)
        if region:
            queryset = queryset.filter(asset__site__engineer__region=region)
        if name:
            name = name.strip().upper()
            queryset = queryset.filter(
                Q(asset__rtu_name__contains=name) | Q(asset__site__name__contains=name)
            )
        queryset = queryset.order_by('asset__site__engineer__region', 'asset__rtu_name')

        page = self.paginate_queryset(queryset)

        rsp = []

        if page is not None:
            for apsa in page:
                # 初始化数据变量
                """
                Internal Involuntary Stop LIN Consumption: QII内部被动停机液氮消耗
                Voluntary and Not Budget Stop LIN Consumption: QVNB主动无预算停机液氮消耗
                Normal Maintenance Stop LIN Consumption : QN计划内保养停机液氮消耗
                External Interruptions LIN Consumption:QEI外部原因((客户原因)停机液氮消耗
                
                Internal Involuntary Duration: TII内部被动停机总时间
                Voluntary and Not Budget Duration: TVNB主动无预算停机总时间
                Budget Maintenance Duration: TVB计划内保养停机总时间
                External Interruptions Duration:TEI外部原因((客户原因)总停机时间
                
                Number of Internal Involuntary Interruptions: NII内部被动停机总次数
                Number of Voluntary + Not Budget Interruptions: NVNB主动无预算停机总次数
                Number of Budget Maintenance Interruptions: NVB计划内保养停机总次数
                Number of External Interruptions: NEI外部原因((客户原因)总停机次数
                """
                rsp_data = {
                    'qii': 0,
                    'qvnb': 0,
                    'qn': 0,
                    'qei': 0,
                    'tei': 0,
                    'tii': 0,
                    'tvnb': 0,
                    'tvb': 0,
                    'nei': 0,
                    'nii': 0,
                    'nvnb': 0,
                    'nvb': 0
                }

                # 获取所有停机记录
                records = Malfunction.objects.filter(t_start__range=[t_start, t_end], apsa=apsa)

                # 循环记录，统计需要的数据
                for r in records:
                    # 添加序列化的相应
                    if r.reason_main == 'Internal Involuntary Interruptions':
                        rsp_data['nii'] += 1
                        rsp_data['qii'] += r.stop_consumption
                        rsp_data['tii'] += r.stop_hour

                    elif r.reason_main == 'Voluntary + Not Budget Interruptions':
                        rsp_data['nvnb'] += 1
                        rsp_data['qvnb'] += r.stop_consumption
                        rsp_data['tvnb'] += r.stop_hour

                    elif r.reason_main == 'Budget Maintenance Interruptions':
                        rsp_data['nvb'] += 1
                        rsp_data['qn'] += r.stop_consumption
                        rsp_data['tvb'] += r.stop_hour

                    elif r.reason_main == 'Disuse by Customer' or r.reason_main == 'External Interruptions':
                        rsp_data['nei'] += 1
                        rsp_data['qei'] += r.stop_consumption
                        rsp_data['tei'] += r.stop_hour

                rtu_name = apsa.asset.rtu_name.replace('CN_', '')
                rsp.append({
                    "rtu_name": rtu_name,
                    "date": t_end.split(' ')[0],
                    "apsa": apsa.id,
                    "item": "Internal Involuntary Stop LIN Consumption: QII内部被动停机液氮消耗",
                    "value": round(rsp_data['qii'], 2)
                })
                rsp.append({
                    "rtu_name": rtu_name,
                    "item": "Voluntary and Not Budget Stop LIN Consumption: QVNB主动无预算停机液氮消耗",
                    "value": round(rsp_data['qvnb'], 2)
                })
                rsp.append({
                    "rtu_name": rtu_name,
                    "item": "Normal Maintenance Stop LIN Consumption : QN计划内保养停机液氮消耗",
                    "value": round(rsp_data['qn'], 2)
                })
                rsp.append({
                    "rtu_name": rtu_name,
                    "item": "External Interruptions LIN Consumption:QEI外部原因((客户原因)停机液氮消耗",
                    "value": round(rsp_data['qei'], 2)
                })
                rsp.append({
                    "rtu_name": rtu_name,
                    "item": "External Interruptions Duration:TEI外部原因((客户原因)总停机时间",
                    "value": round(rsp_data['tei'], 2)
                })
                rsp.append({
                    "rtu_name": rtu_name,
                    "item": "Internal Involuntary Duration: TII内部被动停机总时间",
                    "value": round(rsp_data['tii'], 2)
                })
                rsp.append({
                    "rtu_name": rtu_name,
                    "item": "Voluntary and Not Budget Duration: TVNB主动无预算停机总时间",
                    "value": round(rsp_data['tvnb'], 2)
                })
                rsp.append({
                    "rtu_name": rtu_name,
                    "item": "Budget Maintenance Duration: TVB计划内保养停机总时间",
                    "value": round(rsp_data['tvb'], 2)
                })
                rsp.append({
                    "rtu_name": rtu_name,
                    "item": "Number of External Interruptions: NEI外部原因((客户原因)总停机次数",
                    "value": round(rsp_data['nei'], 2)
                })
                rsp.append({
                    "rtu_name": rtu_name,
                    "item": "Number of Internal Involuntary Interruptions: NII内部被动停机总次数",
                    "value": round(rsp_data['nii'], 2)
                })
                rsp.append({
                    "rtu_name": rtu_name,
                    "item": "Number of Voluntary + Not Budget Interruptions: NVNB主动无预算停机总次数",
                    "value": round(rsp_data['nvnb'], 2)
                })
                rsp.append({
                    "rtu_name": rtu_name,
                    "item": "Number of Budget Maintenance Interruptions: NVB计划内保养停机总次数",
                    "value": round(rsp_data['nvb'], 2)
                })
            return self.get_paginated_response(rsp)

        return Response(rsp)


class MalfunctionLock(APIView):
    def post(self, request):
        data = request.data.get('id_list')
        confirm = request.data.get('confirm')
        if not all([data, confirm]):
            return Response(status=400, data="参数错误")

        try:
            for id in data:
                m = Malfunction.objects.get(id=id)
                m.confirm = confirm
                m.save()
        except Exception as e:
            return Response(status=500, data=f"数据库错误:{e}")

        return Response(status=200, data="ok")
