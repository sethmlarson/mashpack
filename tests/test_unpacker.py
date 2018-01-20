def test_unpack_nested_maps(unpacker):
    unpacker.feed(b'\x01\x41a\x01\x41b\x01\x41c\x00')
    assert unpacker.unpack() == {'a': {'b': {'c': {}}}}
