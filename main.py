import asyncio
import logging
import os
import json
import random
import shutil

import requests
import vk_api
import datetime

from flask import Flask, render_template, redirect, request
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from data import db_session

# Модели БД
from data.group_participants import GroupParticipants
from data.groups import Groups
from data.tests import Tests
from data.users import Users
from data.tests_and_groups import TestsAndGroups

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


def get_all_students():
    db_sess = db_session.create_session()
    return db_sess.query(Users).filter(Users.type == STUDENT).all()


@app.route('/manage_groups/', defaults={'group_id': -1})
@app.route('/manage_groups/<int:group_id>')
@app.route('/manage_groups/<int:group_id>/<int:page_id>')
@login_required
def manage_groups(group_id, page_id=1):
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

        prev_page = max(page_id - 1, 1)
        next_page = min(page_id + 1, (len(current_people) + 4) // 5)
        # (a + b - 1) // a - округление вверх

        return render_template("groups_for_teacher.html",
                               groups=result,
                               current_group=current_group,
                               current_people=current_people,
                               page_id=page_id,
                               prev_page=prev_page,
                               next_page=next_page)

    db_sess = db_session.create_session()
    # ищем, в каких группах состоит студент
    s = []
    result = db_sess.query(GroupParticipants).filter(GroupParticipants.student_id == current_user.id).all()
    print(result)
    for i in result:
        res = db_sess.query(Groups).filter(Groups.group_id == i.group_id).first()
        print(res)
        s.append(res.group_name)
    return render_template("groups_for_student.html", groups=s, len=len(s))


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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/home")
def home():
    return redirect("/manage_tests")


@app.route('/person_delete/<int:group_id>/<int:page_id>/<int:student_id>')
@login_required
def delete_student_from_group(group_id, page_id, student_id):
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
    return redirect(f'/manage_groups/{group_id}/{page_id}')


@app.route('/person_add/<int:group_id>/<int:page_id>/<int:student_id>')
@login_required
def add_student_to_group(group_id, page_id, student_id):
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
    return redirect(f'/manage_groups/{group_id}/{page_id}')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(Users).filter(
            Users.name == form.name.data, Users.surname == form.surname.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect("/home")
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
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], str(user.id)))
        return redirect('/login')

    return render_template('register.html', title='Регистрация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.after_request
def redirect_to_sign(response):
    if response.status_code == 401:
        return redirect("/register")
    return response


@app.route('/manage_tests/', defaults={'test_id': -1})
@app.route('/manage_tests/<int:test_id>')
@login_required
def manage_tests(test_id=-1):
    if current_user.type == TEACHER:
        db_sess = db_session.create_session()
        # Все работы учителя. Используется для списка в боковой части экрана
        result = db_sess.query(Tests).filter(Tests.teacher_id == current_user.id).all()
        if test_id == -1:
            return render_template(
                'tests_for_teacher.html',
                tests=result,
                current_test=None,
                mode=1
            )
        # Получение группы, с которой в данный момент работает учитель
        current_test = db_sess.query(Tests).filter(Tests.test_id == test_id).first()
        if current_test is None:  # Проверка, существования группы
            abort(404)
        return render_template("tests_for_teacher.html",
                               tests=result,
                               current_test=current_test)

    # код раскомментить после того, как добавится id студента в бд tasks +
    # не трогать даже после этого, так как я недописала правильно его
    # как раз из-за нехватки id :)
    db_sess = db_session.create_session()

    # ищем, в каких группах состоит студент
    s = {}
    groups = db_sess.query(GroupParticipants).filter(GroupParticipants.student_id == current_user.id).all()
    for i in groups:
        res = db_sess.query(Groups).filter(Groups.group_id == i.group_id).first().group_name
        tests = db_sess.query(TestsAndGroups).filter(TestsAndGroups.group_id == i.group_id).all()
        for test in tests:
            res1 = db_sess.query(Tests).filter(Tests.test_id == test.test_id).first()
            print(res1)
            if res not in s:
                s[res] = []
            s[res].append(res1)
    test = db_sess.query(Tests).filter(Tests.test_id == test_id).first()
    return render_template("tests_for_student.html", groups=s, current_test=test)


# ДАННЫЙ КОД ПОКА ЧТО НЕ РАБОТАЕТ!!!
@app.route('/add_task/<int:test_id>', methods=['GET', 'POST'])
def add_task(test_id):
    form = TaskForm()
    if form.validate_on_submit():
        path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id))

        filenames = []
        for file in form.files.data:
            if file.filename == '':
                continue
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
        return redirect(f'/manage_tests/{test_id}/1')
    return render_template('task.html', title='Добавление вопроса', form=form)


@app.route('/new_test', methods=['GET', 'POST'])
@login_required
def add_test():
    if current_user.type != TEACHER:
        abort(401)
    db_sess = db_session.create_session()

    result = db_sess.query(Groups).filter(Groups.teacher_id == current_user.id).all()

    form = TestForm()
    if form.validate_on_submit():
        if db_sess.query(Tests).filter(Tests.name == form.name.data,
                                       Tests.teacher_id == current_user.id).first() is not None:
            return render_template('add_test.html', form=form,
                                   message="Вы ранее создавали группу с таким именем")
        date_s, time_s = form.date_start.data, form.time_start.data
        dt_s = datetime.datetime.combine(date_s, time_s)
        date_e, time_e = form.date_end.data, form.time_end.data
        dt_e = datetime.datetime.combine(date_e, time_e)
        # здесь должен производиться вызов создания заданий в ботах

        # Создание новой работы
        test = Tests(
            name=form.name.data,
            about=form.about.data,
            teacher_id=current_user.id,
            date_start=dt_s,
            end_date=dt_e
        )
        db_sess.add(test)
        db_sess.commit()

        # какой-то непонятный код
        path = os.path.join(app.config['UPLOAD_FOLDER'], f'{current_user.id}/{test.test_id}')
        os.makedirs(path)
        with open(os.path.join(path, f'{test.test_id}.json'), mode='wt') as json_file:
            json.dump({'groups': [], 'tasks': []}, json_file)
        return redirect(f'/manage_tests/{test.test_id}/1')
    return render_template('add_test.html', form=form, groups=result)


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
        form.date_start.data = test.date_start.date()
        form.time_start.data = test.date_start.time()
        form.date_end.data = test.end_date.date()
        form.time_end.data = test.end_date.time()
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
        test.date_start = datetime.datetime.combine(form.date_start.data, form.time_start.data)
        test.end_date = datetime.datetime.combine(form.date_end.data, form.time_end.data)
        # здесь тоже надо добавлять работу в чат-бота
        db_sess.add(test)
        db_sess.commit()
        return redirect(f'/manage_tests/{test.test_id}/1')
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


@app.route('/manage_tests/<int:test_id>/2')
@login_required
def manage_groups_for_test(test_id):
    # Надо снова добавить проверку на дурака
    db_sess = db_session.create_session()
    groups_ids = [x.group_id for x in db_sess.query(TestsAndGroups).filter(TestsAndGroups.test_id == test_id).all()]
    groups = [(group, group.group_id in groups_ids) for group in db_sess.query(Groups).all()]

    test = db_sess.query(Tests).filter(Tests.test_id == test_id).first()
    result = db_sess.query(Tests).filter(Tests.teacher_id == current_user.id).all()
    return render_template('tests_groups_for_teacher.html',
                           groups=groups,
                           current_test=test,
                           tests=result,
                           mode=2)


@app.route('/group_add/<int:test_id>/<int:group_id>')
@login_required
def add_group_to_test(test_id, group_id):
    db_sess = db_session.create_session()
    group_by_task = TestsAndGroups(
        test_id=test_id,
        group_id=group_id
    )
    db_sess.add(group_by_task)
    db_sess.commit()
    return redirect(f'/manage_tests/{test_id}/2')


@app.route("/group_discard/<int:test_id>/<int:group_id>")
@login_required
def discard_group_from_test(test_id, group_id):
    db_sess = db_session.create_session()
    group_by_task = db_sess.query(TestsAndGroups).filter(
        TestsAndGroups.test_id == test_id,
        TestsAndGroups.group_id == group_id
    ).first()
    if not group_by_task:
        abort(404)
    db_sess.delete(group_by_task)
    db_sess.commit()
    return redirect(f'/manage_tests/{test_id}/2')


@app.route('/manage_tests/<int:test_id>/1')
@login_required
def manage_tasks_for_test(test_id):
    path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id), f'{test_id}.json')
    with open(path, mode='rt') as jsonfile:
        data = json.load(jsonfile)
        tasks = data['tasks']
        groups_ids = data['groups']
    # Надо снова добавить проверку на дурака
    db_sess = db_session.create_session()
    tests = [test for test in db_sess.query(Tests).all()]
    test = db_sess.query(Tests).filter(Tests.test_id == test_id).first()
    # result = db_sess.query(Tests).filter(Tests.teacher_id == current_user.id).all()
    return render_template('tests_tasks_for_teacher.html',
                           tasks=tasks,
                           current_test=test,
                           tests=tests,
                           mode=1)


@app.route('/manage_tests/<int:test_id>/3')
@login_required
def manage_students_answers(test_id):
    db_sess = db_session.create_session()
    test = db_sess.query(Tests).filter(Tests.test_id == test_id).first()
    groups_ids = [x.group_id for x in db_sess.query(TestsAndGroups).filter(TestsAndGroups.test_id == test_id).all()]
    students_ids = [x.student_id for x in
                    db_sess.query(GroupParticipants).filter(GroupParticipants.group_id.in_(groups_ids)).all()]
    students = db_sess.query(Users).filter(Users.id.in_(students_ids)).all()
    return render_template('tests_students_for_teacher.html',
                           students=students,
                           current_test=test,
                           current_student=None)


@app.route('/manage_tests/<int:test_id>/3/<int:student_id>')
@login_required
def check_student_answers(test_id, student_id):
    db_sess = db_session.create_session()
    test = db_sess.query(Tests).filter(Tests.test_id == test_id).first()
    groups_ids = [x.group_id for x in db_sess.query(TestsAndGroups).filter(TestsAndGroups.test_id == test_id).all()]
    students_ids = [x.student_id for x in
                    db_sess.query(GroupParticipants).filter(GroupParticipants.group_id.in_(groups_ids)).all()]
    students = db_sess.query(Users).filter(Users.id.in_(students_ids)).all()
    current_student = db_sess.query(Users).filter(Users.id == students)
    with open(os.path.join(app.config['UPLOAD_FOLDER'], str(student_id), f'{test_id}.json'), mode='rt') as jsonfile:
        data = json.load(jsonfile)['answers']
    return render_template('tests_students_for_teacher.html',
                           current_student=current_student,
                           students=students,
                           current_test=test,
                           answers=data)


@app.route("/delete_material/<int:test_id>/<int:question_id>/<path:filename>")
@login_required
def delete_material(test_id, filename, question_id):
    path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id))
    with open(os.path.join(path, f'{test_id}.json'), mode='rt', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
    data['tasks'][question_id - 1]['extra_files'].remove(filename)
    with open(os.path.join(path, f'{test_id}.json'), mode='wt', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile)
    os.remove(os.path.join(path, filename))
    return redirect(f'/manage_tests/{test_id}/1')


@app.route('/edit_task/<int:test_id>/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(test_id, task_id):
    if current_user.type != TEACHER:
        abort(401)
    form = TaskForm()
    path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id))
    with open(os.path.join(path, f'{test_id}.json'), mode='rt', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)

    if request.method == 'GET':
        form.question.data = data['tasks'][task_id - 1]['question']

    if form.validate_on_submit():
        data['tasks'][task_id - 1]['question'] = form.question.data
        filenames = []
        for file in form.files.data:
            if file.filename == '':
                continue
            filename = secure_filename(transliterate(file.filename.replace(' ', '_')))
            file.save(os.path.join(path, filename))
            filenames.append(filename)
        data['tasks'][task_id - 1]['extra_files'].extend(filenames)
        with open(os.path.join(path, f'{test_id}.json'), mode='wt', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile)
        return redirect(f'/manage_tests/{test_id}/1')
    return render_template('task.html', form=form)


@app.route('/delete_task/<int:test_id>/<int:task_id>')
@login_required
def delete_task(test_id, task_id):
    if current_user.type != TEACHER:
        abort(401)
    path = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), str(test_id))
    with open(os.path.join(path, f'{test_id}.json'), mode='rt', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
    for file in data['tasks'][task_id - 1]['extra_files']:
        os.remove(os.path.join(path, file))
    del data['tasks'][task_id - 1]
    with open(os.path.join(path, f'{test_id}.json'), mode='wt', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile)
    return redirect(f'/manage_tests/{test_id}/1')


def create_message_text(student: Users, test: Tests) -> str:
    return f'''
Здравствуйте {student}
Ваша работа {test.name}
({test.about})
от учителя {db_session.create_session().query(Users).filter(Users.id == test.teacher_id).first()}
началась
окончание работы - неизвестно'''


def create_message_files(question, number):
    return f'''
вопрос № {number}
текст вопроса: {question['question']}'''


def start_test(student: Users, test: Tests):
    path = os.path.join(app.config['UPLOAD_FOLDER'], str(test.teacher_id), str(test.test_id))
    with open(os.path.join(path, f'{test.test_id}.json'), mode='rt') as json_file:
        data = json.load(json_file)
        max_task = len(data['tasks'])
    with open(os.path.join(app.config['UPLOAD_FOLDER'], str(student.id), f'{test.test_id}.json'),
              mode='wt') as jsonfile:
        json.dump({"answers": [None for _ in range(max_task)]}, jsonfile)
    with open(os.path.join(app.config['UPLOAD_FOLDER'], str(student.id), f'{test.test_id}.txt'), mode='wt') as txtfile:
        txtfile.write('-1')
    # print(f'message to {student} is sent')
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    keyboard1 = VkKeyboard(one_time=False)
    i = j = 0
    while 4 * i + j < max_task:
        if j == 4:
            keyboard1.add_line()
            i += 1
            j = 0
        else:
            text = str(4 * i + j + 1)
            keyboard1.add_button(
                text,
                color=VkKeyboardColor.SECONDARY,
                payload="{\"task\":\"" + text + "\"}"
            )
            j += 1
    keyboard1.add_line()
    keyboard1.add_button("Отослать работу", color=VkKeyboardColor.POSITIVE, payload="{\"send\":\"1\"}")
    vk.messages.send(user_id=int(student.contact_link),
                     message=create_message_text(student, test),
                     random_id=random.randint(0, 2 ** 64),
                     keyboard=keyboard1.get_keyboard())


@app.route('/check_db')
def check_db():
    dt_now = datetime.datetime.now()
    db_sess = db_session.create_session()
    global tests_begun
    for test in db_sess.query(Tests).filter(
            Tests.date_start <= dt_now,
            Tests.end_date >= dt_now).all():
        test_id = test.test_id
        if test_id in tests_begun:
            continue
        tests_begun.add(test_id)
        for group in db_sess.query(TestsAndGroups).filter(TestsAndGroups.test_id == test_id).all():
            for student_id in db_sess.query(GroupParticipants.student_id).filter(
                    GroupParticipants.group_id == group.group_id).all():
                student = db_sess.query(Users).filter(Users.id == student_id[0]).first()
                start_test(student, test)
    # оставим учителю возможность удалять работы
    # for test in db_sess.query(Tests).filter(
    #         Tests.end_date < dt_now
    # ):
    #     db_sess.delete(test)
    # db_sess.commit()
    return 'OK'


def get_student_test_by_vk_id(link):
    logging.debug('user id: ', link)
    # просит сменить задание
    db_sess = db_session.create_session()
    # ученик по профилю вк
    student = db_sess.query(Users).filter(
        Users.contact_link == str(link), Users.type == STUDENT).first()
    # id группы по id ученика
    group_participants = db_sess.query(GroupParticipants).filter(
        GroupParticipants.student_id == student.id).first()
    test_and_group = db_sess.query(TestsAndGroups).filter(
        TestsAndGroups.group_id == group_participants.group_id).first()
    test = db_sess.query(Tests).filter(Tests.test_id == test_and_group.test_id).first()
    return student, test


async def upload_audio(filename, peer_id, upload, att):
    temp = upload.audio_message(
        audio=filename,
        peer_id=peer_id
    )['audio_message']
    att.append(f'doc{temp["owner_id"]}_{temp["id"]}')


async def upload_document(filename, file, peer_id, upload, att):
    temp = upload.document_message(
        filename,
        file,
        peer_id=peer_id)['doc']
    att.append(f'doc{temp["owner_id"]}_{temp["id"]}')


async def f2(tasks):
    await asyncio.gather(*tasks)


async def f(task, path, peer_id, att):
    vk_session = vk_api.VkApi(token=TOKEN)
    upload = vk_api.VkUpload(vk_session)
    tasks = []
    for file in task:
        if file.split('.')[-1] in ['mp3', 'wav', 'ogg']:
            tasks.append(asyncio.create_task(
                upload_audio(os.path.join(path, file), peer_id, upload,
                             att)))
        else:
            tasks.append(asyncio.create_task(
                upload_document(os.path.join(path, file), file, peer_id, upload,
                                att)))
    await asyncio.gather(*tasks)


@app.route('/vk_bot', methods=['GET', 'POST'])
def vk_bot():
    event = request.json
    if event['type'] == 'confirmation':
        return 'd0c45cf9'
    elif event['type'] == 'message_new':
        if event['object']['message'].get('payload', '') == "{\"send\":\"1\"}":
            vk_session = vk_api.VkApi(token=TOKEN)
            vk = vk_session.get_api()
            vk.messages.send(
                message=f'работа отправлена',
                user_id=event['object']['message']['from_id'],
                peer_id=event['object']['message']['peer_id'],
                random_id=random.randint(0, 2 ** 64),
                keyboard='{"buttons":[]}')
            return 'OK'
        task_number = json.loads(event['object']['message'].get('payload', '{}')).get('task', None)
        if task_number is not None:
            task_number = int(task_number)
            student, test = get_student_test_by_vk_id(str(event['object']['message']['from_id']))
            path = os.path.join(app.config['UPLOAD_FOLDER'], str(test.teacher_id), str(test.test_id))

            with open(os.path.join(path, f'{test.test_id}.json'), mode='rt') as json_file:
                task = json.load(json_file)['tasks'][task_number - 1]
            with open(os.path.join(app.config['UPLOAD_FOLDER'], str(student.id), f'{test.test_id}.txt'),
                      mode='wt') as txtfile:
                txtfile.write(str(task_number))
            vk_session = vk_api.VkApi(token=TOKEN)
            vk = vk_session.get_api()
            att = []
            asyncio.run(f(task['extra_files'], path, event['object']['message']['peer_id'], att))
            vk.messages.send(
                message=create_message_files(task, task_number),
                user_id=event['object']['message']['from_id'],
                peer_id=event['object']['message']['peer_id'],
                attachment=att,
                random_id=random.randint(0, 2 ** 64))
            return 'OK'
        else:
            student, test = get_student_test_by_vk_id(str(event['object']['message']['from_id']))
            filenames = []
            for attachment in event['object']['message']['attachments']:
                if attachment['type'] == 'video':
                    event['object']['message']['text'] += '\n' + attachment['video']['player']
                else:
                    if attachment['type'] == 'photo':
                        filename = 'photo' + str(attachment['photo']['id']) + '.jpg'
                        for size in attachment['photo']['sizes']:
                            if size['type'] in 'yz':
                                url = size['url']
                    elif attachment['type'] == 'audio_message':
                        url = attachment['audio_message']['link_mp3']
                        filename = 'audio_message' + str(attachment['audio_message']['id']) + '.mp3'
                    elif attachment['type'] == 'doc':
                        url = attachment['doc']['url']
                        filename = attachment['doc']['title']
                    else:
                        continue

                    with open(os.path.join(app.config['UPLOAD_FOLDER'], str(student.id), filename), mode='wb') as file:
                        file.write(requests.get(url).content)
                    filenames.append(filename)
            with open(os.path.join(app.config['UPLOAD_FOLDER'], str(student.id), f'{test.test_id}.txt'),
                      mode='rt') as txtfile:
                task_number = int(txtfile.read().strip('\n'))
            with open(os.path.join(app.config['UPLOAD_FOLDER'], str(student.id), f'{test.test_id}.json'),
                      mode='rt') as jsonfile:
                data = json.load(jsonfile)
            data['answers'][int(task_number) - 1] = {
                "answer": event['object']['message']["text"],
                "extra_files": filenames
            }
            with open(os.path.join(app.config['UPLOAD_FOLDER'], str(student.id), f'{test.test_id}.json'),
                      mode='wt') as jsonfile:
                json.dump(data, jsonfile)
            vk_session = vk_api.VkApi(token=TOKEN)
            vk = vk_session.get_api()
            vk.messages.send(
                message=f'ответ на задание {task_number} добавлен\nможете переходить к другому вопросу',
                user_id=event['object']['message']['from_id'],
                peer_id=event['object']['message']['peer_id'],
                random_id=random.randint(0, 2 ** 64))

    return 'OK'


if __name__ == '__main__':
    tests_begun = set()
    TOKEN = "0b5f2faf850401db633f8ef48e3c1490e18590b16b69ee76520712ca09a7265afa06ed3149fe846109671"
    port = int(os.environ.get("PORT", 5000))
    db_session.global_init("users_database.db")
    app.run(host='0.0.0.0', port=port)
