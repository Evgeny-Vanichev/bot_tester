import os
from flask import Flask, render_template, redirect, request
from werkzeug.exceptions import abort
import json

from data import db_session

# Модели БД
from data.group_participants import GroupParticipants
from data.groups import Groups
from data.tests import Tests
from data.users import Users

# Формы для заполнения
from forms.groupForm import GroupForm
from forms.registerForm import RegisterForm
from forms.loginForm import LoginForm
from forms.testForm import TestForm

from flask_login import LoginManager, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = __import__("datetime").timedelta(
    days=365
)

login_manager = LoginManager()
login_manager.init_app(app)

TEACHER, STUDENT = 1, 2


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(Users).get(user_id)


def main():
    db_session.global_init("db/users_database.db")
    app.run()


def get_all_students():
    db_sess = db_session.create_session()
    return db_sess.query(Users).filter(Users.type == STUDENT).all()


@app.route('/manage_groups/', defaults={'group_id': -1})
@app.route('/manage_groups/<int:group_id>')
@login_required
def manage_groups(group_id):
    if current_user.type == TEACHER:
        db_sess = db_session.create_session()

        # Все группы учителя. Используется для списка в боковой части экрана
        result = db_sess.query(Groups).filter(Groups.teacher_id == current_user.id)
        # Получение группы, с которой в данный момент работает учитель
        current_group = db_sess.query(Groups).filter(Groups.group_id == group_id).first()
        if current_group is None and group_id != -1:  # Проверка, существования группы
            abort(404)
        # Получение Id всех учеников из группы
        users_ids = [student.student_id for student in db_sess.query(GroupParticipants).filter(
            GroupParticipants.group_id == group_id)]
        # Получение объектов Users по Id
        current_people = [(student, student.id in users_ids) for student in get_all_students()]
        return render_template("groups_for_teacher.html",
                               groups=result,
                               current_group=current_group,
                               current_people=current_people)
    return render_template("index_for_student.html")


@app.route('/new_group', methods=['GET', 'POST'])
@login_required
def add_group():
    if current_user.type != TEACHER:
        abort(401)
    db_sess = db_session.create_session()

    # Загрузка списка всех студентов в форму
    form = GroupForm()
    if form.validate_on_submit():
        if db_sess.query(Groups).filter(Groups.group_name == form.name.data,
                                        Groups.teacher_id == current_user.id).first() is not None:
            return render_template('add_group.html', form=form,
                                   message="Вы ранее создавали группу с таким именем")
        # Создание новой группы
        group = Groups(
            group_name=form.name.data,
            teacher_id=current_user.id
        )
        db_sess.add(group)
        db_sess.commit()
        return redirect(f'manage_groups/{group.group_id}')
    return render_template('add_group.html', form=form)


@app.route('/rename_group/<int:group_id>', methods=['GET', 'POST'])
@login_required
def rename_group(group_id):
    if current_user.type != TEACHER:
        abort(401)
    db_sess = db_session.create_session()
    group = db_sess.query(Groups).filter(Groups.group_id == group_id,
                                         Groups.teacher_id == current_user.id).first()
    if group is None:
        abort(404)

    # Загрузка списка всех студентов в форму
    form = GroupForm()
    if form.validate_on_submit():
        if db_sess.query(Groups).filter(Groups.group_name == form.name.data,
                                        Groups.teacher_id == current_user.id,
                                        Groups.group_id != group_id).first() is not None:
            return render_template('add_group.html', form=form,
                                   message="Вы ранее создавали группу с таким именем")
        # Создание новой группы
        group.group_name = form.name.data
        db_sess.add(group)
        db_sess.commit()
        return redirect(f'/manage_groups/{group.group_id}')
    return render_template('add_group.html', form=form)


@app.route('/person_delete/<int:group_id>/<int:student_id>')
@login_required
def student_delete(group_id, student_id):
    db_sess = db_session.create_session()
    group = db_sess.query(Groups).filter(Groups.group_id == group_id,
                                         Groups.teacher_id == current_user.id).first()
    if not group:
        abort(404)
    student = db_sess.query(GroupParticipants).filter(
        GroupParticipants.student_id == student_id,
        GroupParticipants.group_id == group_id
    ).first()
    if not student:
        abort(404)
    db_sess.delete(student)
    db_sess.commit()
    return redirect(f'/manage_groups/{group_id}')


@app.route('/person_add/<int:group_id>/<int:student_id>')
@login_required
def student_add(group_id, student_id):
    db_sess = db_session.create_session()
    group = db_sess.query(Groups).filter(Groups.group_id == group_id,
                                         Groups.teacher_id == current_user.id).first()
    if not group:
        abort(404)

    gp = GroupParticipants(
        group_id=group_id,
        student_id=student_id
    )
    db_sess.add(gp)
    db_sess.commit()
    return redirect(f'/manage_groups/{group_id}')


@app.route("/")
@login_required
def index():
    # а вообще надо-бы сверстать приветственную страничку
    return redirect('/manage_tests')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(Users).filter(
            Users.name == form.name.data, Users.surname == form.surname.data).first()
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
                Users.name == form.name.data, Users.surname == form.surname.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        name = form.name.data
        surname = form.surname.data
        email = form.email.data
        contact_type = form.contact_type.data
        contact_link = form.contact_link.data

        if form.type.data == "student":
            user = Users(
                name=name,
                surname=surname,
                email=email,
                contact_type=contact_type,
                contact_link=contact_link,
                type=STUDENT
            )
        else:
            user = Users(
                name=name,
                surname=surname,
                email=email,
                contact_type=contact_type,
                contact_link=contact_link,
                type=TEACHER
            )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        if user.type == TEACHER:
            path = os.path.abspath(os.getcwd() + '/user_data')
            os.chdir(path)
            os.mkdir(str(user.id))
            os.chdir('..')
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


@app.route('/manage_tests/', defaults={'test_id': -1})
@app.route('/manage_tests/<int:test_id>')
@login_required
def manage_tasks(test_id):
    if current_user.type == TEACHER:
        db_sess = db_session.create_session()
        # Все работы учителя. Используется для списка в боковой части экрана
        result = db_sess.query(Tests).filter(Tests.teacher_id == current_user.id).all()
        if test_id == -1:
            return render_template(
                'tests_for_teacher.html',
                tests=result,
                current_test=None
            )
        # Получение группы, с которой в данный момент работает учитель
        current_test = db_sess.query(Tests).filter(Tests.test_id == test_id).first()
        if current_test is None:  # Проверка, существования группы
            abort(404)
        return render_template("tests_for_teacher.html",
                               tests=result,
                               current_test=current_test)
    return render_template("index_for_student.html")


# ДАННЫЙ КОД ПОКА ЧТО НЕ РАБОТАЕТ!!!
@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    form = TestForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        task = Tests()
        task.name = form.name.data
        task.about = form.about.data
        current_user.tasks.append(task)
        db_sess.merge(current_user)
        db_sess.commit()
        return redirect('/')
    return render_template('task.html', title='Добавление вопроса',
                           form=form)


@app.route('/new_test', methods=['GET', 'POST'])
def add_test():
    if current_user.type != TEACHER:
        abort(401)
    db_sess = db_session.create_session()

    form = TestForm()
    if form.validate_on_submit():
        if db_sess.query(Tests).filter(Tests.name == form.name.data,
                                       Tests.teacher_id == current_user.id).first() is not None:
            return render_template('add_test.html', form=form,
                                   message="Вы ранее создавали группу с таким именем")
        # Создание новой группы
        task = Tests(
            name=form.name.data,
            about=form.about.data,
            teacher_id=current_user.id
        )
        db_sess.add(task)
        db_sess.commit()
        with open(f'user_data/{current_user.id}/{task.test_id}.json', mode='wt') as json_file:
            json.dump({'groups': [], 'tasks': []}, json_file)
            print('file_created')
        return redirect(f'manage_tests/{task.test_id}')
    return render_template('add_test.html', form=form)




if __name__ == '__main__':
    main()
