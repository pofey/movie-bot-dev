import datetime
import decimal
from enum import Enum


class Serializable(object):
    """支持对象序列化。继承这个类，可以让自定义的对象方便序列化成json"""
    hidden_fields = []

    def get_fields(self):
        """
        返回所有字段
        :return:
        """
        return self.__dict__

    def __parse_field_value__(self, field_value):
        if isinstance(field_value, decimal.Decimal):  # Decimal -> float
            field_value = round(float(field_value), 2)
        elif isinstance(field_value, datetime.datetime):  # datetime -> str
            field_value = str(field_value)
        elif isinstance(field_value, list):
            field_value = [self.__parse_field_value__(i) for i in field_value]
        if hasattr(field_value, 'to_json'):
            field_value = field_value.to_json()
        elif isinstance(field_value, Enum):
            field_value = field_value.name
        return field_value

    def to_json(self, hidden_fields=None):
        """
        Json序列化
        :param hidden_fields: 覆盖类属性 hidden_fields
        :return:
        """

        hf = hidden_fields if hidden_fields and isinstance(hidden_fields, list) else self.hidden_fields

        model_json = {}

        for column in self.get_fields():
            if column not in hf:  # 不需要返回的字段与值
                if hasattr(self, column):
                    model_json[column] = self.__parse_field_value__(getattr(self, column))
        if '_sa_instance_state' in model_json:
            del model_json['_sa_instance_state']

        return model_json
