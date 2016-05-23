from tests import testing_constants
from config import Constants


class Fault(Exception):
    def __init__(self, message, code):
        self.message = message
        self.code = code

    def __repr__(self):
        return "<Fault %s: '%s'>" % (self.code, self.message)


class FakeMagentoAPI(object):
    class catalog_product(object):
        @staticmethod
        def list():
            return [
                {
                    'name': testing_constants.MAGENTO_PRODUCT_0_NAME,
                    'sku': testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID
                },

                {
                    'name': testing_constants.MAGENTO_PRODUCT_1_NAME,
                    'sku': testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID
                },

                {
                    'name': testing_constants.MAGENTO_PRODUCT_2_NAME,
                    'sku': testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID
                },

                {
                    'name': 'No equivalent on info',
                    'sku': 'nope'
                }
            ]

        @staticmethod
        def info(sku):
            if sku == testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID:
                return {
                    'status': Constants.MAGENTO_PRODUCT_STATUS_AVAILABLE,
                    'short_description': testing_constants.MAGENTO_PRODUCT_0_DESCRIPTION,
                    'url_key': testing_constants.MAGENTO_PRODUCT_0_URL_KEY
                }

            elif sku == testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID:
                return {
                    'status': Constants.MAGENTO_PRODUCT_STATUS_AVAILABLE,
                    'short_description': testing_constants.MAGENTO_PRODUCT_1_DESCRIPTION,
                    'url_key': testing_constants.MAGENTO_PRODUCT_1_URL_KEY
                }

            elif sku == testing_constants.MAGENTO_PRODUCT_2_PLATFORM_PRODUCT_ID:
                return {
                    'status': Constants.MAGENTO_PRODUCT_STATUS_NOT_AVAILABLE,
                    'short_description': testing_constants.MAGENTO_PRODUCT_2_DESCRIPTION,
                    'url_key': testing_constants.MAGENTO_PRODUCT_2_URL_KEY
                }
            raise Fault('Product not exists.', 101)

    class sales_order(object):
        @staticmethod
        def list():
            return [
                {  # not shipped
                    'order_id': testing_constants.MAGENTO_ORDER_0_PLATFORM_ORDER_ID,
                    'status': Constants.MAGENTO_STATUS_PROCESSING,
                    'created_at': testing_constants.MAGENTO_ORDER_0_CREATED,
                    'customer_email': testing_constants.MAGENTO_ORDER_0_EMAIL,
                    'billing_name': testing_constants.MAGENTO_ORDER_0_NAME,
                    'increment_id': testing_constants.MAGENTO_ORDER_0_INCREMENT_ID
                },
                {  # shipped
                    'order_id': testing_constants.MAGENTO_ORDER_1_PLATFORM_ORDER_ID,
                    'status': Constants.MAGENTO_STATUS_COMPLETE,
                    'created_at': testing_constants.MAGENTO_ORDER_1_CREATED,
                    'customer_email': testing_constants.MAGENTO_ORDER_1_EMAIL,
                    'billing_name': testing_constants.MAGENTO_ORDER_1_NAME,
                    'increment_id': testing_constants.MAGENTO_ORDER_1_INCREMENT_ID
                },
                {  # no items for some reason....
                    'order_id': testing_constants.MAGENTO_ORDER_2_PLATFORM_ORDER_ID,
                    'status': Constants.MAGENTO_STATUS_PROCESSING,
                    'created_at': testing_constants.MAGENTO_ORDER_2_CREATED,
                    'customer_email': testing_constants.MAGENTO_ORDER_2_EMAIL,
                    'billing_name': testing_constants.MAGENTO_ORDER_2_NAME,
                    'increment_id': testing_constants.MAGENTO_ORDER_2_INCREMENT_ID
                }
            ]

        @staticmethod
        def info(increment_id):
            if increment_id == testing_constants.MAGENTO_ORDER_0_INCREMENT_ID:
                return {
                    'items': [
                        {
                            'sku': testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID
                        }
                    ]
                }
            if increment_id == testing_constants.MAGENTO_ORDER_1_INCREMENT_ID:
                return {
                    'items': [
                        {
                            'sku': testing_constants.MAGENTO_PRODUCT_0_PLATFORM_PRODUCT_ID
                        },
                        {
                            'sku': testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID
                        },
                        {
                            'sku': testing_constants.MAGENTO_PRODUCT_1_PLATFORM_PRODUCT_ID
                        }
                    ]
                }
            if increment_id == testing_constants.MAGENTO_ORDER_2_INCREMENT_ID:
                return {
                    'items': [
                        {}
                    ]
                }
            raise Fault(message='Requested order not exists.', code=100)

    class sales_order_shipment(object):
        @staticmethod
        def list():
            return [
                {
                    'created_at': testing_constants.MAGENTO_ORDER_1_SHIPPED,
                    'increment_id': testing_constants.MAGENTO_ORDER_1_SHIPMENT_INCREMENT_ID,
                }
            ]

        @staticmethod
        def info(increment_id):
            if increment_id == testing_constants.MAGENTO_ORDER_1_SHIPMENT_INCREMENT_ID:
                return {
                    'created_at': testing_constants.MAGENTO_ORDER_1_SHIPPED,
                    'order_id': testing_constants.MAGENTO_ORDER_1_PLATFORM_ORDER_ID
                }
            raise Fault(message='Requested shipment not exists.', code=100)
