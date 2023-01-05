class TypeUtils:
    """类型操作工具类"""

    @staticmethod
    def find_subclass_from_mod(mod, class_type):
        """
        查找模块内指定类型的第一个类
        :param mod:
        :param class_type:
        :return:
        """
        if not mod:
            return
        for key in dir(mod):
            try:
                if class_type in getattr(mod, key).__bases__:
                    return getattr(mod, key)
            except:
                continue
        return
