from views.view_service import ViewService


class ViewController:

    def __init__(self):
        self.view_service = ViewService()

    def index_template(self, request):
        return self.view_service.get_index_template(request)

    def crawl_states_template(self, request):
        return self.view_service.get_crawl_states_template(request)
    
    def test_fn(self):
        return self.view_service.get_test_result()
