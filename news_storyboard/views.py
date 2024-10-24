from django.shortcuts import render
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create your views here.
def log_and_print(message):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    formatted_message = f"{timestamp} - {message}"
    try:
        logger.info(formatted_message)
    except Exception as e:
        print(f"日志記錄失敗: {str(e)}")
