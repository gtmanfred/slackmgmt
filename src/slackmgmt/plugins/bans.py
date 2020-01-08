
class BanPlugin:

    async def check_ban(self, user, channel):
        if user in self.config.get(channel, {}).get('users', []):
            ret = await self.api_call('conversations.kick', {'channel': channel, 'user': user})
            print(ret)

    async def consumer(self):
        while True:
            msg = await self.queue.get()
            if msg.get('type') == 'member_joined_channel':
                await self.check_ban(user=msg['user'], channel=msg['channel'])
