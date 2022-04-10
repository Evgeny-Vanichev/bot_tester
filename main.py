import os
import json
import shutil

from flask import Flask, render_template, redirect, request
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

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
from forms.taskForm import TaskForm
from forms.testForm import TestForm

from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from static.tools.tools import transliterate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['PERMANENT_SESSION_LIFETIME'] = __import__("datetime").timedelta(
    days=365
)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'user_data')

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
    form = GroupForm()
    if request.method == 'GET':
        db_sess = db_session.create_session()
        group = db_sess.query(Groups).filter(Groups.group_id == group_id,
                                             Groups.teacher_id == current_user.id).first()
        form.name.data = group.group_name
        if group is None:
            abort(404)
    if form.validate_on_submit():
        if db_sess.query(Groups).filter(Groups.group_name == form.name.data,
                                        Groups.teacher_id == current_user.id,
                                        Groups.group_id != group_id).first() is not None:
            return render_template('add_group.html', form=form,
                                   message="Вы ранее создавали группу с таким именем")
        # Обновление информации о группе
        group = db_sess.query(Groups).filter(Groups.group_id == group_id,
                                             Groups.teacher_id == current_user.id).first()
        group.group_name = form.name.data
        db_sess.add(group)
        db_sess.commit()
        return redirect(f'/manage_groups/{group.group_id}')
    return render_template('add_group.html', form=form)


@app.route('/delete_group/<int:group_id>', methods=['GET', 'POST'])
@login_required
def delete_group(group_id):
    db_sess = db_session.create_session()
    group = db_sess.query(Groups).filter(Groups.group_id == group_id,
                                         Groups.teacher_id == current_user.id).first()
    if group is None:
        abort(404)
    for student in db_sess.query(GroupParticipants).filter(
            GroupParticipants.group_id == group.group_id
    ):
        db_sess.delete(student)
    db_sess.delete(group)
    db_sess.commit()
    return redirect('/manage_groups')


@app.route('/person_delete/<int:group_id>/<int:student_id>')
@login_required
def delete_student_from_group(group_id, student_id):
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
def add_student_to_group(group_id, student_id):
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
            os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], str(user.id)))
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
def manage_tests(test_id):
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
        with open(os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id),
                               f'{test_id}.json'), mode='rt') as json_file:
            tasks = json.load(json_file)['tasks']
        print(tasks)
        return render_template("tests_for_teacher.html",
                               tests=result,
                               current_test=current_test,
                               tasks=tasks,
                               current_user=current_user)
    return render_template("index_for_student.html")


@app.route('/add_task/<int:test_id>', methods=['GET', 'POST'])
def add_task(test_id):
    form = TaskForm()
    if form.validate_on_submit():
        path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id))

        filenames = []
        for file in form.files.data:
            filename = secure_filename(transliterate(file.filename.replace(' ', '_')))
            file.save(os.path.join(path, filename))
            filenames.append(filename)
        task = {
            "question": form.question.data,
            "extra_files": filenames
        }
        with open(os.path.join(path, f'{test_id}.json'), mode='rt') as json_file:
            data = json.load(json_file)
            data['tasks'].append(task)
        with open(os.path.join(path, f'{test_id}.json'), mode='wt') as json_file:
            json.dump(data, json_file)
        return redirect('/')
    return render_template('task.html', title='Добавление вопроса',
                           form=form)


@app.route('/new_test', methods=['GET', 'POST'])
@login_required
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
        # Создание новой работы
        task = Tests(
            name=form.name.data,
            about=form.about.data,
            teacher_id=current_user.id
        )
        db_sess.add(task)
        db_sess.commit()

        path = os.path.join(app.config['UPLOAD_FOLDER'], f'{current_user.id}/{task.test_id}')
        os.makedirs(path)
        with open(os.path.join(path, f'{task.test_id}.json'), mode='wt') as json_file:
            json.dump({'groups': [], 'tasks': []}, json_file)
        return redirect(f'/manage_tests/{task.test_id}')
    return render_template('add_test.html', form=form)


@app.route('/edit_test/<int:test_id>', methods=['GET', 'POST'])
@login_required
def edit_test_info(test_id):
    if current_user.type != TEACHER:
        abort(401)
    db_sess = db_session.create_session()
    form = TestForm()
    if request.method == 'GET':
        test = db_sess.query(Tests).filter(Tests.test_id == test_id,
                                           Tests.teacher_id == current_user.id).first()
        if not test:
            abort(404)
        form.name.data = test.name
        form.about.data = test.about
    if form.validate_on_submit():
        if db_sess.query(Tests).filter(Tests.name == form.name.data,
                                       Tests.teacher_id == current_user.id,
                                       Tests.test_id != test_id).first() is not None:
            return render_template('add_test.html', form=form,
                                   message="Вы ранее создавали группу с таким именем")

        test = db_sess.query(Tests).filter(Tests.test_id == test_id,
                                           Tests.teacher_id == current_user.id).first()

        test.name = form.name.data
        test.about = form.about.data
        db_sess.add(test)
        db_sess.commit()
        return redirect(f'/manage_tests/{test.test_id}')
    return render_template('add_test.html', form=form)


@app.route('/delete_test/<int:test_id>', methods=['GET', 'POST'])
@login_required
def delete_test(test_id):
    db_sess = db_session.create_session()

    test = db_sess.query(Tests).filter(Tests.test_id == test_id,
                                       Tests.teacher_id == current_user.id).first()
    if test is None:
        abort(404)
    db_sess.delete(test)
    db_sess.commit()

    path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
    shutil.rmtree(os.path.join(path, str(test_id)))
    return redirect('/manage_tests')


@app.route('/view_groups/<int:test_id>')
@login_required
def manage_groups_for_test(test_id):
    path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id),
                        f'{test_id}.json')
    with open(path, mode='rt') as jsonfile:
        data = json.load(jsonfile)
        groups_ids = data['groups']
    # Надо снова добавить проверку на дурака
    db_sess = db_session.create_session()
    groups = [(group, group.group_id in groups_ids) for group in db_sess.query(Groups).all()]

    test = db_sess.query(Tests).filter(Tests.test_id == test_id).first()
    result = db_sess.query(Tests).filter(Tests.teacher_id == current_user.id).all()
    return render_template('tests_groups_for_teacher.html',
                           groups=groups,
                           current_test=test,
                           tests=result)


@app.route('/group_add/<int:test_id>/<int:group_id>')
@login_required
def add_group_to_Test(test_id, group_id):
    path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id),
                        f'{test_id}.json')
    with open(path, mode='rt', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        if group_id not in data['groups']:
            data['groups'].append(group_id)
    with open(path, mode='wt', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile)
    return redirect(f'/view_groups/{test_id}')


@app.route("/group_discard/<int:test_id>/<int:group_id>")
@login_required
def discard_group_from_test(test_id, group_id):
    path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id),
                        f'{test_id}.json')
    with open(path, mode='rt', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        if group_id in data['groups']:
            data['groups'].remove(group_id)
    with open(path, mode='wt', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile)
    return redirect(f'/view_groups/{test_id}')


@app.route('/view_tasks/<int:test_id>')
@login_required
def manage_tasks_for_test(test_id):
    path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id),
                        f'{test_id}.json')
    with open(path, mode='rt') as jsonfile:
        data = json.load(jsonfile)
    # Надо снова добавить проверку на дурака
    db_sess = db_session.create_session()
    result = db_sess.query(Tests).filter(Tests.teacher_id == current_user.id).all()

    # Получение группы, с которой в данный момент работает учитель
    current_test = db_sess.query(Tests).filter(Tests.test_id == test_id).first()
    if current_test is None:  # Проверка, существования группы
        abort(404)
    path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id))
    with open(os.path.join(path, f'{test_id}.json'), mode='rt') as json_file:
        tasks = json.load(json_file)['tasks']
    print(tasks)
    return render_template("tests_tasks_for_teacher.html",
                           tests=result,
                           current_test=current_test,
                           tasks=tasks,
                           current_user=current_user)


if __name__ == '__main__':
    main()
