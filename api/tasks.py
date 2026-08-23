from celery import shared_task
import time
@shared_task
def send_order_confirmation_email(user_email):
    print(f"starting to send email to {user_email}")
    time.sleep(5)
    print(f"email successfuly send to {user_email}")
    return f"email send to {user_email}"

