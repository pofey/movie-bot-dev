class MovieBotException(Exception):
    pass


class IllegalAccessException(MovieBotException):
    pass


class IPLimitException(MovieBotException):
    pass


class SettingErrorException(MovieBotException):
    pass


class MediaServerErrorException(MovieBotException):
    pass


class DownloadClientErrorException(MovieBotException):
    pass


class RateLimitException(MovieBotException):
    pass


class OCRError(MovieBotException):
    pass


class UnsupportedOperationException(MovieBotException):
    pass


class DownloadErrorException(MovieBotException):
    pass


class NotFoundDownloadPathException(DownloadErrorException):
    pass


class SiteErrorException(MovieBotException):
    pass


class PluginsErrorException(MovieBotException):
    pass


class PluginNotSupportException(PluginsErrorException):
    pass


class PluginNotFoundException(PluginsErrorException):
    def __init__(self, plugin_name: str, *args):
        super().__init__(*args)
        self.plugin_name = plugin_name


class ParameterErrorException(MovieBotException):
    pass


class InvalidParameterException(ParameterErrorException):
    def __init__(self, param_name: str, *args):
        super().__init__(*args)
        self.param_name: str = param_name


class MediaFileError(MovieBotException):
    pass
