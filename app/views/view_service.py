import uuid
import requests
# import redis
from utils.flask_table import StateTable, ErrorCountTable, JobURL
from fastapi.templating import Jinja2Templates
from model.redis_model import RedisModel
from model.mysql_model import MySQLModel


class ViewService:

    def __init__(self):
        self.urls_option = []
        self.templates = Jinja2Templates(directory="templates")
        self.redis_model = RedisModel()

    def get_index_template(self, request):
        status = {
            "kafka_connected": self.redis_model.redis.ping(),
            "node_health": "RED",
            "redis_connected": self.redis_model.redis.ping(),
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
        table = StateTable(self.redis_model.crawl_states)
        context = {"request": request, "status": status, "table": table}
        return self.templates.TemplateResponse('crawl_states.html', context=context)
    
    def get_states_data(self, request):
        table = ErrorCountTable(self.redis_model.error_stat, no_items="Wait for loading.")
        # for module in ['UrlCollector', 'HtmlProcessor', 'redis', 'kafka']:
        #     if module in self._module_status:
        #         if time.time() - self._module_status[module]['receive_time'] > 20:
        #             self._module_status[module]['alive'] = 0
        #             if module == 'UrlCollector':
        #                 self._module_status[module]['lambda_trigger'] = 0

        # return json.dumps({"states": table.__html__(), "modules_status": RedisModel().states_data,
        #                    "update_process_state_thread": int(self._states_thread.is_alive()),
        #                    "update_module_state_thread": int(self._module_status_thread.is_alive())})
        return {"states": table.__html__(),
                "modules_status": RedisModel().states_data,
                "update_process_state_thread": 1,
                "update_module_state_thread": 1}

    def get_module_server_states(self, request):
        server_module_state = {}
        module_state_html = ""
        redis = RedisModel()
        for server in redis.signup_servers:
            module_state = requests.get(server + "/output").json()
            for module in module_state:
                if module not in server_module_state:
                    server_module_state[module] = {}
                server_module_state[module][server] = module_state[module] if module_state[module] is not None else "Not Running"
        for module in server_module_state:
            module_state_html += '<div class="col-xs-8 col-sm-6 col-md-3 col-lg-3"><div class="panel panel-info"><div class="panel-heading"><h3 class="panel-title">' + module + '</h3></div><div class="panel-body">'
            for server in server_module_state[module]:
                module_state_html += '<span class="label label-primary">' + server + ':<span class="label-' + get_panel_state(
                    server_module_state[module][server]) + '"> ' + server_module_state[module][
                                         server] + '</span></span>'
            module_state_html += '</div></div></div>'
        return module_state_html

    def get_run_routine_data(self, request):
        running_state = '<span class="label label-success">Running</span>'
        redis_data = RedisModel()
        server_list = {}
        for s in redis_data.signup_servers:
            server_list[s] = requests.get(s + '/output').json()
        context = {
            "request": request,
            "running_state": running_state,
            "running": True,
            "signup": str(redis_data.signup_servers),
            "server_list": server_list
        }
        return self.templates.TemplateResponse('run_routine.html', context=context)

    def get_job_list_template(self, request):
        data = MySQLModel().job_url_data
        button_color = {1: "primary", 0: "danger"}
        index_count = 0
        form = "<form action='change_enable' method='GET'><input name='url' type='hidden' value='{url}'><input name='ori_state' type='hidden' value='{ori_state}'>{button}</form>"
        job = []
        for row in data:
            job.append({
                "url": "<a href='" + row.url + "' target='_blank'>" + row.url + "</a>",
                "parser_name": "<a href='/get_states_list?parser=" + row.parser_name.split(":")[0] + "'>" + row.parser_name.split(":")[0] + "</a>",
                "enable": form.format(
                    url=index_count,
                    ori_state=row.enable,
                    button="<button class='btn btn-" + button_color[row.enable] + "'>" + str(bool(row.enable)) + "</button>"
                )
            })
            index_count += 1
        table = JobURL(job)
        context = {
            "request": request,
            "job_table": table
        }
        return self.templates.TemplateResponse('job_list.html', context=context)


def get_panel_state(state):
    return "success" if state == 'Running' else "danger"

