from webapp import create_app, models, db
from pprint import pprint
import ast

app = create_app('production')
app.app_context().push()

rr_tokens = []
for es in models.SentEmail.query.all():
    tctx = ast.literal_eval(es.template_ctx)
    for rr in tctx['review_requests']:
        rr_tokens.append(rr['token'])

orders = {}
for rr in models.ReviewRequest.query.all():
    d = {'rid': rr.id, 'rpid': rr.for_product_id, 's': 1 if rr.token in rr_tokens else 0}
    if rr.for_order_id in orders:
        orders[rr.for_order_id]['rr'].append(d)
    else:
        orders[rr.for_order_id] = {'rr': [d], 'p': [p.id for p in rr.for_order.products]}

ilo = {}
for oid, od in orders.iteritems():
    if not len(od['p']) == len(od['rr']):
        ilo[oid] = od

pprint(ilo)


# TODO: delete rid 1181, 1196, 1198, 1199, 1197, 1207, 1209
# for rid in [1181, 1196, 1198, 1199, 1197, 1207, 1209]:
#     rr = models.ReviewRequest.query.filter_by(id=rid).first()
#     db.session.delete(rr)
#
# db.session.commit()