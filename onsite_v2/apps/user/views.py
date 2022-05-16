from django.db import DatabaseError
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from utils.pagination import PageNum
from .models import User, Role, Permission, RolePermission
from .serializer import UserSerializer, RoleSerializer, PermissionSerializer, RolePermissionSerializer


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


class UserView(ModelViewSet):
    # 查询集
    queryset = User.objects.all()
    # 序列化器
    serializer_class = UserSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query_params = self.request.query_params
        engineer = query_params.get('engineer')
        region = query_params.get('region')

        query = self.queryset
        if engineer:
            query = query.filter(~Q(group='occ'))
        if region:
            query = query.filter(region=region)

        return query

    def update(self, request, pk):
        username = request.data.get('username')
        first_name = request.data.get('first_name')
        is_staff = request.data.get('is_staff')
        level = request.data.get('level')
        region = request.data.get('region')
        group = request.data.get('group')
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            user = User.objects.get(id=pk)
            user.username = username
            user.first_name = first_name
            if is_staff is not None:
                user.is_staff = is_staff
            user.level = level
            user.region = region
            user.group = group
            user.email = email
            user.save()
            if password != '' and password:
                user.set_password(password.strip())
        except DatabaseError as e:
            print(e)
            return Response('数据库查询错误', status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 200, 'msg': '保存成功'})


class RoleModelView(ModelViewSet):
    # 查询集
    queryset = Role.objects.all()
    # 序列化器
    serializer_class = RoleSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]


class PermissionModelView(ModelViewSet):
    # 查询集
    queryset = Permission.objects.all()
    # 序列化器
    serializer_class = PermissionSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]


class RolePermissionModelView(ModelViewSet):
    # 查询集
    queryset = RolePermission.objects.all()
    # 序列化器
    serializer_class = RolePermissionSerializer
    # 指定分页器
    pagination_class = PageNum

    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query_params = self.request.query_params
        role = query_params.get('role')

        if role:
            return self.queryset.filter(role=role)

        return self.queryset

    def create(self, request, *args, **kwargs):
        """重写新建功能"""
        role_id = request.data.get('role_id')
        permission_ids = request.data.get('permission_id')

        # 验证参数
        if not (all([role_id, permission_ids])):
            return Response(f'参数不齐全', status=status.HTTP_400_BAD_REQUEST)

        for permission_id in permission_ids:
            # 检查是否存在
            if not RolePermission.objects.filter(role_id=role_id, permission_id=permission_id).count():
                RolePermission.objects.create(
                    role=Role.objects.get(id=role_id),
                    permission=Permission.objects.get(id=permission_id)
                )

        return Response({'status': 200, 'msg': '创建成功'})
