from mbot.external.mediaserver import PlexMediaServer

plex = PlexMediaServer(url='http://192.168.1.50:32400', token='xxx')


def test_get_episodes_from_tmdbid():
    items = plex.get_episodes_from_tmdbid(60059, 1)
    print(len(items))
