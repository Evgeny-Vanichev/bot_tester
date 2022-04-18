from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField
from wtforms.validators import DataRequired


class TestForm(FlaskForm):
    name = StringField("Название", validators=[DataRequired()])
    about = StringField("Описание работы", validators=[DataRequired()])
    time = DateField("Дедлайн")

    submit = SubmitField('Добавить работу')
