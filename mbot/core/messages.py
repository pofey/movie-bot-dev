"""系统内队列、跨线程通信的模型类，部分文件可能再将来重构"""
from mbot.common.serializable import Serializable
from mbot.core.task import TaskStatus


class WaitExponential(Serializable):
    def __init__(self, multiplier, min, max):
        self.multiplier = int(multiplier)
        self.min = int(min)
        self.max = int(max)

    multiplier: int = 1
    min: int = 1
    max: int = 0


class ChangeTaskMetaMessage(Serializable):
    def __init__(self, task_id, change_status):
        self.task_id = int(task_id)
        self.change_status = change_status

    task_id: int
    change_status: TaskStatus


class DeferTaskMessage(Serializable):
    def __init__(self, task_id, wait_minutes=None, wait_exponential: WaitExponential = None,
                 stop_after_attempt=None,
                 stop_after_delay_minutes=None):
        self.task_id = task_id
        self.wait_minutes = wait_minutes
        self.wait_exponential = wait_exponential
        self.stop_after_attempt = stop_after_attempt
        self.stop_after_delay_minutes = stop_after_delay_minutes

    task_id: int
    wait_minutes: int = None
    wait_exponential: WaitExponential = None
    stop_after_attempt: int = None
    stop_after_delay_minutes: int = None


class DownloadSubtitleMediaInfo(Serializable):
    tmdb_id: int = None
    type: str = None
    name: str = None
    year: int = None
    season_year: int = None
    season_index: int = None
    episodes: str = None


class DownloadSubtitleMessage(Serializable):
    task_id: int = None
    content_path: str = None
    media_info: DownloadSubtitleMediaInfo = None
