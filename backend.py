from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from functools import lru_cache
import concurrent.futures
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Включаем CORS для всего приложения

#@lru_cache(maxsize=None)
def get_article_data(session, link):
    response_page = session.get(link).text
    soup_page = BeautifulSoup(response_page, 'lxml')
    block_content = soup_page.find('div', id="site-content")
    articles = block_content.find_all('article', class_="col-md-8 col-md-push-4")
    for article in articles:
        date_element = article.find('span', class_="posted-date")
        title_element = article.find('h1', class_="single-title")
        content_element = article.find('div', class_="single-entry-summary")
        if date_element and title_element and content_element:
            return [date_element.text.strip().replace("\xa0", " "),
                    title_element.text.strip().replace("\xa0", " "),
                    content_element.text.strip().replace("\n", "").replace("\xa0", " ")]
    return None

def remark(page_number, category_id):
    menu = ['sobytiya', 'anons', 'obyavleniya', 'about us', 'blog']
    data_list = []
    base_url = "https://dk-lesnoy.ru/"

    if category_id in [0, 1, 2, 4]:
        link = f"https://dk-lesnoy.ru/category/{menu[category_id]}/page/{page_number}"
        with requests.Session() as session:
            response = session.get(link).text
            soup = BeautifulSoup(response, 'lxml')
            block = soup.find('div', id="site-content")
            links = [item.find('a')['href'] for item in block.find_all('h2', class_="entry-title")]

            with concurrent.futures.ThreadPoolExecutor() as executor:
                results = executor.map(lambda link: get_article_data(session, link), links)
                data_list.extend(result for result in results if result)

        return data_list

#     elif category_id == 3:
#         with requests.Session() as session:
#             response = session.get(base_url).text
#             soup = BeautifulSoup(response, 'lxml')
#             titles = [a.get('title', '') for a in soup.find_all('a', class_="dropdown-item")][1:]
#             subcategories = [
#                 {"title": "Наша история", "id": 5},
#                 {"title": "Клубные формирования", "id": 6},
#                 {"title": "Информация", "id": 7}
#             ]
#             return subcategories

    elif category_id == 3:
        with requests.Session() as session:
            response = session.get(base_url).text
            soup = BeautifulSoup(response, 'lxml')
            # Извлекаем ссылки, а не только заголовки
            hrefs = [a['href'] for a in soup.find_all('a', class_="dropdown-item") if a.has_attr('href')][1:]
            subcategories = [
                {"title": "Наша история", "link": hrefs[0], "id": 5},
                {"title": "Клубные формирования", "link": hrefs[1], "id": 6},
                {"title": "Информация", "link": hrefs[2], "id": 7}
            ]
            return subcategories

#     elif category_id in [5, 6, 7]:
#         response = requests.get("https://dk-lesnoy.ru/").text
#         soup = BeautifulSoup(response, 'lxml')
#         hrefs = [a['href'] for a in soup.find_all('a', class_="dropdown-item") if a.has_attr('href')][1:]
#         subcategories = [
#             {"title": "Наша история", "id": 5},
#             {"title": "Клубные формирования", "id": 6},
#             {"title": "Информация", "id": 7}
#         ]
# 
#         index = category_id - 5
#         response_page = requests.get(hrefs[index]).text
#         soup_page = BeautifulSoup(response_page, 'lxml')
#         title = subcategories[index]['title']

    elif category_id in [5, 6, 7]:
        # Используем ссылки, полученные в категории 3
        subcategories = remark(1, 3)  # получаем данные подкатегорий, включая ссылки
        index = category_id - 5
        subcategory = subcategories[index]
        response_page = requests.get(subcategory['link']).text # Используем ссылку из subcategory
        soup_page = BeautifulSoup(response_page, 'lxml')
        title = soup_page.title.text.strip() # Берём title из <title> тега страницы

        if category_id == 5:
            content = ' '.join(p.text.strip().replace("\n", "").replace("\xa0", " ") for p in soup_page.find('div', class_="elementor-widget-container").find_all('p', style="text-align: justify;"))
        elif category_id == 6:
            content = '\n'.join(p.text.strip().replace("\n", "").replace("\xa0", " ") for p in soup_page.find('div', id="mega_info_bar_2").find('div', class_="mega_content").find('p'))
            content += '\n'.join(p.text.strip().replace("\n", "").replace("\xa0", " ") for p in soup_page.find('div', class_="elementor-image-box-content"))
            content += '\n'.join(figcaption.text.strip().replace("\n", "").replace("\xa0", " ") for figcaption in soup_page.find_all('div', class_= "elementor-widget-container")[3:])
        elif category_id == 7:
            content = '\n\n'.join(p.text.strip().replace("\n", "").replace("\xa0", " ") for p in soup_page.find('div', class_="page-area").find_all('p')[:-1])
        
        return [{'title': title, 'content': content}]

@app.route('/get-data')
def get_data():
    category = int(request.args.get('category', 0))
    page = int(request.args.get('page', 1))
    data = remark(page, category)

    return jsonify({'data': data, 'has_next': len(data) >= 5 if category in [0, 1, 2, 4] else False})

# @app.route('/get-data')
# def get_data():
#     category = int(request.args.get('category', 0))
#     page = int(request.args.get('page', 1))
#     data = remark(page, category)
# 
#     if category == 3:  # About Us
#         with requests.Session() as session:
#             response = session.get("https://dk-lesnoy.ru/").text
#             soup = BeautifulSoup(response, 'lxml')
#             hrefs = [a['href'] for a in soup.find_all('a', class_="dropdown-item") if a.has_attr('href')][1:]
#             subcategories = [
#                 {"title": "Наша история", "link": hrefs[0], "id": 5},
#                 {"title": "Клубные формирования", "link": hrefs[1], "id": 6},
#                 {"title": "Информация", "link": hrefs[2], "id": 7}
#             ]
#             return jsonify({'data': subcategories, 'has_next': False})
#     else:
#         has_next = len(data) > 0 #  Простая проверка.  Вам нужно определить, есть ли следующая страница.
#         return jsonify({'data': data, 'has_next': has_next})
    

@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    # Здесь вы можете сохранить данные data, если нужно.
    # В данном случае просто возвращаем успешный ответ.
    return jsonify({'status': 'success'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

# if __name__ == '__main__':
#     app.run(debug=True, port=0)


# import socket
# 
# def find_free_port():
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#         s.bind(('', 0))  # 0 означает автоматический выбор порта
#         return s.getsockname()[1]
# 
# if __name__ == '__main__':
#     port = find_free_port()
#     print(f"Starting server on port {port}")
#     app.run(host='0.0.0.0', port=port, debug=True)


