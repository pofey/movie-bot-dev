"""
系统插件的加载器核心实现，所有的系统内置插件、外部自定义插件，均有此加载为可执行的实例
系统内提供了多种插件扩展点，当前支持的有：事件监听、定时任务，持续扩充中
"""
import datetime
import importlib
import json
import logging
import os.path
import shutil
import sys
from typing import List

import httpx

from mbot.common.extractutils import ExtractUtils
from mbot.common.osutils import OSUtils
from mbot.core import MovieBot
from mbot.core.context import local_var
from mbot.core.plugins import PluginManifest, PluginMeta
from mbot.exceptions import MovieBotException, PluginsErrorException

MANIFEST_FILENAME = 'manifest.json'
SKIP_FOLDER = ['__pycache__']


class ManifestErrorException(MovieBotException):
    """插件描述信息错误"""
    pass


_LOGGER = logging.getLogger(__name__)


class PluginLoader:
    """插件加载器"""

    def __init__(self, plugin_folder, namespace, mbot: MovieBot):
        """
        初始化事件加载器
        :param plugin_folder: 插件所在目录
        :param namespace: 插件目录在系统内的模块包路径
        :param mbot: 应用超级对象
        """
        if not plugin_folder:
            return
        self.plugin_folder = plugin_folder
        self.namespace = namespace
        self.mbot = mbot

    @staticmethod
    def get_manifest(plugin_path) -> PluginManifest:
        """
        获取插件描述信息
        :param plugin_path: 插件文件夹
        :return:
        """
        plugin_meta_filepath = os.path.join(plugin_path, MANIFEST_FILENAME)
        if not os.path.exists(plugin_meta_filepath):
            return
        with open(plugin_meta_filepath, 'r', encoding='utf-8') as file:
            meta = json.load(file)
        return PluginManifest(meta, plugin_meta_filepath)

    def load(self) -> List[PluginMeta]:
        """
        加载目录下所有插件
        :return:
        """
        if not os.path.exists(self.plugin_folder):
            _LOGGER.error(f'插件目录不存在：{self.plugin_folder}')
            return
        plugins: List[PluginMeta] = []
        for p in os.listdir(self.plugin_folder):
            plugin_path = os.path.join(self.plugin_folder, p)
            if os.path.isfile(plugin_path) or p in SKIP_FOLDER:
                continue
            plugin = self.setup(plugin_path)
            if not plugin:
                continue
            plugins.append(plugin)
        return plugins

    def import_mod(self, name):
        """
        导入模块
        :param name:
        :return:
        """
        if not name:
            return
        try:
            if name in sys.modules:
                return importlib.reload(sys.modules[name])
            else:
                return importlib.import_module(name)
        except Exception as e:
            _LOGGER.error(f'加载类失败：{name}', exc_info=True)
            return

    def import_modules(self, pkg_path: str, mods: list):
        if not mods or len(mods) == 0:
            return
        for name in mods:
            if name.endswith('.py'):
                name = name[0:len(name) - 3]
            mod_path = f'{pkg_path}.{name}'
            self.import_mod(mod_path)

    def setup(self, plugin_path) -> PluginMeta:
        """
        初始化插件
        :param plugin_path: 插件所在目录
        :return:
        """
        try:
            manifest = self.get_manifest(plugin_path)
            if not manifest:
                _LOGGER.error(f'加载插件时没有发现插件描述文件: {plugin_path}/manifest.json')
                return
            local_var.plugin_manifest = manifest
            mod_name = os.path.split(plugin_path)[-1]
            full_mod_name = f'{self.namespace}.{mod_name}'
            plugin = PluginMeta(manifest.name, full_mod_name, manifest, plugin_path)
            """
            为同线程设置插件的描述文件信息和插件元信息实例
            保证在插件代码加载时，可以通过plugin变量操作属于自己的插件数据
            """
            local_var.plugin = plugin
            self.import_mod(full_mod_name)
            self.mbot.plugins.update({manifest.name: plugin})
            """
            经过插件加载后，同线程可见的插件元数据对象内，应该加载了很多扩展点，注册到主程序
            """
            if plugin.get_listener():
                for x in plugin.get_listener():
                    # 注册插件定义的事件监听器
                    self.mbot.event_bus.add_listener(x)
            if plugin.get_task():
                for x in plugin.get_task():
                    # 注册插件定义的定时任务
                    self.mbot.task_manager.add_task(x.task, x.name, x.desc, x.cron_expression, x.jitter, x.minutes,
                                                    x.seconds, x.run_at_startup, x.run_at_startup_in_thread,
                                                    manifest.name)
            if plugin._after_setup:
                # 触发插件中标记的after_setup函数
                plugin._after_setup(plugin, self.mbot.config.plugins_config.get(manifest.name) or {})
            return plugin
        except Exception as e:
            _LOGGER.error(f'插件加载失败（请尝试删除重新安装）：{plugin_path}', exc_info=True)

    def _download_file(self, url):
        r = httpx.get(url)
        if not r:
            raise RuntimeWarning(f'download error: {url}')
        filename = os.path.basename(url)
        filepath = os.path.join(self.plugin_folder, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        with open(filepath, "wb") as f:
            f.write(r.content)
            f.flush()
        return filepath

    def install(self, download_url) -> str:
        _LOGGER.info(f'开始下载插件：{download_url}')
        filepath = self._download_file(download_url)
        return self.install_by_filepath(filepath)

    def install_by_filepath(self, filepath: str):
        ex_path = os.path.join(self.plugin_folder, str(round(datetime.datetime.now().timestamp())))
        ExtractUtils.extract_file(filepath, ex_path)
        plugin_path = OSUtils.find_file(ex_path, MANIFEST_FILENAME)
        parent_path = os.path.split(plugin_path)[0]
        dst = os.path.join(self.plugin_folder, os.path.split(parent_path)[-1])
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.move(parent_path, dst)
        shutil.rmtree(ex_path)
        os.remove(filepath)
        _LOGGER.info(f'插件下载完毕，已经解压到：{dst}')
        return dst

    def uninstall(self, plugin_name, delete_config=True):
        if plugin_name not in self.mbot.plugins:
            raise PluginsErrorException('已经没有这个插件，如果卸载未生效请重新启用应用')
        plugin: PluginMeta = self.mbot.plugins.get(plugin_name)
        _LOGGER.info(f'开始卸载插件：{plugin.manifest.title}')
        shutil.rmtree(plugin.plugin_folder)
        if plugin.get_listener():
            for x in plugin.get_listener():
                self.mbot.event_bus.remove_listener(x)
            _LOGGER.info(f'插件相关监听器已经移除')
        tasks = self.mbot.task_manager.get_tasks()
        plugin_tasks = []
        if tasks:
            for t in tasks:
                if not t.plugin_name:
                    continue
                if t.plugin_name == plugin:
                    plugin_tasks.append(t)
        if plugin_tasks:
            for t in plugin_tasks:
                self.mbot.task_manager.remove_task(t)
            _LOGGER.info(f'插件相关任务已经移除')
        if delete_config and plugin_name in self.mbot.config.plugins_config:
            del self.mbot.config.plugins_config[plugin_name]
            self.mbot.config.plugins_config.save()
            _LOGGER.info(f'插件相关的配置已经删除')
        del self.mbot.plugins[plugin_name]
        _LOGGER.info(f'插件{plugin.manifest.title}卸载完毕')
