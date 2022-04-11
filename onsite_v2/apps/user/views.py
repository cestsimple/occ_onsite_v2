from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from .models import User


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
