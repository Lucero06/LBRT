# project/routing.py
from channels.routing import ProtocolTypeRouter, URLRouter
import tarea.routing 
application = ProtocolTypeRouter({    
    # (http->Django views is added by default)    
    'websocket':    
        URLRouter(
            tarea.routing.websocket_urlpatterns
        ),
})