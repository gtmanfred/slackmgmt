import asyncio

from aiohttp import web

from . import bot
from . import server


def main():
    loop = asyncio.get_event_loop()
    outbox = asyncio.Queue()
    instance = bot.SlackBot.from_argv()
    asyncio.ensure_future(instance.consumer(outbox.get), loop=loop)
    app = server.make_app(outbox.put)
    web.run_app(app)
