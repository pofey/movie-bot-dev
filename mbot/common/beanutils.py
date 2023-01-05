from typing import Optional


class BeanUtils:
    @staticmethod
    def if_attr_not_none_than_copy(source: object, target: object) -> Optional[object]:
        if not source:
            return target
        if not target:
            return
        for key in source.__dict__:
            if hasattr(target, key):
                val = getattr(source, key)
                if val:
                    setattr(target, key, val)
        return target
