from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FileField
from wtforms.validators import DataRequired


class TaskForm(FlaskForm):
    name = StringField("Название", validators=[DataRequired()])
    about = StringField("Описание вопроса", validators=[DataRequired()])
    submit = SubmitField('Добавить вопрос')
