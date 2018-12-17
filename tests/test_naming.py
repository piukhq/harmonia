from app import naming


def test_name_maxification():
    assert naming.maxify("flaming", "longbow") == ["flongbow"]
    assert naming.maxify("irritating", "ocarina") == ["irritating", "ocarina"]
    assert naming.maxify("baleful", "brooch") == ["baleful", "brooch"]
    assert naming.maxify("cynical", "crossbow") == ["cynicrossbow"]
