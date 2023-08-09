from time import sleep
import pandas as pd
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from get_chrome_driver import GetChromeDriver
import gspread
from google.oauth2.service_account import Credentials
import datetime
from gspread_dataframe import set_with_dataframe

# webdriverの設定
get_driver = GetChromeDriver()
get_driver.install()

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--incognito')
driver = webdriver.Chrome(options=options)

# 削除対象の単語
unwanted_patterns = ['分冊版', 'モノクロ版', 'noicomi','先行あり','独占あり']

# アクセス対象のURL
url = 'https://book.dmm.com/gigatoon/'

# スクレイピングの関数定義
def ranking(url, unwanted_patterns):
    driver.get(url)
    sleep(3)
    html = driver.page_source
    sleep(1)
    soup = BeautifulSoup(html, 'html.parser')
    comics_lists = []
    ichioshi_comics = soup.select('ul.css-1mhm924 > li')[:15]
    sleep(1)
    comics_lists.append(ichioshi_comics)
    mens_comics = soup.select('ul.css-1cnzxie > li')[:6]
    sleep(1)
    comics_lists.append(mens_comics)
    womens_comics = soup.select('ul.css-1cnzxie > li')[6:11]
    sleep(1)
    comics_lists.append(womens_comics)
    bl_comics = soup.select('ul.css-1cnzxie > li')[11:16]
    sleep(1)
    comics_lists.append(bl_comics)
    tl_comics = soup.select('ul.css-1cnzxie > li')[16:21]
    sleep(1)
    comics_lists.append(tl_comics)
    
    d_list=[]
    for comics_list in comics_lists:
        for comic in comics_list:
            title = comic.select_one('span.css-1lhr4hw').text
            # タイトル前後のスペース削除
            title = ' '.join(title.split())

            # 削除対象の文字列を削除
            pattern = re.compile('|'.join(map(re.escape, unwanted_patterns)))
            title = pattern.sub('', title)

            # ()もしくは【】もしくは（）とその中の文字列を削除　→　（たったら負け）という文字列はタイトルに含まれるため除外
            cleaned_title = re.sub(r'\([^()]*\)|\【[^【】]*】|\（[^（）]*\）', '', title)
            cleaned_title = re.sub(r'\((?![たったら負け])[^()]*\)|\【(?![たったら負け])[^【】]*】|\（(?![たったら負け])[^（）]*\）', '', title)

            #もし正規タイトルが【】等で囲まれていた場合の処理
            if not cleaned_title.strip():
                cleaned_title = title
            d_list.append({'Title': cleaned_title})
            sleep(1)
    df_title = pd.DataFrame(d_list)
    return df_title

# スクレイピングを実行し、データフレームに保存
df = pd.DataFrame()
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
    SP_SHEET_KEY = '1Smi7cNIbdsmN3-mD8_703fgzYxaPG2LdzTqDl07Wp9w'
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




