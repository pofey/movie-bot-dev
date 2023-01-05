from typing import List

from mbot.common import apputils
from mbot.constants import APP_VERSION
from mbot.exceptions import PluginNotSupportException


class PluginUtils:
    @staticmethod
    def check_dependencies(dependencies: dict, media_server_types: List[str]):
        if not dependencies:
            return
        for key in dependencies:
            val = dependencies[key]
            if key == 'appVersion':
                condition = val[0:1]
                if condition == '>':
                    if val[1:2] == '=':
                        if not apputils.version_to_number(APP_VERSION) >= apputils.version_to_number(val[2:]):
                            raise PluginNotSupportException(f'应用版本必须大于等于{val[2:]} 当前版本：{APP_VERSION}')
                    else:
                        if not apputils.version_to_number(APP_VERSION) > apputils.version_to_number(val[1:]):
                            raise PluginNotSupportException(f'应用版本必须大于{val[1:]} 当前版本：{APP_VERSION}')
                elif condition == '<':
                    if val[1:2] == '=':
                        if not apputils.version_to_number(APP_VERSION) <= apputils.version_to_number(val[2:]):
                            raise PluginNotSupportException(f'应用版本必须小于等于{val[2:]} 当前版本：{APP_VERSION}')
                    else:
                        if not apputils.version_to_number(APP_VERSION) < apputils.version_to_number(val[1:]):
                            raise PluginNotSupportException(f'应用版本必须小于{val[1:]} 当前版本：{APP_VERSION}')
                elif condition == '=':
                    if val[1:2] == '=':
                        exp = val[2:]
                    else:
                        exp = val[1:]
                    if not apputils.version_to_number(APP_VERSION) == apputils.version_to_number(exp):
                        raise PluginNotSupportException(f'应用版本必须小于等于{val[2:]} 当前版本：{APP_VERSION}')
            elif key == 'mediaServer':
                if str(val).lower() == 'all':
                    continue
                if str(val).lower() not in media_server_types:
                    raise PluginNotSupportException(f'应用配置的媒体服务器必须是{val} 当前为{media_server_types}')
        return
