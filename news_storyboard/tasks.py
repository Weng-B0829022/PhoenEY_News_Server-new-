from celery import shared_task
from .services.news_service import execute_newsapi, execute_news_gen

@shared_task
def task_run_newsapi(keyword):
    result = execute_newsapi(keyword)
    print(result)
    return f"NewsAPI executed for keyword: {keyword}"

@shared_task
def task_run_news_gen():
    result = execute_news_gen()
    print(result)
    return "News generation executed"