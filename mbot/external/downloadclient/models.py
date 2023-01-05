import asyncio
import datetime
import hashlib
import logging
import os.path
import time
from abc import ABCMeta, abstractmethod
from typing import List

import aria2p
import bencoder
import qbittorrentapi
import requests
import transmission_rpc
from qbittorrentapi import TorrentInfoList

from mbot.common.magnet2torrent import Magnet2Torrent
from mbot.common.serializable import Serializable
from mbot.core.health import HealthIndicator, Health


class ClientTorrent(Serializable):
    hash: str = None
    name: str = None
    save_path: str = None
    content_path: str = None
    size: int = None
    size_str: str = None
    dlspeed: int = None
    dlspeed_str: str = None
    upspeed: int = None
    upspeed_str: str = None
    progress: float = None
    uploaded: int = None
    uploaded_str: str = None
    downloaded: int = None
    downloaded_str: str = None
    seeding_time: int = None
    ratio: float = None
    tracker: str = None


class DownloadClient(metaclass=ABCMeta):
    @abstractmethod
    def download_from_file(self, torrent_filepath: str, savepath: str, category: str = None) -> bool:
        pass

    @abstractmethod
    def download_from_url(self, url: str, savepath: str, category: str = None) -> bool:
        pass

    @abstractmethod
    def exists(self, torrent_filepath):
        pass

    @abstractmethod
    def completed_torrents(self) -> dict:
        pass

    @abstractmethod
    def download_torrents(self) -> dict:
        pass

    @abstractmethod
    def exists_hash(self, torrent_hash: str) -> bool:
        pass

    @abstractmethod
    def get_by_hash(self, torrent_hash: str) -> ClientTorrent:
        pass

    @abstractmethod
    def delete(self, torrent_hash):
        pass

    @abstractmethod
    def torrents(self) -> List[ClientTorrent]:
        pass

    @abstractmethod
    def move(self, torrent_hash, save_path, category: str = None):
        pass

    @abstractmethod
    def transfer_info(self) -> dict:
        pass

    @staticmethod
    def __size_format__(byte_size: int):
        if byte_size is None or byte_size == 0:
            return '0'
        if byte_size < 1048576:
            return f'{round(byte_size / 1024, 2)} KB'
        elif byte_size < 1073741824:
            return f'{round(byte_size / 1024 / 1024, 2)} MB'
        elif byte_size < 1099511627776:
            return f'{round(byte_size / 1024 / 1024 / 1024, 2)} GB'
        elif byte_size < 1125899906842624:
            return f'{round(byte_size / 1024 / 1024 / 1024 / 1024, 2)} TB'

    @staticmethod
    def info_hash(torrent_file):
        try:
            with open(torrent_file, "rb") as f:
                decoded_dict = bencoder.decode(f.read())
                info_hash = hashlib.sha1(bencoder.encode(decoded_dict[b"info"])).hexdigest()
            return info_hash
        except Exception as e:
            logging.error('获取种子hash失败：%s' % torrent_file)
            raise e


class QbittorrentClient(DownloadClient):
    def download_from_url(self, url: str, savepath: str, category: str = None) -> bool:
        r = self.qb.torrents_add(urls=url, save_path=savepath, category=category,
                                 use_auto_torrent_management=True if category else False)
        return 'Ok.' == r

    def transfer_info(self) -> dict:
        try:
            info = self.qb.transfer_info()
            return {'dl_speed': info.get('dl_info_speed'), 'up_speed': info.get('up_info_speed')}
        except Exception as e:
            return

    def move(self, torrent_hash, save_path, category: str = None):
        try:
            self.qb.torrents_set_location(location=save_path, torrent_hashes=torrent_hash)
            if category:
                self.qb.torrents_set_category(category=category, torrent_hashes=torrent_hash)
        except qbittorrentapi.exceptions.LoginFailed as e:
            logging.info('qbit登陆过期，开始自动重新自动登陆。')
            self.login()
            return self.move(torrent_hash, save_path, category)

    def __init__(self, url: str, need_login: bool = False, username: str = None, password: str = None,
                 test: bool = False):
        self.need_login = need_login
        self.username = username
        self.password = password
        try:
            self.qb = qbittorrentapi.Client(
                host=url,
                username=username,
                password=password,
            )
            self.login()
        except requests.exceptions.ConnectionError as ce:
            raise RuntimeError('连接失败，请检查访问地址有效性或容器网络与qbit是否可通信')
        except qbittorrentapi.LoginFailed as e:
            raise RuntimeError('必须登陆才可以访问')

    def torrents(self) -> List[ClientTorrent]:
        try:
            tt = self.qb.torrents_info()
            if not tt:
                return []
            result = []
            for t in tt:
                result.append(self.__trans_model__(t))
            return result
        except qbittorrentapi.exceptions.LoginFailed as e:
            self.login()
            return self.torrents()

    def __trans_model__(self, t):
        ct = ClientTorrent()
        ct.name = t['name']
        ct.hash = t['hash']
        ct.save_path = t['save_path']
        if 'content_path' in t:
            ct.content_path = os.path.join(t['content_path'])
        else:
            ct.content_path = os.path.join(t['save_path'], t['name'])
        ct.progress = round(t['progress'] * 100, 2)
        ct.size = t['size']
        ct.size_str = self.__size_format__(t['size'])
        ct.dlspeed = t['dlspeed']
        ct.dlspeed_str = self.__size_format__(t['dlspeed'])
        ct.upspeed = t['upspeed']
        ct.upspeed_str = self.__size_format__(t['upspeed'])
        ct.uploaded = t['uploaded']
        ct.uploaded_str = self.__size_format__(t['uploaded'])
        if 'seeding_time' in t:
            ct.seeding_time = t.get('seeding_time')
        elif 'completion_on' in t:
            if t.get('completion_on') <= 0:
                ct.seeding_time = 0
            else:
                ct.seeding_time = round(time.time() - t.get('completion_on'))
        else:
            logging.error('无法通过下载器获取准确做种时间，尽快升级下载器版本把。')
            ct.seeding_time = 0
        ct.downloaded = t['downloaded']
        ct.downloaded_str = self.__size_format__(t['downloaded'])
        ct.ratio = t['ratio']
        if 'tracker' in t:
            ct.tracker = t['tracker']
        return ct

    def delete(self, torrent_hash):
        self.qb.torrents_delete(delete_files=True, torrent_hashes=torrent_hash)

    def get_by_hash(self, torrent_hash: str) -> ClientTorrent:
        try:
            torrents: TorrentInfoList = self.qb.torrents_info(torrent_hashes=torrent_hash)
            if not torrents:
                return
            return self.__trans_model__(torrents[0])
        except qbittorrentapi.exceptions.LoginFailed as e:
            logging.info('qbit登陆过期，开始自动重新自动登陆。')
            self.login()
            return self.get_by_hash(torrent_hash)

    def download_torrents(self) -> dict:
        try:
            result: dict = {}
            for t in self.qb.torrents_info(status_filter='downloading'):
                result[t['hash']] = self.__trans_model__(t)
            return result
        except qbittorrentapi.exceptions.LoginFailed as e:
            self.login()
            return self.download_torrents()

    def exists_hash(self, torrent_hash: str) -> ClientTorrent:
        try:
            torrents_in_qbit = list(filter(lambda x: x['hash'] == torrent_hash, self.qb.torrents_info()))
            return len(torrents_in_qbit) > 0
        except qbittorrentapi.exceptions.LoginFailed as e:
            self.login()
            return self.exists_hash(torrent_hash)

    def completed_torrents(self) -> dict:
        try:
            result: dict = {}
            for t in self.qb.torrents_info(filter='completed'):
                result[t['hash']] = self.__trans_model__(t)
            return result
        except qbittorrentapi.exceptions.LoginFailed as e:
            self.login()
            return self.completed_torrents()

    def login(self):
        self.qb.auth_log_in()

    def exists(self, torrent_filepath):
        try:
            thash = self.info_hash(torrent_filepath)
            return self.exists_hash(thash)
        except qbittorrentapi.exceptions.LoginFailed as e:
            self.login()
            return self.exists(torrent_filepath)

    def download_from_file(self, torrent_filepath: str, savepath: str, category: str = None) -> bool:
        try:
            with open(torrent_filepath, 'rb') as f:
                dr = self.qb.torrents_add(torrent_files=f, save_path=savepath, category=category,
                                          use_auto_torrent_management=True if category else False,
                                          is_paused=False)
            return 'Ok.' == dr
        except qbittorrentapi.exceptions.LoginFailed as e:
            self.login()
            return self.download_from_file(torrent_filepath, savepath, category)


class TransmissionClient(DownloadClient):
    def download_from_url(self, url: str, savepath: str, category: str = None) -> bool:
        try:
            import tempfile
            filepath = os.path.join(tempfile.gettempdir(), "%s.torrent" % time.time())

            async def fetch_that_torrent():
                m2t = Magnet2Torrent(url)
                filename, torrent_data = await m2t.retrieve_torrent()
                with open(filepath, 'wb') as file:
                    file.write(torrent_data)

            asyncio.run(fetch_that_torrent())
            return self.download_from_file(filepath, savepath, category)
        except Exception as e:
            logging.info('磁力链转换为种子失败：%s' % url)
            return False

    def transfer_info(self) -> dict:
        try:
            session = self.client.session_stats()
            return {'dl_speed': session.downloadSpeed, 'up_speed': session.uploadSpeed}
        except Exception as e:
            return

    def move(self, torrent_hash, save_path, category: str = None):
        self.client.move_torrent_data(torrent_hash, save_path)

    def __trans_model__(self, t):
        ct = ClientTorrent()
        ct.name = t.name
        ct.hash = t.hashString
        ct.save_path = t.download_dir
        ct.content_path = os.path.join(t.download_dir, t.name)
        ct.progress = t.progress
        ct.dlspeed = t.rateDownload
        ct.dlspeed_str = self.__size_format__(t.rateDownload)
        ct.upspeed = t.rateUpload
        ct.upspeed_str = self.__size_format__(t.rateUpload)
        ct.size = t.total_size
        ct.size_str = self.__size_format__(t.total_size)
        ct.uploaded = t.uploadedEver
        ct.uploaded_str = self.__size_format__(t.uploadedEver)
        ct.downloaded = t.downloadedEver
        ct.downloaded_str = self.__size_format__(t.downloadedEver)
        if t.uploadRatio:
            ct.ratio = t.uploadRatio
        else:
            ct.ratio = 0
        if t.date_done:
            naive = t.date_done.replace(tzinfo=None)
            ct.seeding_time = round((datetime.datetime.now() - naive).total_seconds())
        else:
            ct.seeding_time = 0
        return ct

    def torrents(self) -> List[ClientTorrent]:
        try:
            result = []
            for t in self.client.get_torrents():
                ct = self.__trans_model__(t)
                result.append(ct)
            return result
        except Exception as e:
            logging.error('获取tr完成种子信息出错，但暂时不会影响机器人运行。', exc_info=True)
            return []

    def delete(self, torrent_hash):
        self.client.remove_torrent(torrent_hash, True)

    def get_by_hash(self, torrent_hash: str) -> ClientTorrent:
        try:
            t = self.client.get_torrent(torrent_hash)
            return self.__trans_model__(t)
        except KeyError as ke:
            return
        except Exception as e:
            raise e

    def download_torrents(self) -> dict:
        try:
            result: dict = {}
            for t in self.client.get_torrents():
                if t.status not in ['download pending', 'downloading', 'stopped']:
                    continue
                ct = self.__trans_model__(t)
                result[ct.hash] = ct
            return result
        except Exception as e:
            logging.error('获取tr完成种子信息出错，但暂时不会影响机器人运行。', exc_info=True)
            return {}

    def exists_hash(self, torrent_hash: str) -> bool:
        try:
            t = self.client.get_torrent(torrent_hash)
            return t is not None
        except KeyError as ke:
            return False
        except Exception as e:
            raise e

    def completed_torrents(self) -> dict:
        try:
            result: dict = {}
            for t in self.client.get_torrents():
                if t.status in ['download pending', 'downloading', 'stopped']:
                    continue
                ct = self.__trans_model__(t)
                result[ct.hash] = ct
            return result
        except Exception as e:
            logging.error('获取tr完成种子信息出错，但暂时不会影响机器人运行。', exc_info=True)
            return {}

    def exists(self, torrent_filepath):
        hash = self.info_hash(torrent_filepath)
        torrents_in_qbit = list(filter(lambda x: x.hashString == hash, self.client.get_torrents()))
        return len(torrents_in_qbit) > 0

    def __init__(self, host: str, port: int, username: str, password: str):
        host = str(host)
        if port:
            port = int(str(port))
        else:
            port = 80
        if username is not None:
            username = str(username)
        if password is not None:
            password = str(password)
        try:
            self.client = transmission_rpc.Client(host=host, port=port, username=username, password=password)
        except requests.exceptions.ConnectionError as ce:
            raise RuntimeError('连接失败，请检查访问地址有效性或容器网络与tr是否可通信')
        except transmission_rpc.error.TransmissionAuthError as ae:
            raise RuntimeError('需要正确登陆才能访问，请检查账号密码是否正确')

    def download_from_file(self, torrent_filepath: str, savepath: str, category: str = None) -> bool:
        with open(torrent_filepath, 'rb') as f:
            return self.client.add_torrent(f, download_dir=savepath) is not None


class Aria2(DownloadClient):
    client = None

    def __init__(self, host, port, secret):
        self.client = aria2p.API(
            aria2p.Client(
                host="http://%s" % host,
                port=int(port),
                secret=str(secret)
            )
        )

    def __trans_model__(self, t):
        ct = ClientTorrent()
        ct.name = t.name
        ct.hash = t.info_hash
        ct.save_path = str(t.dir)
        ct.content_path = os.path.join(ct.save_path, t.name)
        ct.progress = round(t.progress, 2)
        ct.dlspeed = t.download_speed
        ct.dlspeed_str = self.__size_format__(ct.dlspeed)
        ct.upspeed = t.upload_speed
        ct.upspeed_str = self.__size_format__(ct.upspeed)
        ct.size = t.total_length
        ct.size_str = self.__size_format__(ct.size)
        ct.uploaded = t.upload_length
        ct.uploaded_str = self.__size_format__(ct.uploaded)
        ct.downloaded = t.completed_length
        ct.downloaded_str = self.__size_format__(ct.downloaded)
        try:
            ct.ratio = round(t.upload_length / t.total_length, 2)
        except:
            ct.ratio = 0
        ct.seeding_time = 0
        return ct

    def download_from_file(self, torrent_filepath: str, savepath: str, category: str = None) -> bool:
        r = self.client.add_torrent(torrent_filepath, [], {'dir': savepath})
        if not r:
            return False
        return r.status and r.status != 'error'

    def download_from_url(self, url: str, savepath: str, category: str = None) -> bool:
        r = self.client.add_magnet(url, {'dir': savepath})
        if not r:
            return False
        return r.status and r.status != 'error'

    def exists(self, torrent_filepath):
        info_hash = self.info_hash(torrent_filepath)
        return self.exists_hash(info_hash)

    def completed_torrents(self) -> dict:
        downloads = self.client.get_downloads()
        result: dict = {}
        for t in downloads:
            if not t.following_id:
                continue
            if t.status not in ['error', 'complete']:
                continue
            model = self.__trans_model__(t)
            result[model.hash] = model
        return result

    def download_torrents(self) -> dict:
        downloads = self.client.get_downloads()
        result: dict = {}
        for t in downloads:
            if t.status in ['error', 'complete']:
                continue
            model = self.__trans_model__(t)
            if model.hash in result:
                if t.following_id:
                    result[model.hash] = model
            else:
                result[model.hash] = model
        return result

    def exists_hash(self, torrent_hash: str) -> bool:
        result = list(filter(lambda x: x.info_hash == torrent_hash,
                             self.client.get_downloads()))
        if result and len(result) >= 2:
            # 大于2个可能是存在metadata下载任务，则排除掉
            result = list(filter(lambda x: x.following_id, result))
        if result:
            return True
        else:
            return False

    def get_by_hash(self, torrent_hash: str) -> ClientTorrent:
        result = list(filter(lambda x: x.info_hash == torrent_hash,
                             self.client.get_downloads()))
        if result and len(result) >= 2:
            # 大于2个可能是存在metadata下载任务，则排除掉
            result = list(filter(lambda x: x.following_id, result))
        if result:
            return self.__trans_model__(result[0])
        else:
            return

    def delete(self, torrent_hash):
        result = list(filter(lambda x: x.info_hash == torrent_hash,
                             self.client.get_downloads()))
        if not result:
            return
        self.client.remove(result, force=True, files=True, clean=True)

    def torrents(self) -> List[ClientTorrent]:
        torrents = self.client.get_downloads()
        if not torrents:
            return []
        result = []
        for t in torrents:
            if not t.following_id:
                continue
            result.append(self.__trans_model__(t))
        return result

    def move(self, torrent_hash, save_path, category: str = None):
        raise NotImplementedError

    def transfer_info(self) -> dict:
        stats = self.client.get_stats()
        return {'dl_speed': stats.download_speed, 'up_speed': stats.upload_speed}


class DownloadClientHealthIndicator(HealthIndicator):
    client: DownloadClient = None

    def __init__(self, service_name, client: DownloadClient):
        super().__init__('DownloadClient', service_name)
        self.client = client

    def health(self) -> Health:
        if not self.client:
            return Health.down()
        try:
            session = self.client.transfer_info()
            if session:
                return Health.up()
            else:
                return Health.down()
        except:
            return Health.down()
