"""User schemas. hashed_password is never exposed."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.CAREGIVER
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=12, max_length=256)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=256)


class UserSelfUpdate(BaseModel):
    """A user updating their own profile (cannot escalate role)."""

    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=12, max_length=256)


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
