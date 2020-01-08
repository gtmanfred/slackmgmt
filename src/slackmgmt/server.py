from aiohttp import web


class Handler:

    def __init__(self, put):
        self.put = put

    async def webhook(self, request):
        data = await request.json()
        return web.json_response({'challenge': data['challenge']}, status=200)


def make_app(put):
    app = web.Application()
    handler = Handler(put)
    app.add_routes([
        web.post('/webhook', handler.webhook),
    ])
    return app
