from enum import Enum
from typing import List

from iso639 import Lang

from mbot.common.serializable import Serializable

ListStr = List[str]
ListInt = List[int]


def __get_language__(tags):
    l = tags.get('language')
    if not l:
        return l
    if l in ['普通话']:
        l = 'chi'
    return l


class MediaType(str, Enum):
    """媒体类型"""
    Movie = '电影'
    TV = '剧集'
    XX = 'XX'
    Other = '其他'

    @staticmethod
    def get_type(type_str):
        if not type_str:
            return
        l = type_str.lower()
        if l == 'movie':
            return MediaType.Movie
        elif l == 'tv' or l == 'series':
            return MediaType.TV
        elif l == 'xx':
            return MediaType.TV
        else:
            return MediaType.Other

    def __str__(self):
        return str(self.name)


class SubtitleStream(Serializable):
    """字幕流信息"""

    def __init__(self, meta=None):
        if meta and isinstance(meta, dict):
            self.codec = meta.get('codec_name')
            tags = meta.get('tags', {})
            self.language = __get_language__(tags)
            if tags.get('title'):
                self.display_title = tags.get('title')
                self.display_language = Lang(self.language).name
            elif self.language:
                self.display_language = Lang(self.language).name
                self.display_title = self.display_language
            self.is_default = bool(meta.get('disposition', {}).get('default'))
            self.external = False

    codec: str = None
    language: str = None
    display_language: str = None
    display_title: str = None
    # 外部字幕
    external: bool = None
    is_default: bool = None


class AudioStream(Serializable):
    """音频流信息"""

    def __init__(self, meta=None):
        if meta and isinstance(meta, dict):
            self.codec = meta.get('codec_name')
            self.display_title = meta.get('codec_long_name')
            self.is_default = bool(meta.get('disposition', {}).get('default'))
            tags = meta.get('tags', {})
            self.language = __get_language__(tags)
            if tags.get('title'):
                self.display_title = tags.get('title')
                self.display_language = Lang(self.language).name
            elif self.language:
                self.display_language = Lang(self.language).name
                self.display_title = self.display_language
            self.channel_layout = meta.get('channel_layout')

    codec: str = None
    language: str = None
    display_language: str = None
    display_title: str = None
    is_default: bool = None
    channel_layout: str = None


class MediaItem(Serializable):
    """媒体服务器的影片基础模型"""
    tmdb_id: int = None
    imdb_id: str = None
    tvdb_id: str = None
    url: str = None
    id: str = None
    name: str = None
    # 剧集才有，集号
    index: int = None
    # 类型 Movie、Series
    type: str = None
    poster_url: str = None
    thumb_url: str = None
    backdrop_url: str = None

    # 视频容器类型 mkv 原盘
    video_container: str = None
    # 视频编码
    video_codec: str = None
    # 视频分辨率
    video_resolution: str = None
    # 字幕流
    subtitle_streams: List[SubtitleStream] = None
    # 音频流
    audio_streams: List[AudioStream] = None
    sub_items: list
    # 播放状态
    status: int = 1


class MediaFolder:
    """媒体服务器配置的影音库文件夹"""
    id: str = None
    name: str = None
    path: str
    sub_folders: list


class People(Serializable):
    """剧组人员、导演、演员等人员信息"""
    douban_id: int = None
    tmdb_id: int = None
    imdb_id: str = None
    name: str = None
    en_name: str = None
    role: str = None
    pic_url: str = None
    type: str = None


class Movies(Serializable):
    """历史遗留模型，目前仅豆瓣在用"""
    id: str = None
    url: str = None
    name: str = None
    area: ListStr = None
    type: str = None
    cates: ListStr = None
    tags: ListStr = None
    release_year: str = None
    local_name: str = None
    en_name: str = None
    alias: ListStr = []
    season_index: int = None
    # 剧集才会存在的信息
    total_ep_count: int = None
    site_name: str = None
    cover_image: str = None
    rating: float = None
    imdb: str = None
    tags: list = None
    user_id: str = None
    intro: str = None
    release_date: str = None
    director: List[People] = None
    actor: List[People] = None
    duration: int = None
    trailer_video_url: str = None


class MediaImage(Serializable):
    """影片图片资源"""
    source: str = None
    banner: str = None
    poster: str = None
    small_poster: str = None
    clear_logo: str = None
    background: str = None
    small_backdrop: str = None
    thumb: str = None
    main_background = None
    main_poster = None
