from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from services.view_controller import ViewController


router = APIRouter()


@router.get("/", tags=["Page"], response_class=HTMLResponse)
def index(request: Request):
    return ViewController().index_template(request)


@router.get("/crawl_states", tags=["Page"], response_class=HTMLResponse)
def crawl_states(request: Request):
    return ViewController().crawl_states_template(request)


@router.get("/get_module_server_states", tags=["Page"])
def get_module_server_states(request: Request):
    return ViewController().module_server_states(request)

@router.get("/get_states_data", tags=['Page'])
def get_states_data(request: Request):
    return ViewController().states_data(request)

@router.get("/run_routine", tags=['Page'])
def run_routine(request: Request):
    return ViewController().run_routine(request)

@router.get("/job_list", tags=["Page"])
def job_list(request: Request):
    return ViewController().job_list_template(request)
