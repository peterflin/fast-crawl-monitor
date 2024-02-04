from threading import Thread
from fastapi import FastAPI
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html
)
from fastapi.staticfiles import StaticFiles
from router import router as main_router
from utils.backend_thread import states_from_db, process_module_status

app = FastAPI(docs_url=None, redoc_url=None)
app.openapi_version = "3.0.2"
app.include_router(main_router)
app.mount("/static", StaticFiles(directory='static'), name='static')


@app.on_event("startup")
async def start_up():
    states_thread = Thread(target=states_from_db)
    states_thread.setDaemon(True)
    states_thread.start()
    #
    states_thread = Thread(target=process_module_status)
    states_thread.setDaemon(True)
    states_thread.start()


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/swagger", include_in_schema=False)
async def custom_swagger_ui_html():
    print(app.openapi_url)
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI ",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )
