import logging
import os
import signal
import sys

_LOGGER = logging.getLogger(__name__)

SPID_FILE = "/app/supervisord.pid"


def kill_app(msg=None):
    """
    杀掉docker中的守护信息
    :param msg: 杀死之前打印的日志
    :return:
    """
    if msg:
        print('''
██╗    ██╗ █████╗ ██████╗ ███╗   ██╗██╗███╗   ██╗ ██████╗ 
██║    ██║██╔══██╗██╔══██╗████╗  ██║██║████╗  ██║██╔════╝ 
██║ █╗ ██║███████║██████╔╝██╔██╗ ██║██║██╔██╗ ██║██║  ███╗
██║███╗██║██╔══██║██╔══██╗██║╚██╗██║██║██║╚██╗██║██║   ██║
╚███╔███╔╝██║  ██║██║  ██║██║ ╚████║██║██║ ╚████║╚██████╔╝
 ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ''')
        print(msg)
        _LOGGER.info(msg)
    try:
        if os.path.exists(SPID_FILE):
            with open(SPID_FILE) as f:
                pid = int(f.readline()[0])
                os.kill(pid, signal.SIGKILL)
        os.kill(os.getpid(), signal.SIGKILL)
    except:
        sys.exit(1)


def version_to_number(version: str):
    if not version:
        return 0
    arr = version.split('.')
    s = ''
    if len(arr) == 1:
        s += arr[0].zfill(3)
        s += '000000'
    elif len(arr) == 2:
        s += arr[0].zfill(3)
        s += arr[1].zfill(3)
        s += '000'
    elif len(arr) == 3:
        s += arr[0].zfill(3)
        s += arr[1].zfill(3)
        s += arr[2].zfill(3)
    return int(s)
