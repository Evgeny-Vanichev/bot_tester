from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, MultipleFileField


class TaskForm(FlaskForm):
    question = TextAreaField("Текст задания")
    files = MultipleFileField('Дополнительные материалы')
    submit = SubmitField('Добавить задание')