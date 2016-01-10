import csv


def save_leads_from_memory(reviews):
    with open("", 'w') as f:
        header = ["source","date","stars","review","messaged"]
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        for review in reviews:
            writer.writerow([])

