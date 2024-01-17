import kafka
import settings
import json
import pymysql
from datetime import datetime, timedelta
import time
import sys
import logging
# from geolite2 import geolite2


logging.basicConfig(format='%(asctime)s [%(name)-12s]: [%(levelname)s] : %(message)s', level=logging.INFO)


class DataConsumer(object):
    def __init__(self, open_on='localhost'):
        self.open_on = open_on
        # 建立kafka consumer連線，消費"crawled_data" topic
        self.kafka_consumer = kafka.KafkaConsumer(settings.KAFKA_STORE_DATA_TOPIC, group_id='data_group',
                                                  bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                                                  consumer_timeout_ms=1000)
        # 建立kafka producer連線
        self.kafka_producer = kafka.KafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS)
        # DB連線
        self.db = pymysql.connect(**settings.DB_SETTING)
        self.cursor = self.db.cursor()
        # log
        self.logger = logging.getLogger(__class__.__name__)
        self.stop_flag = False

    def run(self):
        # 先儲存資料，完成後再紀錄狀態
        while 1:
            for msg in self.kafka_consumer:
                msg2json = json.loads(msg.value)  # 取得的訊息為bytes，需轉換回json格式
                # 根據傳過來的"DataType" key決定用哪種存資料方法
                # for ptt
                if msg2json['DataType'] == "ptt":
                    self.ptt(msg2json)
                # for 新聞
                elif msg2json['DataType'] == "news":
                    # self.news(msg2json)
                    pass
                # record state
                message = {"time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), "state": "store",
                           "state-message": "Store data to db.", "parser_name": msg2json["parser_name"],
                           "url": msg2json['url'], "uid": msg2json['uid'], "open_on": self.open_on, }
                future = self.kafka_producer.send(settings.KAFKA_STATES_TOPIC, bytes(json.dumps(message), encoding='utf8'))
                result = future.get(timeout=10)
                self.logger.info(result)
            if self.stop_flag:
                break
        print('Data Consumer Stop.')

    def stop(self):
        self.stop_flag = True

    # def ptt(self, msg_data):
    #     data = msg_data['data']
    #     self.logger.info("Consume Ptt.")
    #     # ---------------------ip、country我自己的額外需求做的----------------------------------------------------#
    #     reader = geolite2.reader()
    #     if data['ip'] != '':
    #         country = reader.get(data['ip'])['country']['iso_code'] if reader.get(data['ip']) is not None else ""
    #     else:
    #         country = ""
    #     # -------------------------------end 額外需求------------------------------------------------------------#
    #
    #     # --------------------------------------------------------------------------------------------------------- #
    #
    #     # 儲存資料至db
    #     self.cursor.execute(
    #         "insert ignore into ptt_content(title,content,tp,url,author,board,ip,country,uid) values('{}','{}',str_to_date('{}', '%Y-%m-%d %H:%i:%S'),'{}','{}','{}','{}','{}', '{}')".format(
    #             data['title'], clear_string(data['content']), data['tp'], data['url'], data['author'], data['board'],
    #             data['ip'],
    #             country,
    #             msg_data['uid']))
    #     self.db.commit()

    def news(self, msg_data):
        # 作法同上

        data = msg_data['data']
        print(data)
        self.logger.info("Consume news. {}".format(data))
        self.cursor.execute(
            "insert ignore into ptt_content(title,article,pub_datetime,docID,creator,source, uid) values('{}','{}',str_to_date('{}', '%Y-%m-%d %H:%i:%S'),'{}','{}','{}','{}')".format(
                data['title'], clear_string(data['article']), str(data['pub_datetime']), data['docID'], data['creator'],
                data['source'], msg_data['uid']))
        self.db.commit()


# 用來處理引號及反斜線，避免進行sql語法儲存資料時語法錯誤
def clear_string(input_string):
    output_string = ""
    for c in input_string:
        if c == "\'" or c == "\'" or c == "\\":
            output_string += "\\" + c
        else:
            output_string += c
    return output_string


if __name__ == '__main__':
    DataConsumer().run()
