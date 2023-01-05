import logging
import os.path
import shutil
from enum import Enum
from typing import Dict, List

from cacheout import Cache

from mbot.common.mediaparserutils import MediaParserUtils

_LOGGER = logging.getLogger(__name__)
hardlink_cache = Cache(maxsize=50, ttl=60 * 5, default=None)


class LinkMode(Enum):
    LINK = 'link'
    COPY = 'copy'
    MOVE = 'move'

    @staticmethod
    def get_by_value(value):
        for l in LinkMode:
            if str(l.value).lower() == str(value).lower():
                return l
        return


class OSUtils:
    """包装的文件系统操作工具集"""

    @staticmethod
    def link_test(source_dir, target_dir):
        """
        硬链接测试
        :param source_dir:
        :param target_dir:
        :return:
        """
        sfile = os.path.join(source_dir, 'testlink.txt')
        tfile = os.path.join(target_dir, 'testlink.txt')
        with open(sfile, "w") as f:
            f.write('text')
        os.link(sfile, tfile)
        os.remove(sfile)
        os.remove(tfile)

    @staticmethod
    def split_path(path: str):
        """
        按不同操作系统的路径分隔符拆分字符串
        :param path:
        :return:
        """
        if path is None or len(path) == 0:
            return []
        arr = []
        if path.find('\\') != -1:
            arr = path.split('\\')
        else:
            arr = path.split(os.sep)
        if arr is None or len(arr) == 0:
            return []
        return arr

    @staticmethod
    def get_first_path(path: str):
        if not path:
            return
        arr = OSUtils.split_path(path)
        if len(arr) > 2:
            return f'{os.sep}{arr[1]}'
        else:
            return f'{os.sep}{arr[0]}'

    @staticmethod
    def get_path_sub_name(path: str):
        """
        获取一个路径的最后一段名称
        :param path:
        :return:
        """
        if path is None:
            return None
        arr = OSUtils.split_path(path)
        if len(arr) == 0:
            return ''
        return arr[-1]

    @staticmethod
    def my_link(src, dst, file_process_mode: str = 'link'):
        """
        对文件进行转移操作，支持硬链接、复制、移动
        :param src:
        :param dst:
        :param file_process_mode:
        :return:
        """
        if file_process_mode is None or file_process_mode == 'link':
            if os.path.exists(dst):
                os.remove(dst)
            try:
                os.link(src, dst)
            except OSError as e:
                logging.error(
                    '%s to %s 硬链接失败，请检查源目录和目标目录是否跨盘符，更多硬链接知识请自行Google！' % (src, dst))
        elif file_process_mode == 'copy':
            if os.path.exists(dst):
                os.remove(dst)
            shutil.copyfile(src, dst)
        elif file_process_mode == 'move':
            shutil.move(src, dst)
        else:
            logging.info('%s to %s 什么也不做：%s' % (src, dst, file_process_mode))

    @staticmethod
    def create_if_not_exists(path, *paths):
        """
        拼接一个路径，如果不存在则自动创建
        :param path:
        :param paths:
        :return:
        """
        join_str = [path] + list(paths)
        join_str = list(filter(None, join_str))
        path = os.path.join(*join_str)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    @staticmethod
    def find_file(path, filename):
        """
        按名称查找一个路径内文件
        :param path:
        :param filename:
        :return:
        """
        if not path or not filename:
            return
        if not os.path.exists(path):
            return
        filename = str(filename).lower()
        if os.path.isfile(path):
            if str(path).lower().endswith(filename):
                return path
            else:
                return
        for p, dir_list, file_list in os.walk(path):
            for f in file_list:
                fp = os.path.join(p, f)
                if f.lower() == filename:
                    return fp
        return

    @staticmethod
    def link_folder(path: str, link_path: str, link_mode: LinkMode, ignore_file=None, filter_season=None,
                    filter_episodes=None):
        if not ignore_file:
            ignore_file = []
        if not link_mode:
            link_mode = LinkMode.LINK
        if path is None or path == '':
            return
        if not os.path.exists(path):
            return
        if not os.path.exists(link_path):
            os.makedirs(link_path)
        if isinstance(filter_episodes, str):
            filter_episodes = [int(filter_episodes)]
        elif isinstance(filter_episodes, int):
            filter_episodes = [filter_episodes]
        elif isinstance(filter_episodes, list):
            filter_episodes = [int(x) for x in filter_episodes]
        if isinstance(filter_season, str):
            filter_season = [int(filter_season)]
        elif isinstance(filter_season, int):
            filter_season = [filter_season]
        elif isinstance(filter_season, list):
            filter_season = [int(x) for x in filter_season]
        _LOGGER.info(f'开始转移文件夹 {path} 到 {link_path} 转移模式{link_mode}')
        for p in os.listdir(path):
            if p in ignore_file:
                continue
            if filter_season:
                ses = MediaParserUtils.parse_season(p)
                if ses and ses.get('text'):
                    if ses.get('start') not in filter_season:
                        continue
            if filter_episodes:
                epi = MediaParserUtils.parse_episode(p)
                if epi and epi.get('text'):
                    if epi.get('start') not in filter_episodes:
                        continue
            full_path = os.path.join(path, p)
            full_link_path = os.path.join(link_path, p)
            if os.path.isdir(full_path):
                if not os.path.exists(full_link_path):
                    os.makedirs(full_link_path)
                OSUtils.link_folder(full_path, full_link_path, link_mode, ignore_file, filter_season, filter_episodes)
            else:
                OSUtils.my_link(full_path, full_link_path, link_mode.value)

    @staticmethod
    def findfile(start, name):
        for relpath, dirs, files in os.walk(start):
            if name in files:
                full_path = os.path.join(start, relpath, name)
                return os.path.normpath(os.path.abspath(full_path))
        return

    @staticmethod
    def is_hardlink(filepath):
        sfs = os.stat(filepath)
        return sfs.st_nlink > 1

    @staticmethod
    def find_hardlink_files(source_filepath, find_path=None, use_cache: bool = True):
        if not source_filepath:
            return
        if os.path.isdir(source_filepath):
            return
        if not find_path:
            find_path = OSUtils.get_first_path(source_filepath)
        sfs = os.stat(source_filepath)
        if sfs.st_nlink <= 1:
            return
        source_ino = sfs.st_ino
        if isinstance(find_path, str):
            find_path = [find_path]
        result = []
        for path in find_path:
            if not os.path.exists(path):
                continue
            tmp = []
            ino_cache: Dict[int, List[str]] = dict()
            if use_cache and hardlink_cache.get(path):
                ino_cache = hardlink_cache.get(path)
                if source_ino in ino_cache:
                    tmp = ino_cache[source_ino]
            if not tmp:
                for root, ds, fs in os.walk(path):
                    for f in fs:
                        fp = os.path.join(root, f)
                        fs = os.stat(fp)
                        if fs.st_nlink > 1:
                            ino = fs.st_ino
                            if ino in ino_cache:
                                ino_cache[ino].append(fp)
                            else:
                                ino_cache[ino] = [fp]
                hardlink_cache.set(path, ino_cache)
                if source_ino in ino_cache:
                    tmp = ino_cache[source_ino]
            result += tmp
        return result
