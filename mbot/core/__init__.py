import collections
import functools
from concurrent.futures import ThreadPoolExecutor

from mbot.core.config import Config
import logging
from typing import OrderedDict
from mbot.core.event.eventbus import EventBus
from mbot.core.event.eventlistener import EventListener
from mbot.core.plugins import PluginMeta

_LOGGER = logging.getLogger(__name__)


class MovieBot:
    """应用超级对象，启动时初始化"""

    def __init__(self, executor=None):
        # 配置文件操作类，包含所有配置信息
        self.config = Config()
        # 事件总线，系统内所有的事件会通过这里控制
        self.event_bus = EventBus(self)
        # 所有已经加载的插件信息
        self.plugins: OrderedDict[str, PluginMeta] = collections.OrderedDict()
        self.task_manager = None
        if executor:
            self.executor = executor
        else:
            self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix='MBotExecutor')

    def set_task_manager(self, task_manager):
        self.task_manager = task_manager

    def on_event(
            self,
            bind_event,
            order: int = 100
    ):
        """
        程序内部用的事件订阅装饰函数，插件不要直接使用这个方法
        :param bind_event:
        :param order:
        :return:
        """
        def decorator(func):
            @functools.wraps(func)
            def wrap(*args, **kwargs):
                return func(*args, **kwargs)

            listener = EventListener(wrap, bind_event, order)
            self.event_bus.add_listener(listener)
            return wrap

        return decorator
