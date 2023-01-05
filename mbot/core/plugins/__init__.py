import collections
import json
from typing import List, Optional, Dict, Callable, Any, OrderedDict, Union

from mbot.common.serializable import Serializable
from mbot.core.context import LocalContext
import functools
import inspect
import logging
from enum import Enum

from mbot.core.context import local_var
from mbot.core.event.eventlistener import EventListener
from mbot.core.params import ArgSchema, ArgType

_LOGGER = logging.getLogger(__name__)
# 创建一个同线程可见的对象实例
plugin: "PluginMeta" = LocalContext('plugin')  # type: ignore[assignment]


class PluginManifest(Serializable):
    """插件描述信息"""
    id: int
    name: str
    # 插件名称，中文名称，简短描述插件
    title: str
    # 作者
    author: str
    # 插件简介
    description: str = None
    # 插件版本
    version: str
    # 插件依赖的python模块
    requirements: List[str] = []
    # 插件配置描述字段
    configField: List = []
    dependencies: Dict[str, str]
    logoUrl: str
    githubUrl: str
    helpDocUrl: str
    _filepath: str

    @staticmethod
    def trans_config_field(config_field):
        if not config_field:
            return
        for field in config_field:
            if field['fieldType'] == 'Enum':
                if field.get('enumValues'):
                    new_vals = []
                    vals = field.get('enumValues')
                    for key in vals:
                        new_vals.append({'name': key, 'value': vals[key]})
                    field['enumValues'] = new_vals

    def __init__(self, json_manifest: Optional[Dict] = None, filepath: Optional[str] = None):
        if 'configField' in json_manifest:
            self.trans_config_field(json_manifest['configField'])
            json_manifest['configField'] = json_manifest['configField']
        self.id = int(json_manifest.get('id')) if json_manifest.get('id') else None
        self.name = json_manifest.get('name')
        self.title = json_manifest.get('title')
        self.author = json_manifest.get('author')
        self.description = json_manifest.get('description')
        self.version = json_manifest.get('version')
        self.requirements = json_manifest.get('requirements')
        self.configField = json_manifest.get('configField')
        self.logoUrl = json_manifest.get('logoUrl')
        self.githubUrl = json_manifest.get('githubUrl')
        self.helpDocUrl = json_manifest.get('helpDocUrl')
        self.dependencies = json_manifest.get('dependencies')
        self._filepath: str = filepath

    def save(self):
        with open(self._filepath, 'w', encoding='utf-8') as f:
            data = self.__dict__.copy()
            del data['_filepath']
            json.dump(data, f, ensure_ascii=False, indent=2)


class PluginTask:
    def __init__(self, task: Callable, name, desc, cron_expression=None, jitter=None, minutes=None, seconds=None,
                 plugin_name=None, run_at_startup=False,
                 run_at_startup_in_thread=False):
        self.task: Callable = task
        self.name = name
        self.desc = desc
        self.cron_expression = cron_expression
        self.jitter = jitter
        self.minutes = minutes
        self.seconds = seconds
        self.plugin_name = plugin_name
        self.run_at_startup = run_at_startup
        self.run_at_startup_in_thread = run_at_startup_in_thread


class PluginCommandResponse:
    def __init__(self, success: bool, message: str):
        self.success = success
        self.message = message


class PluginCommand:
    def __init__(self, func: Callable, name: str, title: str, desc: Optional[str] = None,
                 icon: Optional[str] = None, run_in_background: bool = False):
        sig = inspect.signature(func)
        self._params = sig.parameters
        self.func: Callable = func
        self.name: str = name
        self.title: str = title
        self.desc: Optional[str] = desc
        self.icon: Optional[str] = icon
        self.run_in_background: bool = run_in_background
        self.arg_schema: Optional[OrderedDict[str, ArgSchema]] = self._arg_schema()

    def _arg_schema(self) -> Optional[OrderedDict[str, ArgSchema]]:
        if not self._params:
            return collections.OrderedDict()
        schema: OrderedDict[str, ArgSchema] = collections.OrderedDict()
        for name in self._params:
            val = self._params.get(name)
            anno = val.annotation
            if anno == PluginCommandContext:
                continue
            if isinstance(anno, ArgSchema):
                s = anno
                s.name = name
            elif isinstance(anno, dict) or anno == Dict:
                s = ArgSchema(ArgType.get_type(anno.get('type')), anno.get('label'), anno.get('help'), name)
                if anno.get('default'):
                    s.default_value = anno.get('default')
                anno = anno.get('type')
            elif isinstance(anno, tuple):
                s = ArgSchema(ArgType.get_type(anno[0]), anno[1], anno[2], name)
                anno = anno[0]
            elif anno == str:
                s = ArgSchema(ArgType.String, name, name)
            elif anno == int:
                s = ArgSchema(ArgType.Int, name, name)
            elif issubclass(anno, Enum):
                s = ArgSchema(ArgType.Enum, name, name)
            else:
                s = ArgSchema(ArgType.String, name, name)
            if not s.default_value:
                if val.default is None:
                    s.required = False
                elif val.default is not inspect._empty:
                    s.required = False
                    if issubclass(type(val.default), Enum):
                        s.default_value = val.default.name
                    else:
                        s.default_value = val.default
            schema.update({name: s})
        return schema

    def __call__(self, ctx: "PluginCommandContext", args_data: Optional[Dict] = None) -> PluginCommandResponse:
        if args_data:
            return self.func(ctx, **args_data)
        else:
            return self.func(ctx)


class PluginMeta:

    def __init__(
            self,
            name: str,
            module_name: str,
            manifest: PluginManifest,
            plugin_folder: str
    ):
        self.name: str = name
        self.module_name: str = module_name
        self.manifest: PluginManifest = manifest
        self.plugin_folder: str = plugin_folder
        self._listener = []
        self._command: List[PluginCommand] = []
        self._config_changed = None
        self._after_setup = None
        self._tasks: List[PluginTask] = []

    def get_listener(self):
        return self._listener

    def get_command(self) -> List[PluginCommand]:
        return self._command

    def get_task(self):
        return self._tasks

    def command(self, name: str, title: str, desc: Optional[str] = None,
                icon: Optional[str] = None, run_in_background: bool = False):
        def decorator(func: Callable):
            action = PluginCommand(func, name, title, desc, icon, run_in_background)
            self._command.append(action)
            _LOGGER.info(f'插件{self.manifest.title}新增功能指令：{title}')
            return action

        return decorator

    def task(self,
             name,
             desc,
             cron_expression=None,
             jitter=None,
             minutes=None,
             seconds=None,
             run_at_startup=False,
             run_at_startup_in_thread=False
             ):
        """

        """

        def decorator(func: Callable):
            @functools.wraps(func)
            def wrap(*args, **kwargs):
                return func(*args, **kwargs)

            self._tasks.append(
                PluginTask(wrap, name, desc, cron_expression, jitter, minutes, seconds, None, run_at_startup,
                           run_at_startup_in_thread))

        return decorator

    def config_changed(self, func: Callable):
        self._config_changed = func
        return func

    def after_setup(self, func: Callable):
        self._after_setup = func
        return func

    def on_event(self, bind_event: Union[List, str], order: int = 100):
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrap(*args, **kwargs):
                return func(*args, **kwargs)

            listener = EventListener(wrap, bind_event, order)
            if hasattr(local_var, 'plugin'):
                listener.set_plugin(local_var.plugin)
            self._listener.append(listener)
            return wrap

        return decorator


class PluginCommandContext:
    def __init__(self, uid: int):
        self.uid: int = uid


class PluginContext:
    """插件上下文信息，包含一些实现插件执行前后一些关键对象"""

    def __init__(self, mbot, plugin: PluginMeta, config: dict = None):
        self.mbot = mbot
        self.plugin: PluginMeta = plugin
        if config:
            self.config = config
        else:
            self.config: dict = dict()
