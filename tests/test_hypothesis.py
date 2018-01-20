import hypothesis
from hypothesis import strategies as st
from mashpack import ExtType


@st.composite
def mashpack_obj(draw):
    obj_type = draw(st.integers(min_value=0, max_value=9))
    if obj_type == 0:
        return draw(st.dictionaries(keys=st.text(min_size=1, max_size=0xFF),
                                    values=mashpack_obj(),
                                    average_size=4))
    elif obj_type == 1:
        return draw(st.lists(mashpack_obj(), average_size=4))
    elif obj_type == 2:
        return draw(st.integers(min_value=-0x7FFFFFFF, max_value=0xFFFFFFFF))
    elif obj_type == 3:
        return draw(st.floats())
    elif obj_type == 4:
        return True
    elif obj_type == 5:
        return False
    elif obj_type == 6:
        return None
    elif obj_type == 7:
        return draw(st.text(min_size=0, max_size=0xFFFFFF, average_size=0xFF))
    elif obj_type == 8:
        return ExtType(draw(st.integers(min_value=0, max_value=0x7F)), draw(st.binary(min_size=0, max_size=0xFFFFFF, average_size=0xFF)))
    else:
        return draw(st.binary(min_size=0, max_size=0xFFFFFF, average_size=0xFF))


@hypothesis.given(obj=mashpack_obj())
def test_pack_and_unpack_hypothesis(obj, packer, unpacker_type):
    unpacker = unpacker_type()
    data = packer.pack(obj)
    unpacker.feed(data)
    assert unpacker.unpack() == obj
    assert not unpacker._got_extra_data()
