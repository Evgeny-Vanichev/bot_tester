from flask import Flask, render_template, redirect

from data import db_session
from data.students import Students
from data.teachers import Teachers
from forms.registerForm import RegisterForm
from forms.loginForm import LoginForm

import datetime

from flask_login import LoginManager, login_user, login_required, logout_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(
    days=365
)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_student(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(Students).get(user_id)


def main():
    db_session.global_init("db/users_database.db")
    app.run()


@app.route("/")
def index():
    return render_template("index.html")


@app.route('/login_teacher', methods=['GET', 'POST'])
def login_teacher():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        teacher = db_sess.query(Teachers).filter(
            Teachers.name == form.name.data and Teachers.surname == form.surname.data).first()
        if teacher and teacher.check_password(form.password.data):
            login_user(teacher)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/login_student', methods=['GET', 'POST'])
def login_student():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        student = db_sess.query(Students).filter(
            Students.name == form.name.data and Students.surname == form.surname.data).first()
        if student and student.check_password(form.password.data):
            login_user(student)
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
        if form.type.data == "student":
            if db_sess.query(Students).filter(
                    Students.name == form.name.data and Students.surname == form.surname.data).first():
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Такой пользователь уже есть")
            student = Students(
                name=form.name.data,
                surname=form.surname.data,
                grade=form.grade.data,
                contact=form.contact.data,
                type=2
            )
            student.set_password(form.password.data)
            db_sess.add(student)
            db_sess.commit()
            return redirect('/login_student')
        elif form.type.data == "teacher":
            if db_sess.query(Teachers).filter(
                    Teachers.name == form.name.data and Teachers.surname == form.surname.data).first():
                return render_template('register.html', title='Регистрация',
                                       form=form,
                                       message="Такой пользователь уже есть")
            teacher = Teachers(
                name=form.name.data,
                surname=form.surname.data,
                contact=form.contact.data,
                type=1
            )
            teacher.set_password(form.password.data)
            db_sess.add(teacher)
            db_sess.commit()
            return redirect('/login_teacher')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/login_student")


if __name__ == '__main__':
    main()
