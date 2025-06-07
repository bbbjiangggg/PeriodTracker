# notify.py
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import sqlite3
from sms_module import send_notification 

DB_FILE = "period.db"

def check_upcoming_events():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT date FROM periods ORDER BY date")
    dates = [datetime.strptime(row[0], '%Y-%m-%d').date() for row in c.fetchall()]
    conn.close()

    if len(dates) < 2:
        return

    # 找出最近的周期开始
    dates.sort()
    distinct_periods = []
    prev = None
    for date in dates:
        if not prev or (date - prev).days > 1:
            distinct_periods.append(date)
        prev = date

    if len(distinct_periods) < 2:
        return

    # 计算平均间隔和预测时间
    intervals = [(distinct_periods[i] - distinct_periods[i - 1]).days for i in range(1, len(distinct_periods))]
    avg_interval = round(sum(intervals) / len(intervals))
    last_period = distinct_periods[-1]
    predicted_next = last_period + timedelta(days=avg_interval)
    predicted_ovulation = last_period + timedelta(days=14)
    today = datetime.now().date()

    # 发提醒
    if 0 <= (predicted_ovulation - today).days <= 1:
        send_notification("🌸 Tomorrow might be your ovolution period, stay hydrated～")
    elif 0 <= (predicted_next - today).days <= 1:
        send_notification("🩸 Period is coming, rest well～")

def send_test_sms():
    send_notification("✅ Message Test: Twilio sent success？")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_upcoming_events, 'interval', hours=24)
    scheduler.start()
