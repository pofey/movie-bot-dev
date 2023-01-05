from typing import List, Dict

from mbot.common.serializable import Serializable
from mbot.core.params import ArgSchema


class ChannelDefinition(Serializable):
    """推送通道的描述信息"""

    def __init__(self, name: str, channel_type: str, icon_url: str, args: List[ArgSchema], cls):
        self.name = name
        self.channel_type = channel_type
        self.args = args
        self.icon_url = icon_url
        self.cls = cls


# 所有通过装饰器定义的推送通道管理
channel_definition_manager: Dict[str, ChannelDefinition] = dict()


def channel(name: str, channel_type: str, icon_url: str, args: List[ArgSchema]):
    """
    描述一个推送通道
    :param name: 通道名称
    :param channel_type: 通道类型，一个英文的唯一的字符串
    :param icon_url: 推送通道在前端页面展示的icon地址 examples: /static/icon/bark.png
    :param args: 推送通道配置参数
    :return:
    """
    def decorator(cls):
        channel_definition_manager.update({channel_type: ChannelDefinition(name, channel_type, icon_url, args, cls)})
        return cls

    return decorator
