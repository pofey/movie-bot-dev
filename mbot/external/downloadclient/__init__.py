import logging
import typing as t

from requests import RequestException
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed, Retrying

from mbot.exceptions import DownloadClientErrorException
from mbot.external.downloadclient.models import DownloadClient, QbittorrentClient, TransmissionClient, Aria2

_LOGGER = logging.getLogger(__name__)


@retry(retry=retry_if_exception_type(RequestException), stop=stop_after_attempt(3), wait=wait_fixed(5))
def build_client(client_config) -> DownloadClient:
    client = None
    client_type = client_config.get('type')
    if client_type == 'qbittorrent':
        client = QbittorrentClient(
            url=client_config.get('url'),
            need_login=client_config.get('need_login'),
            username=client_config.get('username'),
            password=client_config.get('password'),
        )
    elif client_type == 'transmission':
        client = TransmissionClient(
            host=client_config.get('host'),
            port=client_config.get('port'),
            username=client_config.get('username'),
            password=client_config.get('password')
        )
    elif client_type == 'aria2':
        client = Aria2(
            host=client_config.get('host'),
            port=client_config.get('port'),
            secret=client_config.get('secret')
        )
        client.transfer_info()
    return client


def download_client_wrapper(func):
    def wrapper(*args, **kwargs):
        count = 0
        for attempt in Retrying(retry=retry_if_exception_type(RequestException), stop=stop_after_attempt(3),
                                wait=wait_fixed(10), reraise=True):
            if count > 1:
                _LOGGER.error(f'访问DownloadClient.{func.__name__}异常，正在重试...')
            with attempt:
                val = func(*args, **kwargs)
            count += 1
        return val

    return wrapper


class DownloadClientProxy:
    def __init__(self, client: DownloadClient, client_config: dict):
        self.client: DownloadClient = client
        self.client_config = client_config

    def get_client_name(self):
        return self.client_config.get('name')

    def __getattr__(self, attr):
        if not self.client:
            _LOGGER.info(f'检测到需要访问外部下载器{self.client_config.get("name")}({self.client_config.get("type")})，开始初始化下载器配置')
            self.client = build_client(self.client_config)
        func = object.__getattribute__(self.client, attr)
        return download_client_wrapper(func)


class DownloadClientManager:

    def __init__(self):
        self.client_configs: dict = dict()
        self.clients: dict = dict()
        self.proxy: dict = dict()
        self.client_name_list: list = []

    def init(self, client_configs: t.Union[t.List, t.Dict], lazy_connect=True):
        if isinstance(client_configs, dict):
            client_configs = [client_configs]
        for x in client_configs:
            self.client_name_list.append(x.get('name'))
            self.client_configs.update({x.get('name'): x})
        if not lazy_connect:
            for x in client_configs:
                client = build_client(x)
                self.clients.update({x.get('name'): client})

    def filter_client(self, monitor_all_torrents=None, site_id=None) -> t.Union[
        DownloadClientProxy, DownloadClient, t.List[t.Union[DownloadClientProxy, DownloadClient]]]:
        if monitor_all_torrents is not None:
            result = []
            for name in self.client_configs:
                config = self.client_configs.get(name)
                if monitor_all_torrents is not None:
                    if monitor_all_torrents and not config.get('monitor_all_torrents'):
                        continue
                result.append(self.get(name))
            return result
        elif site_id is not None:
            # 找到匹配的下载器
            client_list = list(filter(lambda x: x.get('site_id') and site_id in x.get('site_id'),
                                      self.client_configs.values()))
            if client_list:
                # 指定站点配置最少的下载器优先
                client_list.sort(key=lambda x: len(x.get('site_id')) if x.get('site_id') else 0)
                client_name = client_list[0].get('name')
            else:
                # 匹配不到就用默认下载器
                client_name = DownloadClientInstance.default_client_name()
            return self.get(client_name)
        else:
            return self.default()

    def default_client_name(self) -> str:
        fd = list(filter(lambda x: self.client_configs.get(x).get('is_default'), self.client_configs))
        if not fd or len(fd) == 0:
            raise DownloadClientErrorException(f'你没有指定默认使用的下载器，请到应用设置中检查你的下载器设置')
        return fd[0]

    def default(self) -> t.Union[DownloadClientProxy, DownloadClient]:
        return self.get(self.default_client_name())

    def get(self, client_name: str) -> t.Union[DownloadClientProxy, DownloadClient]:
        if client_name in self.proxy:
            return self.proxy.get(client_name)
        config = self.client_configs.get(client_name)
        if not config:
            raise DownloadClientErrorException(f'找不到下载器：{client_name} 请到应用设置中检查你的下载器设置：')
        client = self.clients.get(client_name)
        p = DownloadClientProxy(client, config)
        self.proxy.update({client_name: p})
        return p

    def __contains__(self, x):  # 判断一个定点是否包含在里面
        return x in self.client_configs

    def __len__(self):
        return len(self.client_configs)

    def __call__(self, client_name) -> t.Union[DownloadClientProxy, DownloadClient]:
        return self.get(client_name)

    def __getitem__(self, key) -> t.Union[DownloadClientProxy, DownloadClient]:
        if isinstance(key, str):
            return self.__call__(key)
        else:
            return self.get(self.client_name_list[key])


DownloadClientInstance: DownloadClientManager = DownloadClientManager()
