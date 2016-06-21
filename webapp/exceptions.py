class ExceptionMessages(object):
    UNKNOWN_ERROR = "Unknown error occurred."

    MISSING_PARAM = 'Param {param} is missing'
    INSTANCE_NOT_EXISTS = '{instance} with id {id} does not exist'
    PARAM_NOT_INTEGER = '{param} needs to be an integer.'
    PRODUCT_NOT_WITHIN_SHOP_DOMAIN = "Product url needs to start with the shop domain: {shop_domain}"
    CAPTCHA_FAIL = 'CAPTCHA failed'
    USER_EXISTS = 'User {user_email} already exists'
    DOMAIN_NEEDED = "Sorry, we couldn't process your shop domain name. " \
                    "Are you sure it looks like one of these? " \
                    "https://www.shop.com, http://www.shop.com, www.shop.com"

    SHOPIFY_INVALID_SHOP_DOMAIN = "Invalid shop domain."
    SHOPIFY_INVALID_SHOP_NAME = "Invalid shop name."
    SHOPIFY_INCORRECT_NONCE = 'Incorrect nonce.'
    SHOPIFY_INVALID_HMAC = 'Invalid hmac.'

    NOT_YOUR_INSTANCE = "Not your {instance}"
    NOT_YOUR_SHOP = "Not your shop"
    NOT_YOUR_REVIEW = "Not your review."

    CANT_FEATURE_THAT_REVIEW = "Can't feature that review."


class RequirementException(Exception):
    def __init__(self, message, error_code, error_category):
        self.message = message
        self.error_code = error_code
        self.error_category = error_category


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
