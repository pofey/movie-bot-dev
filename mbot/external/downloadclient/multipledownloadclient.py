from concurrent.futures import ThreadPoolExecutor

from tenacity import wait_fixed, retry, stop_after_attempt

from mbot.external.downloadclient import DownloadClientInstance


class _MultipleDownloadClient:
    def __init__(self):
        self.client_thread_pool = ThreadPoolExecutor(max_workers=max(len(DownloadClientInstance), 1))

    @retry(wait=wait_fixed(3), stop=stop_after_attempt(3))
    def get_torrents(self, client_list=None):
        if client_list is None:
            client_list = DownloadClientInstance
        if not client_list:
            return []
        futures = []
        for client in client_list:
            futures.append(self.client_thread_pool.submit(client.torrents))
        torrents: list = list()
        for f in futures:
            res = f.result()
            torrents += res
        return torrents

    @retry(wait=wait_fixed(3), stop=stop_after_attempt(3))
    def get_completed_torrents(self, client_list=None):
        if client_list is None:
            client_list = DownloadClientInstance
        if not client_list:
            return []
        futures = []
        for client in client_list:
            futures.append(self.client_thread_pool.submit(client.completed_torrents))
        torrents: dict = dict()
        for f in futures:
            res = f.result()
            torrents.update(res)
        return torrents

    @retry(wait=wait_fixed(3), stop=stop_after_attempt(3))
    def get_downloading_torrent(self, client_list=None):
        if client_list is None:
            client_list = DownloadClientInstance
        if not client_list:
            return {}
        futures = []
        for client in client_list:
            futures.append(self.client_thread_pool.submit(client.download_torrents))
        torrents: dict = dict()
        for f in futures:
            res = f.result()
            torrents.update(res)
        return torrents

    @retry(wait=wait_fixed(3), stop=stop_after_attempt(3))
    def exists_hash(self, info_hash, client_list=None):
        if client_list is None:
            client_list = DownloadClientInstance
        if not client_list:
            return False
        futures = []
        for client in client_list:
            futures.append(self.client_thread_pool.submit(client.exists_hash, info_hash))
        result = False
        for f in futures:
            res = f.result()
            if res:
                result = True
                break
        return result

    @retry(wait=wait_fixed(3), stop=stop_after_attempt(3))
    def get_torrent_by_info_hash(self, info_hash, client_list=None):
        if client_list is None:
            client_list = DownloadClientInstance
        if not client_list:
            return
        futures = []
        for client in client_list:
            futures.append(self.client_thread_pool.submit(client.get_by_hash, info_hash))
        result = None
        for f in futures:
            res = f.result()
            if res:
                result = res
                break
        return result

    @retry(wait=wait_fixed(3), stop=stop_after_attempt(3))
    def delete_torrent_by_info_hash(self, info_hash, client_list=None):
        if client_list is None:
            client_list = DownloadClientInstance
        if not client_list:
            return False
        for client in client_list:
            self.client_thread_pool.submit(client.delete, info_hash)


MultipleDownloadClient = _MultipleDownloadClient()
