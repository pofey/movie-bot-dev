import json
import logging
import re
from itertools import groupby
from typing import List, Dict, Optional

import requests

from mbot.common.numberutils import NumberUtils
from mbot.external.mediaserver.models import MediaServer
from mbot.external.mediaserver.models import ListMediaItem, ListMediaFolder
from mbot.models.mediamodels import MediaType, MediaItem, AudioStream, SubtitleStream, MediaFolder


class EmbyMediaServer(MediaServer):
    logger = logging.getLogger(__name__)
    headers = {
        'Accept': 'application/json',
        'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Application': 'Movie Robot',
        'Accept-Charset': 'UTF-8,*',
        'Accept-encoding': 'gzip',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36',
    }

    def test_connect(self) -> bool:
        if self.test():
            return True
        else:
            return False

    def __init__(self, **args):
        args.setdefault('test', True)
        self.api_key = args['api_key']
        self.host = args['host']
        self.port = args['port']
        self.is_https = args['https']
        self.server = '%s://%s:%s' % ("https" if self.is_https else "http", self.host, self.port)
        if args.get('test'):
            self.test()
        self.admin_id = self._get_admin()

    def __wrapper_params__(self, params):
        if params:
            params['api_key'] = self.api_key
        else:
            params = {'api_key': self.api_key}
        return params

    def __do_get__(self, api, params=None):
        return requests.get(f'{self.server}{api}', params=self.__wrapper_params__(params), headers=self.headers)

    def __do_post__(self, api, params=None):
        return requests.post(f'{self.server}{api}', data=self.__wrapper_params__(params), headers=self.headers)

    def get_seasons(self, item_id):
        if not item_id:
            return []
        r = self.__do_get__(f'/emby/Shows/{item_id}/Seasons')
        try:
            json_data = r.json()
            if json_data.get('Items'):
                return json_data.get('Items')
            else:
                return []
        except Exception as e:
            logging.info('Emby访问失败: %s' % e)
            raise e

    def delete(self, item_id):
        if not item_id:
            return
        r = requests.delete(f'{self.server}/emby/Items/{item_id}?api_key={self.api_key}', headers=self.headers)
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
                        self.logger.info(f'开始删除Emby中 {s.get("SeriesName")} 第{s.get("IndexNumber")}季')
                        self.delete(s.get('Id'))
                        del_cnt += 1
                    break
            if len(item_seasons) == del_cnt:
                # 如果只有一季，把父剧集也删了
                self.logger.info(f'开始删除Emby中剧集 {i.name}')
                self.delete(i.id)

    def delete_movie(self, media_id, id_type='tmdb'):
        items = self.search_by_id(media_id, id_type)
        if not items:
            self.logger.error(f'没有在影视库找到需要删除的信息{id_type}: {media_id}')
            return
        for i in items:
            result = self.delete(i.id)
            self.logger.info(f'删除Emby中的{i.name}{"成功" if result else "失败"}')

    def search_by_id(self, id, id_type: str = 'tmdb', fetch_all: bool = True) -> ListMediaItem:
        r = self.__do_get__('/emby/Items', {
            'AnyProviderIdEquals': f'{id_type}.{id}',
            'Recursive': 'true'
        })
        json_data = r.json()
        media_items = json_data.get('Items')
        if not media_items:
            return []
        data: ListMediaItem = []
        for r in media_items:
            if r['Type'] not in ['Movie', 'Series']:
                continue
            data.append(self.__trans_to_media__(r))
        return data

    def test(self):
        r = self.__do_get__('/emby/System/Info')
        text = r.text
        if text is None:
            raise RuntimeError('连接失败，请检查访问地址有效性或容器网络与Emby是否可通信')
        if text == 'Access token is invalid or expired.':
            raise RuntimeError('Emby的api key错误或过期，请重新配置')
        try:
            json_data = json.loads(text)
            msg = 'Emby连接正常，%s版本为%s' % (json_data['ServerName'], json_data['Version'])
            logging.info(msg)
            return msg
        except Exception as e:
            logging.info('Emby访问失败，请检查相关配置')
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
            r = self.__do_get__('/emby/Items',
                                {'IncludeItemTypes': 'Movie' if movie_type == MediaType.Movie else 'Series',
                                 'Recursive': 'true', 'SearchTerm': t})
            json_data = r.json()
            if len(json_data['Items']) > len(media_items):
                media_items = json_data['Items']
        data: ListMediaItem = []
        for r in media_items:
            data.append(self.__trans_to_media__(r))
        return data

    def __trans_to_media__(self, item):
        media = MediaItem()
        media.id = item.get('Id')
        media.url = '%s/web/index.html#!/item?id=%s&serverId=%s' % (self.server, media.id, item.get('ServerId'))
        media.name = item.get('Name')
        media.type = item.get('Type')
        media.index = item.get('IndexNumber')
        media.video_container = item.get('Container')
        if item.get('ImageTags'):
            if item.get('ImageTags').get('Primary'):
                media.poster_url = '%s/emby/Items/%s/Images/Primary' % (self.server, media.id)
            if item.get('ImageTags').get('Thumb'):
                media.thumb_url = '%s/emby/Items/%s/Images/Thumb' % (self.server, media.id)
        if item.get('ParentThumbItemId'):
            media.thumb_url = '%s/emby/Items/%s/Images/Thumb' % (self.server, item.get('ParentThumbItemId'))
        if item.get('BackdropImageTags'):
            media.backdrop_url = '%s/emby/Items/%s/Images/Backdrop/0' % (self.server, media.id)
        if item.get('ParentBackdropItemId'):
            media.backdrop_url = '%s/emby/Items/%s/Images/Backdrop/0' % (self.server, item.get('ParentBackdropItemId'))
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
                    subtitle.display_language = stream.get('DisplayLanguage')
                    subtitle.display_title = stream.get('DisplayTitle')
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

    def search_by_keyword(self, keyword) -> List[MediaItem]:
        if str(keyword).startswith('tt'):
            r = self.__do_get__('/emby/Items', {
                'AnyProviderIdEquals': f'imdb.%s' % keyword,
                'Recursive': 'true'
            })
            json_data = r.json()
            media_items = json_data.get('Items')
            if not media_items:
                return []
            for item in media_items:
                if item.get('Type') not in ['Movie', 'Episode', 'Series']:
                    continue
                if 'SeriesName' in item:
                    query = {'query': item.get('SeriesName'), 'season_index': None}
                else:
                    query = {'query': item.get('Name'), 'season_index': None}
                break
        else:
            query = self.parse_query(keyword)
        if not query:
            return []
        # 先做一次基本查询，分析是电影还是剧集结果
        r = self.__do_get__('/emby/Items',
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
            r = self.__do_get__('/emby/Items',
                                {'IncludeItemTypes': 'Movie', 'Fields': 'MediaStreams,ProviderIds', 'Recursive': 'true',
                                 'SearchTerm': query.get('query')})
            data = r.json()
            for item in data.get('Items'):
                media_list.append(self.__trans_to_media__(item))
        else:
            r = self.__do_get__('/emby/Items',
                                {'IncludeItemTypes': 'Series', 'Fields': 'MediaStreams,ProviderIds',
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
                    media_season.sub_items = self.get_episodes_from_season_id(media.id, media_season.id)
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
                if sub_list:
                    # 剧集音频字幕流抽最后一季的
                    ss = sub_list[-1]
                    media.video_codec = ss.video_codec
                    media.video_container = ss.video_container
                    media.video_resolution = ss.video_resolution
                    media.audio_streams = ss.audio_streams
                    media.subtitle_streams = ss.subtitle_streams
                if len(sub_list) > 0:
                    media.sub_items = sub_list
                    media_list.append(media)
        return media_list

    def get_episodes_from_tmdbid(self, tmdb_id, season_index, fetch_all=True) -> ListMediaItem:
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

    def get_episodes_from_season_id(self, item_id, season_id) -> ListMediaItem:
        r = self.__do_get__('/emby/Shows/%s/Episodes?SeasonId=%s' % (item_id, season_id))
        if not r:
            return []
        data = r.json()
        if not data or not data.get('Items'):
            return []
        media_list = []
        for item in data.get('Items'):
            if item.get('LocationType') and item.get('LocationType') == 'Virtual':
                continue
            media_list.append(self.__trans_to_media__(item))
        return media_list

    def get_episodes(self, id, season_index: int) -> ListMediaItem:
        r = self.__do_get__('/emby/Shows/%s/Episodes' % id)
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
        season_grouped = groupby(items, key=lambda r: r['SeasonName'])
        episodes = {}
        for key, group in season_grouped:
            season_ep = []
            for ep in list(group):
                season_ep.append(self.__trans_to_media__(ep))
            episodes[key] = season_ep
        # 找emby的季度名称前缀
        fskey = '季'
        for k in episodes.keys():
            if k == 'Specials':
                continue
            fskey = k
            break
        # 季 1、Season 1
        snprefix = fskey.split(' ')[0]
        season_name = '%s %s' % (snprefix, season_index)
        if season_name not in episodes.keys():
            unknown_season = []
            for skey in episodes.keys():
                if re.match(r'%s\s\d+' % snprefix, skey):
                    continue
                unknown_season.append(skey)
            if len(unknown_season) == 0:
                return []
            # 未刮对的季信息，算为匹配
            season = episodes[unknown_season[0]]
        else:
            season = episodes[season_name]
        return season

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
        r = self.__do_get__('/emby/Library/SelectableMediaFolders')
        try:
            result: ListMediaFolder = list()
            json_list = r.json()
            if len(json_list) == 0:
                return []
            for item in json_list:
                m = MediaFolder()
                if 'Name' in item:
                    m.name = item['Name']
                m.id = item['Id']
                m.sub_folders = []
                for sf in item['SubFolders']:
                    sm = MediaFolder()
                    if 'Name' in sf:
                        sm.name = sf['Name']
                    sm.id = sf['Id']
                    sm.path = sf['Path']
                    m.sub_folders.append(sm)
                result.append(m)
            return result
        except Exception as e:
            logging.error('获取Emby媒体文件夹失败', exc_info=True)
            return []

    def refresh_item(self, item_id, metadata=False):
        api = f'/emby/Items/{item_id}/Refresh?Recursive=true&MetadataRefreshMode=Default&ImageRefreshMode=Default&api_key={self.api_key}'
        self.__do_post__(api)

    def get_media_streams(self, item_id) -> MediaItem:
        r = self.__do_get__('/emby/Items', {
            'Ids': item_id,
            'Recursive': 'true',
            'Fields': 'MediaStreams'
        })
        if not r:
            return
        data = r.json()
        if not data or not data.get('Items'):
            return
        return self.__trans_to_media__(data.get('Items')[0])

    def list_all(self, media_type):
        if media_type == 'Movie':
            r = self.__do_get__('/emby/Items',
                                {'IncludeItemTypes': 'Movie', 'Fields': 'MediaStreams,ProviderIds',
                                 'Recursive': 'true'})
            data = r.json()
        else:
            r = self.__do_get__('/emby/Items',
                                {'IncludeItemTypes': 'Series', 'Fields': 'MediaStreams,ProviderIds',
                                 'Recursive': 'true'})
            data = r.json()
        return data

    def _get_admin(self):
        r = self.__do_get__('/emby/Users')
        if not r:
            return
        users = r.json()
        for user in users:
            if user.get("Policy", {}).get("IsAdministrator"):
                return user.get("Id")
        return

    def get_item(self, item_id):
        r = self.__do_get__(f'/emby/Users/{self.admin_id}/Items/{item_id}')
        try:
            return r.json()
        except:
            return

    def get_system_webhooks(self):
        r = self.__do_get__('/emby/System/Configuration/webhooks')
        try:
            j = r.json()
            if not j or not j.get('Webhooks'):
                return
            return j.get('Webhooks')
        except:
            return

    def add_system_webhooks(self, url: str, events: List[str]):
        event_ids = []
        if 'Playback' in events:
            event_ids.append('playback.start')
            event_ids.append('playback.pause')
            event_ids.append('playback.unpause')
            event_ids.append('playback.stop')
        for e in events:
            if e.find('.') != -1:
                event_ids.append(e)
                events.remove(e)
        r = self.__do_post__(f'/emby/Webhooks?X-Emby-Token={self.api_key}', {
            'Events': events,
            'EventIds': event_ids,
            'Url': url,
            'UserId': '',
            'FriendlyName': "MBot Webhook"
        })
        r.raise_for_status()
