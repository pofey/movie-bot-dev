from abc import ABCMeta, abstractmethod
from enum import Enum


class HealthStatus(Enum):
    """系统健康状态"""
    UP = '可用'
    DOWN = '不可用'
    UNKNOWN = '未知'


class Health:
    """健康状态信息"""

    class Builder:
        status: HealthStatus = None
        details: dict = None

        def __init__(self):
            self.status = HealthStatus.UNKNOWN
            self.details = dict()

        def with_detail(self, name, key):
            self.details[name] = key

        def build(self):
            return Health(self)

    status: HealthStatus = None
    details: dict = None

    def __init__(self, builder: Builder):
        self.status = builder.status
        self.details = builder.details

    @staticmethod
    def up() -> Builder:
        builder = Health.Builder()
        builder.status = HealthStatus.UP
        return builder

    @staticmethod
    def down() -> Builder:
        builder = Health.Builder()
        builder.status = HealthStatus.DOWN
        return builder


class HealthIndicator(metaclass=ABCMeta):
    """健康检测监测点，实现这个类，可以自动进入健康检查页面，并以固定频率调用health方法检查健康状态"""
    indicator_type: str = None
    service_name: str = None

    def __init__(self, indicator_type, service_name):
        self.indicator_type = indicator_type
        self.service_name = service_name

    def get_indicator_type(self):
        return self.indicator_type

    def get_service_name(self):
        return self.service_name

    @abstractmethod
    def health(self) -> Health:
        pass
