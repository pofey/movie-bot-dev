import collections
import typing
from collections import OrderedDict
from enum import Enum
import typing as t
from mbot.common.serializable import Serializable
from mbot.exceptions import InvalidParameterException


class ArgType(str, Enum):
    String = '字符串'
    Int = '数字'
    Enum = '枚举'

    @staticmethod
    def get_type(t):
        if t == str:
            return ArgType.String
        elif t == int:
            return ArgType.Int
        elif issubclass(t, Enum):
            return ArgType.Enum
        else:
            return


class ArgSchema(Serializable):
    def __init__(self,
                 arg_type: ArgType,
                 label: str,
                 helper: str,
                 name: typing.Optional[str] = None,
                 enum_values: typing.Optional[typing.Union[typing.Dict[str, str], typing.Callable]] = None,
                 default_value=None,
                 required: typing.Optional[bool] = None,
                 multi_value: bool = True
                 ):
        self.arg_type: ArgType = arg_type
        self.label: str = label
        self.helper: str = helper
        self.name: str = name
        self.enum_values: typing.Optional[typing.Dict[str, str]] = enum_values
        self.default_value = default_value
        if multi_value is not None:
            self.multi_value = multi_value
        else:
            self.multi_value = True
        if required is not None:
            self.required = required
        else:
            self.required = True


def parser_to_args(args: t.Dict[str, t.Any], schema: t.OrderedDict[str, ArgSchema]) -> t.Optional[
    t.OrderedDict[str, t.Any]]:
    if not args:
        if schema:
            raise InvalidParameterException('', "请提供必要的参数")
        return
    if not schema:
        return
    result: t.Optional[t.OrderedDict[str, t.Any]] = collections.OrderedDict()
    for name in schema:
        val = args.get(name)
        s = schema.get(name)
        if not val:
            if s.required:
                raise InvalidParameterException(s.name, f"参数为空:{s.label}")
            val = s.default_value
        else:
            if s.arg_type == ArgType.String:
                val = str(val)
            elif s.arg_type == ArgType.Int:
                val = int(val)
            elif s.arg_type == ArgType.Enum:
                if isinstance(val, str):
                    val = str(val)
                    if val not in [x.get('value') for x in s.enum_values]:
                        raise InvalidParameterException(s.name,
                                                        f"参数{s.label}的值必须为：{[x.get('value') for x in s.enum_values]}")
                elif isinstance(val, list):
                    check_val = [x.get('value') for x in s.enum_values]
                    for v in val:
                        if v not in check_val:
                            raise InvalidParameterException(s.name,
                                                            f"参数{s.label}的值必须为：{[x.get('value') for x in s.enum_values]}")
        result.update({name: val})
    return result
