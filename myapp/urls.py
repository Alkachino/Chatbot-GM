from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('get_response/', views.get_bot_response, name='get_response'),
]