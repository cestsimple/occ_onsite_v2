from django.db import DatabaseError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from utils.pagination import PageNum
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
        username = request.data.get('username')
        first_name = request.data.get('first_name')
        is_staff = request.data.get('is_staff')
        level = request.data.get('level')
        region = request.data.get('region')
        group = request.data.get('group')
        email = request.data.get('email')

        try:
            user = User.objects.get(id=pk)
            user.username = username
            user.first_name = first_name
            if is_staff:
                user.is_staff = is_staff
            user.level = level
            user.region = region
            user.group = group
            user.email = email
            user.save()
        except DatabaseError as e:
            print(e)
            return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '保存成功'})
