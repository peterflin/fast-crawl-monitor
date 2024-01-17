import kafka
import settings
import json
import pymysql
from datetime import datetime, timedelta
import traceback
import logging


logging.basicConfig(format='%(asctime)s [%(name)-12s]: [%(levelname)s] : %(message)s', level=logging.INFO)


# 用來處理各module寫入到kafka的state訊息
class StatesConsumer(object):

    def __init__(self, open_on='localhost'):
        self.open_on = open_on
        # kafka consumer，topic: states(settings.py中有寫)
        # 如果量大時亦可執行多個StatesConsumer，在consumer group需設定相同，避免重複拿到一樣的訊息
        self.consumer = kafka.KafkaConsumer(settings.KAFKA_STATES_TOPIC, group_id=settings.KAFKA_STATES_CONSUME_GROUP,
                                            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                                            consumer_timeout_ms=1000)
        # DB connection
        self.db = pymysql.connect(**settings.DB_SETTING)
        self.cursor = self.db.cursor()
        self.stop_flag = False
        self.logger = logging.getLogger(__class__.__name__)

    def run(self):
        url_cache = []
        uid_cache = []
        while 1:
            for msg in self.consumer:
                msg2json = json.loads(msg.value)  # 取得的訊息為bytes，需轉換回json格式
                print(msg2json)
                state2code = {"init": 0, "request": 1, "parse": 2, "store": 3, "error": 4, "enqueue": 5, "dequeue": 6,
                              'drop': 7}
                try:
                    print(msg2json['url'] in url_cache)
                    print(msg2json['uid'] in uid_cache)
                    if msg2json['url'] not in url_cache:
                        url_cache.append(msg2json['url'])
                    if msg2json['uid'] not in uid_cache:
                        uid_cache.append(msg2json['uid'])
                    print("insert into `crawl_states`(states, spider, domain, url, tp, crawlid, state_comment, open_on) values({}, '{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(
                            state2code[msg2json['state']],
                            "" if "spider" not in msg2json else msg2json['spider'],
                            msg2json['parser_name'].split(":")[0],
                            msg2json['url'],
                            msg2json['time'],
                            msg2json['uid'],
                            clear_string("") if "state-message" not in msg2json and msg2json['state'] == 4 else clear_string(msg2json['state-message']),
                            msg2json['open_on'] if 'open_on' in msg2json else ""
                        ))
                    self.cursor.execute(
                        "insert into `crawl_states`(states, spider, domain, url, tp, crawlid, state_comment, open_on) values({}, '{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(
                            state2code[msg2json['state']],
                            "" if "spider" not in msg2json else msg2json['spider'],
                            msg2json['parser_name'].split(":")[0],
                            msg2json['url'],
                            msg2json['time'],
                            msg2json['uid'],
                            clear_string("") if "state-message" not in msg2json and msg2json['state'] == 4 else clear_string(msg2json['state-message']),
                            msg2json['open_on'] if 'open_on' in msg2json else ""
                        ))
                    self.db.commit()
                # 存state的table，scheme為states(int)、spider(被哪個crawler處理html)、domain(parser_name)、tp(時間)、
                #                         crawlid(job id)、state_comment(state的簡單描述)
                # primary key: states+tp+crawlid
                # 可能會有同時間有兩個同樣的狀態需要紀錄(根據拿到的html去parse的時間是有可能的)，因此嘗試將時間+1秒，
                # 最多加三秒(嘗試三次)
                except pymysql.err.IntegrityError:
                    new_time = str(datetime.strptime(msg2json['time'], "%Y-%m-%d %H:%M:%S") + timedelta(seconds=1))
                    for i in range(3):
                        try:
                            self.cursor.execute(
                                "insert into `crawl_states`(states, spider, domain, url, tp, crawlid, state_comment, open_on) values({}, '{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(
                                    state2code[msg2json['state']],
                                    "" if "spider" not in msg2json else msg2json['spider'],
                                    msg2json['parser_name'].split(":")[0],
                                    msg2json['url'],
                                    msg2json['time'],
                                    msg2json['uid'],
                                    clear_string("") if "state-message" not in msg2json and msg2json['state'] == 4 else clear_string(msg2json['state-message']),
                                    msg2json['open_on'] if 'open_on' in msg2json else ""
                                ))
                            self.db.commit()
                        except pymysql.err.IntegrityError:
                            self.logger.error(traceback.format_exc())

                print(msg2json)
            if self.stop_flag:
                break
        self.logger.warning("States Consumer Stop.")

    def stop(self):
        self.stop_flag = True


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
    StatesConsumer().run()

