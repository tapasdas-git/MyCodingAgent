class InventoryError(Exception):
    """Base exception for inventory operations."""


class ProductNotFoundError(InventoryError):
    """Raised when a product cannot be found."""


class DuplicateSKUError(InventoryError):
    """Raised when attempting to create or update a duplicate SKU."""
