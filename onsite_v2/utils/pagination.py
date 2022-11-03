from django.db.models import QuerySet
from rest_framework.pagination import PageNumberPagination

from utils import JResp


class PageNum(PageNumberPagination):
    """
    自定义分页器
    """
    page_size_query_param = 'pagesize'  # 每一页的最大数量
    max_page_size = 50000  # 指定每页最大返回量

    def get_paginated_response(self, data):
        """重写返回方法"""
        return JResp(
            msg="ok",
            status=200,
            data={
                'total': self.page.paginator.count,
                'page': self.page.number,
                'pages': self.page.paginator.num_pages,
                'pagesize': self.max_page_size,
                'list': data,
            }
        )


def paginator(page: int = 1, pagesize: int = 10, query_set: QuerySet = None) -> dict:
    # 总数
    total = query_set.count()
    # set不够分直接返回
    if total == 0:
        return {'total': total, 'list': [], 'page': 1, 'pagesize': 10}
    if total < pagesize:
        return {'total': total, 'list': query_set, 'page': 1, 'pagesize': 10}
    # 分情况返回
    start = (page - 1) * pagesize + 1
    end = page * pagesize
    q = query_set[start, end]
    print(q)
    if end < total:
        return {'total': total, 'list': query_set[start, end], 'page': page, 'pagesize': pagesize}
    elif start <= total < end:
        return {'total': total, 'list': query_set[start, total], 'page': page, 'pagesize': pagesize}
    elif total < start:
        return {'total': total, 'list': query_set[1, pagesize], 'page': 1, 'pagesize': 10}
