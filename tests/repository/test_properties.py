from pmea.repository.properties import PropertiesRepository

def test_properties_by_id():
    repo = PropertiesRepository(properties_path="data/properties_db.json")
    assert repo.property_exists(100)
    assert repo.property_exists(9)
    assert not repo.property_exists(101)
    assert repo.get_property_by_id(100) is not None
    assert repo.get_property_by_id(9) is not None
    assert repo.get_property_by_id(101) is None