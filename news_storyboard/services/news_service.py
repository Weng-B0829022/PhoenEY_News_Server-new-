# news_storyboard/services/news_service.py

from .newsapi import run_newsapi
from .news_gen import run_news_gen
from .news_gen_img import run_news_gen_img

def execute_newsapi(keyword):
    try:
        result = run_newsapi(keyword)
        return {"status": "success", "message": f"NewsAPI execution completed for keyword: {keyword}", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def execute_news_gen():
    try:
        result = run_news_gen()
        return {"status": "success", "message": "News generation completed", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
def execute_news_gen_img():
    try:
        result = run_news_gen_img()
        return {"status": "success", "message": "News generation completed", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}