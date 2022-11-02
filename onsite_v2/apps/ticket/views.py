from django.shortcuts import render
from django.views import View

from utils import JResp


# Create your views here.
class PingView(View):
    def get(self, request):
        return JResp()


class TicketList(View):
    def get(self, request):
        pass