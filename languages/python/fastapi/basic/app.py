from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from enum import Enum
import os

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

app = FastAPI()

templates = Jinja2Templates(directory="templates") 

fake_items_db = [{"item_name": "Foo"}, {"item_name": "Bar"}, {"item_name": "Baz"}]

# Path Parameters

# Case 1: default
@app.get("/")
async def root():
    return {"message": "Hello World"}

# Case 2: parameters with types
@app.get("/user/{user_id}")
def user(user_id: int):
    return {"user_id": user_id}

# Case 3: predefined values
@app.get("/models/{model_name}")
async def get_model(model_name: ModelName):
    if model_name is ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}

    if model_name.value == "lenet":
        return {"model_name": model_name, "message": "LeCNN all the images"}

    return {"model_name": model_name, "message": "Have some residuals"}

# Query Parameters

# Case 1: default
# /items/?skip=1&limit=10

@app.get("/items/")
async def read_item_default(skip: int = 0, limit: int = 10):
    return fake_items_db[skip : skip + limit]

# Case 2: optional parameters
# /items/1?q=1

@app.get("/items/{item_id}")
async def read_item_optional(item_id: str, q: str | None = None):
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}

# Case 3: type conversions
# /items/foo?short=1 or /items/foo?short=true

@app.get("/items/{item_id}")
async def read_item_type_conv(item_id: str, q: str | None = None, short: bool = False):
    item = {"item_id": item_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update(
            {"description": "This is an amazing item that has a long description"}
        )
    return item

# Case 4: multiple path and query parameters
# /users/123/items/456?q=1&short=true

@app.get("/users/{user_id}/items/{item_id}")
async def read_user_item(
    user_id: int, item_id: str, q: str | None = None, short: bool = False
):
    item = {"item_id": item_id, "owner_id": user_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update(
            {"description": "This is an amazing item that has a long description"}
        )
    return item

# Case 5: required parameter `needy`
# `needy`, a required str.
# `skip`, an int with a default value of 0.
# `limit`, an optional int.
# /items-new/foo?needy=sooneedy&skip=1&limit=3

@app.get("/items-new/{item_id}")
async def read_user_item2(
    item_id: str, needy: str, skip: int = 0, limit: int | None = None
):
    item = {"item_id": item_id, "needy": needy, "skip": skip, "limit": limit}
    return item

# Submit Page
@app.get("/submit", response_class=HTMLResponse)
async def submit_form(request: Request):
    return templates.TemplateResponse("submit.html", {"request": request})

@app.post("/submit", response_class=HTMLResponse)
async def process_submit(request: Request, name: str = Form(...)):
    return RedirectResponse(url=f"/hello/{name}", status_code=302)

@app.get("/hello/{name}", response_class=HTMLResponse)
async def hello(request: Request, name: str):
    return HTMLResponse(f"Hello {name}")


def main():
    import uvicorn
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()