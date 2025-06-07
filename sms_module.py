import os
from dotenv import load_dotenv

def send_sms_twilio(message):
    from twilio.rest import Client
    load_dotenv() 

    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_FROM_NUMBER')
    to_number = os.getenv('TWILIO_TO_NUMBER')

    if not all([account_sid, auth_token, from_number, to_number]):
        print("⚠️ Twilio environment set up incomplete")
        return

    client = Client(account_sid, auth_token)
    
    # ✅ 正确地捕获返回对象
    msg = client.messages.create(
        body=message,
        from_=from_number,
        to=to_number
    )
    print("✅ Twilio message sent, SID:", msg.sid)


# ---- 统一调用接口 ----
def send_notification(message):
    send_sms_twilio(message)
    
