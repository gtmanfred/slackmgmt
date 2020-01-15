import asyncio
import importlib.abc
import importlib.machinery
import importlib.util
import inspect
import json
import logging
import pathlib
import random
import sys
import typing

import aiohttp
import aiohttp.client_exceptions
import slack
import toml

import slackmgmt.config.parser


class PluginLoader(importlib.abc.SourceLoader):

    def __init__(self, fullname: str, path: typing.Union[bytes, str]):
        """Cache the module name and the path to the file found by the
        finder."""
        self.name = fullname
        self.path = path

    def get_filename(self, fullname: str) -> typing.Union[bytes, str]:
        return self.path

    def get_data(self, path: typing.Union[bytes, str]) -> bytes:
        with open(path, 'rb') as codefile:
            return codefile.read()


class SlackBot:
    bots: typing.ClassVar[typing.List[SlackBot]] = []  # noqa: F821
    debug: typing.ClassVar[bool]
    _channels: typing.ClassVar[typing.List[typing.Dict]]
    queue: asyncio.Queue
    config: typing.Dict
    token: str
    events_api: bool

    def __init__(self, token, config, events_api=False) -> None:
        self.token = token
        self.config = config
        self.queue = asyncio.Queue()
        self.loop = asyncio.get_event_loop()
        self.events_api = events_api
        if self.debug is True:
            logging.basicConfig(level=logging.DEBUG)
        self.log.debug(f'Setup {self.__class__.__name__} Plugin.')

    @property
    def _client(self) -> slack.WebClient:
        if not hasattr(self, '__client'):
            self.__client = slack.WebClient(
                token=self.token,
                run_async=True
            )
        return self.__client

    def setup_bots(self) -> None:
        plugin_config = self.config.get('slackmgmt', {}).get('plugins', {})
        for name, botclass in self.bot_classes:
            plugin = type(name, (botclass, SlackBot), {})
            self.bots.append(plugin(
                self.token,
                plugin_config.get(plugin.__name__, {}),
                events_api=self.events_api,
            ))
            self.loop.create_task(self.bots[-1].consumer())

    def _find_bot_classes(self) -> typing.Set[typing.Tuple[str, typing.Type]]:
        classes: typing.Set[typing.Tuple[str, typing.Type]] = set()
        path = pathlib.Path(__file__).parent / 'plugins'
        loader_details = (
            typing.cast(importlib.abc.Loader, PluginLoader),
            importlib.machinery.SOURCE_SUFFIXES
        )
        finder = importlib.machinery.FileFinder(str(path), loader_details)
        for plugin_file in path.iterdir():
            modname = plugin_file.with_suffix('').name
            spec = typing.cast(importlib.machinery.ModuleSpec, finder.find_spec(modname))
            if not spec.loader:
                continue
            module = importlib.util.module_from_spec(spec)
            typing.cast(importlib.abc.Loader, spec.loader).exec_module(module)
            classes.update(obj for obj in inspect.getmembers(
                module,
                lambda x: inspect.isclass(x) and hasattr(x, 'consumer')
            ))
        return classes

    @property
    def bot_classes(self) -> typing.Set[typing.Tuple[str, typing.Type]]:
        if not hasattr(self, '_bot_classes'):
            self._bot_classes = self._find_bot_classes()
        return self._bot_classes

    async def channels(self, refresh: bool = False) -> typing.List[typing.Dict]:
        if refresh is True or not hasattr(SlackBot, '_channels'):
            SlackBot._channels = await self._client.conversations_list()
        return SlackBot._channels

    def __repr__(self) -> str:
        return f'<SlackBot token={self.token} config={self.config}>'

    @property
    def log(self) -> logging.Logger:
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(__name__)
        return self._logger

    @property
    def queues(self) -> typing.List[asyncio.Queue]:
        return [self.queue] + [b.queue for b in self.bots]

    async def start(self) -> None:
        self.loop.create_task(self.consumer())
        while True:
            done, pending = await asyncio.wait(
                (self.producer(), self.ping()),
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            if hasattr(self, 'ws'):
                del self.ws
            self.loop.stop()

    def pong(self, message) -> None:
        self.log.debug(
            'Pong received: {0}'.format(message['reply_to'])
        )
        self.msgid = message['reply_to']

    async def consumer(self) -> None:
        while True:
            message = await self.queue.get()
            self.log.debug(f'message={message}')
            if message.get('type') == 'pong':
                self.pong(message)
            elif self.events_api:
                continue
            else:
                for b in self.bots:
                    await b.queue.put(message)

    async def producer(self) -> None:
        rtm = await self._client.rtm_start()
        if not rtm['ok']:
            raise ConnectionError('Error connecting to RTM')
        async with aiohttp.ClientSession(loop=self.loop) as session:
            async with session.ws_connect(rtm['url']) as self.ws:
                self.log.debug('Listening to Slack')
                async for msg in self.ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        self.log.debug(msg.data)
                        await self.queue.put(json.loads(msg.data))
                    else:
                        break

    async def ping(self) -> None:
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
            except aiohttp.client_exceptions.ClientResponseError:
                break
            await asyncio.sleep(20)
            if msgid != self.msgid:
                break

    @classmethod
    def from_config(cls, cfg: typing.Dict) -> SlackBot:  # noqa: F821
        with open(cfg['config']) as cfgfile:
            config = toml.load(cfgfile)
        if cfg.get('token', None) is not None:
            token = cfg['token']
        else:
            token = config['slackmgmt']['token']
        cls.debug = cfg.get('debug', False) or config['slackmgmt'].get('debug', False)
        return cls(token=token, config=config, events_api=cfg.get('events_api', False))

    @classmethod
    def from_argv(cls, argv: typing.List = None) -> SlackBot:  # noqa: F821
        parser = slackmgmt.config.parser.get_parser()
        args = parser.parse_args(argv or sys.argv[1:])
        return cls.from_config(cfg=args.__dict__)
