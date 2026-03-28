from celery import shared_task

from .utils import Util


@shared_task
def send_reset_password_email_task(data):
    Util.send_email(data)
