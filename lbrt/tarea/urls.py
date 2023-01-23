from django.urls import path

from . import views

urlpatterns = [
    path('tarea', views.TareaView.as_view(), name='tarea'),
    path('order', views.update_items, name='order'),
]
