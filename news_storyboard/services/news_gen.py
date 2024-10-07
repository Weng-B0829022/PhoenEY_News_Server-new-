import os
from dotenv import load_dotenv
from openai import OpenAI
from .newsapi import NewsAPI
import json
from django.conf import settings
import os
import json


def access_gpt(messages):
    load_dotenv(os.path.join(settings.BASE_DIR, '.env'))
    client = OpenAI(
        api_key=os.environ.get('OPENAI_API_KEY'),
    )

    chat_completion = client.chat.completions.create(
        messages=messages,
        model='gpt-4o',
    )

    return chat_completion.choices[0].message.content


def read_news_json(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        news = json.load(file)
        return news


def extract_news_fact(articles):
    integrated_news_list = []

    PROMPT_EXTRACT_AND_INTEGRATE_1 = '# Step 1\n\nArticle 1: '
    PROMPT_EXTRACT_AND_INTEGRATE_2 = None
    with open('prompt_extract_and_integrate/2.txt', 'r', encoding='utf-8') as file:
        PROMPT_EXTRACT_AND_INTEGRATE_2 = file.read()
    PROMPT_EXTRACT_AND_INTEGRATE_3 = None
    with open('prompt_extract_and_integrate/3.txt', 'r', encoding='utf-8') as file:
        PROMPT_EXTRACT_AND_INTEGRATE_3 = file.read()

    for article in articles:
        content = article.get('content')

        gpt_messages = []

        # Extract news fact
        prompt_extract_fact = (
            f'{PROMPT_EXTRACT_AND_INTEGRATE_1}'
            f'{content}\n'
            f'{PROMPT_EXTRACT_AND_INTEGRATE_2}'
        )

        gpt_messages.append({
            'role': 'user',
            'content': prompt_extract_fact,
        })

        extracted_fact = access_gpt(gpt_messages)
        print(extracted_fact)

        print('\n\n--\n\n')

        gpt_messages.append({
            'role': 'user',
            'content': extracted_fact,
        })

        # Integrate multiple similar news
        prompt_integrate_news = PROMPT_EXTRACT_AND_INTEGRATE_3
        gpt_messages.append({
            'role': 'user',
            'content': prompt_integrate_news,
        })
        integrated_news = access_gpt(gpt_messages)
        print(integrated_news)

        integrated_news_list.append(integrated_news)

    return integrated_news_list



def extract_keyword_news_fact(articles):
    base_path = os.path.join(settings.BASE_DIR, 'news_storyboard', 'services', 'prompt_extract_and_integrate_keyword')

    def read_file(filename):
        file_path = os.path.join(base_path, filename)
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    PROMPT_EXTRACT_AND_INTEGRATE_1 = '# Step 1\n\nArticle 1: '
    PROMPT_EXTRACT_AND_INTEGRATE_2 = read_file('2.txt')
    PROMPT_EXTRACT_AND_INTEGRATE_3 = read_file('3.txt')
    PROMPT_EXTRACT_AND_INTEGRATE_4 = read_file('4.txt')
    PROMPT_EXTRACT_AND_INTEGRATE_5 = read_file('5.txt')

    print("Step 1: Reading prompts completed")

    content = ''
    for article in articles:
        content = content + article.get('content')

    print("Step 2: Concatenated article contents")

    gpt_messages = []

    # Extract news fact
    prompt_extract_fact = (
        f'{PROMPT_EXTRACT_AND_INTEGRATE_1}'
        f'{content}\n'
        f'{PROMPT_EXTRACT_AND_INTEGRATE_2}'
    )

    gpt_messages.append({
        'role': 'user',
        'content': prompt_extract_fact,
    })

    extracted_fact = access_gpt(gpt_messages)
    print("Step 3: Extracted news fact")
    print(f"Extracted fact: {extracted_fact[:100]}...") # Print first 100 characters
 
    gpt_messages.append({
        'role': 'user',
        'content': extracted_fact,
    })

    # Integrate multiple related news
    prompt_integrate_news = PROMPT_EXTRACT_AND_INTEGRATE_3
    gpt_messages.append({
        'role': 'user',
        'content': prompt_integrate_news,
    })
    integrated_news = access_gpt(gpt_messages)
    print("Step 4: Integrated multiple related news")
    print(f"Integrated news: {integrated_news[:100]}...") # Print first 100 characters

    # Generate derivative news articles
    prompt_derivative_articles = PROMPT_EXTRACT_AND_INTEGRATE_4
    gpt_messages.append({
        'role': 'user',
        'content': prompt_derivative_articles,
    })
    derivative_articles = access_gpt(gpt_messages)
    print("Step 5: Generated derivative news articles")
    print(f"Derivative articles: {derivative_articles[:100]}...") # Print first 100 characters
    
    # Parse the JSON string returned by GPT
    try:
        derivative_articles_json = json.loads(derivative_articles)
        print("Step 6: Successfully parsed JSON from GPT response")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw GPT response: {derivative_articles}")
        raise

    print("Derivative articles JSON structure:")
    print(json.dumps(derivative_articles_json, indent=2, ensure_ascii=False)[:500] + "...") # Print first 500 characters

    derivative_articles_path = os.path.join(settings.BASE_DIR, 'news_storyboard', 'services', 'derivative_articles.json')
    with open(derivative_articles_path, 'w', encoding='utf-8') as file:
        json.dump(derivative_articles_json, file, ensure_ascii=False, indent=4)
    print(f"Step 7: Wrote derivative articles to {derivative_articles_path}")

    # Generate storyboards
    output = derivative_articles_json
    for i, article in enumerate(output['articles'], 1):
        prompt_generate_storyboard = 'Article: ' + article.get('content') + PROMPT_EXTRACT_AND_INTEGRATE_5
        gpt_messages = [{
            'role': 'user',
            'content': prompt_generate_storyboard,
        }]
        storyboard = access_gpt(gpt_messages)
        article['storyboard'] = storyboard
        print(f"Step 8.{i}: Generated storyboard for article {i}")
        print(f"Storyboard for article {i}: {storyboard[:100]}...") # Print first 100 characters

    print("Step 9: Completed processing all articles")
    return output

def fetch_financial_data():
    PROMPT_FINANCIAL_DATA = None
    with open('prompt_financial_data.txt', 'r', encoding='utf-8') as file:
        PROMPT_FINANCIAL_DATA = file.read()

    gpt_messages = []
    gpt_messages.append({
        'role': 'user',
        'content': PROMPT_FINANCIAL_DATA,
    })

    financial_data = access_gpt(gpt_messages)
    return financial_data

    
def run_news_gen():# # Get Taiwan news
    # taiwan_news = news_api.get_taiwan_news()
    # with open('taiwan_news.json', 'w') as file:
    #     json.dump(taiwan_news, file, ensure_ascii=False, indent=4)

    # # Get international news
    # international_news = news_api.get_international_news()
    # with open('international_news.json', 'w') as file:
    #     json.dump(international_news, file, ensure_ascii=False, indent=4)

    # Get news based on keyword
    keyword_taiwan_news = read_news_json('keyword_taiwan_news.json')
    derivative_articles_and_storyboards = extract_keyword_news_fact(keyword_taiwan_news)
    with open('derivative_articles_and_storyboards.json', 'w', encoding='utf-8') as file:
        json.dump(derivative_articles_and_storyboards, file, ensure_ascii=False, indent=4)
    return derivative_articles_and_storyboards

if __name__ == '__main__':
    run_news_gen()  # 這裡可以保留原本的測試邏輯