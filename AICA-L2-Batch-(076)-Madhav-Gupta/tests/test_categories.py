import pytest
from repositories import category_repository
from utils.validation import ValidationError, validate_category_code


def test_update_category_name_and_code(db_conn):
    conn = db_conn
    cat_id = category_repository.create_category(conn, "Computers", "COM")
    category_repository.update_category(conn, cat_id, category_name="Computers & IT", category_code="CIT")
    updated = category_repository.get_category(conn, cat_id)
    assert updated["category_name"] == "Computers & IT"
    assert updated["category_code"] == "CIT"


def test_deactivate_and_reactivate_category(db_conn):
    conn = db_conn
    cat_id = category_repository.create_category(conn, "Computers", "COM")
    category_repository.set_category_active(conn, cat_id, False)
    assert category_repository.get_category(conn, cat_id)["active"] == 0
    category_repository.set_category_active(conn, cat_id, True)
    assert category_repository.get_category(conn, cat_id)["active"] == 1


def test_cannot_rename_to_duplicate_code(db_conn):
    conn = db_conn
    cat1 = category_repository.create_category(conn, "Computers", "COM")
    category_repository.create_category(conn, "Furniture", "FNF")
    existing = category_repository.existing_codes(conn, exclude_category_id=cat1)
    with pytest.raises(ValidationError):
        validate_category_code("FNF", existing)