import threading

local_var = threading.local()


class LocalContext:
    """同线程可读取到的上下文变量管理器"""
    def __init__(self, name: str):
        self.name = name

    def __getattr__(self, attr):
        if not hasattr(local_var, self.name):
            raise TypeError()
        obj = getattr(local_var, self.name)
        return getattr(obj, attr)
