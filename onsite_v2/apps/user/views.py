import json

from django.db import DatabaseError
from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from utils.pagination import PageNum
from .models import User, Role, Permission, RolePermission, UserRole
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

    def destroy(self, request, *args, **kwargs):
        try:
            user = self.get_object()
            user_roles = UserRole.objects.filter(user=user)
            # 删除用户角色
            for x in user_roles:
                x.delete()
            # 删除用户
            user.delete()
        except Exception as e:
            print(e)
            return Response(f'数据库操作异常: {e}', status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 200, 'msg': '删除用户成功'})


class RoleModelView(ModelViewSet):
    # 查询集
    queryset = Role.objects.all()
    # 序列化器
    serializer_class = RoleSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        try:
            role = self.get_object()
            user_roles = UserRole.objects.filter(role=role)
            role_permissions = RolePermission.objects.filter(role=role)
            # 删除用户角色
            for x in user_roles:
                x.delete()
            # 删除角色权限
            for j in role_permissions:
                j.delete()
            # 删除角色
            role.delete()
        except Exception as e:
            print(e)
            return Response(f'数据库操作异常: {e}', status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 200, 'msg': '删除角色成功'})


class PermissionModelView(ModelViewSet):
    # 查询集
    queryset = Permission.objects.all()
    # 序列化器
    serializer_class = PermissionSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        try:
            permission = self.get_object()
            role_permissions = RolePermission.objects.filter(permission=permission)
            # 删除角色权限
            for x in role_permissions:
                x.delete()
            # 删除权限
            permission.delete()
        except Exception as e:
            print(e)
            return Response(f'数据库操作异常: {e}', status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 200, 'msg': '删除权限成功'})


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


class UserAssignRole(APIView):
    def put(self, request):
        user_id = request.data.get('id')
        role_ids = request.data.get('roleIds')
        # 参数不能为空
        if not role_ids:
            return Response('参数错误', status=400)

        # 获取当前用户的角色列表
        user_role_list_old = [x.role_id for x in UserRole.objects.filter(user_id=user_id)]

        # 对比更新后的列表
        create_list = [x for x in role_ids if x not in user_role_list_old]
        delete_list = [x for x in user_role_list_old if x not in role_ids]

        # 创建用户角色
        if create_list:
            for r_id in create_list:
                UserRole.objects.create(role_id=r_id, user_id=user_id)

        # 删除用户角色
        if delete_list:
            for r_id in delete_list:
                UserRole.objects.get(role_id=r_id, user_id=user_id).delete()

        return Response('保存成功', status=200)
