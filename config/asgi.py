import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_asgi = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter

from messaging.middleware import JwtAuthMiddleware
from messaging.routing import websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi,
        "websocket": JwtAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
