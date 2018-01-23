# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## [1.0.0] (2018-01-22)
### Added

- Add support for extensions using `ExtType`.
- Add the Python implementation of `mashpack.Packer`.
- Add the Python implementation of `mashpack.Unpacker`.
- Add the `ARRAY8`, `ARRAY16`, `ARRAY32` data types for typed arrays to save
  space on header information.
- Add the `MARRAYP`, `MARRAY8`, `MARRAY16`, and `MARRAY32` data types for
  mixed type arrays which are equivalent to MessagePack arrays.
- Add the `EXT16` data type.
- Add all the base data types: `STRP`, `MAPP`, `INTP`, `NINTP`, `ARRAYP`,
  `FALSE`, `TRUE`, `MAP8`, `MAP16`, `MAP32`, `STR8`, `STR16`, `STR32`,
  `ARRAY8`, `ARRAY16`, `ARRAY32`, `BIN8`, `BIN16`, `BIN32`, `INT8`, `INT16`,
  `INT32`, `INT64`, `UINT8`, `UINT16`, `UINT32`, `UINT64`, `FLOAT32`,
  `FLOAT64`, `EXT8`, `EXT32`, and `NULL`.

### Removed
- Removed the `ARRAYP` data type in favor of `MARRAYP`.
- Removed the `MATRIX16` and `MATRIX32` types in favor of extensions.

[1.0.0]: https://github.com/SethMichaelLarson/mashpack/compare/e094d8eef3c29acfd0201141703a22de52af2ba0...1.0.0
