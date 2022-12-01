# -*- coding:utf-8 -*-
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from utils.pagination import PageNum
from .models import Project, NodeContent, Node, Task, TaskHistory
from .serializer import ProjectSerializer, NodeSerializer, NodeContentSerializer, TaskSerializer, TaskHistorySerializer


# Create your views here.
class ProjectView(ModelViewSet):
    # 查询集
    queryset = Project.objects.all()
    # 序列化器
    serializer_class = ProjectSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]


class NodeView(ModelViewSet):
    # 查询集
    queryset = Node.objects.all()
    # 序列化器
    serializer_class = NodeSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]


class NodeContentView(ModelViewSet):
    # 查询集
    queryset = NodeContent.objects.all()
    # 序列化器
    serializer_class = NodeContentSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]


class TaskView(ModelViewSet):
    # 查询集
    queryset = Task.objects.all()
    # 序列化器
    serializer_class = TaskSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]


class TaskHistoryView(ModelViewSet):
    # 查询集
    queryset = TaskHistory.objects.all()
    # 序列化器
    serializer_class = TaskHistorySerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]
