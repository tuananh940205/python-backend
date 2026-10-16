Read 
Completed with input: {
  "path": "D:\\projects\\python\\python-backend\\app\\main.py"
}

Uvicorn cần một ASGI app để chạy. Với lệnh:

```bash
uvicorn app.main:app --reload
```

Uvicorn import module `app.main`, rồi tìm thuộc tính `app` trong module đó. Nếu `app` chỉ là biến cục bộ bên trong một hàm, Uvicorn không thể tìm thấy nó theo cách này.

Nếu muốn tạo app bên trong hàm, hãy dùng **app factory**: hàm tạo và trả về app, kèm cờ `--factory`:

```python
from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/")
    def root():
        return {"message": "Hello World"}

    return app
```

Chạy bằng:

```bash
uvicorn app.main:create_app --factory --reload
```

Ở đây Uvicorn gọi `create_app()` rồi dùng đối tượng được trả về. Trong `main.py` hiện tại, `run_uvicorn_directly()` tạo app cục bộ nhưng không `return` app, nên chưa dùng được như factory. `start()` hiện cũng không trả về app; nếu chọn giữ tên `start`, hàm đó phải tạo và trả về `FastAPI`, rồi lệnh tương ứng là `uvicorn app.main:start --factory --reload`.