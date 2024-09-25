# news_storyboard/services/news_service.py

from .newsapi import run_newsapi
from .news_gen import run_news_gen
from .news_gen_img import run_news_gen_img
from .news_composite_video import run_news_composite_video

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
    
def execute_news_gen_img(index):
    try:
        result = run_news_gen_img(index)
        return {"status": "success", "message": "News generation completed", "data": result}
    except Exception as e:
        print(str(e))
        return {"status": "error", "message": str(e)}
    
def execute_news_composite_video(index):
    try:
        result = run_news_composite_video(index)
        return {"status": "success", "message": f"News video generation completed for index: {index}", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}