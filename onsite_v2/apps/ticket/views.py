# -*- coding:utf-8 -*-
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from utils import JResp
from utils.pagination import PageNum
from .models import Project, NodeContent, Node, Task, TaskHistory
from .serializer import ProjectSerializer, NodeSerializer, NodeContentSerializer, TaskSerializer, TaskHistorySerializer


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
    queryset = Task.objects.order_by('-created_at')
    # 序列化器
    serializer_class = TaskSerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params
        user = query.get('user', '')
        status = query.get('status', '0')
        if user:
            self.queryset = self.queryset.filter(create_user=user)
        if status == '1' or status == '9':
            self.queryset = self.queryset.filter(status=status)
        return self.queryset


class TaskHistoryView(ModelViewSet):
    # 查询集
    queryset = TaskHistory.objects.all()
    # 序列化器
    serializer_class = TaskHistorySerializer
    # 指定分页器
    pagination_class = PageNum
    # 权限
    permission_classes = [IsAuthenticated]


# =========================== 自定义api接口 ==========================
def get_my_todo_tasks(request):
    # 获取查询参数
    user = request.GET.get('user', '')
    if not user:
        return JResp('参数错误', 400)

    # 查询
    tasks = Task.objects.filter(next_charge=user, status=1)

    # 返回响应
    rsp = {}
    rsp['list'] = TaskSerializer(tasks, many=True).data
    rsp['total'] = tasks.count()
    return JResp('TodoTaskList查询成功', 200, rsp)
