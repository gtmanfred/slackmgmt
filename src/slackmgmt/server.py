import asyncio
import logging

from aiohttp import web


class Handler:

    def __init__(self, queue: asyncio.Queue):
        self.put = queue.put

    @property
    def log(self) -> logging.Logger:
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(__name__)
        return self._logger

    async def webhook(self, request: web.Request) -> web.Response:
        data = await request.json()
        self.log.debug(f'data={data}')
        resp = {}
        if 'challenge' in data:
            resp['challenge'] = data['challenge']
        await self.put(data['event'])
        return web.json_response(resp, status=200)


def make_app(queue: asyncio.Queue) -> web.Application:
    app = web.Application()
    handler = Handler(queue)
    app.add_routes([
        web.post('/webhook', handler.webhook),
    ])
    return app
