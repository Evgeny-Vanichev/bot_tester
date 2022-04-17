from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, DateTimeField, DateField, TimeField
from wtforms.validators import DataRequired


class TestForm(FlaskForm):
    name = StringField("Название", validators=[DataRequired()])
    about = StringField("Описание работы", validators=[DataRequired()])
    date = DateField("Дата работы", validators=[DataRequired()])
    time = TimeField("Время работы", validators=[DataRequired()])
    submit = SubmitField('Добавить работу')
