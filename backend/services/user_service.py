"""
A.R.G.U.S. — User Service (OOP Application Layer)
Manages user entity retrieval, role queries, and user profile queries.
"""

import uuid
from typing import Optional, List
from sqlalchemy.orm import Session

from database.models.user import User, Role
from database.repository import (
    get_user_by_id,
    get_user_by_username,
    get_user_by_email,
    get_role_by_name,
    create_role_if_not_exists,
    get_users_list,
)


class UserService:
    """
    Application service managing identity entities and operational roles.
    Encapsulates identity lookup logic and role resolution.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return get_user_by_id(self.db, user_id)

    get_by_id = get_user_by_id

    def get_user_by_username(self, username: str) -> Optional[User]:
        return get_user_by_username(self.db, username)

    get_by_username = get_user_by_username

    def get_user_by_email(self, email: str) -> Optional[User]:
        return get_user_by_email(self.db, email)

    get_by_email = get_user_by_email

    def get_role_by_name(self, name: str) -> Optional[Role]:
        return get_role_by_name(self.db, name)

    def ensure_role(self, name: str, description: Optional[str] = None) -> Role:
        return create_role_if_not_exists(self.db, name, description)

    def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        return get_users_list(self.db, limit=limit, offset=offset)
