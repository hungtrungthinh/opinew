from config import basedir
import os
from webapp import Constants
from premailer import Premailer


def inline_email(html_filename, css_filename="simple.css"):
    inlined_html=""
    css_styles = None
    with open(os.path.join(basedir, 'email_templates_not_inlined',"css", css_filename), mode='r') as css_file:
        css_styles = css_file.read().decode('utf-8')

    css_styles_path = os.path.join(basedir, 'email_templates_not_inlined',"css", css_filename)
    with open(os.path.join(basedir, 'email_templates_not_inlined', html_filename), mode='r') as html_file:
        html_doc = html_file.read().decode('utf-8')
        p = Premailer(html_doc, external_styles=css_styles_path,
                      include_star_selectors=True,
                      remove_classes=False)
        inlined_html = p.transform().encode('utf8')

    with open(os.path.join(basedir, 'webapp', 'templates', 'email', html_filename), mode='w') as html_file:
        html_file.write(inlined_html)


def inline_all_emails():
    for filename in Constants.HTML_TO_INLINE_FILENAMES:
        inline_email(filename)
