from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render


# Create your views here.
def index(request):
    return render(request, 'index.html')