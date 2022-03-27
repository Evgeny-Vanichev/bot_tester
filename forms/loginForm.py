from flask_wtf import FlaskForm
from wtforms.fields import PasswordField, SubmitField, StringField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    name = StringField("Имя", validators=[DataRequired()])
    surname = StringField("Фамилия", validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')
