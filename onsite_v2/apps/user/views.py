from django.db import DatabaseError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from .models import User
from .serializer import UserSerializer
from ..iot.models import Apsa


class IndexView(View):
    def get(self, request):
        return render(request, 'index.html')


class AdminCreateView(View):
    def get(self, request):
        if User.objects.filter(username='admin').count() != 0:
            return JsonResponse({'status': 400, 'msg': '账户已存在'})

        try:
            User.objects.create_user(
                username='admin',
                password='admin',
                is_staff=True,
                is_superuser=True,
                level=5,
            )
        except Exception as e:
            return JsonResponse({'status': 400, 'msg': '数据库错误', 'error': e})

        return JsonResponse({'status': 200, 'msg': '创建成功'})


class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')


class UserView(ModelViewSet):
    # 查询集
    queryset = User.objects.all()
    # 序列化器
    serializer_class = UserSerializer
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
        rtu_name = request.data.get('rtu_name')
        engineer = request.data.get('engineer')
        onsite_type = request.data.get('onsite_type')
        onsite_series = request.data.get('onsite_series')
        facility_fin = request.data.get('facility_fin')
        daily_js = request.data.get('daily_js')
        temperature = request.data.get('temperature')
        vap_max = request.data.get('vap_max')
        vap_type = request.data.get('vap_type')
        norminal_flow = request.data.get('norminal_flow')
        daily_bind = request.data.get('daily_bind')
        flow_meter = request.data.get('flow_meter')
        cooling_fixed = request.data.get('cooling_fixed')
        comment = request.data.get('comment')

        try:
            apsa = Apsa.objects.get(id=int(pk))
            apsa.asset.rtu_name = rtu_name
            apsa.asset.site.engineer = engineer['id']
            apsa.onsite_type = onsite_type
            apsa.onsite_series = onsite_series
            apsa.facility_fin = facility_fin
            apsa.daily_js = daily_js
            apsa.temperature = temperature
            apsa.vap_max = vap_max
            apsa.vap_type = vap_type
            apsa.norminal_flow = norminal_flow
            apsa.daily_bind = daily_bind
            apsa.flow_meter = flow_meter
            apsa.cooling_fixed = cooling_fixed
            apsa.comment = comment
            apsa.save()
        except DatabaseError as e:
            print(e)
            return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '保存成功'})
