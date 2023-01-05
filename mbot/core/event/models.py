"""
事件的基本模型，提供了系统内置的事件类型枚举描述；以及事件监听器接口定义；
可以通过扩展监听器接口，来订阅系统内事件，完成一些自定义操作
"""

from mbot.common.enums import StrNameEnum
from mbot.common.serializable import Serializable


class EventType(StrNameEnum):
    """官方系统事件列表"""
    """
    订阅一部电影或者剧集
    """
    SubMedia = '订阅影片'
    DeleteSubMedia = '删除订阅影片'
    """
    任何渠道提交的下载，提交下载器成功后
    """
    DownloadStart = '开始下载'
    """
    任何渠道提交的下载，下载完成后
    """
    DownloadCompleted = '下载完成'
    """
    访问网站出现需要人工检查的异常时
    """
    SiteError = '站点异常'
    EmbyPlaybackStart = 'Emby播放开始'
    EmbyPlaybackPause = 'Emby播放暂停'
    EmbyPlaybackUnpause = 'Emby暂停继续'
    EmbyPlaybackStop = 'Emby停止继续'
    EmbyLibraryNew = 'Emby新增入库'


class EventBuilder:
    """事件构造器"""
    """
    事件类型
    """
    event_type: str
    """
    事件产生时所包含的数据
    """
    data: dict

    def set_event_type(self, value):
        self.event_type = str(value)
        return self

    def set_data(self, value):
        self.data = value
        return self

    def build(self):
        return Event(self)


class Event(Serializable):
    """
    事件类型
    """
    event_type: str
    """
    对应事件关联的数据
    """
    data: dict

    def __init__(self, builder: EventBuilder):
        self.event_type = builder.event_type
        self.data = builder.data

    @staticmethod
    def builder():
        return EventBuilder()
