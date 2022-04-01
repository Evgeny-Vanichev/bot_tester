from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField
from wtforms.validators import DataRequired


class TestForm(FlaskForm):
    name = StringField("Название", validators=[DataRequired()])
    about = StringField("Описание работы", validators=[DataRequired()])
    submit = SubmitField('Добавить работу')
