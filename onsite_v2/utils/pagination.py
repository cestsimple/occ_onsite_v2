from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PageNum(PageNumberPagination):
    """
    自定义分页器
    """
    page_size_query_param = 'pagesize'  # 每一页的最大数量
    max_page_size = 50  # 指定每页最大返回量

    def get_paginated_response(self, data):
        """重写返回方法"""
        return Response(
            {
                'total': self.page.paginator.count,
                'page': self.page.number,
                'pages': self.page.paginator.num_pages,
                'pagesize': self.max_page_size,
                'list': data,
            }
        )
