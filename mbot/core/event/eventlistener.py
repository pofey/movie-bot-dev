import logging
import typing

from mbot.core.event.models import EventType

_LOGGER = logging.getLogger(__name__)


class EventListener:
    """事件监听器"""

    def __init__(self, func: typing.Callable,
                 bind_event: typing.Optional[typing.Union[typing.List, str, EventType]] = None,
                 order: typing.Optional[int] = None):
        self.func: typing.Callable = func
        self.bind_event: typing.Optional[typing.Union[typing.List, str, EventType]] = bind_event
        self.order: int = order
        self.plugin = None

    def set_plugin(self, plugin):
        self.plugin = plugin

    def __call__(self, *args, **kwargs):
        try:
            self.func(*args, **kwargs)
        except Exception as e:
            if self.plugin:
                _LOGGER.error(f'插件：{self.plugin.manifest.title}接收事件{self.bind_event}处理失败', exc_info=True)
            _LOGGER.error(f'事件{self.bind_event}处理失败', exc_info=True)
