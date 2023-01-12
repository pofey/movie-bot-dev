import json
import logging
import re
import uuid
from typing import List

import requests

from mbot.common.numberutils import NumberUtils
from mbot.constants import APP_VERSION
from mbot.external.mediaserver.models import MediaServer
from mbot.external.mediaserver.models import library_cache, ListMediaItem, ListMediaFolder
from mbot.models.mediamodels import MediaType, AudioStream, SubtitleStream, MediaFolder, MediaItem


class JellyfinMediaServer(MediaServer):
    def test_connect(self) -> bool:
        if self.__get_admin__():
            return True
        else:
            return False

    logger = logging.getLogger(__name__)
    device_id = uuid.UUID(int=uuid.getnode())

    def __get_headers__(self):
        return {
            'Accept': 'application/json',
            'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Application': 'Movie Robot',
            'Accept-Charset': 'UTF-8,*',
            'Accept-encoding': 'gzip',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36',
            'X-Emby-Authorization': f'MediaBrowser Client="Movie Robot", Device="docker", DeviceId="{self.device_id}", Version="{APP_VERSION}", Token="{self.api_key}"'
        }

    def __do_get__(self, api, params=None):
        return requests.get(f'{self.server}{api}', params=params, headers=self.__get_headers__())

    def __do_post__(self, api, params=None):
        return requests.post(f'{self.server}{api}', data=params, headers=self.__get_headers__())

    def __do_delete__(self, api, params=None):
        return requests.delete(f'{self.server}{api}', data=params, headers=self.__get_headers__())

    def __trans_to_media__(self, item):
        media = MediaItem()
        media.id = item.get('Id')
        media.url = '%s/web/index.html#!/details?id=%s&serverId=%s' % (self.server, media.id, item.get('ServerId'))
        media.name = item.get('Name')
        media.type = item.get('Type')
        media.index = item.get('IndexNumber')
        media.video_container = item.get('Container')
        if item.get('ImageTags'):
            if item.get('ImageTags').get('Primary'):
                media.poster_url = '%s/Items/%s/Images/Primary' % (self.server, media.id)
            if item.get('ImageTags').get('Thumb'):
                media.thumb_url = '%s/Items/%s/Images/Thumb' % (self.server, media.id)
        if item.get('ParentThumbItemId'):
            media.thumb_url = '%s/Items/%s/Images/Thumb' % (self.server, item.get('ParentThumbItemId'))
        if item.get('BackdropImageTags'):
            media.backdrop_url = '%s/Items/%s/Images/Backdrop/0' % (self.server, media.id)
        if item.get('ParentBackdropItemId'):
            media.backdrop_url = '%s/Items/%s/Images/Backdrop/0' % (self.server, item.get('ParentBackdropItemId'))
        audio_streams = []
        subtitle_streams = []
        if item.get('MediaStreams'):
            for stream in item.get('MediaStreams'):
                if stream.get('Type') == 'Video' and (not media.video_codec or stream.get('IsDefault')):
                    media.video_codec = stream.get('Codec')
                    media.video_resolution = '%sx%s' % (stream.get('Width'), stream.get('Height'))
                elif stream.get('Type') == 'Audio':
                    audio = AudioStream()
                    audio.codec = stream.get('Codec')
                    audio.language = stream.get('Language')
                    audio.display_language = stream.get('DisplayLanguage')
                    audio.display_title = stream.get('DisplayTitle')
                    audio.is_default = stream.get('IsDefault')
                    audio.channel_layout = stream.get('ChannelLayout')
                    audio_streams.append(audio)
                elif stream.get('Type') == 'Subtitle':
                    subtitle = SubtitleStream()
                    subtitle.codec = stream.get('Codec')
                    subtitle.language = stream.get('Language')
                    subtitle.display_language = stream.get('DisplayTitle')
                    subtitle.external = stream.get('IsExternal')
                    subtitle.is_default = stream.get('IsDefault')
                    subtitle_streams.append(subtitle)
        media.audio_streams = audio_streams
        media.subtitle_streams = subtitle_streams
        if item.get('ProviderIds'):
            media.tmdb_id = int(item.get('ProviderIds').get('Tmdb')) if item.get('ProviderIds').get('Tmdb') else None
            media.imdb_id = item.get('ProviderIds').get('Imdb')
            media.tvdb_id = item.get('ProviderIds').get('Tvdb') if item.get('ProviderIds').get('Tvdb') else None
        media.status = 1
        return media

    def get_seasons(self, item_id):
        if not item_id:
            return []
        api = f'/Shows/{item_id}/Seasons'
        r = self.__do_get__(api)
        text = r.text
        try:
            json_data = json.loads(text)
            if json_data.get('Items'):
                return json_data.get('Items')
            else:
                return []
        except Exception as e:
            logging.info('Jellyfin访问失败: %s' % e)
            raise e

    def delete(self, item_id):
        if not item_id:
            return
        r = self.__do_delete__(f'/Items/{item_id}')
        return r.status_code == 204

    def delete_tv(self, media_id, id_type='tmdb', season_index=None, episodes=None):
        items = self.search_by_id(media_id, id_type)
        if not items:
            self.logger.error(f'没有在影视库找到需要删除的信息{id_type}: {media_id}')
            return
        if episodes:
            if isinstance(episodes, str):
                arr = []
                for s in episodes.split(','):
                    arr.append(int(s))
                episodes = arr

        for i in items:
            item_seasons = self.get_seasons(i.id)
            if not item_seasons:
                if season_index is None:
                    # 季度留空并且没有季度，直接删
                    self.delete(i.id)
                continue
            del_cnt = 0
            for s in item_seasons:
                if season_index is None:
                    self.logger.info(f'开始删除Emby中 {s.get("SeriesName")} 第{s.get("IndexNumber")}季')
                    self.delete(s.get('Id'))
                    del_cnt += 1
                elif s.get('IndexNumber') == int(season_index):
                    if episodes:
                        self.logger.info(
                            f'开始删除Emby中 {s.get("SeriesName")} 第{s.get("IndexNumber")}季 第{episodes}集')
                        eps = self.get_episodes(i.id, season_index)
                        ep_dl_cnt = 0
                        if eps:
                            for e in eps:
                                if e.index in episodes:
                                    self.delete(e.id)
                                    ep_dl_cnt += 1
                        if ep_dl_cnt == len(eps):
                            # 如果删除的集数和查回集数一致，则把季信息也删了
                            self.delete(s.get('Id'))
                            del_cnt += 1
                    else:
                        self.logger.info(f'开始删除Jellyfin中 {s.get("SeriesName")} 第{s.get("IndexNumber")}季')
                        self.delete(s.get('Id'))
                        del_cnt += 1
                    break
            if len(item_seasons) == del_cnt:
                # 如果只有一季，把父剧集也删了
                self.logger.info(f'开始删除Jellyfin中剧集 {i.name}')
                self.delete(i.id)

    def delete_movie(self, media_id, id_type='tmdb'):
        items = self.search_by_id(media_id, id_type)
        if not items:
            self.logger.error(f'没有在影视库找到需要删除的信息{id_type}: {media_id}')
            return
        for i in items:
            result = self.delete(i.id)
            self.logger.info(f'删除Jellyfin中的{i.name}{"成功" if result else "失败"}')

    def __get_all__(self):
        key = 'jellyfin:all'
        if library_cache.get(key):
            return library_cache.get(key)
        r = self.__do_get__(
            f'/Users/{self.admin_uid}/Items',
            params={
                'IncludeItemTypes': 'Movie,Series',
                'fields': 'ProviderIds',
                'Recursive': 'true',
            }
        )
        json_data = r.json()
        items = json_data.get('Items')
        if not items:
            return []
        library_cache.set(key, items)
        return items

    def search_by_id(self, id, id_type: str = 'Tmdb', fetch_all: bool = True) -> ListMediaItem:
        items = self.__get_all__()
        if id_type:
            id_type = f'{id_type[0].upper()}{id_type[1:]}'
        media_items = []
        for item in items:
            if not item.get('ProviderIds') or not item.get('ProviderIds').get(id_type):
                continue
            if item.get('ProviderIds').get(id_type) == str(id):
                media_items.append(item)
        data: ListMediaItem = []
        for r in media_items:
            if r['Type'] not in ['Movie', 'Series']:
                continue
            data.append(self.__trans_to_media__(r))
        return data

    def __get_admin__(self):
        r = self.__do_get__('/Users')
        if not r:
            return
        users = r.json()
        for user in users:
            if user.get("Policy", {}).get("IsAdministrator"):
                return user.get("Id")
        return

    def __init__(self, **args):
        args.setdefault('test', True)
        self.api_key = args['api_key']
        self.host = args['host']
        self.port = args['port']
        self.is_https = args.get('https')
        self.server = '%s://%s:%s' % ("https" if self.is_https else "http", self.host, self.port)
        if args.get('test'):
            self.test()
        self.admin_uid = self.__get_admin__()

    def test(self):
        r = self.__do_get__('/System/Info')
        if not r:
            raise RuntimeError('连接失败，请检查访问地址有效性或容器网络与Jellyfin是否可通信，或者设置的api密钥是否正确')
        text = r.text
        if text == 'Access token is invalid or expired.':
            raise RuntimeError('Jellyfin的api key错误或过期，请重新配置')
        try:
            json_data = json.loads(text)
            msg = 'Jellyfin连接正常，%s版本为%s' % (json_data['ServerName'], json_data['Version'])
            logging.info(msg)
            return msg
        except Exception as e:
            logging.info('Jellyfin访问失败，请检查相关配置')
            raise e

    def search(self, keyword: str, movie_type: MediaType) -> ListMediaItem:
        term_arr = None
        if movie_type == MediaType.TV:
            m_season = re.search('第.+季', keyword)
            if m_season:
                term_arr = [keyword, keyword.replace(m_season.group(), '').strip()]
        if term_arr is None:
            term_arr = [keyword]
        media_items = []
        # 多个关键词匹配结果最多的为准
        for t in term_arr:
            r = self.__do_get__(f'/Users/{self.admin_uid}/Items',
                                params={'IncludeItemTypes': 'Movie' if movie_type == MediaType.Movie else 'Series',
                                        'Recursive': 'true', 'searchTerm': t})
            json_data = r.json()
            if len(json_data['Items']) > len(media_items):
                media_items = json_data['Items']
        data: ListMediaItem = []
        for r in media_items:
            data.append(self.__trans_to_media__(r))
        return data

    def get_episodes(self, id, season_index: int) -> ListMediaItem:
        r = self.__do_get__('/Shows/%s/Episodes' % id, {
            'userId': self.admin_uid,
            'season': season_index
        })
        text = r.text
        if not text or text == 'Series not found':
            return []
        try:
            json_data = json.loads(text)
        except Exception as e:
            logging.info('获取媒体服务中剧集信息错误：%s' % text, exc_info=True)
            raise e
        items = json_data['Items']
        if len(items) == 0:
            return []
        episodes = []
        for ep in items:
            episodes.append(self.__trans_to_media__(ep))
        return episodes

    def get_missing_episodes(self, item_id, season_index: int, total_ep_cnt: int) -> List[int]:
        if not total_ep_cnt:
            total_ep_cnt = 0
        if not isinstance(item_id, list):
            item_id = [item_id]
        episodes = []
        for i in item_id:
            tmp = self.get_episodes(i, season_index)
            if tmp:
                episodes += tmp
        if not episodes:
            return None
        index_set: set = set()
        for e in episodes:
            index_set.add(e.index)
        if len(index_set) >= total_ep_cnt:
            return []
        else:
            set_idx = set(index_set)
            if len(set_idx) == 1 and next(iter(set_idx)) is None:
                # 如果emby没刮好，index会全部为空，此时假设是符合预期的结果，自动为index补值
                set_idx = set(NumberUtils.crate_number_list(1, len(index_set)))
            miss_ep = list(
                set(NumberUtils.crate_number_list(1, total_ep_cnt)).difference(set_idx))
            miss_ep.sort()
            return miss_ep

    def library_media_folders(self) -> ListMediaFolder:
        r = self.__do_get__('/Library/VirtualFolders')
        try:
            result: ListMediaFolder = list()
            json_list = r.json()
            if len(json_list) == 0:
                return []
            for item in json_list:
                m = MediaFolder()
                if 'Name' in item:
                    m.name = item['Name']
                m.id = item['ItemId']
                m.sub_folders = []
                for path in item['Locations']:
                    sm = MediaFolder()
                    sm.name = m.name
                    sm.id = m.id
                    sm.path = path
                    m.sub_folders.append(sm)
                result.append(m)
            return result
        except Exception as e:
            logging.error('获取Jellyfin媒体文件夹失败', exc_info=True)
            return []

    def refresh_item(self, item_id, metadata=False):
        api = f'/Items/{item_id}/Refresh?Recursive=true&MetadataRefreshMode=Default&ImageRefreshMode=Default'
        self.__do_post__(api)

    def get_episodes_from_tmdbid(self, tmdb_id, season_index: int, fetch_all=True):
        result: ListMediaItem = self.search_by_id(tmdb_id)
        if not result:
            return
        episodes = []
        ids: set = set()
        for r in result:
            tmp = self.get_episodes(r.id, season_index)
            if tmp:
                for e in tmp:
                    if e.index in ids:
                        continue
                    ids.add(e.index)
                    episodes.append(e)
        return episodes

    def search_by_keyword(self, keyword):
        if str(keyword).startswith('tt'):
            media_items = self.search_by_id(keyword, id_type='Imdb')
            if not media_items:
                return []
            query = {'query': media_items[0].name, 'season_index': None}
        else:
            query = self.parse_query(keyword)
        if not query:
            return []
        api = f'/Users/{self.admin_uid}/Items'
        r = self.__do_get__(api,
                            {'Recursive': 'true', 'SearchTerm': query.get('query')})
        if not r:
            return []
        data = r.json()
        movie_cnt = 0
        tv_cnt = 0
        for item in data.get('Items'):
            if not item.get('Type'):
                continue
            if item.get('Type') == 'Movie':
                movie_cnt += 1
            elif item.get('Type') == 'Series':
                tv_cnt += 1
        media_list = []
        if movie_cnt > tv_cnt:
            r = self.__do_get__(api,
                                {'IncludeItemTypes': 'Movie', 'fields': 'MediaStreams,ProviderIds', 'Recursive': 'true',
                                 'SearchTerm': query.get('query')})
            data = r.json()
            for item in data.get('Items'):
                media_list.append(self.__trans_to_media__(item))
        else:
            r = self.__do_get__(api,
                                {'IncludeItemTypes': 'Series', 'fields': 'MediaStreams,ProviderIds',
                                 'Recursive': 'true',
                                 'SearchTerm': query.get('query')})
            data = r.json()
            for item in data.get('Items'):
                media = self.__trans_to_media__(item)
                seasons = self.get_seasons(media.id)
                sub_list = []
                for s in seasons:
                    if query.get('season_index') and s.get('IndexNumber') != query.get('season_index'):
                        # 季度检索
                        continue
                    media_season = self.__trans_to_media__(s)
                    media_season.sub_items = self.get_episodes(media.id, media_season.index)
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

    def get_item(self, item_id):
        r = self.__do_get__(f'/Users/{self.admin_uid}/Items/{item_id}')
        try:
            return r.json()
        except:
            return

    def get_media_streams(self, item_id) -> MediaItem:
        r = self.__do_get__(f'/Users/{self.admin_uid}/Items', {
            'Ids': item_id,
            'Recursive': 'true',
            'fields': 'MediaStreams'
        })
        if not r:
            return
        data = r.json()
        if not data or not data.get('Items'):
            return
        return self.__trans_to_media__(data.get('Items')[0])
