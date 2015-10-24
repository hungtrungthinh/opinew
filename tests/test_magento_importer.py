import os
from importers import magento


basedir = os.path.abspath(os.path.dirname(__file__))

magento.products_import(os.path.join(basedir, 'test_files', 'beauty_kitchen.csv'))