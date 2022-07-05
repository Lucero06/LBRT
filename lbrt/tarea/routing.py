from django.urls import include, re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/$', consumers.TareaConsumer.as_asgi()),
]
