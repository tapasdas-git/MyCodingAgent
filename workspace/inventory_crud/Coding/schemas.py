from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    description: str | None = Field(default=None, max_length=2000)
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    category: str | None = Field(default=None, max_length=120)

    @field_validator("name", "sku", "category", mode="before")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            value = value.strip()
        return value or None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$")
    description: str | None = Field(default=None, max_length=2000)
    price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=120)

    @field_validator("name", "sku", "category", mode="before")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            value = value.strip()
        return value

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            value = value.strip()
        return value or None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    sku: str
    description: str | None
    price: float
    stock: int
    category: str | None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ProductFilter(BaseModel):
    query: str | None = Field(default=None, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    min_stock: int | None = Field(default=None, ge=0)
    max_stock: int | None = Field(default=None, ge=0)
    include_deleted: bool = False
    sort_by: Literal["created_at", "updated_at", "name", "price", "stock"] = "created_at"
    sort_order: Literal["asc", "desc"] = "asc"

    @field_validator("query", "sku", "category", mode="before")
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            value = value.strip()
        return value or None

    @field_validator("max_price")
    @classmethod
    def validate_price_bounds(cls, value: float | None, info):
        min_price = info.data.get("min_price")
        if value is not None and min_price is not None and value < min_price:
            raise ValueError("max_price must be greater than or equal to min_price")
        return value

    @field_validator("max_stock")
    @classmethod
    def validate_stock_bounds(cls, value: int | None, info):
        min_stock = info.data.get("min_stock")
        if value is not None and min_stock is not None and value < min_stock:
            raise ValueError("max_stock must be greater than or equal to min_stock")
        return value


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
