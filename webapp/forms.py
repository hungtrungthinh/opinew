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
    password = PasswordField('Password', validators=[DataRequired(),
                                                     EqualTo('password_verify', message='Passwords must match')])
    password_verify = PasswordField('Password Verify', validators=[DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Sign up')


class ReviewForm(Form):
    body = TextAreaField('', validators=[Length(max=260)])
    photo = FileField('photo')
    submit = SubmitField('Post')
