import asyncio

from aiohttp import web

from . import bot
from . import server


def main():
    loop = asyncio.get_event_loop()
    instance = bot.SlackBot.from_argv()
    instance.setup_bots()
    if instance.events_api is True:
        loop.create_task(instance.consumer())
        app = server.make_app(instance.queue)
        web.run_app(app)
    else:
        loop.create_task(instance.start())
        loop.run_forever()
