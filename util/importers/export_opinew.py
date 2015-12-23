import csv


def save_leads_from_memory(reviews):
    with open("leads2.csv", 'w') as f:
        header = ["shop_name","shopify_shop_url",
                  "shop_url","tld","source","date","stars","review","messaged"]
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        for review in reviews:
            writer.writerow([lead['shop_name'], lead['shopify_shop_url'], lead['shop_url'], lead['tld'],
                            lead['source'], lead['date'], lead['stars'], lead['review'], lead['messaged']])

