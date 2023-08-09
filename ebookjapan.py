from time import sleep
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import datetime
from gspread_dataframe import set_with_dataframe

# 削除対象の単語
unwanted_patterns = ['（※ただしエッチも含みます）', '漫画版　',
                     '@COMIC', ':', '：', '［1話売り］', '[1話売り]', '(合本版)','（合本版）','（コミック）', '(コミック)'
                     ]
target_words = ['巻', '話', ')', '）']
target_words_2 = ['story', 'vol', 'Vol', '分冊版', '（分冊版）', '#']
target_words_3 = ['(', '（']
# アクセス対象のURL
urls = ['https://ebookjapan.yahoo.co.jp/exclusive/',
        'https://ebookjapan.yahoo.co.jp/exclusive/tl/',
        'https://ebookjapan.yahoo.co.jp/exclusive/bl/',
        ]
# 巻数削除用の関数定義
def remove_text_until_space(text, target_word):
    index = text.rfind(target_word)  # 特定の文字列の最後の出現位置を取得
    if index != -1:
        before_space = text.rfind(' ', 0, index)  # スペースの直前の位置を取得
        if before_space != -1:
            return text[:before_space + 1]  # スペースの直後までの部分を返す
    return text  # 特定の文字列が見つからない場合は元の文字列を返す

def remove_text_after_keyword(text, keyword):
    index = text.find(keyword)  # 特定のキーワードの最初の出現位置を取得
    if index != -1:
        return text[:index]  # キーワードの位置までの部分を返す
    return text  # キーワードが見つからない場合は元の文字列を返す

# スクレイピングの関数定義
def ranking(url, unwanted_patterns):
    r = requests.get(url)
    sleep(1)
    soup = BeautifulSoup(r.content, 'lxml')

    # 同じクラス名を持つdivタグのリストを取得
    ul_elements = soup.select('ul.slider-body__list')

    # 上位2つの要素を取得
    top_two_ul = ul_elements[:2]

    comic_url_list = []
    # 上位2つの要素を表示
    for ul in top_two_ul:
        comics = ul.select('li')
        sleep(1)
        for comic in comics:
            comic_url= 'https://ebookjapan.yahoo.co.jp' + comic.select_one('a').get('href')
            sleep(1)
            comic_url_list.append(comic_url)
    
    sleep(1)

    d_list=[]
    for comic_url in comic_url_list:
        comic_r = requests.get(comic_url)
        sleep(1)
        comic_soup = BeautifulSoup(comic_r.content, 'lxml')

        title = comic_soup.select_one('div.page-book__main > div:first-of-type > h1').text

        # タイトル前後のスペース削除
        title = ' '.join(title.split())

        # 各種括弧とその中の文字列を削除
        cleaned_title = re.sub(r'\([^()]*\)|\【[^【】]*】|\（[^（）]*\|[[^[]]*]|\［[^［］]*］）', '', title)
        # cleaned_title = re.sub(r'\((?![※本人])[^()]*\)|\【(?![※本人])[^【】]*】|\（(?![※本人])[^（）]*\）', '', title)
        
        # 巻数表現の削除
        for target_word in target_words:
            cleaned_title = remove_text_until_space(cleaned_title, target_word)

        for target_word in target_words_2:
            cleaned_title = remove_text_after_keyword(cleaned_title, target_word)
        
        for target_word in target_words_3:
            cleaned_title = remove_text_until_space(cleaned_title, target_word)

        # 削除対象の文字列を削除
        pattern = re.compile('|'.join(map(re.escape, unwanted_patterns)))
        cleaned_title = pattern.sub('', cleaned_title)

        #もし正規タイトルが【】等で囲まれていた場合の処理 ⇒ ほぼ【推しの子】専用対策
        if not cleaned_title.strip():
            cleaned_title = title
        d_list.append({'Title': cleaned_title})
        sleep(1)
    df_title = pd.DataFrame(d_list)
    return df_title

# スクレイピングを実行し、データフレームに保存
df = pd.DataFrame()
for url in urls:
    df = pd.concat([df, ranking(url, unwanted_patterns)], ignore_index=True)


# 重複タイトルの削除
unique_df = df.drop_duplicates()

# スプレッドシートへの自動書き込み
def db_update():
    # スプレッドシート編集のための認証
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    credentials = Credentials.from_service_account_file(
        'service_account.json',
        scopes=scopes
    )

    gc = gspread.authorize(credentials)

    # スプレッドシートのキーでスプレッドシートを指定し、開く
    SP_SHEET_KEY = '12twLJ21QvuGyqCxaoSZt41k7Ux__1hpzfwtaVWHL5hc'
    sh = gc.open_by_key(SP_SHEET_KEY)

    # シート名を取得日の日付にして新しいシートをスプレッドシートへ追加
    t_delta = datetime.timedelta(hours=9)
    JST = datetime.timezone(t_delta, 'JST')
    now = datetime.datetime.now(JST)
    d = now.strftime('%Y年%m月%d日')

    worksheet = sh.add_worksheet(title=d, rows="100", cols="12")

    df = unique_df

    set_with_dataframe(worksheet, df, row=1, col=1)

# 関数の実行
db_update()




