from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired


class GroupForm(FlaskForm):
    name = StringField("Название группы", validators=[DataRequired()])
    submit = SubmitField("Подтвердить изменения")
