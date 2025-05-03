from django.http import HttpResponse, JsonResponse
from .models import Proyect, Task
from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request,'index.html')

def hello(request):
    return HttpResponse("<h1>Hello, world!</h1>")

def about(request):
    return HttpResponse("<h2>About</h2>")
