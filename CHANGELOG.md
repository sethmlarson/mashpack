# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added

- Add the Python implementation of `mashpack.Unpacker`.
- Add the `ARRAY8`, `ARRAY16`, `ARRAY32` data types for typed arrays to save space on header information.
- Add the `MARRAYP`, `MARRAY8`, `MARRAY16`, and `MARRAY32` data types for mixed
  type arrays which are equivalent to MessagePack arrays.
- Add the `EXT16` data type.
- Add all the base data types: `STRP`, `MAPP`, `INTP`, `NINTP`, `ARRAYP`,
  `FALSE`, `TRUE`, `MAP8`, `MAP16`, `MAP32`, `STR8`, `STR16`, `STR32`,
  `ARRAY8`, `ARRAY16`, `ARRAY32`, `BIN8`, `BIN16`, `BIN32`, `INT8`, `INT16`,
  `INT32`, `INT64`, `UINT8`, `UINT16`, `UINT32`, `UINT64`, `FLOAT32`, `FLOAT64`,
  `EXT8`, `EXT32`, and `NULL`.

### Removed
- Removed the `ARRAYP` data type in favor of `MARRAYP`.
- Removed the `MATRIX16` and `MATRIX32` types in favor of extensions.

[Unreleased]: https://github.com/SethMichaelLarson/mashpack/compare/e094d8eef3c29acfd0201141703a22de52af2ba0...HEAD

| MAPP      | `00xxxxxx` | `0x00-0x3F` |
| STRP      | `01xxxxxx` | `0x40-0x7F` |
| MARRAYP   | `100xxxxx` | `0x80-0x9F` |
| INTP      | `101xxxxx` | `0xA0-0xBF` |
| NINTP     | `110xxxxx` | `0xC0-0xDF` |
| FALSE     | `11100000` | `0xE0`      |
| TRUE      | `11100001` | `0xE1`      |
| MAP8      | `11100010` | `0xE2`      |
| MAP16     | `11100011` | `0xE3`      |
| MAP32     | `11100100` | `0xE4`      |
| STR8      | `11100101` | `0xE5`      |
| STR16     | `11100110` | `0xE6`      |
| STR32     | `11100111` | `0xE7`      |
| ARRAY8    | `11101000` | `0xE8`      |
| ARRAY16   | `11101001` | `0xE9`      |
| ARRAY32   | `11101010` | `0xEA`      |
| MARRAY8   | `11101011` | `0xEB`      |
| MARRAY16  | `11101100` | `0xEC`      |
| MARRAY32  | `11101101` | `0xED`      |
| BIN8      | `11101110` | `0xEE`      |
| BIN16     | `11101111` | `0xEF`      |
| BIN32     | `11110000` | `0xF0`      |
| INT8      | `11110001` | `0xF1`      |
| INT16     | `11110010` | `0xF2`      |
| INT32     | `11110011` | `0xF3`      |
| INT64     | `11110100` | `0xF4`      |
| UINT8     | `11110101` | `0xF5`      |
| UINT16    | `11110110` | `0xF6`      |
| UINT32    | `11110111` | `0xF7`      |
| UINT64    | `11111000` | `0xF8`      |
| FLOAT32   | `11111001` | `0xF9`      |
| FLOAT64   | `11111010` | `0xFA`      |
| EXT8      | `11111011` | `0xFB`      |
| EXT16     | `11111100` | `0xFC`      |
| EXT32     | `11111101` | `0xFD`      |
| RESERVED  | `11111110` | `0xFE`      |
| NULL      | `11111111` | `0xFF`      |