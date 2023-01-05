import os


class DownloadUtils:
    """下载相关工具类，此类待重构"""

    @staticmethod
    def get_save_mode(save_mode: list, conditions: dict):
        if save_mode is None:
            return
        if save_mode is None or len(save_mode) == 0:
            return
        for mode in save_mode:
            mode_keys: list = list(conditions.keys())
            none_cnt = 0
            total_eq_cnt = 0
            for k in mode_keys:
                if mode.get(k):
                    if isinstance(mode[k], list):
                        val = mode[k]
                    else:
                        val = [mode[k]]
                    val = list(filter(None, val))
                    if len(val) == 0:
                        continue
                    eq_cnt = 0
                    compare_val = conditions[k]
                    for v in val:
                        if v == '':
                            continue
                        if isinstance(compare_val, str) and v == compare_val:
                            eq_cnt += 1
                        elif isinstance(compare_val, list) and v in compare_val:
                            eq_cnt += 1
                    if k == 'area':
                        # or 匹配模式
                        if eq_cnt >= 1:
                            total_eq_cnt += 1
                    else:
                        # and 匹配模式
                        if eq_cnt == len(val):
                            total_eq_cnt += 1
                else:
                    none_cnt += 1
            if len(conditions) - none_cnt == total_eq_cnt:
                return mode['download_path'] if 'download_path' in mode else None
        return

    @staticmethod
    def rstrip_path(path):
        if not path:
            return
        if path.find('\\') != -1:
            trim_save_path = path.rstrip('\\')
        else:
            trim_save_path = path.rstrip(os.sep)
        return trim_save_path
