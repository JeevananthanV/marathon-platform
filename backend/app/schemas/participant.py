from datetime import date
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class ParticipantBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone_number: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    date_of_birth: date
    gender: Literal["MALE", "FEMALE", "OTHER"]
    blood_group: Literal["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
    tshirt_size: Literal["XS", "S", "M", "L", "XL", "XXL"]
    emergency_contact_name: str = Field(..., min_length=2, max_length=150)
    emergency_contact_phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)


class ParticipantCreate(ParticipantBase):
    pass


class ParticipantResponse(ParticipantBase):
    id: str

    model_config = ConfigDict(from_attributes=True)
