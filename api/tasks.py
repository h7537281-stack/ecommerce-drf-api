from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_order_confirmation_email(order_id, customer_email):
    subject = f"تأكيد الطلب رقم #{order_id}"
    message = f"شكراً لتسوقك معنا! تم تأكيد طلبك رقم #{order_id} بنجاح."
    from_email = 'no-reply@ecommerce.com'
    
    send_mail(subject, message, from_email, [customer_email])
    return f"Email sent for order {order_id}"
