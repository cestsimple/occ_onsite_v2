import threading

from django.db import DatabaseError
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.http import JsonResponse
from django.views import View
from rest_framework.permissions import IsAdminUser

from utils import jobs
from utils.pagination import PageNum


class FillingCalculate(View):
    def get(self, request):
        # 检查Job状态
        if jobs.check('ONSITE_FILLING'):
            return JsonResponse({'status': 400, 'msg': '任务正在进行中，请稍后刷新'})

        # 创建子线程
        threading.Thread(target=self.calculate_main).start()

        # 返回相应结果
        return JsonResponse({'status': 200, 'msg': '请求成功，正在刷新中'})

    def calculate_main(self):
        # 更新Job状态
        jobs.update('ONSITE_FILLING', 'OK')


class FillingView(ModelViewSet):
    # 查询集
    # queryset = Filling.objects.all()
    # # 序列化器
    # serializer_class = UserSerializer
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
            user = User.objects.get(id=pk)
            user.save()
        except DatabaseError as e:
            print(e)
            return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '保存成功'})
