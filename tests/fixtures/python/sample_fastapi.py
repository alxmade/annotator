"""Sample FastAPI file used as a test fixture for annotator."""

from fastapi import FastAPI

app = FastAPI()


def add(a: int, b: int) -> int:
    return a + b


def documented_func(x: float) -> float:
    """Return the square of x."""
    return x * x


@app.get("/users")
async def get_users():
    return []


@app.post("/users")
async def create_user(name: str):
    return {"name": name}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"id": user_id}


class UserService:
    def get_by_id(self, user_id: int):
        return None

    def create(self, name: str, email: str):
        return {"name": name, "email": email}
