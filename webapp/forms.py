from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FileField, HiddenField, RadioField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from flask_security.forms import ConfirmRegisterForm


class LoginForm(Form):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Keep me logged in')
    submit = SubmitField('Log in')


class SubscribeForm(Form):
    email = StringField('Email', validators=[DataRequired(), Email()])
    website = StringField('Your Website', validators=[])


class ExtendedRegisterForm(Form):
    name = StringField('Name', [DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(),
                                                     Length(min=6, max=128)])
    password_confirm = PasswordField(
        'Retype Password',
        validators=[EqualTo('password', message='Passwords do not match')])
    is_shop_owner = BooleanField('I am a shop owner')
    submit = SubmitField('Register')


class ShopForm(Form):
    name = StringField('Shop name', validators=[])
    domain = StringField('Shop Domain', validators=[])
    description = TextAreaField('Description', validators=[])
    submit = SubmitField('Save')


class ReviewImageForm(Form):
    image = FileField('image')


class ReviewForm(Form):
    name = StringField('Name')
    email = StringField('Email', validators=[Email()])
    password = PasswordField('Password', validators=[])
    body = TextAreaField('', validators=[Length(max=260)])
    star_rating = RadioField('Label', choices=[(1,''),
                                               (2,''),
                                               (3,''),
                                               (4,''),
                                               (5,'')])
    image_url = HiddenField()
    review_request_id = HiddenField()
    review_request_token = HiddenField()


class ReviewRequestForm(Form):
    from_customer_id = HiddenField()
    to_user_id = HiddenField()
    for_product_id = HiddenField()
    for_shop_id = HiddenField()
