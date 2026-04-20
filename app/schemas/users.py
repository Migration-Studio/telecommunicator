from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    id: int
    username: str
    email: str
    display_name: str | None

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=64)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
