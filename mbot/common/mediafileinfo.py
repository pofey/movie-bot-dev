import os
from typing import Dict, Optional

from pymediainfo import MediaInfo, Track

from mbot.common.fileprobe import FileProbe
from mbot.exceptions import MediaFileError

_height_title = {
    '480p': [400, 599],
    '720p': [600, 799],
    '1080p': [800, 1200],
    '4K': [1500, 2500],
    '8K': [3500, 5000]
}
_weight_title = {
    640: '480p',
    1280: '720p',
    1920: '1080p',
    3840: '4K',
    7680: '8K'
}


class Resolution:
    width: int
    height: int
    title: str

    def __init__(self, width, height):
        title = None
        if width in _weight_title:
            title = _weight_title.get(width)
        else:
            for t in _height_title:
                range_ = _height_title[t]
                if range_[0] <= height <= range_[1]:
                    title = t
                    break
        self.width = width
        self.height = height
        self.title = title


class MediaFileInfo:
    def __init__(self, filepath):
        self.filepath = filepath
        self._media_info: Dict = dict()

    @property
    def main_video_filepath(self):
        if os.path.isfile(self.filepath):
            return self.filepath
        else:
            max_video_file = FileProbe.find_max_size_video_file(self.filepath)
            if not max_video_file:
                raise FileNotFoundError(f'找不到目录内的有效视频文件：{self.filepath}')
            return max_video_file

    @property
    def general_track(self):
        if not self.mediainfo.general_tracks:
            return
        return self.mediainfo.general_tracks[0]

    @property
    def mediainfo(self):
        if self._media_info:
            return self._media_info
        self._media_info = MediaInfo.parse(self.main_video_filepath)
        return self._media_info

    @property
    def main_video_track(self) -> Optional[Track]:
        if not self.mediainfo.video_tracks:
            raise MediaFileError(f'无法分析视频信息：{self.main_video_filepath}')
        return self.mediainfo.video_tracks[0]

    @property
    def file_size(self):
        return self.general_track.file_size

    @property
    def internet_media_type(self):
        return self.main_video_track.internet_media_type

    @property
    def hdr_format_commercial(self):
        hdr = self.main_video_track.hdr_format_commercial
        if not hdr:
            return
        if hdr.find(' / ') != -1:
            if self.main_video_track.hdr_format.find('Dolby Vision') != -1:
                return 'Dolby Vision'
            else:
                return 'HDR10'
        else:
            return hdr

    @property
    def color_primaries(self):
        return self.main_video_track.color_primaries

    @property
    def codec_name(self):
        return self.main_video_track.format

    @property
    def frame_rate(self) -> float:
        return round(float(
            self.main_video_track.frame_rate if self.main_video_track.frame_rate else self.main_video_track.original_frame_rate),
                     2)

    @property
    def bit_rate(self) -> int:
        return self.main_video_track.bit_rate

    @property
    def bit_depth(self) -> int:
        return self.main_video_track.bit_depth

    @property
    def duration_second(self) -> Optional[int]:
        if self.main_video_track.duration is None:
            return
        return round(float(self.main_video_track.duration) / 1000)

    @property
    def resolution(self) -> Optional[Resolution]:
        height = self.main_video_track.height
        width = self.main_video_track.width
        if not width:
            return
        return Resolution(width, height)
