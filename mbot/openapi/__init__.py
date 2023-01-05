from typing import Dict, Union, List

from moviebotapi import MovieBotServer

from mbot.external.mediaserver import MediaServer, MediaServerProxy


class MediaServerManager:
    def __init__(self):
        self._default_name = None
        self._servers: Dict[str, Union[MediaServer, MediaServerProxy]] = dict()
        self._master_plex = None
        self._master_emby = None
        self._master_jellyfin = None

    def set_default_name(self, name: str):
        self._default_name = name

    @property
    def master(self) -> Union[MediaServer, MediaServerProxy]:
        return self._servers.get(self._default_name)

    def _filter_server(self, type_: str):
        res = []
        for item in self._servers.values():
            if item.server_type == type_:
                res.append(item)
        return res

    @staticmethod
    def _get_first_master(items):
        if not items:
            return
        for item in items:
            if item.server_config.get('master_server'):
                return item
        return

    @property
    def master_emby(self) -> Union[MediaServer, MediaServerProxy, None]:
        if self._master_emby:
            return self._master_emby
        res = self._filter_server('emby')
        server = self._get_first_master(res)
        if not server and res:
            server = res[0]
        self._master_emby = server
        return server

    @property
    def master_plex(self) -> Union[MediaServer, MediaServerProxy, None]:
        if self._master_plex:
            return self._master_plex
        res = self._filter_server('plex')
        server = self._get_first_master(res)
        if not server and res:
            server = res[0]
        self._master_plex = server
        return server

    @property
    def master_jellyfin(self) -> Union[MediaServer, MediaServerProxy, None]:
        if self._master_jellyfin:
            return self._master_jellyfin
        res = self._filter_server('jellyfin')
        server = self._get_first_master(res)
        if not server and res:
            server = res[0]
        self._master_jellyfin = server
        return server

    @property
    def all(self) -> List[Union[MediaServer, MediaServerProxy]]:
        return list(self._servers.values())

    def get(self, name: str):
        return self._servers.get(name)

    def get_server_types(self) -> List[str]:
        result = []
        for name in self._servers:
            result.append(self._servers.get(name).server_type)
        return result

    def put(self, name: str, server: Union[MediaServer, MediaServerProxy]):
        self._servers.update({name: server})


mbot_api: MovieBotServer = MovieBotServer()

media_server_manager: MediaServerManager = MediaServerManager()
