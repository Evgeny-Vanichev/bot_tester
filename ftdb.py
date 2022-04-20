import os

from data import db_session
from data.users import Users
from itertools import product
from static.tools.tools import transliterate


def register_user(name, surname, contact_type='vk', contact_link='406386837'):
    db_sess = db_session.create_session()
    n3 = transliterate(name[:4])
    s3 = transliterate(surname[:4])
    login = f'{n3}{s3}'
    user = Users(
        name=name,
        surname=surname,
        email=f'{login}@mail.ru',
        type=2,
        contact_type=contact_type,
        contact_link=contact_link
    )
    user.set_password(f'{n3}${s3}2')
    db_sess.add(user)
    db_sess.commit()
    os.mkdir(
        os.path.join(os.getcwd(), 'static', 'user_data', str(user.id))
    )
    print(name, surname, "успешно зарегистрирован")


db_session.global_init("db/users_database.db")
students_names = [
    'Василий',
    'Иван',
    'Петр',
    'Григорий',
    'Павел',
    'Эрен'
]
students_surnames = [
    'Смирнов',
    'Иванов',
    'Петров',
    'Дуров'
]
for name, surname in product(students_names, students_surnames):
    register_user(name, surname)
user = Users(
    name="Евгений",
    surname="Ваничев",
    email="mail@mail.com",
    type=1,
    contact_type="vk",
    contact_link="vk.com"
)
user.set_password('3may2018')
db_sess = db_session.create_session()
db_sess.add(user)
db_sess.commit()