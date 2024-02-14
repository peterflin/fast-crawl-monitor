# Fast Crawler

Web service for a distributed crawler system using FastAPI

## Tech Stack
- FastAPI
- Redis
- Kafka
- MySQL

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

## 介紹 & 名詞定義

### 運作流程
1. TaskRequester: Construct a task and push a new task into kafka queue, wait for consumer in the next stage(UrlCollector).
2. UrlCollector: Collect url and send request to get HTML or data. Push result to kafka queue, wait for consumer in the next stage(.
3. HtmlProcessor:
    - Get HTML or data, and parse the unstructure data into structure data according to parser name(in metadata).
    - Default use program which base on scrapy. Hence, follow the rules of scrapy to call parse function and return `scrapy.item` class.
        - Scrapy.Request: Real scrpay.request object or create a fake reqeust object whick follow the scrapy.request rule. It would be transformed into a object which contains an url(string) and a callback function name(string).
        - Scrapy.Response: Real scrapy.response object or create a fake response object which follow the scrapy.response rule.
        - Scrapy.items: Real scrapy.items object or create a fake response object which follow the scrapy.items rule. It would be pushed into kafka queue, and wait for consumer int the next stage(DataConsumer).
4. DataConsumer: Accord to the data type which from kafka queue to decide how to store data.
5. StateConsumer: Process message of stage to trace every progress of task.

---
> 以下尚未更新內容...

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
