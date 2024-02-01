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


@router.get("/test1")
def test():
    return ViewController().test_fn()
