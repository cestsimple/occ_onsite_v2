from django.shortcuts import render
# Create your views here
from rest_framework.response import Response
from rest_framework.views import APIView


class IotSiteData(APIView):
    def get(self, request):
        return Response({'status': 200, 'msg': '请求成功，正在刷新'})