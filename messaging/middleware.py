from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User


@database_sync_to_async
def _user_from_token(token):
    try:
        access = AccessToken(token)
    except TokenError:
        return AnonymousUser()
    user = User.objects.filter(pk=access.get("user_id")).first()
    if user is None or not user.is_active:
        return AnonymousUser()
    return user


class JwtAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        scope["user"] = await _user_from_token(token) if token else AnonymousUser()
        return await self.app(scope, receive, send)
