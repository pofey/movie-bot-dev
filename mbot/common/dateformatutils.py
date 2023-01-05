import datetime


class DateFormatUtils:
    """时间格式处理工具类"""

    @staticmethod
    def str_to_date(strdate, pattern: str) -> datetime:
        """
        字符串转时间对象
        :param strdate: 字符串时间
        :param pattern: 时间格式
        :return:
        """
        if strdate is None or strdate == '':
            return None
        return datetime.datetime.strptime(strdate, pattern)

    @staticmethod
    def parse_year_from_str(strdate, pattern: str) -> datetime:
        """
        提取字符串时间中的年份
        :param strdate:
        :param pattern:
        :return:
        """
        if strdate is None or strdate == '':
            return None
        try:
            date = datetime.datetime.strptime(strdate, pattern)
            return date.year
        except Exception as e:
            return None

    @staticmethod
    def seconds_format(time_cost: int):
        """
        耗费时间格式转换，输入秒，返回一个字符串时间
        :param time_cost:
        :return:
        """
        min = 60
        hour = 60 * 60
        day = 60 * 60 * 24
        if not time_cost or time_cost < 0:
            return ''
        elif time_cost < min:
            return '%s秒' % time_cost
        elif time_cost < hour:
            return '%s分%s秒' % (divmod(time_cost, min))
        elif time_cost < day:
            cost_hour, cost_min = divmod(time_cost, hour)
            return '%s小时%s' % (cost_hour, DateFormatUtils.seconds_format(cost_min))
        else:
            cost_day, cost_hour = divmod(time_cost, day)
            return '%s天%s' % (cost_day, DateFormatUtils.seconds_format(cost_hour))

    @staticmethod
    def date_distance_str(date1: datetime, date2: datetime):
        """
        计算两个时间的距离，返回一个格式化好的时间差字符串
        :param date1:
        :param date2:
        :return:
        """
        diff: datetime.timedelta = date1 - date2
        seconds = int(diff.total_seconds())
        if diff.seconds <= 0:
            return '0秒'
        return DateFormatUtils.seconds_format(seconds)
