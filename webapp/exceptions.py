class ResponseException(Exception):
    def __init__(self, message=None, status_code=None):
        super(Exception, self).__init__(message)
        self.status_code = status_code


class ParamException(ResponseException):
    pass


class DbException(ResponseException):
    pass


class ApiException(ResponseException):
    pass