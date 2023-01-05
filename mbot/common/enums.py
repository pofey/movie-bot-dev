from enum import Enum


class StrValueEnum(str, Enum):
    """返回value字符串的枚举类"""

    def __str__(self):
        return str(self.value)


class StrNameEnum(str, Enum):
    """返回name字符串的枚举类"""

    def __str__(self):
        return str(self.name)
