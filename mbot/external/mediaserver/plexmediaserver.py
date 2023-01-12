import logging
import re
import threading
from typing import List, Dict, Optional
from urllib.parse import urlparse

import plexapi
import requests
from plexapi.exceptions import Unauthorized
from plexapi.server import PlexServer

from mbot.common.numberutils import NumberUtils
from mbot.external.mediaserver.models import MediaServer, ListMediaItem, ListMediaFolder
from mbot.models.mediamodels import MediaType, AudioStream, SubtitleStream, MediaFolder, MediaItem

_LOGGER = logging.getLogger(__name__)


class PlexMediaServer(MediaServer):

    def test_connect(self) -> bool:
        if self.plex.account():
            return True
        else:
            return False

    def __init__(self, **args):
        self._lock = threading.Lock()
        try:
            self.server_url = args['url']
            self.plex = PlexServer(args['url'], args['token'])
            """
            外部依赖ID与plex关系的缓存
            'tmdb://902478'
            'imdb://tt16606348'
            'tvdb://332684'
            """
            self._id_mapping_cache: Dict[str, List[int]] = dict()
            # 是否需要加载新增
            self._load_added: bool = False
            _LOGGER.info('Plex连接正常，欢迎回来：%s' % self.plex._server.friendlyName)
        except Unauthorized as ue:
            raise RuntimeError('鉴权失败，请检查Token的有效性！')
        except requests.exceptions.ConnectionError as ce:
            raise RuntimeError('连接失败，请检查访问地址有效性或容器网络与Plex是否可通信')

    def _load_added_id_mapping_cache(self):
        if self._id_mapping_cache:
            _LOGGER.info('获取Plex媒体库近期增量ID映射数据')
            items = self.plex.library.recentlyAdded()
            for i, item in enumerate(items):
                if item.type != 'movie':
                    item = self.plex.fetchItem(item.parentRatingKey)
                if not hasattr(item, 'guids'):
                    continue
                for guid in item.guids:
                    if guid.id in self._id_mapping_cache:
                        items = self._id_mapping_cache.get(guid.id)
                    else:
                        items = []
                    items.append(item.ratingKey)
                    self._id_mapping_cache.update({guid.id: items})
            _LOGGER.info('Plex媒体库近期增量ID映射数据加载完毕')

    @property
    def id_mapping_cache(self) -> Dict[str, List[int]]:
        with self._lock:
            if self._id_mapping_cache and not self._load_added:
                return self._id_mapping_cache
            if self._load_added:
                self._load_added_id_mapping_cache()
                self._load_added = False
                if self._id_mapping_cache:
                    return self._id_mapping_cache
            _LOGGER.info('获取Plex全量媒体库ID映射数据，此过程速度较慢')
            items = self.plex.library.all()
            for item in items:
                if not hasattr(item, 'guids'):
                    continue
                for guid in item.guids:
                    if guid.id in self._id_mapping_cache:
                        items = self._id_mapping_cache.get(guid.id)
                    else:
                        items = []
                    items.append(item.ratingKey)
                    self._id_mapping_cache.update({guid.id: items})
            _LOGGER.info('Plex媒体库ID缓存加载完毕')
            return self._id_mapping_cache

    def delete_tv(self, media_id, id_type='tmdb', season_index=None, episodes=None):
        if episodes:
            if isinstance(episodes, str) or isinstance(episodes, int):
                arr = []
                for s in str(episodes).split(','):
                    arr.append(int(s))
                episodes = arr
        items = self._search_by_id(id_type, media_id)
        for show in items:
            if season_index:
                for s in show.seasons():
                    if s.index == int(season_index):
                        if episodes:
                            dl_ep_cnt = 0
                            for e in s.episodes():
                                if e.episodeNumber in episodes:
                                    try:
                                        e.delete()
                                    except Exception as e:
                                        _LOGGER.error('删除plex剧集分集出错：%s' % e)
                                        continue
                                    dl_ep_cnt += 1
                        else:
                            try:
                                s.delete()
                            except Exception as e:
                                _LOGGER.error('删除plex剧集出错：%s' % e)
                                continue
                        break
            else:
                try:
                    show.delete()
                except Exception as e:
                    _LOGGER.error('删除plex剧集出错：%s' % e)
                    continue
                break

    def delete_movie(self, media_id, id_type='tmdb'):
        items = self._search_by_id(id_type, media_id)
        for item in items:
            try:
                item.delete()
                break
            except Exception as e:
                _LOGGER.error('删除plex电影出错：%s' % e)

    def _trans_to_media(self, item, fetch_all=True):
        media = MediaItem()
        media.name = item.title
        if item.type == 'movie':
            media.type = 'Movie'
            media.id = str(item.ratingKey)
            if fetch_all:
                item.reload()
        elif item.type == 'show':
            media.type = 'Series'
            media.id = str(item.ratingKey)
        elif item.type == 'season':
            media.type = 'Season'
            media.id = str(item.ratingKey)
            media.index = item.seasonNumber
        elif item.type == 'episode':
            media.type = 'Episode'
            media.id = str(item.ratingKey)
            media.index = item.episodeNumber
        media.url = '%s/web/index.html#!/server/%s/details?key=%s' % (
            self.server_url, self.plex.machineIdentifier, item.key)
        media.poster_url = item.posterUrl
        media.thumb_url = item.thumbUrl
        media.backdrop_url = None
        if fetch_all:
            audio_streams = []
            if hasattr(item, 'media') and item.media:
                m = item.media[0]
                media.video_container = m.container
                media.video_codec = m.videoCodec
                media.video_resolution = '%sx%s' % (m.width, m.height)
                if m.parts:
                    p = m.parts[0]
                    if p.audioStreams():
                        for stream in p.audioStreams():
                            audio = AudioStream()
                            audio.codec = stream.codec
                            audio.language = stream.languageCode
                            audio.display_language = stream.language
                            audio.display_title = stream.displayTitle
                            audio.is_default = stream.default
                            audio.channel_layout = stream.audioChannelLayout
                            audio_streams.append(audio)
            subtitle_streams = []
            try:
                if hasattr(item, 'subtitleStreams') and item.subtitleStreams():
                    for stream in item.subtitleStreams():
                        subtitle = SubtitleStream()
                        subtitle.codec = stream.codec
                        subtitle.language = stream.languageCode
                        subtitle.display_language = stream.language
                        subtitle.display_title = stream.displayTitle
                        subtitle.external = stream.key is not None
                        subtitle.is_default = stream.default
                        subtitle_streams.append(subtitle)
            except Exception as e:
                pass
            media.audio_streams = audio_streams
            media.subtitle_streams = subtitle_streams
        if hasattr(item, 'guids') and item.guids:
            for g in item.guids:
                parsed = urlparse(g.id)
                if parsed.scheme == 'imdb':
                    media.imdb_id = parsed.hostname
                elif parsed.scheme == 'tmdb':
                    media.tmdb_id = int(parsed.hostname) if parsed.hostname else None
                elif parsed.scheme == 'tvdb':
                    media.tvdb_id = int(parsed.hostname) if parsed.hostname else None
        media.status = 1
        return media

    def get_item(self, item_id):
        try:
            return self.plex.library.fetchItem(int(item_id))
        except Exception as e:
            return

    def _search_by_id(self, id_type: str, id_):
        key = f'{id_type}://{id_}'
        if key not in self.id_mapping_cache:
            return []
        items = self.id_mapping_cache.get(key)
        result = []
        for ratingKey in items:
            item = self.get_item(ratingKey)
            if not item:
                del self._id_mapping_cache[key]
                continue
            result.append(item)
        return result

    def search_by_id(self, id_, id_type: str = 'tmdb', fetch_all: bool = True) -> ListMediaItem:
        result = self._search_by_id(id_type, id_)
        data: ListMediaItem = []
        for r in result:
            try:
                data.append(self._trans_to_media(r, fetch_all))
            except:
                pass
        return data

    def refresh_item(self, item_id, metadata=False):
        if not item_id:
            return
        is_section = False
        if str(item_id).startswith('section:'):
            item = self.plex.library.sectionByID(int(item_id[8:]))
            is_section = True
        else:
            rating_key = int(item_id)
            item = self.plex.library.fetchItem(rating_key)
        if not item:
            return
        try:
            if metadata:
                logging.info('已经通知plex刷新媒体库元数据：%s' % item.title)
                item.refresh()
            if is_section:
                section = item
            else:
                section = self.plex.library.sectionByID(item.librarySectionID)
            if section:
                logging.info('已经通知plex重新扫描媒体库：%s' % section.title)
                section.update()
        except plexapi.exceptions.NotFound as e:
            logging.error('plex中找不到这个编号：%s' % item_id)

    def library_media_folders(self) -> ListMediaFolder:
        sections = self.plex.library.sections()
        if not sections:
            return []
        result: ListMediaFolder = list()
        for s in sections:
            m = MediaFolder()
            m.name = s.title
            m.id = f'section:{s.key}'
            m.sub_folders = []
            for path in s.locations:
                sub = MediaFolder()
                sub.name = s.title
                sub.id = f'section:{s.key}'
                sub.path = path
                m.sub_folders.append(sub)
            result.append(m)
        return result

    def search(self, keyword: str, movie_type: MediaType) -> ListMediaItem:
        movies_type = 'movie' if movie_type == MediaType.Movie else 'show'
        term_arr = None
        if movies_type == MediaType.TV:
            m_season = re.search('第.+季', keyword)
            if m_season:
                term_arr = [keyword, keyword.replace(m_season.group(), '').strip()]
        if term_arr is None:
            term_arr = [keyword]
        media_items = []
        # 多个关键词匹配结果最多的为准
        for t in term_arr:
            try:
                tmp = self.plex.search(t)
            except Exception as e:
                logging.info(e)
                logging.info('search keyword:%s' % t)
                continue
            if tmp is None:
                continue
            if len(tmp) > len(media_items):
                media_items = tmp
        if len(media_items) == 0:
            return []
        data: ListMediaItem = []
        for r in media_items:
            if r.type not in movies_type:
                continue
            data.append(self._trans_to_media(r))
        return data

    def get_missing_episodes(self, item_id, season_index: int, total_ep_cnt: int) -> List[int]:
        all_eps = []
        if not isinstance(item_id, list):
            item_id = [item_id]
        episode_cache: set = set()
        for i in item_id:
            rating_key = int(i)
            item = self.plex.library.fetchItem(rating_key)
            tmp = item.episodes()
            if tmp:
                for e in tmp:
                    if e.parentIndex != season_index:
                        continue
                    if e.episodeNumber in episode_cache:
                        continue
                    episode_cache.add(e.episodeNumber)
                    all_eps.append(e)
        all_eps = list(set(all_eps))
        if not all_eps:
            return
        episodes = []
        for e in all_eps:
            if e.parentIndex != season_index:
                continue
            episodes.append(e.episodeNumber)
        if len(episodes) >= total_ep_cnt:
            return []
        miss_ep = list(
            set(NumberUtils.crate_number_list(1, total_ep_cnt)).difference(set(episodes)))
        miss_ep.sort()
        return miss_ep

    def get_episodes_from_tmdbid(self, tmdb_id, season_index, fetch_all=True) -> ListMediaItem:
        result = self.search_by_id(tmdb_id)
        if not result:
            return
        all_eps = []
        ids: set = set()
        for r in result:
            tmp = self.plex.library.fetchItem(int(r.id)).episodes()
            if tmp:
                for e in tmp:
                    if e.parentIndex != season_index:
                        continue
                    if e.episodeNumber in ids:
                        continue
                    ids.add(e.episodeNumber)
                    all_eps.append(self._trans_to_media(e, fetch_all=fetch_all))
        return all_eps

    def search_by_keyword(self, keyword):
        if str(keyword).startswith('tt'):
            media_items = self.search_by_id(keyword, id_type='imdb')
            if not media_items:
                return []
            query = {'query': media_items[0].name, 'season_index': None}
        else:
            query = self.parse_query(keyword)
        if not query:
            return []
        result = self.plex.search(query.get('query'))
        if not result:
            return []
        movie_cnt = 0
        tv_cnt = 0
        for item in result:
            if item.type == 'movie':
                movie_cnt += 1
            elif item.type == 'show':
                tv_cnt += 1
        media_list = []
        if movie_cnt > tv_cnt:
            for item in result:
                if item.type == 'movie':
                    media_list.append(self._trans_to_media(item))
        else:
            for item in result:
                if item.type != 'show':
                    continue
                media = self._trans_to_media(item)
                sub_list = []
                for s in item.seasons():
                    if query.get('season_index') and s.seasonNumber != query.get('season_index'):
                        # 季度检索
                        continue
                    media_season = self._trans_to_media(s)
                    media_season.sub_items = []
                    for e in s.episodes():
                        media_season.sub_items.append(self._trans_to_media(e))
                    if media_season.sub_items:
                        # 季度音频字幕流抽最后一集的信息
                        ep_media = self.get_media_streams(media_season.sub_items[-1].id)
                        if ep_media:
                            media_season.video_codec = ep_media.video_codec
                            media_season.video_container = ep_media.video_container
                            media_season.video_resolution = ep_media.video_resolution
                            media_season.audio_streams = ep_media.audio_streams
                            media_season.subtitle_streams = ep_media.subtitle_streams
                    sub_list.append(media_season)
                if len(sub_list) > 0:
                    media.sub_items = sub_list
                    media_list.append(media)
        return media_list

    def get_media_streams(self, item_id) -> MediaItem:
        if not item_id:
            return
        rating_key = int(item_id)
        item = self.plex.library.fetchItem(rating_key)
        return self._trans_to_media(item)

    def reload_cache(self):
        with self._lock:
            self._load_added = True
