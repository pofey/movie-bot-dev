import logging
import typing
import typing as t

from cacheout import Cache
from requests import RequestException
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed, Retrying

from mbot.common.osutils import OSUtils
from mbot.exceptions import SettingErrorException
from mbot.external.mediaserver.embymediaserver import EmbyMediaServer
from mbot.external.mediaserver.jellyfinmediaserver import JellyfinMediaServer
from mbot.external.mediaserver.models import MediaServer
from mbot.external.mediaserver.plexmediaserver import PlexMediaServer

_LOGGER = logging.getLogger(__name__)


@retry(retry=retry_if_exception_type(RequestException), stop=stop_after_attempt(3), wait=wait_fixed(5))
def build_server(server_type, server_config):
    if not server_type or not server_config:
        msg = '没有设置媒体服务器，请尽快完成媒体服务器配置'
        _LOGGER.error(msg)
        raise SettingErrorException(msg)
    server = None
    if server_type == 'emby':
        server = EmbyMediaServer(**server_config)
    elif server_type == 'plex':
        server = PlexMediaServer(**server_config)
    elif server_type == 'jellyfin':
        server = JellyfinMediaServer(**server_config)
    return server


def media_server_wrapper(func):
    def wrapper(*args, **kwargs):
        count = 0
        for attempt in Retrying(retry=retry_if_exception_type(RequestException), stop=stop_after_attempt(3),
                                wait=wait_fixed(5), reraise=True):
            if count > 1:
                _LOGGER.error(f'访问媒体服务器异常，正在重试...')
            with attempt:
                val = func(*args, **kwargs)
            count += 1
        return val

    return wrapper


class MediaServerProxy:
    def __init__(self):
        self.server_type = None
        self.server_config = None
        self.media_server = None
        self._refresh_media_item_cache = Cache(maxsize=50, ttl=3600, default=None)

    def init(self, server_type, server_config, lazy_connect=True):
        self.server_type = str(server_type).lower()
        self.server_config = server_config
        if not lazy_connect:
            self.media_server = build_server(self.server_type, self.server_config)

    def refresh_media_server(self, tmdb_id, content_path: str, media_type, metadata=False):
        if not tmdb_id:
            return
        if not content_path:
            return
        media_type = str(media_type).lower()
        item_id = None
        # 刷新媒体库的搜索缓存。刷新媒体库接受缓存过期查找带来的开销，以此来降低搜索媒体库的频率
        result_cache = self._refresh_media_item_cache.get(tmdb_id)
        result = []
        if result_cache:
            for item in result_cache:
                # 查验是否还真的存在
                media = self.get_item(item.id)
                if media:
                    result.append(item)
        if not result:
            result = self.search_by_id(tmdb_id)
        if result:
            self._refresh_media_item_cache.set(tmdb_id, result)
        if not result or media_type == 'movie':
            save_path_split = OSUtils.split_path(content_path)
            media_folders = self.library_media_folders()
            if media_folders is None or len(media_folders) == 0:
                _LOGGER.info('影音库没找到媒体文件夹需要刷新。')
                return
            max_match = 0
            for f in media_folders:
                sub_max_match = 0
                sub_item_id = None
                for j in f.sub_folders:
                    media_path_split = OSUtils.split_path(j.path)
                    match_cnt = 0
                    if media_path_split[-1] in [save_path_split[-1],
                                                save_path_split[-2] if len(save_path_split) > 2 else None]:
                        match_cnt += 1
                    if len(save_path_split) >= 2:
                        if save_path_split[-2] == media_path_split[-2]:
                            match_cnt += 1
                    if match_cnt == 0:
                        continue
                    if match_cnt > sub_max_match:
                        sub_max_match = match_cnt
                        sub_item_id = f.id
                if sub_max_match == 0:
                    continue
                if sub_max_match > max_match:
                    max_match = sub_max_match
                    item_id = sub_item_id
            if item_id is None:
                _LOGGER.error(f'TMDB ID: {tmdb_id}没有找到在影音库的对应媒体库，路径: {content_path}')
                return
            self.refresh_item(item_id, metadata=metadata)
            logging.info(f'通知媒体库刷新完成，tmdb_id: {tmdb_id} save_path: {content_path} item_id: {item_id}')
        else:
            for item in result:
                self.refresh_item(item.id, metadata=metadata)
                logging.info(f'通知媒体库刷新完成，tmdb_id: {tmdb_id} save_path: {content_path} item_id: {item.id}')

    def __getattr__(self, attr):
        if not self.media_server:
            _LOGGER.info(f'检测到需要访问外部媒体服务{self.server_type}，开始初始化媒体服务器连接')
            self.media_server = build_server(self.server_type, self.server_config)
        func = object.__getattribute__(self.media_server, attr)
        if isinstance(func, typing.Callable):
            return media_server_wrapper(func)
        else:
            return func


MediaServerInstance: t.Union[MediaServer, MediaServerProxy] = MediaServerProxy()
