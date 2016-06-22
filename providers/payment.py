import stripe
from flask import current_app
from config import Constants



class StripeAPI():
    #TODO 2 functions below were moved to StripeOpinewAdapter but we still have to check if they were used somewhere before nd refctor there to point to StripeOpinewAdapter
    def create_token(self, number, cvc, exp_month, exp_year):
        return self.stripe_proxy.Token.create(
            card={
                "number": number,
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvc": cvc
            },
        )

    def charge_customer_once(self, customer_id, charge_in_cents):
        # Charge the Customer instead of the card
        self.stripe_proxy.Charge.create(
            amount=charge_in_cents,
            currency=Constants.CURRENCY,
            customer=customer_id  # Previously stored, then retrieved
        )

    # def __init__(self):
    #     # Set your secret key: remember to change this to your live secret key in production
    #     # See your keys here https://dashboard.stripe.com/account/apikeys
    #     self.stripe_proxy = stripe
    #     if current_app.config.get('TESTING'):
    #         self.stripe_proxy.api_base = Constants.VIRTUAL_SERVER + '/vstripe'
    #     self.stripe_proxy.api_key = current_app.config.get('STRIPE_API_KEY')

    def create_customer(self, opinew_customer_email):
        # Create a Stripe Customer
        stripe_customer = self.stripe_proxy.Customer.create(
            email=opinew_customer_email,
            description=opinew_customer_email
        )
        return stripe_customer.id

    def create_paying_customer(self, opinew_customer, stripe_token):
        # Get the credit card details submitted by the form
        # Update the Stripe Customer
        stripe_customer = self.stripe_proxy.Customer.retrieve(opinew_customer.stripe_customer_id)
        if stripe_customer and 'deleted' not in stripe_customer:
            stripe_customer.source = stripe_token
            stripe_customer.save()

        has_customer_entered_card = stripe_customer and 'sources' in stripe_customer and \
            'data' in stripe_customer.sources and type(stripe_customer.sources.data) is list and \
            len(stripe_customer.sources.data) > 0 and 'last4' in stripe_customer.sources.data[0]

        if has_customer_entered_card:
            return stripe_customer.sources.data[0].last4

    def create_subscription(self, stripe_plan_id, stripe_customer_id):
        stripe_customer = self.stripe_proxy.Customer.retrieve(stripe_customer_id)
        stripe_customer.subscriptions.create(plan=stripe_plan_id)
        subscription = stripe_customer.save()
        stripe_subscription = subscription.subscriptions.data[0]
        return stripe_subscription.id

    def update_subscription(self, stripe_customer_id, stripe_subscription_id, stripe_plan_id):
        stripe_customer = self.stripe_proxy.Customer.retrieve(stripe_customer_id)
        stripe_subscription = stripe_customer.subscriptions.retrieve(stripe_subscription_id)
        stripe_subscription.plan = stripe_plan_id
        stripe_subscription.save()
        return stripe_subscription.id

    def cancel_subscription(self, stripe_customer_id, stripe_subscription_id):
        stripe_customer = stripe.Customer.retrieve(stripe_customer_id)
        stripe_subscription = stripe_customer.subscriptions.retrieve(stripe_subscription_id).delete()
        assert stripe_subscription['status'] == 'canceled'


    def create_token(self, number, cvc, exp_month, exp_year):
        return self.stripe_proxy.Token.create(
            card={
                "number": number,
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvc": cvc
            },
        )

    def charge_customer_once(self, customer_id, charge_in_cents):
        # Charge the Customer instead of the card
        self.stripe_proxy.Charge.create(
            amount=charge_in_cents,
            currency=Constants.CURRENCY,
            customer=customer_id  # Previously stored, then retrieved
        )
