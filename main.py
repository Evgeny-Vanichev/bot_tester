from flask import Flask, render_template, redirect

from data import db_session
from data.users import Users
from forms.registerForm import RegisterForm
from forms.loginForm import LoginForm

import datetime

from flask_login import LoginManager, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(
    days=365
)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(Users).get(user_id)


def main():
    db_session.global_init("db/users_database.db")
    app.run()


@app.route("/")
@login_required
def index():
    if current_user.type == 1:
        return render_template("index_for_teacher.html")
    return render_template("index_for_student.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(Users).filter(
            Users.name == form.name.data and Users.surname == form.surname.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(Users).filter(
                Users.name == form.name.data and Users.surname == form.surname.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        if form.type.data == "student":
            user = Users(
                name=form.name.data,
                surname=form.surname.data,
                grade=form.grade.data,
                contact=form.contact.data,
                type=2
            )
        else:
            user = Users(
                name=form.name.data,
                surname=form.surname.data,
                contact=form.contact.data,
                type=1
            )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/login")


@app.after_request
def redirect_to_sign(response):
    if response.status_code == 401:
        return redirect("/register")

    return response


if __name__ == '__main__':
    main()
