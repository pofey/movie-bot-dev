import logging
import typing
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from mbot.core.event.eventlistener import EventListener
from mbot.core.event.models import EventType, Event
from mbot.core.plugins import PluginContext

"""监听器绑定事件的快捷属性"""
BIND_EVENT_NAME = '__bind_event__'
"""监听器设定监听器顺序的快捷属性"""
ORDER_NAME = '__order__'

_LOGGER = logging.getLogger(__name__)


class EventBus:
    """事件处理总线"""

    def __init__(self, mbot):
        self.mbot = mbot
        self.listeners: Dict[str, list] = dict()
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix='Event')

    def remove_listener(self, event_listener: EventListener):
        for key in self.listeners:
            ll: list = self.listeners[key]
            for l in ll:
                if l['listener'] == event_listener:
                    ll.remove(l)

    def add_listener(self, event_listener: EventListener, show_log=True):
        """
        添加一个监听器，并按order完成排序
        :param event_listener:
        :param order:
        :param show_log:
        :return:
        """
        event_types = event_listener.bind_event
        if isinstance(event_types, EventType):
            event_types = [str(event_types)]
        elif isinstance(event_types, str):
            event_types = [event_types]
        order = event_listener.order
        if order is None:
            order = 100
        for t in event_types:
            t = str(t)
            if t in self.listeners:
                l: list = self.listeners[t]
            else:
                l: list = []
                self.listeners[t] = l
            l.append({
                'listener': event_listener,
                'order': order
            })
            l.sort(key=lambda x: x['order'])
            self.listeners[t] = l
        if show_log:
            _LOGGER.info(
                f'监听器已经添加: {event_listener.func.__module__}.{event_listener.func.__name__} 绑定事件: {",".join([str(t) for t in event_types]) if event_types else ""} 顺序：{order}')

    def publish_event(self, event: Event, run_in_background: bool = False):
        """
        触发一个事件
        :param event:
        :return:
        """
        listeners: typing.List[EventListener] = self.listeners.get(event.event_type)
        if not listeners or len(listeners) == 0:
            return
        for l in listeners:
            listener = l['listener']
            try:
                if listener.plugin:
                    ctx = PluginContext(self.mbot, listener.plugin,
                                        self.mbot.config.plugins_config.get(listener.plugin.name))
                    if run_in_background:
                        self.executor.submit(lambda p: listener(*p), (ctx, event.event_type, event.data))
                    else:
                        listener(ctx, event.event_type, event.data)
                else:
                    if run_in_background:
                        self.executor.submit(listener.func, (event.event_type, event.data))
                    else:
                        listener(event.event_type, event.data)
            except Exception as e:
                _LOGGER.error(f'on_event error: {type(listener).__name__} event: {event.to_json()}', exc_info=True)
