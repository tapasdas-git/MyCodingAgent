from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from difflib import SequenceMatcher
from threading import RLock
from typing import Iterable
from uuid import uuid4

from .exceptions import DuplicateSKUError, ProductNotFoundError
from .schemas import ProductCreate, ProductFilter, ProductResponse, ProductUpdate, utc_now


@dataclass(slots=True)
class _ProductRecord:
    id: str
    name: str
    sku: str
    description: str | None
    price: float
    stock: int
    category: str | None
    is_deleted: bool
    created_at: object
    updated_at: object
    deleted_at: object | None

    def to_response(self) -> ProductResponse:
        return ProductResponse(**asdict(self))


class InventoryRepository:
    """Thread-safe in-memory product repository."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._products: dict[str, _ProductRecord] = {}

    def create_product(self, payload: ProductCreate) -> ProductResponse:
        with self._lock:
            self._ensure_unique_sku(payload.sku)
            now = utc_now()
            record = _ProductRecord(
                id=str(uuid4()),
                name=payload.name,
                sku=payload.sku,
                description=payload.description,
                price=payload.price,
                stock=payload.stock,
                category=payload.category,
                is_deleted=False,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            )
            self._products[record.id] = record
            return record.to_response()

    def get_product_by_id(self, product_id: str, include_deleted: bool = False) -> ProductResponse:
        with self._lock:
            record = self._require_product(product_id)
            if record.is_deleted and not include_deleted:
                raise ProductNotFoundError(f"Product '{product_id}' not found")
            return record.to_response()

    def list_products(self, filter_: ProductFilter | None = None) -> list[ProductResponse]:
        filter_ = filter_ or ProductFilter()
        with self._lock:
            records = [record for record in self._products.values() if filter_.include_deleted or not record.is_deleted]
            records = [record for record in records if self._matches_filter(record, filter_)]
            records.sort(key=lambda item: self._sort_key(item, filter_.sort_by), reverse=filter_.sort_order == "desc")
            return [record.to_response() for record in records]

    def update_product(
        self,
        product_id: str,
        payload: ProductUpdate,
        *,
        replace: bool = False,
    ) -> ProductResponse:
        with self._lock:
            record = self._require_product(product_id)
            if record.is_deleted:
                raise ProductNotFoundError(f"Product '{product_id}' not found")

            data = payload.model_dump(exclude_unset=not replace)
            if replace:
                required_fields = {"name", "sku", "price", "stock"}
                missing = {
                    field
                    for field in required_fields
                    if field not in payload.model_fields_set or data.get(field) is None
                }
                if missing:
                    raise ValueError(f"Full replacement requires fields: {sorted(missing)}")

            if "sku" in data:
                self._ensure_unique_sku(data["sku"], exclude_id=product_id)

            updated = replace_record(record, data)
            updated.updated_at = utc_now()
            self._products[product_id] = updated
            return updated.to_response()

    def delete_product(self, product_id: str, *, hard_delete: bool = False) -> None:
        with self._lock:
            record = self._require_product(product_id)
            if hard_delete:
                del self._products[product_id]
                return

            if record.is_deleted:
                return

            now = utc_now()
            self._products[product_id] = replace(record, is_deleted=True, updated_at=now, deleted_at=now)

    def _require_product(self, product_id: str) -> _ProductRecord:
        try:
            return self._products[product_id]
        except KeyError as exc:
            raise ProductNotFoundError(f"Product '{product_id}' not found") from exc

    def _ensure_unique_sku(self, sku: str, *, exclude_id: str | None = None) -> None:
        for product_id, record in self._products.items():
            if product_id == exclude_id:
                continue
            if record.sku == sku:
                raise DuplicateSKUError(f"SKU '{sku}' already exists")

    def _matches_filter(self, record: _ProductRecord, filter_: ProductFilter) -> bool:
        if filter_.sku and record.sku != filter_.sku:
            return False
        if filter_.category and (record.category or "").lower() != filter_.category.lower():
            return False
        if filter_.min_price is not None and record.price < filter_.min_price:
            return False
        if filter_.max_price is not None and record.price > filter_.max_price:
            return False
        if filter_.min_stock is not None and record.stock < filter_.min_stock:
            return False
        if filter_.max_stock is not None and record.stock > filter_.max_stock:
            return False
        if filter_.query and not self._matches_query(record, filter_.query):
            return False
        return True

    def _matches_query(self, record: _ProductRecord, query: str) -> bool:
        needle = query.casefold()
        haystacks = [record.name, record.sku, record.description or "", record.category or ""]
        for haystack in haystacks:
            candidate = haystack.casefold()
            if needle in candidate:
                return True
            if candidate and SequenceMatcher(None, needle, candidate).ratio() >= 0.6:
                return True
        return False

    def _sort_key(self, record: _ProductRecord, sort_by: str):
        return getattr(record, sort_by)


def replace_record(record: _ProductRecord, data: dict[str, object]) -> _ProductRecord:
    return replace(
        record,
        name=data.get("name", record.name),
        sku=data.get("sku", record.sku),
        description=data.get("description", record.description),
        price=data.get("price", record.price),
        stock=data.get("stock", record.stock),
        category=data.get("category", record.category),
    )
