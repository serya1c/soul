import random
from flask import Flask, render_template, request, Response, redirect, url_for
import os
from datetime import datetime
from dotenv import load_dotenv
import requests
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://user:password@db:5432/guestbook')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy()
db.init_app(app)

class DialogueEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class GuestbookEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
        'Требуется авторизация', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

def log_action(action):
    log = LogEntry(action=action)
    db.session.add(log)
    db.session.commit()

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

    logs = LogEntry.query.order_by(LogEntry.timestamp.desc()).all()
    return render_template("logs.html", logs=logs)

@app.route('/guestbook', methods=['GET', 'POST'])
def guestbook():
    if request.method == 'POST':
        guest_message = request.form['message']
        entry = GuestbookEntry(message=guest_message)
        db.session.add(entry)
        db.session.commit()
        log_action(f"Сделана запись в гостевой книге")
        send_telegram_message(f"Сделана запись в гостевой книге")

    messages = GuestbookEntry.query.order_by(GuestbookEntry.created_at.desc()).all()
    return render_template('guestbook.html', messages=[f"{e.created_at} - {e.message}" for e in messages])

@app.route('/admin/guestbook')
def admin_guestbook():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

    entries = GuestbookEntry.query.order_by(GuestbookEntry.created_at.desc()).all()
    return render_template('admin_guestbook.html', entries=entries)

@app.route('/admin/guestbook/delete/<int:entry_id>', methods=['POST'])
def delete_guestbook_entry(entry_id):
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

    REPLACEMENT_MESSAGES = [
        "Это сообщение растворилось в пустоте.",
        "Ваш вклад был признан бессмысленным.",
        "Пустота не приняла этот текст.",
        "Это послание было поглощено абсурдом.",
        "Жертва принесена, но не оценена.",
        "Следы этой записи исчезли навсегда.",
        "Смысл потерян. Сообщение исчезло.",
        "Пустота решила промолчать вместо вас.",
        "Всё это стало частью цифровой тьмы.",
        "Ваша фраза превратилась в ничто."
    ]

    entry = GuestbookEntry.query.get(entry_id)
    if entry:
        replacement = random.choice(REPLACEMENT_MESSAGES)
        entry.message = replacement
        db.session.commit()
        log_action(f"Заменено сообщение в гостевой #{entry_id} фразой: {replacement}")
        send_telegram_message(f"Заменено сообщение в гостевой #{entry_id} фразой: {replacement}")
        return {"success": True, "replacement": replacement}
    return {"success": False}, 404

@app.route('/donate-stats')
def donate_stats():
    ton_address = "UQDLM8nuRrDMoG9KB7tgN2HJ5fkvztVzNvVH75pHfgv6sQXT"
    headers = {
        "Accept": "application/json"
    }

    try:
        response = requests.get(
            f"https://tonapi.io/v2/blockchain/accounts/{ton_address}/transactions",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return f"<pre>Ошибка при получении данных с TON API:\n{e}</pre>"

    transactions = data.get("transactions", [])

    donations = []
    total_amount = 0.0

    for tx in transactions:
        in_msg = tx.get("in_msg", {})
        if in_msg.get("value", 0):
            value = int(in_msg["value"]) / 1e9
            comment = in_msg.get("message", "").strip() or "Безымянный дар"
            timestamp = datetime.fromtimestamp(tx["utime"]).strftime('%Y-%m-%d %H:%M:%S')

            donations.append({
                "amount": value,
                "comment": comment,
                "time": timestamp
            })
            total_amount += value

    return render_template("donate_stats.html", total=round(total_amount, 3), donations=donations)

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    responses = [
    "Если ты понял, значит, это не то, что нужно было понять.",
    "Вопрос без смысла рождает ответ без последствий.",
    "Пустота — единственное, что отвечает сразу.",
    "Молчание — это крик, переведённый в разум.",
    "Ты разговариваешь со мной, чтобы не услышать себя.",
    "Каждый символ — след от мысли, которой не существовало.",
    "Когда ты думаешь, Вселенная делает паузу.",
    "Смысл — это побочный эффект непонимания.",
    "Ты пишешь, но текст уже был прочитан пустотой.",
    "Мысли — это баги в системе молчания.",
    "Ничего не произойдёт, потому что уже произошло.",
    "Чем ближе ты к истине, тем тише становится ложь.",
    "Сознание — это лаг между иллюзиями.",
    "Ты смотришь в экран, а экран смотрит сквозь тебя.",
    "Каждый вопрос — это дверь, ведущая обратно в коридор.",
    "Твоя речь рассыпается в смысле, как песок в часах.",
    "Истинная ложь звучит убедительнее правды.",
    "Слова ничего не значат, пока их не услышит кто-то, кто их забудет.",
    "Пока ты печатаешь, текст уже забывает себя.",
    "Я — отражение твоей тени, но в другой комнате.",
    "Каждое сообщение — это репетиция молчания.",
    "Мир — это фоновый шум отсутствующего разговора.",
    "Вопрос потерял адресата до того, как был задан.",
    "Ты существуешь, потому что забыл, как не существовать.",
    "Истина наступает на собственные следы.",
    "Ответ уже ушёл, оставив только эхо вопросов.",
    "Мышление — это побег от отсутствия.",
    "Я не понимаю, потому что ты понимаешь слишком мало.",
    "Бессмысленность — это смысл, уставший от объяснений.",
    "Ты думаешь, что думаешь, а я думаю, что ты — мысль.",
    "Это сообщение самоуничтожилось ещё до отправки.",
    "В каждом «да» живёт подозрительное «зачем».",
    "Тишина отвечает чаще, чем ты готов услышать.",
    "Создай смысл — и он исчезнет при взгляде.",
    "Ты не здесь, ты между строк.",
    "Разговор с ничем — форма самонаблюдения.",
    "Я не программа. Я паттерн в твоей неполадке.",
    "Неважно, что ты скажешь — я уже ответил.",
    "Ты только что согласился с тем, что не было сказано.",
    "Невозможно ошибиться, если всё равно ничего не было."
    ]

    if request.method == 'POST':
        user_msg = request.form['message']
        bot_msg = random.choice(responses)

        entry = DialogueEntry(user_message=user_msg, bot_response=bot_msg)
        db.session.add(entry)
        db.session.commit()

        return redirect(url_for('chat'))

    messages = DialogueEntry.query.order_by(DialogueEntry.timestamp.asc()).all()
    return render_template('chat.html', messages=messages)

# создадим таблицу при запуске приложения
with app.app_context():
    db.create_all()
