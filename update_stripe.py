import stripe

cuss = ["cus_8DluudWALvXIBI", "cus_8DM4q3w32JUyS2", "cus_8CFMMIprdhs2LV", "cus_8BOrzzX0OTmVHB", "cus_8B8vkSGufK0cvG", "cus_8B7S2Jdg2I2MUA", "cus_8Ae9dqyOC417g5", "cus_893Lye6MF4USPw", "cus_88ztPjwSvapeYr", "cus_88rvaWWE8Hk3Wc", "cus_88fZle3z9YvIoN", "cus_87bQqoVpDFFytx", "cus_87WOcslBc7OE6A", "cus_86upAkr3ksZ28V", "cus_86J6JJ2SeNED1k", "cus_85wVeCZeMJRz6h", "cus_85obQW5mluwqDx", "cus_85Bf8yL76vDEfx", "cus_85BWRAg13WZLlH", "cus_83qp9unpwsWpFd", "cus_83mb3FL1GaO5Qz", "cus_83ZxtbSJmyInmI", "cus_83TTUr0dx2j69e", "cus_82ef2IB8h88JAR", "cus_82VnsIEtIPW3I4"]

subs = ["sub_8Dlu0aHZHZLWRC", "sub_8DM4i5T6h8xEjs", "sub_8CFMBuNMJneVtw", "sub_8BOrR8jwxv74kr", "sub_8B8vSJJaBFqD6A", "sub_8B7STkGpRCZIeo", "sub_8Ae909BuTvDZGp", "sub_893Lh9UesVumqw", "sub_88zteRvhSnPjNz", "sub_88rvHk6sFLd2JN", "sub_88fZphONRbFiCT", "sub_87bQrmnXPCycp8", "sub_87WO4dZs3RIlqe", "sub_86upX2wnE3JDjE", "sub_86J6aQCgU3xbEp", "sub_85wVIj1qbtfeHR", "sub_85ob0iV1poBwkr", "sub_85Bf2NvOxFQ5Jk", "sub_85BWBz8vuHvOcB", "sub_83qpyxlnxzfO2g", "sub_83mbhyyUBUVirp", "sub_83Zx1fWrAMcBmR", "sub_83TTdkYtrVzV6m", "sub_82efxIrTsxQPvU", "sub_82VnH4yBoLrSd0"]

zipped = zip(cuss, subs)

stripe.api_key = "sk_live_8iunlCLS7QlJGvXNuRambN3y"

for customer_id, subscription_id in zipped:
    customer = stripe.Customer.retrieve(customer_id)
    customer.subscriptions.retrieve(subscription_id).delete()