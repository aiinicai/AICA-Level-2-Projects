from repositories import category_repository, asset_repository


def test_category_based_asset_ids(db_conn):
    conn = db_conn
    computer_id = category_repository.create_category(conn, "Computers", "COM")
    furniture_id = category_repository.create_category(conn, "Furniture & Fixtures", "FNF")
    plant_id = category_repository.create_category(conn, "Plant & Machinery", "PNM")

    id1 = asset_repository.generate_next_asset_id(conn, computer_id, "COM")
    id2 = asset_repository.generate_next_asset_id(conn, computer_id, "COM")
    id3 = asset_repository.generate_next_asset_id(conn, furniture_id, "FNF")
    id4 = asset_repository.generate_next_asset_id(conn, plant_id, "PNM")

    assert id1 == "COM-000001"
    assert id2 == "COM-000002"
    assert id3 == "FNF-000001"
    assert id4 == "PNM-000001"


def test_sequential_category_ids_continue(db_conn):
    conn = db_conn
    cat_id = category_repository.create_category(conn, "Computers", "COM")
    asset_repository.generate_next_asset_id(conn, cat_id, "COM")
    asset_repository.generate_next_asset_id(conn, cat_id, "COM")
    third = asset_repository.generate_next_asset_id(conn, cat_id, "COM")
    assert third == "COM-000003"