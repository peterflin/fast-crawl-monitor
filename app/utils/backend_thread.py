import time
import redis
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from utils import sql_helper
from utils.models import CrawlState, JobUrl
from sqlalchemy import func

state2code = {"init": 0, "request": 1, "parse": 2, "store": 3, "error": 4, "enqueue": 5, "dequeue": 6, "drop": 7}


# 無限迴圈，隔一段時間重新更新kafka、redis、各server上的模組狀態及製作top10錯誤列表
def states_from_db():
    # state2code = self.state2code
    code2state = {state2code[k]: k for k in state2code}
    while 1:
        # get server session
        session = sql_helper.create_session()
        r = redis.StrictRedis(host='127.0.0.1', port=6379, socket_timeout=3, password='redis@cia_0119')
        # reset keys
        r.delete("crawl_state_key")
        r.delete("error_state_key")
        r.delete("module_state")
        r.delete("module_state_redis")
        r.delete("module_state_kafka")
        # update states data
        result = session.query(CrawlState).order_by(CrawlState.tp.desc()).limit(5).all()
        states = []
        for i, row in enumerate(result):
            row_result = session.query(CrawlState).filter(CrawlState.crawlid == row.crawlid).order_by(CrawlState.tp.desc()).all()
            first = row_result[0]
            start_time = str(row_result[-1].tp)
            this_data = {
                "st": code2state[first.states],
                "spider": "<a href='/get_states_list?parser=" + first.domain + "'>" + first.domain + "</a>",
                "start_time": start_time,
                "tp": str(first.tp),
                "url": "<a href='" + first.url + "' target='_blank'>" + first.url + "</a>",
                "crawlid": "<a href='/get_states_list?uid=" + first.crawlid + "'>" + first.crawlid + "</a>"
            }
            states.append(this_data)
            r.hset(f'crawl_state{i}', mapping=this_data)
            r.lpush("crawl_state_key", f'crawl_state{i}')
        # print({key.decode('utf-8'): value.decode('utf-8') for key, value in crawl_state.items()})
        for i, row in enumerate(session.query(
            func.count().label('count'), CrawlState.domain
            ).filter(
                CrawlState.states == 4, CrawlState.domain != ''
            ).group_by(
                CrawlState.domain
            ).order_by(
                func.count().desc()).limit(10).all()):
            r.hset(f"error_state{i}", mapping={"count": row.count, "domain": row.domain})
            r.lpush("error_state_key", f"error_state{i}")
        # get url data
        url_list = {}
        urls_option = "<select name='url' class='form-control'>"
        data = session.query(JobUrl).all()
        for row in data:
            if row.enable == 1:
                url_list[row.url] = row.parser_name
            urls_option += "<option value='" + row.url + "'>" + row.parser_name.split(":")[0] + " : " + row.url + "</option>"
        urls_option += "</select>"
        session.close()
        try:
            KafkaConsumer(bootstrap_servers=['localhost:9094'])
            r.hset("module_state_kafka", mapping={
                "receive_time": time.time(), "alive": 1
            })
        except NoBrokersAvailable:
            r.hset("module_state_kafka", mapping={
                "receive_time": time.time(), "alive": 0
            })
        r.hset("module_state_redis", mapping={
            "receive_time": time.time(), "alive": 1
        })
        time.sleep(3)
