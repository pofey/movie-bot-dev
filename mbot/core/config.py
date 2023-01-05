import json
import os.path
import typing
from typing import Any

import yaml

from mbot.exceptions import UnsupportedOperationException, SiteErrorException

"""默认配置的文件名称"""
BASE_CONFIG_FILENAME = 'base_config.yml'
PLUGINS_CONFIG_FILENAME = 'plugins_config.yml'
"""默认的基础配置文件内容"""
DEFAULT_BASE = {
    'server': {},
    'frontend': {},
    'media_server': {},
    'download_client': [],
    'media_path': [],
    'notify_channel': [],
    'web': {'host': '::', 'port': 1329, 'server_url': None},
    'free_download': {'avg_statistics_period': 5, 'enable': False},
    'movie_metadata': {
        'douban': {'cookie': None}
    },
    'file_link': {
        'movie': {
            'filename': '{{name}} ({{year}}){%if version %} - {{version}}{% endif %}',
            'folder': '{{name}} ({{year}})'
        },
        'tv': {
            'filename': '{{name}} S{{season}}E{{ep_start}}{%if ep_end %}-E{{ep_end}}{% endif %}{%if version %} - {{version}}{% endif %}',
            'folder': '{{name}} ({{year}})'
        },
        'recognize': True,
        'exact_year': False,
        'use_unknown_dir': True,
        'file_process_mode': 'link',
        'use_area_folder': False,
        'disc_single_folder': False,
        'fix_emby_bdmv_bug': False,
    },
    'scraper': {
        'generate_nfo': True,
        'use_cn_person_name': False,
        'person_nfo_path': None
    },
    'subtitle': {
        'enable': True,
        'finder_type': ['zimuku'],
        'file_name_template': '{{ name }}.{{ language[0] }}{% if language[0] == "zh-cn" and language | length == 2 %}.default{% endif%}{{ subtitle_ext }}',
        'filter_type': ['srt', 'ass'],
        'filter_language': ['双语', '简体', '繁体'],
        'sync_language': ['zh-cn', 'zh-tw'],
        'subhd_check_code': 329681,
        'exclude_area': ['中国大陆', '中国台湾']
    },
    'smart_download': {},
    'subscribe': {
        'download_process_executor_worker': 1,
        'error_waiting_time': 600,
        'approval_required': False
    }
}


def load_yaml_config(filepath: str):
    """
    加载一个yaml格式的文件
    :param filepath:
    :return:
    """
    if not filepath or not os.path.exists(filepath):
        raise FileNotFoundError(f'找不到配置文件: {filepath}')
    with open(filepath, 'r', encoding='utf-8') as file:
        user_config = yaml.safe_load(file)
    return user_config


def load_json_config(config_path: str):
    with open(config_path) as file:
        config = json.load(file)
    return config


class ConfigValues(dict):
    """封装后的配置文件内容，可以config.xxx 打点调用属性值；同时增加了一些配置文件操作方法"""

    def __init__(self, data: dict, config_filepath=None):
        self._config_filepath = config_filepath
        super().__init__(data)

    def __setattr__(self, key, value):
        if str(key).startswith('_'):
            super().__setattr__(key, value)
            return
        self.update({key: value})

    def __getattr__(self, attr) -> Any:
        result = self.get(attr)
        if result and not isinstance(result, ConfigValues):
            if isinstance(result, dict):
                self.update({attr: ConfigValues(result)})
            else:
                return result
            return self.get(attr)
        else:
            return result

    def exists(self):
        return os.path.exists(self._config_filepath)

    def _to_dict(self, data):
        """
        把包装类型还原成原始的dict来保证json yaml序列化可用
        :param data:
        :return:
        """
        new_data = dict()
        if isinstance(data, ConfigValues):
            for key in data:
                new_data.update({key: data[key]})
        elif isinstance(data, dict):
            for key in data:
                new_data.update({key: self._to_dict(data.get(key))})
        elif isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                new_list = []
                for item in data:
                    new_list.append(self._to_dict(item))
                new_data = new_list
            else:
                return data
        else:
            return data
        return new_data

    def save(self):
        """
        保存配置
        :return:
        """
        if not self._config_filepath:
            return
        path = os.path.dirname(self._config_filepath)
        if not os.path.exists(self._config_filepath) and not os.path.exists(path):
            os.makedirs(path)
        with open(self._config_filepath, "w",
                  encoding="utf-8") as f:
            yaml.dump(self._to_dict(self.copy()), f, default_style=False, encoding='utf-8', allow_unicode=True)


class SiteConfig(ConfigValues):
    def __init__(self, config_filepath: str):
        self._ext_data: typing.Dict[str, typing.Any] = dict()
        self.config_filepath = config_filepath
        try:
            with open(config_filepath, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                user_config = yaml.safe_load(''.join(lines))
                self._parse_ext_data(lines)
        except Exception as e:
            raise SiteErrorException(f'站点适配文件错误，请检查文件是否标准yml文件，没有掺杂无效信息：{config_filepath}')
        super().__init__(user_config)

    @staticmethod
    def _parse_ext_data_var(l):
        arr = l.split(' ')
        idx = arr[1].index('=')
        if idx == -1:
            # err var
            return
        key = arr[1][0:idx]
        value = arr[1][idx + 1:]
        return {key: value}

    @staticmethod
    def _line_is_ext_data(l):
        return l.startswith('#!DATA')

    def _parse_ext_data(self, lines: typing.List[str]):
        if not lines:
            return
        for l in lines:
            l = l.strip()
            if not self._line_is_ext_data(l):
                continue
            var = self._parse_ext_data_var(l)
            if not var:
                continue
            self._ext_data.update(var)

    def ext_data_to_text(self):
        if not self._ext_data and len(self._ext_data.keys()):
            return
        text = ''
        for key in self._ext_data:
            text += f'#!DATA {key}={self._ext_data[key]}\n'
        return text

    def get_ext_data(self, key: str):
        return self._ext_data.get(key)

    def set_ext_data(self, key: str, value: str, update_file=False):
        with open(self.config_filepath, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        update = False
        for i, l in enumerate(lines):
            if not self._line_is_ext_data(l.strip()):
                continue
            var = self._parse_ext_data_var(l.strip())
            if not var or key not in var:
                continue
            lines[i] = f'#!DATA {key}={value}\n'
            update = True
            break
        if update_file:
            if not update:
                lines.insert(0, f'#!DATA {key}={value}\n')
            with open(self.config_filepath, 'w', encoding='utf-8') as file:
                file.writelines(lines)
        self._ext_data.update({key: value})

    def save(self):
        raise UnsupportedOperationException('站点配置文件不支持直接修改')


def merge_dict(a, b):
    """
    合并两个dict，只做一级合并，用于补充配置文件新增的变化
    :param a:
    :param b:
    :return:
    """
    if not b:
        b.update(a)
        return True
    update = False
    for key in a:
        if key not in b:
            b[key] = a[key]
            update = True
    return update


class Config:
    """配置文件管理的一个类"""

    def __init__(self):
        self.work_dir = None
        # 配置文件目录
        self.config_dir = None
        self.user_config_dir = None
        self.site_config_dir = None
        # 插件目录
        self.plugin_dir = None
        # 基础配置文件对象
        self.base: ConfigValues = None
        self.plugins_config: ConfigValues = None
        # 通知模版配置文件对象
        self.notify_templates: typing.Dict[str, ConfigValues] = dict()
        self.sites: typing.Dict[str, SiteConfig] = dict()
        self.rules: typing.Dict[str, dict] = dict()

    @staticmethod
    def get_first_true_item(items: typing.List[typing.Dict], key: str, if_none_than_get_first: bool = True):
        if not items:
            return
        for item in items:
            if bool(item.get(key)):
                return item
        if if_none_than_get_first:
            return items[0]
        return

    def load_config(self, config_dir):
        """
        加载目录内的配置文件
        :param config_dir:
        :return:
        """
        self.config_dir = config_dir
        base_config_filepath = os.path.join(config_dir, BASE_CONFIG_FILENAME)
        base = None
        if os.path.exists(base_config_filepath):
            base = load_yaml_config(base_config_filepath)
        # 记录是否第一次初始化，首次启动应用程序没有配置文件，不要为用户自动生成；以是否有配置文件作为系统是否完成初装的判断
        first_init = False
        if base is None:
            base = {}
            first_init = True
        # 合并配置中缺失的默认项
        merge_base = merge_dict(DEFAULT_BASE, base)
        # 转化成包装的配置操作类
        self.base = ConfigValues(base, base_config_filepath)
        if merge_base and not first_init:
            # 非瘦子初始化产生合并自动保存
            self.base.save()
        notify_tmpl_dir = os.path.join(config_dir, 'notify_template')
        notify_templates: typing.Dict[str, ConfigValues] = dict()
        for f in os.listdir(notify_tmpl_dir):
            fp = os.path.join(notify_tmpl_dir, f)
            if not os.path.exists(fp):
                continue
            notify_tmpl = load_yaml_config(fp)
            notify_templates.update({notify_tmpl.get('channel_type'): ConfigValues(notify_tmpl, fp)})
        self.notify_templates = notify_templates
        self.load_rule_config(os.path.join(config_dir, 'rule'))
        plugins_config_filepath = os.path.join(config_dir, PLUGINS_CONFIG_FILENAME)
        if os.path.exists(plugins_config_filepath):
            plugins_config = load_yaml_config(plugins_config_filepath)
            self.plugins_config = ConfigValues(plugins_config, plugins_config_filepath)
        else:
            self.plugins_config = ConfigValues({}, plugins_config_filepath)
            self.plugins_config.save()

    def load_site_config(self, site_config_dir: str):
        self.site_config_dir = site_config_dir
        for path, dir_list, file_list in os.walk(site_config_dir):
            for file_name in file_list:
                if os.path.splitext(file_name)[1] == '.yml':
                    filepath = os.path.join(site_config_dir, file_name)
                    site_config = SiteConfig(filepath)
                    self.sites.update({site_config.get('id'): site_config})

    def load_rule_config(self, rule_dir: str):
        if not os.path.exists(rule_dir):
            os.makedirs(rule_dir)
        for path, dir_list, file_list in os.walk(rule_dir):
            for file_name in file_list:
                if os.path.splitext(file_name)[1] == '.json':
                    rule_config_path = os.path.join(rule_dir, file_name)
                    config = load_json_config(rule_config_path)
                    self.rules[config.get('rule_name')] = config
