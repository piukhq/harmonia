from app.naming import gfycat_name


def test_default_args():
    assert len(gfycat_name().split('-')) == 3


def test_custom_counts():
    assert len(gfycat_name(5, 5).split('-')) == 10
    assert len(gfycat_name(0, 1).split('-')) == 1
    assert len(gfycat_name(1, 0).split('-')) == 1
    assert len(gfycat_name(0, 4).split('-')) == 4
    assert len(gfycat_name(4, 0).split('-')) == 4
    assert len(gfycat_name(0, 0)) == 0


def test_custom_separators():
    assert '+' in gfycat_name(separator='+')
    assert 'testing' in gfycat_name(separator='testing')
    assert '-' not in gfycat_name(separator='')
