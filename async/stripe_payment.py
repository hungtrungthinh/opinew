import stripe
from flask import current_app
from config import Constants


class PaymentInterface(object):
    def create_customer(self, opinew_customer, stripe_token):
        raise NotImplementedError()

    def create_plan(self, opinew_plan):
        raise NotImplementedError()

    def create_subscription(self, opinew_subscription):
        raise NotImplementedError()

    def update_subscription(self, opinew_subscription, opinew_new_plan):
        raise NotImplementedError()


class StripeAPI(PaymentInterface):
    def __init__(self, stripe_api_key):
        # Set your secret key: remember to change this to your live secret key in production
        # See your keys here https://dashboard.stripe.com/account/apikeys
        self.stripe_proxy = stripe
        self.stripe_proxy.api_key = stripe_api_key

    def create_customer(self, opinew_customer, stripe_token):
        # Get the credit card details submitted by the form
        # Create a Stripe Customer
        if current_app.config.get('TESTING'):
            return opinew_customer
        if stripe_token:
            customer = self.stripe_proxy.Customer.create(
                source=stripe_token,
                description=opinew_customer.user.email
            )
        else:
            customer = self.stripe_proxy.Customer.create(
                description=opinew_customer.user.email
            )
        return customer

    def create_plan(self, opinew_plan):
        if current_app.config.get('TESTING'):
            return opinew_plan
        try:
            plan = stripe.Plan.retrieve(opinew_plan.name)
        except stripe.InvalidRequestError:
            plan = self.stripe_proxy.Plan.create(
                amount=opinew_plan.amount,
                interval=opinew_plan.interval,
                name=opinew_plan.name,
                currency=Constants.CURRENCY,
                trial_period_days=opinew_plan.trial_period_days,
                id=opinew_plan.name
            )
        return plan

    def create_subscription(self, opinew_subscription):
        if current_app.config.get('TESTING'):
            return opinew_subscription
        customer = self.stripe_proxy.Customer.retrieve(opinew_subscription.customer.stripe_customer_id)
        customer.subscriptions.create(plan=opinew_subscription.plan.stripe_plan_id)
        subscription = customer.save()
        return subscription

    def update_subscription(self, opinew_subscription, opinew_new_plan):
        if current_app.config.get('TESTING'):
            return opinew_subscription
        customer = self.stripe_proxy.Customer.retrieve(opinew_subscription.customer.stripe_customer_id)
        subscription = customer.subscriptions.retrieve(opinew_subscription.stripe_subscription_id)
        subscription.plan = opinew_new_plan.stripe_plan_id
        subscription.save()
        return subscription

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


class StripeOpinewAdapter(PaymentInterface):
    def __init__(self):
        self.stripe_api = StripeAPI(current_app.config.get('STRIPE_API_KEY'))

    def create_customer(self, opinew_customer, stripe_token):
        stripe_customer = self.stripe_api.create_customer(opinew_customer, stripe_token)
        opinew_customer.stripe_customer_id = stripe_customer.id
        return opinew_customer

    def create_plan(self, opinew_plan):
        stripe_plan = self.stripe_api.create_plan(opinew_plan)
        opinew_plan.stripe_plan_id = stripe_plan.id
        return opinew_plan

    def create_subscription(self, opinew_subscription):
        stripe_subscription = self.stripe_api.create_subscription(opinew_subscription)
        opinew_subscription.stripe_subscription_id = stripe_subscription.id
        return opinew_subscription

    def update_subscription(self, opinew_subscription, opinew_new_plan):
        stripe_subscription = self.stripe_api.update_subscription(opinew_subscription, opinew_new_plan)
        opinew_subscription.stripe_subscription_id = stripe_subscription.id
        return opinew_subscription