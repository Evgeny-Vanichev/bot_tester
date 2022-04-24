import requests
import time


def kick_server():
    print(requests.get('http://baikapp.herokuapp.com/check_db'))


while True:
    kick_server()
    time.sleep(60)
