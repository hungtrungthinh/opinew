import datetime
from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FileField, SelectField, \
    IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange


class LoginForm(Form):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log in')


class SignupForm(Form):
    email = StringField('Email', validators=[DataRequired(), Email()])
    name = StringField('Name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(),
                                                     EqualTo('password_verify', message='Passwords must match')])
    password_verify = PasswordField('Password Verify', validators=[DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Sign up')


class CustomerSignupForm(SignupForm):
    MONTHS = [(month, month) for month in range(1,13)]
    this_year = datetime.date.today().year
    YEARS = [(year, year) for year in range(this_year, this_year + 15)]
    # Credit card number
    card_number = StringField('Card number', validators=[DataRequired(), Length(min=16, max=16)])
    # Security code (CVV)
    card_cvv = IntegerField('CVV', validators=[DataRequired(), NumberRange(min=100, max=999)])
    # Card expiration - month
    card_exp_month = SelectField('Expiry Month', choices=MONTHS)
    # Card expiration - year
    card_exp_year = SelectField('Expiry Year',choices=YEARS)


class ReviewForm(Form):
    body = TextAreaField('', validators=[Length(max=260)])
    photo = FileField('photo')
    submit = SubmitField('Post')
