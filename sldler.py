#Google Drive ファイル一括ダウンロード
#必要なパッケージをインポート
from __future__ import print_function
from dataclasses import fields
from httplib2 import Http
import os.path
import re
import io
from googleapiclient.discovery import build
from oauth2client import file,client,tools
from googleapiclient.http import MediaIoBaseDownload
from apiclient import errors
from tqdm import tqdm

#スコープの設定　今回はダウンロードとメタデータの取得を行うのでこれにしている
SCOPES = ['https://www.googleapis.com/auth/drive']

credential_path = "client_secret.json"
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path

#ダウンロードを行う際に何バイト単位で分割ダウンロードするかの指定
chunk_size = 1000000


#テキストファイルからリンクを読み出してidを配列に格納
def getListFromText():
    path = 'input.txt'

    with open(path,mode='r') as f:
        urllist = [a.strip() for a in f.readlines()]    #テキストファイルから改行ごとに取り出したものをリスト化する
        id_1 = [b.replace('https://drive.google.com/file/d/','') for b in urllist]
        id_2 = [c.replace('','') for c in id_1] 
        idlist = [re.sub('\/','',d) for d in id_2]  #右端につきまとう/を削除
        return idlist


def main():
    print("GoogleDrive 一括ダウンローダー\n")
    if os.path.isfile("input.txt"):
            id_ready = getListFromText()    #関数を実行して戻り値のリストを受け取る
            #ここからGoogleDriveAPIドキュメンテーションのコピペ
            store = file.Storage('token.json')
            creds = store.get()
            if not creds or creds.invalid:
                flow = client.flow_from_clientsecrets('./client_secret.json', SCOPES)
                creds = tools.run_flow(flow, store)
                drive_service = build('drive', 'v3', http=creds.authorize(Http()))

            #ここからGoogleAPI呼び出し
            drive_service = build('drive', 'v3', http=creds.authorize(Http()))
            for i,downid in enumerate(id_ready,1):
                #次に、ここからダウンロードを行う
                #まずそのファイルにGETリクエストをAPIでかけてメタデータを取得する　このときgetまでで止めず、executeまで書かないとgetリクエストが行われず、JSONメタデータがちゃんと返ってこないので注意。
                try:
                    metadata = drive_service.files().get(fileId=downid,fields='name,size').execute()
                    file_name = str(metadata['name'])  #JSONの中からファイル名に当たるものをとってくる
                    file_size = int(metadata['size'])  #JSONからファイルサイズもとってくる、これはlong型でバイト数で入って来る
                    
                    #次にファイルをHttpRequestsオブジェクトとして取得する
                    getdata = drive_service.files().get_media(fileId=downid)
                    fh = io.BytesIO()   #空のBytesオブジェクトを生成
                    downloader = MediaIoBaseDownload(fh,getdata,chunksize=chunk_size)    #MediaIoBaseDownloadでダウンロードしてfhにぶちこむ
                    #ファイルサイズが十分大きくないとチャンクサイズより小さく、一回のダウンロードで終了してしまうため、進捗が微妙な表示になる？(chunksizeは何バイト単位でダウンロードしてくるかを入力する、小さすぎるといつまで経っても終わらないしループが長くなる)
                    progress_bar = tqdm(total=file_size, unit="B", unit_scale=True)
                    done = False
                    while done is False:
                        status,done = downloader.next_chunk()
                        progress_bar.update(chunk_size)
                    progress_bar.close()
                    print(f"{file_name}のダウンロード完了。現在{i}個/%d個\n" % len(id_ready))
                    print(f"サイズは{file_size}Bでした\n")
            
                    #Downloadというフォルダを作り、そこにダウンロードする
                    os.makedirs(f"Download",exist_ok=True)
                    with open(os.path.join("Download",file_name),mode='wb') as f:
                        f.write(fh.getbuffer()) #fhをgetbufferで内容を持ってきて書き込み

                    #ここでなぜかIDでGETをしたときに404 ID~~~~~~.という謎のピリオドが入って404が出るのどうにかならん？
                except: #例外処理　すでに削除されてるファイルが含まれてる場合は404が出るため。 HttpErrorって名前のはずなのに指定できないからbare exceptionを使う
                        #なぜこの例外が起こるかわからないが、まれに起こるので存在しなかった場合はfailed.txtに書き込む
                        #法則性として日本語のファイル名だった場合に起こる？→違った、多分権限がすべてのユーザーになってるから認証問題で何らかのエラーが起きてる
                    with open('failed.txt','a') as f:
                        f.write(f"https://drive.google.com/file/d/{downid}/view?usp=sharing\n")
                        print(f"存在しません。ファイル管理者に確認してみてください。\n")
    else:
        print("input.txtにファイルのURLを入力・保存してください。\n")


           
#実行
if __name__ == "__main__":
    main()