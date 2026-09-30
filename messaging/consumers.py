from channels.generic.websocket import AsyncJsonWebsocketConsumer


class MessageConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close()
            return
        self.group_name = f"user-{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def conversation_event(self, event):
        await self.send_json(event["payload"])

    async def notification_event(self, event):
        await self.send_json(event["payload"])
