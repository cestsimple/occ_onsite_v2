from apps.iot.models import AsyncJob
from datetime import datetime


def check(name, silent: bool = False):
    """检查job是否存在，存在返回1，不存在返回0并创建"""
    job = AsyncJob.objects.filter(name=name).order_by('-start_time')
    if job:
        job = job[0]
        if job.finish_time is None:
            return 1

    # 添加Job状态
    if not silent:
        job = AsyncJob.objects.create(
            name=name,
            start_time=datetime.now(),
        )
    return 0


def update(name, result):
    job = AsyncJob.objects.filter(name=name).order_by('-start_time')[0]
    job.finish_time = datetime.now()
    job.result = result
    job.save()
