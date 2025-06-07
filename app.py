from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, session
from notify import start_scheduler
import sqlite3
from datetime import datetime, timedelta
from io import StringIO
import csv
import random

app = Flask(__name__)
app.secret_key = "🌸lovely-secret🌸"  
app.permanent_session_lifetime = timedelta(minutes=30)
DB_FILE = "period.db"

USERNAME = "your-username"
PASSWORD = "your-password"

@app.route("/login", methods=["GET", "POST"])
def login():
    images = [
        "image/image1.png",
        "image/image2.png",
        "image/image3.png",
        "image/image4.png",
        "image/image5.png"
    ]
    selected_image = random.choice(images)

    if request.method == "POST":
        name = request.form.get("username")
        pw = request.form.get("password")
        if name == USERNAME and pw == PASSWORD:
            session["user"] = name
            session.permanent = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="❌ Wrong user name or password", background=selected_image)

    return render_template("login.html", background=selected_image)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE
        )
    ''')
    try:
        c.execute("ALTER TABLE periods ADD COLUMN note TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def add_periods(start_date, end_date, note=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    current = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    first = True
    while current <= end:
        try:
            if first:
                c.execute("INSERT INTO periods (date, note) VALUES (?, ?)", (current.strftime("%Y-%m-%d"), note))
                first = False
            else:
                c.execute("INSERT INTO periods (date) VALUES (?)", (current.strftime("%Y-%m-%d"),))
        except sqlite3.IntegrityError:
            pass
        current += timedelta(days=1)
    conn.commit()
    conn.close()

def delete_period(date):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM periods WHERE date = ?", (date,))
    conn.commit()
    conn.close()

def get_all_dates():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT date FROM periods ORDER BY date DESC")
    rows = c.fetchall()
    conn.close()
    return [datetime.strptime(row[0], "%Y-%m-%d") for row in rows]

def predict_next(dates):
    if len(dates) < 3:
        return None
    intervals = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
    avg = round(sum(intervals) / len(intervals))
    return dates[0] + timedelta(days=avg)

@app.route("/", methods=["GET"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    init_db()
    dates = get_all_dates()
    predicted = predict_next(dates)
    events = [{
        "title": "Period",
        "start": d.strftime("%Y-%m-%d"),
        "allDay": True,
        "backgroundColor": "#ff8fa3",
        "borderColor": "#ff8fa3"
    } for d in dates]
    record_dates_str = [d.strftime('%Y-%m-%d') for d in dates]

    return render_template(
        "index.html",
        records=dates,
        predicted=predicted,
        events=events,
        now=datetime.now(),
        record_dates_str=record_dates_str
    )

@app.route("/add", methods=["POST"])
def add():
    start = request.form.get("start_date")
    end = request.form.get("end_date")
    note = request.form.get("note", "")
    if start and end:
        add_periods(start, end, note)
    return jsonify({"success": True})

@app.route("/delete", methods=["POST"])
def delete():
    date = request.form.get("date")
    if date:
        delete_period(date)
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route("/stats")
def stats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT date FROM periods")
    records = [datetime.strptime(row[0], '%Y-%m-%d').date() for row in c.fetchall()]
    conn.close()

    if not records:
        return jsonify({
            "last_period": "-",
            "days_since": "-",
            "total_days": 0,
            "avg_interval": "-",
            "next_period": "-",
            "ovulation_countdown": "-"
        })

    records.sort()
    distinct_periods = []
    prev = None
    for date in records:
        if not prev or (date - prev).days > 1:
            distinct_periods.append(date)
        prev = date

    last_period_start = max(distinct_periods)
    today = datetime.now().date()

    if len(distinct_periods) >= 2:
        intervals = [(distinct_periods[i] - distinct_periods[i - 1]).days for i in range(1, len(distinct_periods))]
        avg_interval = round(sum(intervals) / len(intervals))
        predicted_next = last_period_start + timedelta(days=avg_interval)
        ovulation_day = last_period_start + timedelta(days=14)
        predicted_next_str = predicted_next.strftime('%Y-%m-%d')
        ovulation_countdown = max((ovulation_day - today).days, 0)
    else:
        avg_interval = "-"
        predicted_next_str = "-"
        ovulation_countdown = "-"

    return jsonify({
        "last_period": last_period_start.strftime('%Y-%m-%d'),
        "days_since": (today - last_period_start).days,
        "total_days": len(distinct_periods),
        "avg_interval": avg_interval,
        "next_period": predicted_next_str,
        "ovulation_countdown": ovulation_countdown
    })

@app.route("/download_records")
def download_records():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT date, note FROM periods ORDER BY date")
    rows = [(datetime.strptime(row[0], "%Y-%m-%d").date(), row[1]) for row in c.fetchall()]
    conn.close()

    merged = []
    if rows:
        start, note = rows[0]
        prev = start
        for i in range(1, len(rows)):
            curr, curr_note = rows[i]
            if (curr - prev).days == 1:
                prev = curr
            else:
                merged.append((start, prev, note))
                start, note = curr, curr_note
                prev = curr
        merged.append((start, prev, note))

    merged.sort(key=lambda x: x[0], reverse=True)

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["Period", "Note"])
    for start, end, note in merged:
        if start == end:
            period_str = start.strftime("%Y.%m.%d")
        else:
            period_str = f"{start.strftime('%Y.%m.%d')} - {end.strftime('%Y.%m.%d')}"
        writer.writerow([period_str, note or ""])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=period_records.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route("/test_twilio")
def test_twilio():
    from notify import send_test_sms
    send_test_sms()
    return "Tried sending message"

if __name__ == "__main__":
    start_scheduler()
    app.run(debug=True)
