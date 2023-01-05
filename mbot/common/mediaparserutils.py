import os
import re

from mbot.common.fileprobe import FileProbe
from mbot.common.numberutils import NumberUtils

CN_EP_PATTERN = '[集话回話画期]'
TV_NUM_PATTERN = '[1234567890一二三四五六七八九十]{1,4}'

SEASON_PATTERNS = [
    re.compile('[sS](%s)?[-—~]{1,3}[sS]?(%s)' % (TV_NUM_PATTERN, TV_NUM_PATTERN)),
    re.compile('第(%s)[季部辑]?分?[-—~]{1,3}第?(%s)[季部辑]分?' % (TV_NUM_PATTERN, TV_NUM_PATTERN)),
    re.compile(r'S(?:eason)?(\d+)', re.IGNORECASE),
    re.compile(r'S(?:eason)?[-]{0,3}(\d+)', re.IGNORECASE),
    re.compile('第(%s)[季部辑]分?' % TV_NUM_PATTERN),
    re.compile(r'S(?:eason)?\s(\d+)', re.IGNORECASE)
]
COMPLETE_SEASON_PATTERNS = [
    re.compile('全(%s)[季部辑]' % TV_NUM_PATTERN)
]
EPISODE_PATTERNS = [
    re.compile('第?(%s)%s' % (TV_NUM_PATTERN, CN_EP_PATTERN)),
    re.compile(r'第\s?(%s)\s?%s' % (TV_NUM_PATTERN, CN_EP_PATTERN)),
    re.compile(r'[Ee][Pp]?(%s)' % TV_NUM_PATTERN),
    re.compile(r'^(%s)\s?$' % TV_NUM_PATTERN),
    re.compile(r'^(%s)\.' % TV_NUM_PATTERN),
    re.compile(r'(%s)[oO][fF]%s' % (TV_NUM_PATTERN, TV_NUM_PATTERN)),
    re.compile(r'[\[【](%s)[】\]]' % TV_NUM_PATTERN),
    re.compile(r'\s{1}-\s{1}(%s)' % TV_NUM_PATTERN)
]
EPISODE_RANGE_PATTERNS = [
    re.compile('第(%s)%s?-第?(%s)%s' % (TV_NUM_PATTERN, CN_EP_PATTERN, TV_NUM_PATTERN, CN_EP_PATTERN)),
    re.compile(r'[Ee][Pp]?(\d{1,4})[Ee][Pp]?(\d{1,4})'),
    re.compile(r'[Ee][Pp]?(\d{1,4})-[Ee]?[Pp]?(\d{1,4})'),
    re.compile(r'^(%s)[-到](%s)$' % (TV_NUM_PATTERN, TV_NUM_PATTERN)),
    re.compile(r'^(%s)\s{0,4}-\s{0,4}.+$' % TV_NUM_PATTERN),
    re.compile(r'[\[【\(](%s)-(%s)[】\]\)]' % (TV_NUM_PATTERN, TV_NUM_PATTERN)),
    re.compile(r'(全)(%s)%s' % (TV_NUM_PATTERN, CN_EP_PATTERN))
]
COMPLETE_EPISODE_PATTERNS = [
    re.compile('全(%s)%s' % (TV_NUM_PATTERN, CN_EP_PATTERN)),
    re.compile('(%s)%s全' % (TV_NUM_PATTERN, CN_EP_PATTERN)),
    re.compile('全%s' % CN_EP_PATTERN),
    re.compile('所有%s' % CN_EP_PATTERN)
]
invalid_words: set = {'sense8', '1080p', '720p', '2160p', '4K', '4k', '8K'}


class MediaParserUtils:
    """媒体信息格式化工具类，待重构完成"""

    @staticmethod
    def is_complete_episodes(text):
        # 匹配是否全集
        for p in COMPLETE_EPISODE_PATTERNS:
            m = p.search(text)
            if m:
                if len(m.groups()) > 0:
                    end = NumberUtils.to_number(m.group(1))
                else:
                    end = 0
                return [1, end]
        return

    @staticmethod
    def is_complete_season(text):
        for p in COMPLETE_SEASON_PATTERNS:
            m = p.search(text)
            if m:
                return [1, NumberUtils.to_number(m.group(1))]

    @staticmethod
    def parse_episode(text, match_single=True, match_range=True):
        if not text:
            return
        text = text.lower()
        for x in invalid_words:
            text = text.replace(x, '')
        if FileProbe.get_file_type(text) != 'unknown':
            text = os.path.splitext(text)[0]
        ep_index_start = None
        ep_index_end = None
        ep_str = None
        pts = []
        if match_range:
            pts += EPISODE_RANGE_PATTERNS
        if match_single:
            pts += EPISODE_PATTERNS
        for p in pts:
            m = p.search(text)
            if m:
                ep_str = m.group()
                if len(m.groups()) == 1:
                    ep_index_start = NumberUtils.to_number(m.group(1))
                    ep_index_end = None
                elif len(m.groups()) == 2:
                    g1 = m.group(1)
                    if g1 == '全':
                        ep_index_start = 0
                    else:
                        ep_index_start = NumberUtils.to_number(g1)
                    ep_index_end = NumberUtils.to_number(m.group(2))
                if ep_index_start and ep_index_start > 2000:
                    # is year,not episode
                    ep_index_start = None
                    ep_index_end = None
                    continue
                break
        if ep_index_start is None:
            return
        return {'start': ep_index_start, 'end': ep_index_end, 'text': ep_str}

    @staticmethod
    def parse_season(text):
        season_start = None
        season_end = None
        season_text = None
        for p in SEASON_PATTERNS:
            m = p.search(text)
            if m:
                season_text = m.group()
                if season_text == text:
                    season_text = m.group(1)
                if len(m.groups()) == 1:
                    season_start = NumberUtils.to_number(m.group(1))
                    season_end = None
                elif len(m.groups()) == 2:
                    season_start = NumberUtils.to_number(m.group(1))
                    season_end = NumberUtils.to_number(m.group(2))
                break
        if season_start is None:
            return
        return {'start': season_start, 'end': season_end, 'text': season_text}

    @staticmethod
    def episode_format(episode, prefix=''):
        if not episode:
            return
        if isinstance(episode, str):
            episode = list(filter(None, episode.split(',')))
            episode = [int(i) for i in episode]
        elif isinstance(episode, int):
            episode = [episode]
        if episode:
            episode.sort()
        if len(episode) <= 2:
            return ','.join([str(e).zfill(2) for e in episode])
        else:
            episode.sort()
            return '%s%s-%s%s' % (prefix, str(episode[0]).zfill(2), prefix, str(episode[len(episode) - 1]).zfill(2))

    @staticmethod
    def trim_name(name):
        if not name:
            return
        name = str(name)
        season = MediaParserUtils.parse_season(name)
        if season and season.get('text'):
            simple_name = name.replace(season.get('text'), '').strip()
        else:
            simple_name = name
        return simple_name
