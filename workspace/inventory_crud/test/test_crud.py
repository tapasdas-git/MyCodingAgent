from __future__ import annotations

import pytest
from pydantic import ValidationError

from workspace.inventory_crud.Coding.exceptions import DuplicateSKUError, ProductNotFoundError
from workspace.inventory_crud.Coding.repository import InventoryRepository
from workspace.inventory_crud.Coding.schemas import ProductCreate, ProductFilter, ProductUpdate


def build_product(**overrides):
    payload = {
        "name": "Alpha Widget",
        "sku": "ALPHA-001",
        "description": "Primary test product",
        "price": 19.99,
        "stock": 10,
        "category": "Widgets",
    }
    payload.update(overrides)
    return ProductCreate(**payload)


def test_crud_lifecycle_and_search():
    repository = InventoryRepository()
    created = repository.create_product(build_product())

    fetched = repository.get_product_by_id(created.id)
    assert fetched.model_dump() == created.model_dump()

    filtered = repository.list_products(ProductFilter(query="alph"))
    assert [product.id for product in filtered] == [created.id]

    updated = repository.update_product(
        created.id,
        ProductUpdate(stock=15, description="Updated description"),
    )
    assert updated.stock == 15
    assert updated.description == "Updated description"
    assert updated.sku == created.sku

    replaced = repository.update_product(
        created.id,
        ProductUpdate(
            name="Beta Widget",
            sku="BETA-002",
            description="Replacement",
            price=29.5,
            stock=7,
            category="Gadgets",
        ),
        replace=True,
    )
    assert replaced.name == "Beta Widget"
    assert replaced.sku == "BETA-002"
    assert replaced.price == 29.5
    assert replaced.stock == 7


def test_duplicate_sku_rejected():
    repository = InventoryRepository()
    repository.create_product(build_product())

    with pytest.raises(DuplicateSKUError):
        repository.create_product(build_product(name="Other", sku="ALPHA-001"))


def test_soft_delete_filters_from_default_listing():
    repository = InventoryRepository()
    created = repository.create_product(build_product())

    repository.delete_product(created.id)

    with pytest.raises(ProductNotFoundError):
        repository.get_product_by_id(created.id)

    assert repository.get_product_by_id(created.id, include_deleted=True).is_deleted is True
    assert repository.list_products() == []
    assert repository.list_products(ProductFilter(include_deleted=True))[0].id == created.id


def test_hard_delete_removes_entity():
    repository = InventoryRepository()
    created = repository.create_product(build_product())

    repository.delete_product(created.id, hard_delete=True)

    with pytest.raises(ProductNotFoundError):
        repository.get_product_by_id(created.id, include_deleted=True)


def test_missing_entity_operations_raise():
    repository = InventoryRepository()

    with pytest.raises(ProductNotFoundError):
        repository.get_product_by_id("missing")

    with pytest.raises(ProductNotFoundError):
        repository.update_product("missing", ProductUpdate(stock=1))

    with pytest.raises(ProductNotFoundError):
        repository.delete_product("missing")


def test_full_replace_requires_all_core_fields():
    repository = InventoryRepository()
    created = repository.create_product(build_product())

    with pytest.raises(ValueError, match="Full replacement requires fields"):
        repository.update_product(created.id, ProductUpdate(name="Replacement"), replace=True)


def test_validation_constraints():
    with pytest.raises(ValidationError):
        ProductCreate(
            name="Bad",
            sku="BAD-1",
            description="invalid",
            price=0,
            stock=0,
            category="Widgets",
        )

    with pytest.raises(ValidationError):
        ProductUpdate(stock=-1)
