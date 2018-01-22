import struct
from mashpack import ExtType


def test_pack_ext8(packer):
    assert packer.pack(ExtType(127, b'\x00' * 0xFF)) == b'\xDB\xFF\x7F' + (b'\x00' * 0xFF)


def test_pack_ext16(packer):
    assert packer.pack(ExtType(127, b'\x00' * 0x100)) == b'\xDC' + struct.pack('>H', 0x100) + b'\x7F' + (b'\x00' * 0x100)


def test_pack_ext32(packer):
    assert packer.pack(ExtType(127, b'\x00' * 0x10000)) == b'\xDD' + struct.pack('>I', 0x10000) + b'\x7F' + (b'\x00' * 0x10000)
