from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField, DateField, TimeField
from wtforms.validators import DataRequired


class TestForm(FlaskForm):
    name = StringField("Название", validators=[DataRequired()])
    about = StringField("Описание работы", validators=[DataRequired()])
    date_start = DateField("Дата работы", validators=[DataRequired()])
    time_start = TimeField("Время работы", validators=[DataRequired()])

    date_start = DateField("Дата окончания работы", validators=[DataRequired()])
    time_start = TimeField("Время окончания работы", validators=[DataRequired()])
    submit = SubmitField('Добавить работу')
