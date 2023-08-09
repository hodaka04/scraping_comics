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
unwanted_patterns = ['分冊版', 'モノクロ版', 'noicomi']

# アクセス対象のURL
urls = ['https://www.cmoa.jp/search/purpose/ranking/all/',
        'https://www.cmoa.jp/search/purpose/ranking/media/',
        'https://www.cmoa.jp/search/purpose/ranking/precede/',
        'https://www.cmoa.jp/search/purpose/ranking/original/',
        'https://www.cmoa.jp/search/purpose/ranking/genre/?id=11'
        ]

# スクレイピングの関数定義
def ranking(url, unwanted_patterns):
    r = requests.get(url)
    sleep(1)
    soup = BeautifulSoup(r.content, 'html.parser')


    comics = soup.select('li.search_result_box')
    comics_ranking10 = comics[:10]
    sleep(1)

    
    d_list=[]
    for comic in comics_ranking10:
        title = comic.select_one('div:nth-of-type(2) > div:nth-of-type(2) > p > a').text
        # 削除対象の文字列を削除
        pattern = re.compile('|'.join(map(re.escape, unwanted_patterns)))
        title = pattern.sub('', title)

        # タイトル前後のスペース削除
        title = ' '.join(title.split())

        # ()もしくは【】もしくは（）とその中の文字列を削除　→　（※本人）という文字列はタイトルに含まれるため除外
        cleaned_title = re.sub(r'\([^()]*\)|\【[^【】]*】|\（[^（）]*\）', '', title)
        cleaned_title = re.sub(r'\((?![※本人])[^()]*\)|\【(?![※本人])[^【】]*】|\（(?![※本人])[^（）]*\）', '', title)

        #もし正規タイトルが【】等で囲まれていた場合の処理
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
    SP_SHEET_KEY = '1nSJmsueJNfaUXDFFQWymS1PMNpytejmf_x-Nqw3PQhA'
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





