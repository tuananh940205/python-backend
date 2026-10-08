from app.schemas.user import UserCreate, UserResponse

class UserService:
    def create_user(self, user: UserCreate) -> UserResponse:
        return UserResponse(
            id = 1,
            name = user.name,
            age = user.age,
        )
    # Giả lập
    # Sau này: Service -> Repository -> PostgreSQL
    def get_user(self, user_id: int) -> UserResponse:
        return UserResponse(
            id = user_id,
            name = "Tuan",
            age = 30,
        )
    def delete_user(self, user_id: int):
        print(f"Delete user {user_id}")