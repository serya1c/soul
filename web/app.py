from flask import Flask, render_template, request, Response, redirect, url_for
import os
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

app = Flask(__name__)

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
        'Требуется авторизация', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def log_action(action):
    with open("logs.txt", "a") as log:
        log.write(f"[{datetime.utcnow()}] {action}\n")

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    requests.post(url, data=payload)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

    file_path = 'index.html'
    message = ''
    if request.method == 'POST':
        new_content = request.form['content']
        with open(file_path, 'w') as f:
            f.write(new_content)
        log_action("Content updated by admin.")
        send_telegram_message("Сайт был обновлён.")
        message = 'Обновлено!'
    with open(file_path, 'r') as f:
        content = f.read()
    return render_template('admin.html', content=content, message=message)

@app.route('/logs')
def logs():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

    with open("logs.txt", "r") as f:
        return "<pre>" + f.read() + "</pre>"

@app.route('/guestbook', methods=['GET', 'POST'])
def guestbook():
    if request.method == 'POST':
        guest_message = request.form['message']
        with open('guestbook.txt', 'a') as f:
            f.write(f"{datetime.utcnow()} - {guest_message}\n")
        log_action(f"Сделана запись в гостевой книге")
        send_telegram_message(f"Сделана запись в гостевой книге")

    with open('guestbook.txt', 'r') as f:
        messages = f.readlines()
    return render_template('guestbook.html', messages=messages)

@app.route('/admin/guestbook')
def admin_guestbook():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

    with open('guestbook.txt', 'r') as f:
        messages = f.readlines()
    return render_template('admin_guestbook.html', messages=messages, enumerate=enumerate)

@app.route('/admin/guestbook/delete/<int:entry_id>', methods=['POST'])
def delete_guestbook_entry(entry_id):
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

    with open('guestbook.txt', 'r') as f:
        messages = f.readlines()

    if 0 <= entry_id < len(messages):
        del messages[entry_id]
        with open('guestbook.txt', 'w') as f:
            f.writelines(messages)
        log_action(f"Удалена запись гостевой книги #{entry_id}")
        send_telegram_message(f"Удалена запись гостевой книги #{entry_id}")

    return redirect(url_for('admin_guestbook'))
