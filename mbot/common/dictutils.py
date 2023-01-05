"""字典的封装"""
from typing import Any


def _readonly(*args: Any, **kwargs: Any) -> Any:
    """Raise an exception when a read only dict is modified."""
    raise RuntimeError("Cannot modify ReadOnlyDict")


class ReadOnlyDict(dict):
    """只读字典，不允许修改值"""

    __setitem__ = _readonly
    __delitem__ = _readonly
    pop = _readonly
    popitem = _readonly
    clear = _readonly
    update = _readonly
    setdefault = _readonly


class DictWrapper(dict):
    """对字典类的一个包装，提供一些固定值类型获取的方法，增强部分值获取的兼容性"""

    def get_value(self, key, default_value=None):
        if self.get(key) is None:
            return default_value
        return self.get(key)

    def get_int(self, key, default_value = None):
        if self.get(key) is None:
            return default_value
        try:
            ss = str(self.get(key)).replace(',', '')
            return int(ss)
        except Exception as e:
            return default_value

    def get_float(self, key, default_value: float = None):
        if self.get(key) is None:
            return default_value
        try:
            ss = str(self.get(key)).replace(',', '')
            return float(ss)
        except Exception as e:
            return default_value
