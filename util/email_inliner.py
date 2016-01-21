from premailer import Premailer
from config import basedir
import os
from io import StringIO
import logging

HTML_TO_INLINE = ["review_order.html",
                  "shop_marketing.html",
                  "shop_marketing_opinew_simple.html",
                  "new_reviewer_user.html",
                  "new_shop_owner_user.html"]

def inline(html_filename,css_filename):
    inlined_html=""
    mylog = StringIO()
    myhandler = logging.StreamHandler(mylog)
    css_styles = None
    with open(os.path.join(basedir, 'email_templates_not_inlined',"css", css_filename), mode='r') as css_file:
        css_styles = css_file.read().decode('utf-8')

    css_styles_path = os.path.join(basedir, 'email_templates_not_inlined',"css", css_filename)
    with open(os.path.join(basedir, 'email_templates_not_inlined', html_filename), mode='r') as html_file:
        html_doc = html_file.read().decode('utf-8')
        print type(html_doc)
        p = Premailer(html_doc, external_styles=css_styles_path,
                      cssutils_logging_handler=myhandler, cssutils_logging_level=logging.INFO)
        inlined_html = p.transform()
        print mylog.getvalue()

    with open(os.path.join(basedir, 'webapp', 'templates','email', html_filename), mode='w') as html_file:
        html_file.write(inlined_html)

for filename in HTML_TO_INLINE:
    inline(filename, "simple.css")