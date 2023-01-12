from abc import ABCMeta, abstractmethod
from typing import List, Optional

from cacheout import Cache

from mbot.common.mediaparserutils import MediaParserUtils
from mbot.core.health import HealthIndicator, Health
from mbot.models.mediamodels import MediaType, MediaItem, MediaFolder

ListMediaItem = List[MediaItem]
ListMediaFolder = List[MediaFolder]

library_cache = Cache(maxsize=256, ttl=900, default=None)


class MediaServer(metaclass=ABCMeta):
    @staticmethod
    def parse_query(keyword):
        """
        把文本关键字转化成一个有效的搜索词
        用户直接输入搜索关键字可能不适用于一些媒体服务器直接搜索
        :param keyword:
        :return:
        """
        if not keyword:
            return
        keyword = str(keyword)
        season = MediaParserUtils.parse_season(keyword)
        if season and season.get('text'):
            if keyword == season.get('text'):
                # 避免关键词被完全替换
                return {'query': keyword.strip(), 'season_index': None}
            keyword = keyword.replace(season.get('text'), '')
            return {'query': keyword.strip(), 'season_index': season.get('start')}
        else:
            return {'query': keyword.strip(), 'season_index': None}

    @abstractmethod
    def search(self, keyword: str, movie_type: MediaType) -> ListMediaItem:
        """
        根据类型搜索影片
        :param keyword:
        :param movie_type:
        :return:
        """
        pass

    @abstractmethod
    def search_by_keyword(self, keyword) -> ListMediaItem:
        """
        根据关键字搜索影片，会自动返回所有类型
        :param keyword:
        :return:
        """
        pass

    @abstractmethod
    def search_by_id(self, id, id_type: str = 'tmdb', fetch_all: bool = True) -> ListMediaItem:
        """
        根据编号搜索影片
        :param id:
        :param id_type:
        :return:
        """
        pass

    @abstractmethod
    def get_missing_episodes(self, item_id, season_index: int, total_ep_cnt: int) -> List[int]:
        """
        获取剧集缺失的集号
        :param item_id:
        :param season_index:
        :param total_ep_cnt:
        :return:
        """
        pass

    @abstractmethod
    def refresh_item(self, item_id, metadata=False):
        """
        刷新媒体库
        :param item_id:
        :return:
        """
        pass

    @abstractmethod
    def library_media_folders(self) -> ListMediaFolder:
        """
        获得媒体库所有文件路径配置
        :return:
        """
        pass

    @abstractmethod
    def delete_tv(self, media_id, id_type='tmdb', season_index=None, episodes=None):
        """
        调用媒体库删除剧集信息
        :param media_id:
        :param id_type:
        :param season_index:
        :param episodes:
        :return:
        """
        pass

    @abstractmethod
    def delete_movie(self, media_id, id_type='tmdb'):
        """
        调用媒体库删除电影信息
        :param media_id:
        :param id_type:
        :return:
        """
        pass

    @abstractmethod
    def get_episodes_from_tmdbid(self, tmdb_id, season_index: int, fetch_all=True) -> ListMediaItem:
        """
        根据tmdbid获得所有集数信息
        :param tmdb_id:
        :param season_index:
        :return:
        """
        pass

    @abstractmethod
    def get_media_streams(self, item_id) -> MediaItem:
        """
        获取媒体流信息，包含音频流，字幕流等信息
        :param item_id:
        :return:
        """
        pass

    @abstractmethod
    def get_item(self, item_id):
        """
        根据媒体库编号获取一个详细信息
        :param item_id:
        :return:
        """
        pass

    @abstractmethod
    def test_connect(self) -> bool:
        pass

    def reload_cache(self):
        pass


class MediaServerHealthIndicator(HealthIndicator):
    """媒体服务器健康检查点"""
    media_server: MediaServer = None

    def __init__(self, service_name, media_server: MediaServer):
        super().__init__('MediaServer', service_name)
        self.media_server = media_server

    def health(self) -> Health:
        if not self.media_server:
            Health.down()
        try:
            # 根据检测连接的结果确认健康情况
            r = self.media_server.test_connect()
            if r:
                return Health.up()
            else:
                return Health.down()
        except:
            return Health.down()
