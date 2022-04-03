from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, SelectField
from wtforms.validators import DataRequired


class RegisterForm(FlaskForm):
    name = StringField("Имя", validators=[DataRequired()])
    surname = StringField("Фамилия", validators=[DataRequired()])
    email = StringField("Электронная почта", validators=[DataRequired()])
    contact_type = SelectField('Предпочитаемый тип связи',
                               choices=[('Telegram', 'Telegram'), ('Discord', 'Discord'),
                                        ('VK', 'VK')])
    contact_link = StringField("Аккаунт для связи", validators=[DataRequired()])

    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Подтвердите пароль', validators=[DataRequired()])

    type = SelectField("Выберите роль", choices=[("teacher", "teacher"), ("student", "student")],
                       validate_choice=True)
    submit = SubmitField('Зарегистрироваться')
