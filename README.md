# Fast Crawler 1.0

A re-build distributed crawler system using FastAPI

## How to run
build image & run
```bash
cd fast-crawl
sh auto_run.sh
```
### ENV
- REDIS_HOST : redis server host name, ex: 127.0.0.1
- REDIS_PORT : redis server port, ex: 6379
- REDIS_PWD : redis password, ex: pwd123
- DB_URI : sqlalchemy connect uri, ex: mysql+pymysql://user:pwd@127.0.0.1/fast_crawl

## Tech Stack
- FastAPI
- Redis
- Kafka
- MySQL

## 介紹 & 名詞定義

### 運作流程
1. 統一蒐集URL，暫存於Redis
2. UrlCollector: 取得一定量於Redis列隊的URL，同時發布到AWS Lambda進行網頁HTML下載
3. LambdaProcessor: 回傳Lambda下載的HTML，存入Redis\(另一個Queue\)等待處理
4. HtmlConsumer: 
    - 取得下載回存於Redis的Html\(一次只處理一個網頁\)，並根據取得的資料\(Html、ParserName、該網頁的URL\)，使用Parser模組丟入HTML進行解析，並回傳資訊
    - 使用Generator取得Return的物件，根據物件的class，
        - Scrapy.Request: 新的請求網頁，callback為Parser，加入Redis等待請求
        - Scrapy.items: 解析出的資料，發布到Kafka等待Consumer處理
5. DataConsumer: crawl item的Consumer，依收到的DataType決定如何儲存\(DB\)

### UrlCollector
```
向Redis取得欲爬取的網址，並於定量後發送request
```
> 類似於原爬蟲階段的指定request

### HtmlConsumer
```
向Redis取得由AWS lambda下載回來的Html，並進行剖析
```
### StatesConsumer
```
處理Module中所記錄的state，並存入資料庫
```
### DataConsumer
```
用於蒐集HtmlConsumer解析後的資料，處理後存入資料庫
```
### ModuleLauncher
初始時須更新最新parser程式碼，且定期更新

## ModuleLauncher
Flask框架的WEB API
- 根據settings的launch_IP，紀錄此Server的服務IP，用於UI介面控制
- 運行另一個thread，負責定時向UI介面服務告知此服務仍在運行

### API
- /output: Dump此服務上各模組運行狀況
- /start_module: 運行一個新的thread，運行模組
- /stop_module: 呼叫模組的stop()方法，模組收到stop指令後跳出無限迴圈，結束此thread
- /reset: 記錄正在運行的模組，停止此服務上所有正在運行的模組，並根據先前紀錄有在運行的模組，重新分配thread給模組並開始重新運行

## UI介面
- /index
- /crawl_states
- /run_routine
- /job_list
- /get_states_list

#### index
- 觀看各模組狀況: 5秒ajax更新資料

#### crawl_states
- 觀看各模組狀況: 5秒ajax更新資料
- 錯誤排名列表\(網站\): 5秒ajax更新資料

#### run_routine
- 控制是否啟動固定時間發布任務功能
- 觀看目前有哪些爬蟲服務啟動
- 控制爬蟲服務的模組啟動或停止

#### job_list
- 觀看目前有抓哪些網站
- 控制下一次網站是否要加入任務列表
- 點選parser可進入爬蟲過程紀錄

#### get_states_list
- 給parser: 列出此parser的crawlid\(曾經發布過的任務\)
- 給crawlid: 列出此crawlid下的任務爬蟲過程

## 主機部屬

- UI Server
- Crawler Server

### UI Server

module
- ui_service.py
- add_request.py
- settings.py
folder
- js
- static
- templates

### Crawler Server
- crawl_launcher.py
- url_collector.py
- crawler.py
- lambda_processor.py
- settings.py
- data_consumer.py
- state_consumer.py

folder
- parsers
