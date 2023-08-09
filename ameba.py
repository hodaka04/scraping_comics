from time import sleep
from selenium import webdriver
import pandas as pd
import re
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import datetime
from gspread_dataframe import set_with_dataframe

# webdriverの設定
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--incognito')

driver = webdriver.Chrome(
    executable_path='tools\chromedriver.exe',
    options=options)

# 削除対象の単語
unwanted_patterns = ['分冊版', 'モノクロ版', 'noicomi']

# アクセス対象のURL
urls = ['https://dokusho-ojikan.jp/ranking/daily/1?categoryType=page_type_adult_male&pageType=adult_male&ref=ranking_all',
        'https://dokusho-ojikan.jp/ranking/daily/1?ref=global_navigation_ranking&pageType=all',
        'https://dokusho-ojikan.jp/'
        ]

# HTML保存の関数定義
def ranking_all(url):    
    # HPへアクセス
    driver.get(url)
    sleep(3)
    html_all = driver.page_source

    return html_all

def ranking_other(url):    
    # HPへアクセス
    driver.get(url)
    sleep(3)
    html_other = driver.page_source

    return html_other

def ranking_mens(url):
    # HPへアクセス
    driver.get(url)
    sleep(3)
    try:
        button = driver.find_element_by_css_selector('div.sc-1ysyk3i-8 > div:first-of-type > button')
        driver.execute_script('arguments[0].click();', button)
    except:
        sleep(1)
    sleep(3)
    html_mens = driver.page_source

    return html_mens

html_mens = ranking_mens(urls[0])
html_all = ranking_all(urls[1])
html_other = ranking_other(urls[2])

# 削除対象の単語
unwanted_patterns = ['分冊版', 'モノクロ版', 'noicomi']

# スクレイピング対象のHTML
html_files = ['ameba_1.html', 'ameba_mens.html']

# ランキングスクレイピングの関数定義
def ranking(html, unwanted_patterns):
    soup = BeautifulSoup(html, 'lxml')
    comics = soup.select('ul.sc-p9znnp-0 > li')
    comics_ranking10 = comics[:10]
    sleep(1)
    
    d_list=[]
    for comic in comics_ranking10:
        title = comic.select_one('p.cYSIdw').text
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
        # print(cleaned_title)
        sleep(1)
    df_title = pd.DataFrame(d_list)
    return df_title

# 注目マンガスクレイピングの関数定義
def listup(html, unwanted_patterns):
    soup = BeautifulSoup(html, 'lxml')
    comics = soup.select('ul.sc-p9znnp-0')
    check_comics = comics[1]
    commercial_commics = comics[4]
    commics_lists = [check_comics, commercial_commics]
    sleep(1)

    d_list=[]
    for commics_list in commics_lists:
        for comic in commics_list:
            title = comic.select_one('p.cYSIdw').text
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
            # print(cleaned_title)
            sleep(1)
    df_title = pd.DataFrame(d_list)
    return df_title


# スクレイピングを実行し、データフレームに保存
df = pd.DataFrame()
df = pd.concat([df, ranking(html_all, unwanted_patterns)], ignore_index=True)
df = pd.concat([df, ranking(html_mens, unwanted_patterns)], ignore_index=True)
df = pd.concat([df, listup(html_other, unwanted_patterns)], ignore_index=True)

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
    SP_SHEET_KEY = '11hcsogJJecgMfAvVe_U86CkKJs-HAOL3NYjhcr7SZkI'
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

driver.quit()



