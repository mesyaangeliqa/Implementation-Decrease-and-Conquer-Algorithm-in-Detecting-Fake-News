# app.py
from flask import Flask, render_template, request
import requests
import xml.etree.ElementTree as ET
import pandas as pd
from urllib.parse import urljoin
from search_functions import string_to_binary, search_in_dataframe, find_similar_binary, check_news_veracity

app = Flask(__name__)

# Daftar URL yang ingin Anda tangani
urls = [
    'https://www.cnbcindonesia.com/rss',
    'https://newsapi.org/v2/top-headlines?country=id&apiKey=fc35180da5dd46f4a404c0de51955d2e',
    'https://www.antaranews.com/rss/terkini.xml',
    'https://www.cnbcindonesia.com/rss',
    'https://www.cnnindonesia.com/rss',
    'https://lapi.kumparan.com/v2.0/rss/',
    'https://sindikasi.okezone.com/index.php/rss/1/RSS2.0',
    'https://www.republika.co.id/rss',
    'https://www.suara.com/rss',
    'http://rss.tempo.co/',
    'https://www.vice.com/id/rss?locale=id_id',
    'https://www.voaindonesia.com/api/zmgqoe$moi',
]

# Inisialisasi DataFrame
df = pd.DataFrame(columns=['source', 'url', 'title', 'title_binary', 'link'])

# Loop untuk setiap URL
for url in urls:
    response = requests.get(url)

    if response.status_code == 200:
        # Mengecek apakah respons berupa XML
        if 'xml' in response.headers.get('Content-Type', ''):
            # Membuat pohon XML dari respons
            root = ET.fromstring(response.content)

            # Menemukan dan mengekstrak judul artikel
            articles = root.findall('.//item')

            # Menambahkan data ke DataFrame
            for article in articles:
                title = article.find('title').text
                link = article.find('link').text
                full_link = urljoin(url, link) if link else 'Link not available'
                new_row = {'source': 'URL', 'url': url, 'title': title, 'title_binary': string_to_binary(title), 'link': full_link}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        else:
            # Jika respons berupa JSON
            data = response.json()

            # Mendapatkan daftar artikel
            articles = data.get('articles', [])

            # Menambahkan data ke DataFrame
            for article in articles:
                title = article.get('title', 'Title not available')
                link = article.get('url', 'Link not available')
                new_row = {'source': 'URL', 'url': url, 'title': title, 'title_binary': string_to_binary(title), 'link': link}
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    else:
        print(f"Error {response.status_code} for URL {url}: {response.text}")

# Baca file CSV
df_csv = pd.read_csv('indonesian_hoax_news.csv')

# Menambahkan kolom 'source' dan mengisinya dengan 'CSV'
df_csv['source'] = 'CSV'

# Konversi judul ke dalam bentuk biner
df_csv['title_binary'] = df_csv['title'].apply(string_to_binary)

# Gabungkan DataFrame dari URL dan DataFrame dari CSV
df = pd.concat([df, df_csv], ignore_index=True)

# Route untuk halaman utama
@app.route('/')
def home():
    return render_template('home.html')

# Menangani permintaan pencarian dari formulir HTML
@app.route('/search', methods=['POST'])
def search():
    search_term = request.form['judul']
    matching_rows = search_in_dataframe(df, search_term)

    if matching_rows.empty:
        similar_row = find_similar_binary(df, string_to_binary(search_term))
        if similar_row is not None:
            similar_news = [{'title': similar_row['title'], 'link': get_link_from_row(similar_row)}]
            return render_template('home.html', similar_news=similar_news)
        else:
            return render_template('home.html', no_result=True)
    else:
        correct_news = []
        for _, row in matching_rows.iterrows():
            title = row['title']
            link = get_link_from_row(row)
            source = row['source']  # Menambahkan informasi sumber data
            is_hoax = check_news_veracity(title, source)
            correct_news.append({'title': title, 'link': link, 'is_hoax': is_hoax})
        return render_template('home.html', correct_news=correct_news)

# Fungsi untuk mendapatkan link dari baris DataFrame
def get_link_from_row(row):
    if row['source'] == 'URL':
        return row['link']
    elif row['source'] == 'CSV':
        return row['url']
    else:
        return 'Link not available'

if __name__ == '__main__':
    app.run(debug=True)
