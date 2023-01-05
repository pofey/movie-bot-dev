import urllib

BT_TRACKER = ['http://1337.abcvg.info:80/announce', 'http://milanesitracker.tekcities.com:80/announce',
              'http://nyaa.tracker.wf:7777/announce', 'http://open-v6.demonoid.ch:6969/announce',
              'http://open.acgnxtracker.com:80/announce', 'http://opentracker.xyz:80/announce',
              'http://share.camoe.cn:8080/announce', 'http://t.nyaatracker.com:80/announce',
              'http://t.publictracker.xyz:6969/announce', 'http://tr.cili001.com:8070/announce',
              'http://tracker.bt4g.com:2095/announce', 'http://tracker.coppersurfer.site:2710/announce',
              'http://tracker.files.fm:6969/announce', 'http://tracker.gbitt.info:80/announce',
              'http://tracker.ipv6tracker.ru:80/announce', 'http://tracker.mywaifu.best:6969/announce',
              'http://uraniumhexafluori.de:1919/announce', 'https://carbon-bonsai-621.appspot.com:443/announce',
              'https://opentracker.i2p.rocks:443/announce', 'https://tr.abiir.top:443/announce',
              'https://tr.burnabyhighstar.com:443/announce', 'https://tr.ready4.icu:443/announce',
              'https://tracker.babico.name.tr:443/announce', 'https://tracker.imgoingto.icu:443/announce',
              'https://tracker.lilithraws.cf:443/announce', 'https://tracker.nanoha.org:443/announce',
              'https://tracker.tamersunion.org:443/announce', 'https://trackme.theom.nz:443/announce',
              'udp://9.rarbg.com:2810/announce', 'udp://bt1.archive.org:6969/announce',
              'udp://exodus.desync.com:6969/announce', 'udp://fe.dealclub.de:6969/announce',
              'udp://ipv4.tracker.harry.lu:80/announce', 'udp://movies.zsw.ca:6969/announce',
              'udp://open.demonii.com:1337/announce', 'udp://open.dstud.io:6969/announce',
              'udp://open.stealth.si:80/announce', 'udp://open.tracker.cl:1337/announce',
              'udp://open.tracker.ink:6969/announce', 'udp://open.xxtor.com:3074/announce',
              'udp://opentor.org:2710/announce', 'udp://opentracker.i2p.rocks:6969/announce',
              'udp://p4p.arenabg.com:1337/announce', 'udp://public.publictracker.xyz:6969/announce',
              'udp://retracker.hotplug.ru:2710/announce', 'udp://run.publictracker.xyz:6969/announce',
              'udp://thetracker.org:80/announce', 'udp://torrentclub.space:6969/announce',
              'udp://tracker.0x.tf:6969/announce', 'udp://tracker.altrosky.nl:6969/announce',
              'udp://tracker.auctor.tv:6969/announce', 'udp://tracker.beeimg.com:6969/announce',
              'udp://tracker.birkenwald.de:6969/announce', 'udp://tracker.bitsearch.to:1337/announce',
              'udp://tracker.dler.com:6969/announce', 'udp://tracker.edkj.club:6969/announce',
              'udp://tracker.jordan.im:6969/announce', 'udp://tracker.leech.ie:1337/announce',
              'udp://tracker.lelux.fi:6969/announce', 'udp://tracker.moeking.me:6969/announce',
              'udp://tracker.monitorit4.me:6969/announce', 'udp://tracker.openbittorrent.com:6969/announce',
              'udp://tracker.openbittorrent.com:80/announce', 'udp://tracker.opentrackr.org:1337/announce',
              'udp://tracker.pomf.se:80/announce', 'udp://tracker.publictracker.xyz:6969/announce',
              'udp://tracker.theoks.net:6969/announce', 'udp://tracker.tiny-vps.com:6969/announce',
              'udp://tracker.torrent.eu.org:451/announce', 'udp://tracker.zerobytes.xyz:1337/announce',
              'udp://tracker1.bt.moack.co.kr:80/announce', 'udp://tracker2.dler.com:80/announce',
              'udp://vibe.sleepyinternetfun.xyz:1738/announce', 'udp://www.torrent.eu.org:451/announce']


class BtUtils:
    """bt资源的处理工具类"""

    @staticmethod
    def parse_url(download_url):
        """
        从bt下载链接中解析种子信息
        :param download_url: bt下载链接
        :return:
        """
        parsed = urllib.parse.urlparse(download_url)
        qs = urllib.parse.parse_qs(parsed.query)
        torrent_hash = qs.get('xt')[0].split(':')[-1]
        return {
            'torrent_hash': torrent_hash,
            'name': qs.get('dn')[0],
            'tracker': qs.get('tr')
        }

    @staticmethod
    def add_tracker(download_url):
        """
        把一些可以加速的bt tracker补充到bt下载链接中
        :param download_url:
        :return:
        """
        parsed = urllib.parse.urlparse(download_url)
        qs = urllib.parse.parse_qs(parsed.query)
        trackers: set = set(BT_TRACKER + qs['tr'])
        qs['tr'] = trackers
        qs_str = ''
        for key in qs:
            for v in qs[key]:
                qs_str += f'{key}={urllib.parse.quote_plus(v)}&'
        if qs_str:
            qs_str = qs_str.rstrip('&')
        new_url = f'{parsed.scheme}:?{qs_str}'
        return new_url
