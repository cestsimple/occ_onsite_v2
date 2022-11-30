# -*- coding:utf-8 -*-
from django.db import models


class Project(models.Model):
    """项目表"""
    id = models.AutoField(primary_key=True, verbose_name='项目id')
    name = models.CharField(max_length=100, verbose_name='项目名称')
    desc = models.CharField(max_length=500, default='', verbose_name='项目说明')
    status = models.IntegerField(default=1, verbose_name='状态(1启用9停用)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = "ticket_project"
        ordering = ['id', 'name']
        indexes = [
            models.Index(fields=['id'], name='ticket_project_id_idx'),
            models.Index(fields=['name'], name='ticket_project_name_idx')
        ]


class Node(models.Model):
    """项目节点表"""
    id = models.AutoField(primary_key=True, verbose_name='节点id')
    project_id = models.IntegerField(verbose_name='项目id')
    name = models.CharField(max_length=100, verbose_name='节点名称')
    desc = models.CharField(max_length=500, verbose_name='节点说明')
    order = models.IntegerField(verbose_name='节点顺序')
    roles = models.CharField(max_length=200, default='', verbose_name='节点负责角色列表')
    users = models.CharField(max_length=100, default='', verbose_name='节点负责用户id列表')
    type = models.CharField(max_length=50, default='过程节点', verbose_name='节点类型')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = "ticket_project_node"
        ordering = ['id', 'order']
        indexes = [
            models.Index(fields=['id'], name='project_node_id_idx'),
        ]


class NodeContent(models.Model):
    """节点内容"""
    id = models.AutoField(primary_key=True, verbose_name='节点内容id')
    node_id = models.IntegerField(verbose_name='节点id')
    label = models.CharField(max_length=100, verbose_name='问题标题')
    type = models.CharField(max_length=20, default='input', verbose_name='内容类型')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = "ticket_project_node_content"
        ordering = ['id']
        indexes = [
            models.Index(fields=['id'], name='node_content_id_idx'),
        ]


class Task(models.Model):
    """任务表"""
    id = models.AutoField(primary_key=True, verbose_name='任务内容id')
    project_id = models.IntegerField(verbose_name='项目id')
    project_name = models.CharField(default='', max_length=100, verbose_name='项目名称')
    name = models.CharField(max_length=100, verbose_name='任务名称')
    current_node_name = models.CharField(max_length=100, default='', verbose_name='当前节点名称')
    next_node_name = models.CharField(max_length=100, default='', verbose_name='下一个节点名称')
    next_charge = models.CharField(max_length=100, verbose_name='下一步负责人')
    status = models.IntegerField(default=1, verbose_name='状态(1进行中9结束)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = "ticket_task"
        ordering = ['id']
        indexes = [
            models.Index(fields=['id'], name='task_id_idx'),
        ]


class TaskHistory(models.Model):
    """任务历史记录表"""
    id = models.AutoField(primary_key=True, verbose_name='任务历史id')
    task_id = models.IntegerField(verbose_name='任务id')
    node_id = models.IntegerField(verbose_name='节点id')
    json = models.CharField(default='', max_length=1000, verbose_name='回答内容json')
    update_user = models.CharField(default='', max_length=100, verbose_name='最后修改人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
