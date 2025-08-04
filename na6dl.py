#
# BeautifulSoupを使用した簡易的な小説家になろうダウンローダー
# 一応青空文庫形式準拠タグ形式で出力
# 制限事項：
#   短編は考慮していない、R18作品はダウンロード不可、前書き・後書き無視
#   ルビや挿絵は無視(BeautifulSoupで自動的に除去)
#
# ver1.0 2025/08/04 初版
#
import requests
from bs4 import BeautifulSoup
import time
import sys
import re
import codecs

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36'}
text_page = []      # 取り出したテキスト保管用
filename = ''

# トップページの情報を取得する
def get_toppage(url):
    global headers, text_page, filename

    res     = requests.get(url, headers=headers)
    soup    = BeautifulSoup(res.text, 'html.parser')
    title   = soup.find('h1', class_='p-novel__title').text
    auther  = soup.find('div', class_='p-novel__author').text
    summary = soup.find('div', class_='p-novel__summary').text
    auther  = str.strip(auther.replace('作者：', ''))
    # 保存するファイル名を作成する
    filename = re.sub('[\\*?+.\t/:;,.| ]', '-', title)
    if len(filename) > 24:
        filename = title[:24]
    filename = filename + '.txt'

    print(f'作品タイトル：{title} をダウンロードします')
    text_page.append(f'{title}\n{auther}\n［＃ここから罫囲み］\n{summary}\n［＃ここで罫囲み終わり］\n［＃改ページ］\n')

# 各ページから章タイトルを取得する
def get_chapter(src) -> str:
    soup = BeautifulSoup(src, 'html.parser')
    ctmp = soup.select('div[class="c-announce"]')
    cpt  = str(ctmp[0])
    try:
        stmp = BeautifulSoup(cpt, 'html.parser')
        chpt = stmp.find('span').text
    except:
        chpt = ''
    return chpt

# メイン処理
def download_narou(url, max_chapters=5) -> bool:
    global headers, text_page

    get_toppage(url)
    # 1ページ目を取得する
    page_url = f'{url}1/'
    res = requests.get(page_url, headers=headers)
    if res.status_code != 200:
        print(f'{i}ページの取得に失敗しました')
        return False
    soup = BeautifulSoup(res.text, 'html.parser')
    # 1/xxxから総ページ数xxxを取得する
    pg   = soup.find('div', class_='p-novel__number js-siori').text
    pgn  = int(pg.replace('1/', ''))    # 総ページ数
    sys.stdout.write('各話を取得中 [ 1/ ' + str(pgn) + ']')
    # 章タイトル、話タイトル、本文を取得する
    chpt = get_chapter(res.text)
    sect = soup.find('h1', class_='p-novel__title p-novel__title--rensai').text
    body = soup.find('div', class_='js-novel-text p-novel__text').text
    chapter = chpt  # 章タイトルを保存する
    # 1ページ目を出力
    if chpt:
        text_page.append(f'［＃大見出し］{chpt}［＃大見出し終わり］')
    text_page.append(f'［＃中見出し］{sect}［＃中見出し終わり］\n{body}\n［＃改ページ］')

    # 2ページ目以降を取得・出力する
    for i in range(2, pgn + 1):
        sys.stdout.write('\r各話を取得中 [ ' + str(i) + '/ ' + str(pgn) + ']')
        page_url = f'{url}{i}/'
        res = requests.get(page_url, headers=headers)
        if res.status_code != 200:
            print(f'{i}ページの取得に失敗しました')
            return False
        chpt = get_chapter(res.text)
        soup = BeautifulSoup(res.text, 'html.parser')
        sect = soup.find('h1', class_='p-novel__title p-novel__title--rensai').get_text()
        body = soup.find('div', class_='js-novel-text p-novel__text').get_text()
        # 章タイトルが存したものと異なる場合は新しい章として大見出しを挿入する
        if chapter != chpt:
            text_page.append(f'［＃大見出し］{chpt}［＃大見出し終わり］')
            chapter = chpt    # 章が変わった
        text_page.append(f'［＃中見出し］{sect}［＃中見出し終わり］\n{body}\n［＃改ページ］')

        time.sleep(0.5)  # サーバー負荷軽減
    print('・・・完了\n')

    return True

def main():
    global text_page, filename

    if len(sys.argv) == 1:
        print('na6dl.py ver1.0 20205/8/4 copyright(c) INOUE, masahiro')
        print('Usage:')
        print('  python(|py|pytho3) na6dl.py 作品トップページURL\n')
        quit()

    if download_narou(sys.argv[1], 2) == False:
        print('ダウンロード出来ませんでした.\n')
    else:
        fout = codecs.open(filename, 'w', 'utf8')
        fout.writelines(text_page)
        fout.close()
        print(filename + ' に保存しました.')

        print('\nダウンロードが完了しました.\n')


if __name__ == '__main__':
    main()
