from views.view_service import ViewService


class ViewController:

    def __init__(self):
        self.view_service = ViewService()

    def index_template(self, request):
        return self.view_service.get_index_template(request)

    def crawl_states_template(self, request):
        return self.view_service.get_crawl_states_template(request)
    
    def module_server_states(self, request):
        return self.view_service.get_module_server_states(request)

    def states_data(self, request):
        return self.view_service.get_states_data(request)

    def run_routine(self, request):
        return self.view_service.get_run_routine_data(request)
    
    def job_list_template(self, request):
        return self.view_service.get_job_list_template(request)
    
    def test_fn(self):
        return self.view_service.get_test_result()
