from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FileField, HiddenField
from wtforms.validators import DataRequired, Email, Length
from flask_security.forms import RegisterForm


class LoginForm(Form):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Keep me logged in')
    submit = SubmitField('Log in')


class ExtendedRegisterForm(RegisterForm):
    name = StringField('Name', [DataRequired()])
    is_shop_owner = BooleanField('I am a shop owner')


class ShopForm(Form):
    name = StringField('Shop name', validators=[])
    domain = StringField('Shop Domain', validators=[])
    description = TextAreaField('Description', validators=[])
    submit = SubmitField('Go')


class ReviewPhotoForm(Form):
    photo = FileField('photo')


class ReviewForm(Form):
    body = TextAreaField('', validators=[Length(max=260)])
    photo_url = StringField()
    submit = SubmitField('Post')


class ReviewRequestForm(Form):
    from_customer_id = HiddenField()
    to_user_id = HiddenField()
    for_product_id = HiddenField()
    for_shop_id = HiddenField()
