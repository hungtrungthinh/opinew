class ExceptionMessages(object):
    MISSING_PARAM = 'Param %s is missing'
    CAPTCHA_FAIL = 'CAPTCHA failed'
    USER_EXISTS = 'User %s already exists'
    DOMAIN_NEEDED = "Sorry, we couldn't process your shop domain name. " \
                    "Are you sure it looks like one of these? " \
                    "https://www.shop.com, http://www.shop.com, www.shop.com"


class ResponseException(Exception):
    def __init__(self, message=None, status_code=None):
        super(Exception, self).__init__(message)
        self.status_code = status_code


class ParamException(ResponseException):
    pass


class DbException(ResponseException):
    pass


class UserExistsException(ResponseException):
    pass


class ApiException(ResponseException):
    pass


class MagentoException(ResponseException):
    pass


class ProductNotFoundException(Exception):
    pass
