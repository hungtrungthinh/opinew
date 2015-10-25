from csv_utf_support import CSVUnicodeReader

def products_import(file_path):
    products = []
    with open(file_path) as f:
        csv_reader = CSVUnicodeReader(f, lineterminator='\n')
        headers = csv_reader.next()
        headers_count = {k:0 for k in headers}
        for line in csv_reader:
            product = {}
            for j, cell in enumerate(line):
                if cell:
                    headers_count[headers[j]] += 1
                product[headers[j]] = cell
            products.append(product)
    return products
