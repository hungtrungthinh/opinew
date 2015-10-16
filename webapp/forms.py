from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, FileField, \
    HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange


class LoginForm(Form):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Keep me logged in')
    submit = SubmitField('Log in')

from flask_security.forms import RegisterForm

class ExtendedRegisterForm(RegisterForm):
    name = StringField('Name', [DataRequired()])

class ReviewPhotoForm(Form):
    photo = FileField('photo')


class ReviewForm(Form):
    body = TextAreaField('', validators=[Length(max=260)])
    photo_url = StringField()
    submit = SubmitField('Post')
