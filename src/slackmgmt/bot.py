import asyncio
import json
import logging
import random
import sys
import textwrap

import aiohttp
import toml

import slackmgmt.config.parser


class SlackBot:

    def __init__(self, token, config):
        self.token = token
        self.config = config
        self.loop = asyncio.get_event_loop()
        if self.debug is True:
            logging.basicConfig(level=logging.DEBUG)

    def __repr__(self):
        return f'<SlackBot token={self.token} config={self.config}>'

    @property
    def log(self):
        return logging.getLogger(__name__)

    async def start(self):
        outbox = asyncio.Queue()
        asyncio.ensure_future(self.consumer(outbox.get), loop=self.loop)
        while True:
            done, pending = await asyncio.wait(
                (self.producer(outbox.put), self.ping()),
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            if hasattr(self, 'ws'):
                del self.ws

    async def api_call(self, method, data=None):
        """Slack API call."""
        async with aiohttp.ClientSession(loop=self.loop) as session:
            form = aiohttp.FormData(data or {})
            form.add_field('token', self.token)
            async with session.post(
                'https://slack.com/api/{0}'.format(method), data=form
            ) as response:
                if response.status == 429:
                    await asyncio.sleep(int(response.headers['Retry-After']))
                    return await self.api_call(method, data)
                if response.status != 200:
                    self.log.debug('Error: %s', response)
                    raise Exception(
                        '{0} with {1} failed.'.format(method, data)
                    )
                return await response.json()

    def pong(self, message):
        self.log.debug(
            'Pong received: {0}'.format(message['reply_to'])
        )
        self.msgid = message['reply_to']

    async def consume(self, message):
        pass

    async def consumer(self, get):
        while True:
            message = await get()
            if message.get('type') == 'pong':
                self.pong(message)
            else:
                await self.consume(message)

    async def producer(self, put):
        rtm = await self.api_call('rtm.start')
        if not rtm['ok']:
            raise ConnectionError('Error connecting to RTM')
        async with aiohttp.ClientSession(loop=self.loop) as session:
            async with session.ws_connect(rtm['url']) as self.ws:
                self.log.debug('Listening to Slack')
                async for msg in self.ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        self.log.debug(msg.data)
                        await put(json.loads(msg.data))
                    else:
                        break

    async def ping(self):
        '''ping websocket'''
        while not hasattr(self, 'ws'):
            await asyncio.sleep(1)
        while True:
            msgid = random.randrange(10000)
            self.log.debug('Sending ping message: {0}'.format(msgid))
            try:
                await self.ws.send_str(
                    json.dumps({'type': 'ping', 'id': msgid})
                )
            except self.client_response_error:
                break
            await asyncio.sleep(20)
            if msgid != self.msgid:
                break

    @classmethod
    def from_config(cls, cfg):
        with open(cfg.config) as cfgfile:
            config = toml.load(cfgfile)
        if cfg.token is not None:
            token = cfg.token
        else:
            token = config['slackmgmt']['token']
        cls.debug = cfg.debug or config['slackmgmt'].get('debug', False)
        return cls(token=token, config=config)
        
    @classmethod
    def from_argv(cls, argv=None):
        parser = slackmgmt.config.parser.get_parser()
        args = parser.parse_args(argv or sys.argv[1:])
        return cls.from_config(cfg=args)
