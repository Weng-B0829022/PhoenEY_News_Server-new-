import json
import requests
from newspaper import Article
from typing import Dict, Any
from datetime import datetime, timedelta


API_KEY = 'a515d699b0eb4a09b3a0560df37f6074'
BASE_URL = 'https://newsapi.org/v2'


class NewsAPI:
    def __init__(self) -> None:
        self.categories = [
            'business',
            'entertainment',
            'general',
            'health',
            'science',
            'sports',
            'technology'
        ]

    def get_everything(self, keyword, date) -> Dict[str, Any]:
        url = (
            f'{BASE_URL}/everything?'
            f'apiKey={API_KEY}&'
            f'q={keyword}&'
            f'domains=ttv.com.tw,ctvnews.tw,cts.com.tw,ftvnews.com.tw,pts.org.tw,setn.com,ettoday.net,taiwanjustice.net,udn.com,storm.mg,nownews.com,cna.com.tw,thenewslens.com,appledaily.com,money.udn.com&'
            f'from={date}&' # Format: 2024-05-27
            f'sortBy=popularity&'
            f'pageSize=100&'
            f'language=zh'
        )

        response = requests.get(url)
        return json.loads(response.text)

    def get_top_headlines(self, category: str, country: str) -> Dict[str, Any]:
        url = (
            f'{BASE_URL}/top-headlines?'
            f'apiKey={API_KEY}&'
            f'category={category}&'
            f'pageSize=100&'
            f'country={country}'
        )

        response = requests.get(url)
        return json.loads(response.text)

    def get_all_top_headlines(self, country: str) -> Dict[str, Any]:
        all_top_headlines = {}
        for category in self.categories:
            top_headlines = self.get_top_headlines(category, country)
            all_top_headlines[category] = top_headlines

        return all_top_headlines

    def __fetch_article_content(self, url: str) -> str:
        article = Article(url)
        article.download()
        article.parse()

        return article.text

    def __normalize_articles(self, articles: Dict[str, str]) -> Dict[str, str]:
        normalized_data = []

        for category in articles.values():
            for article in category.get('articles', []):
                content = None
                try:
                    content = self.__fetch_article_content(article.get('url'))
                except Exception as e:
                    print(f"Error fetching content for article {article.get('url')}: {e}")
                    continue
                
                normalized_article = {
                    'title': article.get('title'),
                    'published_at': article.get('publishedAt'),
                    'url': article.get('url'),
                    'content': content
                }
                normalized_data.append(normalized_article)

        return normalized_data

    def get_taiwan_news(self) -> Dict[str, Any]:
        all_top_headlines = self.get_all_top_headlines('tw')
        normalized_articles = self.__normalize_articles(all_top_headlines)

        return normalized_articles

    def get_international_news(self) -> Dict[str, Any]:
        all_top_headlines = self.get_all_top_headlines('us')
        normalized_articles = self.__normalize_articles(all_top_headlines)

        return normalized_articles

    def get_keyword_taiwan_news(self, keyword, date) -> Dict[str, Any]:
        everything = self.get_everything(keyword, date)
        keyword_taiwan_news = { 'everything': everything }
        normalized_articles = self.__normalize_articles(keyword_taiwan_news)

        return normalized_articles


def run_newsapi(keyword):
    news_api = NewsAPI()

    # taiwan_news = news_api.get_taiwan_news()
    # print(taiwan_news)
    # with open('taiwan_news.json', 'w') as file:
    #     json.dump(taiwan_news, file, ensure_ascii=False, indent=4)

    # international_news = news_api.get_international_news()
    # with open('international_news.json', 'w') as file:
    #     json.dump(international_news, file, ensure_ascii=False, indent=4)


    date_7_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    keyword_taiwan_news = news_api.get_keyword_taiwan_news(keyword, date_7_days_ago)
    with open('keyword_taiwan_news.json', 'w') as file:
        json.dump(keyword_taiwan_news, file, ensure_ascii=False, indent=4)
    return keyword_taiwan_news

if __name__ == '__main__':
    run_newsapi('台積電')  # 這裡可以保留原本的測試邏輯
