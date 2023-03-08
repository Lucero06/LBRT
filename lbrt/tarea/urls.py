from django.urls import path

from . import views

urlpatterns = [
    path('tarea/update_limit', views.TareaView.as_view(), name='tarea'),
    path('tarea/update_price', views.UpdatePrice.as_view(), name='update_price'),
    path('get_orders', views.update_items, name='get_orders'),
]
