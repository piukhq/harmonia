from app import naming


def test_name_generator():
    assert len(naming.new().split('-')) == 2
