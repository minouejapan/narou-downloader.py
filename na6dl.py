#
# BeautifulSoupを使用した小説家になろうダウンローダー
#
# ver1.4 2025/08/11 findの反転方法が間違っており連載状況を付加できなかった不具合を修正した
#                   短編と連載のbody取得処理が重複していたのを集約した
# ver1.3 2025/08/10 ルビ・挿絵に対応した
# ver1.2 2025/08/08 短編に対応した
# ver1.1 2025/08/07 R18系(ノクターン等)作品のDLに対応
#                   指定した作品URLの正当性チェックを追加した
#                   章タイトル取得方法の不具合を修正した
#                   前書き・後書きも取得するようにした
#                   連載状況を付加するようにした
#                   ｜《》を青空文庫形式にエスケープする処理を追加した
# ver1.0 2025/08/04 初版
#
import requests
from bs4 import BeautifulSoup
import time
import sys
import re
import codecs
import html

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
text_page = []  # 取り出したテキスト保管用
filename = ''   # 保存ファイル名
nvl_stat = ''   # 作品連載状況
total_pg = 0    # 作品総ページ数
auth_url = ''   # 作者ページURL
session = requests.session()  # 設定したcookieを維持するためグローバル宣言しておく


# HTMLソーステキストを青空文庫形式準拠のテキストに変換する
def aozora_esc(base: str) -> str:
    tmp = html.unescape(base) # HTMLエスケープ文字を復元
    tmp = tmp.replace('《', '※［＃始め二重山括弧、1-1-52］')  # 青空文庫のルビタグをエスケープ
    tmp = tmp.replace('》', '※［＃終わり二重山括弧、1-1-53］')
    tmp = tmp.replace('｜', '※［＃縦線、1-1-35］')
    tmp = re.sub(r'<a href=".*?"><img.*?src="', '［＃リンクの図（', base) # 挿絵
    tmp = re.sub(r'"*?/></a>', '）入る］', tmp)
    tmp = re.sub(r'</rb><rp>.</rp><rt>', '《', tmp) # ルビ
    tmp = re.sub(r'</rt><rp>.</rp></ruby>', '》', tmp)
    tmp = re.sub(r'<rp>.</rp><rt>', '《', tmp)
    tmp = re.sub(r'</rt><rp>.</rp></ruby>', '》', tmp)
    tmp = tmp.replace('<ruby><rb>', '｜')
    tmp = tmp.replace('<ruby>', '｜')
    tmp = re.sub(r'<.*?>', '', tmp) # 最後にその他のタグを削除
    return tmp

# 作品ページから連載状況を取得する
def get_nvl_stat(url: str) -> bool:
    global nvl_stat, total_pg, auth_url, session

    res    = session.get(url, headers=headers)
    soup   = BeautifulSoup(res.text, 'html.parser')
    try:
        nvl_stat = soup.find('span', class_='p-infotop-type__type').text
    except:
        nvl_stat = ''
    try:
        pg = soup.find('span', class_='p-infotop-type__allep').text
        pg = re.sub('エピソード', '', re.sub('全','', pg))
        total_pg = int(pg)
    except:
        total_pg = 0
    try:
        rurl = re.search('<dd class="p-infotop-data__value"><a href=".*?">', res.text)
        if rurl is not None: # if rurl: で良いような気がするがPythonではNoneで判定するのが流儀らしい
            auth_url = re.sub('">', '', re.sub('<dd class="p-infotop-data__value"><a href="', '', rurl.group()))
    except:
        auth_url = ''
    return nvl_stat != ''


# トップページの情報を取得する
def get_toppage(url):
    global headers, text_page, filename, nvl_stat, session

    res    = session.get(url, headers=headers)
    soup   = BeautifulSoup(res.text, 'html.parser')
    title  = soup.find('h1', class_='p-novel__title').text
    auther = soup.find('div', class_='p-novel__author').text
    auther = str.strip(auther.replace('作者：', ''))
    try:
        summary = aozora_esc(str(soup.find('div', class_='p-novel__summary')))
    except:
        summary = ''
    # 作品情報URLを取得して連先状況を確認する
    a_tags = soup.find_all('a', class_='c-menu__item c-menu__item--headnav')
    get_nvl_stat(a_tags[0].get('href'))
    # 保存するファイル名を作成する(ついでに24文字までに整形)
    filename = re.sub(r'[\\*?+.\t/:;,.| ]', '-', title)
    if len(filename) > 24:
        filename = title[:24]
    # タイトル名に連載状況が含まれていなければ先頭に付加する
    if title.find(nvl_stat) == -1:
        filename = f'【{nvl_stat}】' + filename
        title = f'【{nvl_stat}】' + title
    filename = filename + '.txt'
    print(f'作品タイトル：{title} をダウンロードします')
    text_page.append(f'{title}\n{auther}\n［＃ここから罫囲み］\n{summary}\n［＃ここで罫囲み終わり］\n［＃改ページ］\n')

# 各ページから章タイトルを取得する
def get_chapter(src) -> str:
    soup = BeautifulSoup(src, 'html.parser')
    # クラス名完全一致で検索するのでselectを用いる
    ctmp = soup.select('div[class="c-announce"]')
    try:
        cpt  = str(ctmp[0])
        # クラス名完全一致で検索するのでselectを用いる
        stmp = BeautifulSoup(cpt, 'html.parser')
        # 完全一致で<span>xxx</span>を抽出したいので正規表現を使用
        res = re.search(r'<span>.*</span>', str(stmp))
        if res is not None:
            chpt = re.sub('</span>', '', re.sub('<span>', '', res.group()))
        else:
            chpt = ''
    except:
        chpt = ''
    return chpt

# 各話本文取得処理
def get_body(htmlsrc) -> str:
    soup = BeautifulSoup(htmlsrc, 'html.parser')
    atxt = ''
    try: # 前書き
        irfc = aozora_esc(str(soup.find('div', class_='js-novel-text p-novel__text p-novel__text--preface')))
    except:
        irfc = 'None' # soup.findで帰り値がない場合はObject[None]が返されるがstrでキャストしてるため文字列m'None'が返される
    body = aozora_esc(str(soup.find('div', class_='js-novel-text p-novel__text'))) # 本文
    try: # 後書き
        pscr = aozora_esc(str(soup.find('div', class_='js-novel-text p-novel__text p-novel__text--afterword')))
    except:
        pscr = 'None'
    if irfc != 'None':
        atxt = f'［＃水平線］［＃ここから罫囲み］\n{irfc}\n［＃ここで罫囲み終わり］［＃水平線］\n'
    atxt = atxt + f'{body}\n'
    if pscr != 'None':
        atxt = atxt + f'［＃水平線］［＃ここから罫囲み］\n{pscr}\n［＃ここで罫囲み終わり］［＃水平線］\n'
    atxt = atxt + '［＃改ページ］\n'
    return atxt

# メイン処理
def download_narou(url) -> bool:
    global headers, text_page, session, nvl_stat, total_pg

    get_toppage(url) # トップページ情報取得

    if total_pg == 0: # 短編の場合の本文取得処理
        res = session.get(url, headers=headers)
        if res.status_code != 200:
            print(f'{i}ページの取得に失敗しました')
            return False
        body = get_body(res.text)
        text_page.append('［＃中見出し］本文［＃中見出し終わり］\n')
        text_page.append(body)
    chapter = ''
    for i in range(1, total_pg + 1): # 連載作品の場合の各ページ取得処理
        sys.stdout.write('\r各話を取得中 [ ' + str(i) + '/ ' + str(total_pg) + ']')
        page_url = f'{url}{i}/'
        res = session.get(page_url, headers=headers)
        if res.status_code != 200:
            print(f'{i}ページの取得に失敗しました')
            return False
        chpt = aozora_esc(get_chapter(res.text))
        soup = BeautifulSoup(res.text, 'html.parser')
        sect = aozora_esc(str(soup.find('h1', class_='p-novel__title p-novel__title--rensai')))
        body = get_body(res.text)
        if chapter != chpt: # 章が変わった
            text_page.append(f'［＃大見出し］{chpt}［＃大見出し終わり］\n')
            chapter = chpt
        text_page.append(f'［＃中見出し］{sect}［＃中見出し終わり］\n')
        text_page.append(body)

        time.sleep(0.5)  # サーバー負荷軽減
    print('・・・完了')
    return True

def main():
    global text_page, filename, session

    # コマンドライン引数チェック
    if len(sys.argv) == 1:
        print('na6dl.py ver1.2 20205/8/10 copyright(c) INOUE, masahiro')
        print('Usage:')
        print('  python(|py|pytho3) na6dl.py 作品トップページURL\n')
        quit()
    # URLチェクッ
    url = sys.argv[1]
    if ((re.match(r'^https://ncode.syosetu.com/n\d{4}\w{1,2}/', url) is None) and
       (re.match(r'^https://novel18.syosetu.com/n\d{4}\w{1,2}/', url) is None)):
        print('\nURLが違います.')
        quit()
    # sessionにR18系アクセス許可用クッキーを設定する
    if re.match(r'^https://novel18.*?', url)is not None:
        session.cookies.set('over18', 'yes')

    if download_narou(url) == False:
        print('ダウンロード出来ませんでした.\n')
    else:
        fout = codecs.open(filename, 'w', 'utf8')
        fout.writelines(text_page)
        fout.close()
        print(filename + ' に保存しました.')

if __name__ == '__main__':
    main()
