import logging

from aiohttp import web


class Handler:

    def __init__(self, put):
        self.put = put

    @property
    def log(self):
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(__name__)
        return self._logger

    async def webhook(self, request):
        data = await request.json()
        self.log.debug(f'data={data}')
        resp = {}
        if 'challenge' in data:
            resp['challenge'] = data['challenge']
        return web.json_response(resp, status=200)


def make_app(put):
    app = web.Application()
    handler = Handler(put)
    app.add_routes([
        web.post('/webhook', handler.webhook),
    ])
    return app
