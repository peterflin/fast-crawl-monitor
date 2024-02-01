import uuid
import json
import time
import redis
from utils.flask_table import StateTable, ErrorCountTable
from fastapi.templating import Jinja2Templates
from model.redis_model import RedisModel


class ViewService:

    def __init__(self):
        self.urls_option = []
        self.templates = Jinja2Templates(directory="templates")
        self.model = RedisModel()

    def get_index_template(self, request):
        status = {
            "kafka_connected": False,
            "node_health": "RED",
            "redis_connected": False,
            "uptime_sec": 0
        }
        uid = uuid.uuid1()
        context = {"request": request, "status": status, "uid": uid, "url_list": self.urls_option}
        return self.templates.TemplateResponse('index.html', context=context)
    
    def get_crawl_states_template(self, request):
        status = {
            "kafka_connected": False,
            "node_health": "RED",
            "redis_connected": False,
            "uptime_sec": 0
        }
        state2code = {"init": 0, "request": 1, "parse": 2, "store": 3, "error": 4, "enqueue": 5, "dequeue": 6}
        code2state = {state2code[k]: k for k in state2code}
        table = StateTable(self.model.crawl_states)
        context = {"request": request, "status": status, "table": table}
        return self.templates.TemplateResponse('crawl_states.html', context=context)
    
    def get_states_data(self):
        table = ErrorCountTable(self.model.error_stat, no_items="Wait for loading.")
        # for module in ['UrlCollector', 'HtmlProcessor', 'redis', 'kafka']:
        #     if module in self._module_status:
        #         if time.time() - self._module_status[module]['receive_time'] > 20:
        #             self._module_status[module]['alive'] = 0
        #             if module == 'UrlCollector':
        #                 self._module_status[module]['lambda_trigger'] = 0

        return json.dumps({"states": table.__html__(), "modules_status": self._module_status,
                           "update_process_state_thread": int(self._states_thread.is_alive()),
                           "update_module_state_thread": int(self._module_status_thread.is_alive())})
