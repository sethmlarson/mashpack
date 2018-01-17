# Mashpack

Mashpack is a JSON-object serialization and compression specification
inspired by [MessagePack](https://msgpack.org)
but is tweaked for optimizing for common JSON objects and for data
structures and layouts used commonly in data science, image processing,
and machine learning.

There are a few notable changes between Mashpack and MessagePack along with
explanations as to why these changes were made:

- Mashpack changes the order of the prefixing for data types from what MessagePack
  would describe as it's 'fixed' data types to be spread more evenly across
  common data types that are used in almost even JSON object.

  These prefixed data types are the ones that can be described with only a single
  byte of header information and are constrained to a range of values to maintain
  this property. The more data that can fit into these types the less often
  the packer will have to add additional header bytes.

  | Spec        | Prefixes                                                                   |
  |-------------|----------------------------------------------------------------------------|
  | Mashpack    | `MAPP(2), STRP(2) TARRAYP(3) INTP(3)`                                      |
  | MessagePack | `positive fixint(1), fixstr(3), negative fixint(3), fixmap(4) fixarray(4)` |

  | Data Type             | Range in Mashpack  | Range in MessagePack |
  |-----------------------|--------------------|----------------------|
  | `MAPP vs fixmap`      | 0 to 63 key-values | 0 to 15 key-values   |
  | `STRP vs fixstr`      | 0 to 63 characters | 0 to 31 characters   |
  | `TARRAYP vs fixarray` | 0 to 31 elements\* | 0 to 15 elements     |
  | `NINTP vs nfixint`    | -1 to -32          | -1 to -32            |
  | `INTP vs pfixint`     | 0 to 31            | 0 to 127             |

  \* Must be the same type. See explanation of `TARRAYP` below.

- Mashpack adds 'typed' array types which all have the name `TARRAY*`. These
  function, pack, and unpack exactly the same as normal arrays except they
  take advantage of having the same type of object within them in order to
  compress tighter together only requiring the type information of all
  objects within the array at the beginning of the array. In most cases arrays
  will all be of similar type and so this situation happens quite frequently
  within common JSON objects.

- Mashpack adds the `MATRIX16` and `MATRIX32` objects which are essentially optimized
  versions of `TARRAY16[TARRAY16]` and `TARRAY32[TARRAY32]` objects. They're
  useful for storing data frames, matricies, graphs, and data that is used for
  machine learning algorithms. These objects vastly reduce the overhead of
  storing large amounts of data that all have the same data type.

  Below is an example of how a `ARRAY16`, `TARRAY16`, and `MATRIX16` would encode a
  512x512 matrix of `FLOAT32` values. Because the amount of data from the `FLOAT32` is
  constant among the three we only list the amount of header bytes:

  ```
  Encoding a 512x512 matrix of FLOAT32 into ARRAY16[ARRAY16], TARRAY16[TARRAY16] and MATRIX16

  ARRAY16[ARRAY16]
  b11101000,b00100000[b11101000,b00100000[b11111001,FLOAT]*512]*512 (263,170 header bytes)

  TARRAY16[TARRAY16]
  b11101011,b11101011,[b00100000,b11111001[FLOAT*512]]*512 (1,026 header bytes)

  MATRIX
  b11111011,b00100000,b00100000,b11111001[FLOAT*262144] (4 header bytes)
  ```

- Mashpack sheds a lot of the `EXT*` data types that are used in MessagePack in favor
  of just two: `EXT8` and `EXT32`. Mashpack reserves all `EXT` codes that have a `1`
  in the most significant bit of their extension code.

## Specification

### Data Types Overview

| Data Type | Prefix     | First Byte  |
|-----------|------------|-------------|
| MAPP      | `00xxxxxx` | `0x00-0x3F` |
| STRP      | `01xxxxxx` | `0x40-0x7F` |
| TARRAYP   | `100xxxxx` | `0x80-0x9F` |
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
| TARRAY8   | `11101011` | `0xEB`      |
| TARRAY16  | `11101100` | `0xEC`      |
| TARRAY32  | `11101101` | `0xED`      |
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
| MATRIX16  | `11111011` | `0xFB`      |
| MATRIX32  | `11111100` | `0xFC`      |
| EXT8      | `11111101` | `0xFD`      |
| EXT32     | `11111110` | `0xFE`      |
| NULL      | `11111111` | `0xFF`      |

### Map Family (`MAPP`, `MAP8`, `MAP16`, `MAP32`)

```

```

### String Family (`STRP`, `STR8`, `STR16`, `STR32`)

`TODO`

### Typed Array Family (`TARRAYP`, `TARRAY8`, `TARRAY16`, `TARRAY32`)

`TODO`

### Array Family (`ARRAY8`, `ARRAY16`, `ARRAY32`)

`TODO`

### Binary Family (`BIN8`, `BIN16`, `BIN32`)

`TODO`

### Integer Family (`INTP`, `NINTP`, `UINT8`, `UINT16`, `UINT32`, `UINT64`, `INT8`, `INT16`, `INT32`, `INT64`)

`INT` format stores a signed or unsigned integer in 1, 2, 3, 5, or 9 bytes.

```
INTP stores 5-bit positive integer
+--------+
|101XXXXX|
+--------+
where XXXXX is a 5-bit unsigned integer

NINTP stores 5-bit negative integer
+--------+
|110YYYYY|
+--------+
where YYYYY is a 5-bit unsigned integer


INT8 stores 8-bit signed integer
+--------+--------+
|  0xF1  |XXXXXXXX|
+--------+--------+
where XXXXXXXX is an 8-bit signed integer

INT16 stores 16-bit signed integer
+--------+--------+--------+
|  0xF2  |XXXXXXXX|XXXXXXXX|
+--------+--------+--------+
where XXXXXXXX_XXXXXXXX is an 16-bit unsigned integer

INT32 stores 32-bit signed integer
+--------+--------+--------+--------+--------+
|  0xF3  |XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|
+--------+--------+--------+--------+--------+
where XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX is an 32-bit signed integer

INT64 stores 64-bit signed integer
+--------+--------+--------+--------+--------+--------+--------+--------+--------+
|  0xF4  |XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|
+--------+--------+--------+--------+--------+--------+--------+--------+--------+
where XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX is an 64-bit signed integer


UINT8 stores 8-bit unsigned integer
+--------+--------+
|  0xF1  |XXXXXXXX|
+--------+--------+
where XXXXXXXX is an 8-bit unsigned integer

UINT16 stores 16-bit unsigned integer
+--------+--------+--------+
|  0xF2  |XXXXXXXX|XXXXXXXX|
+--------+--------+--------+
where XXXXXXXX_XXXXXXXX is an 16-bit unsigned integer

UINT32 stores 32-bit unsigned integer
+--------+--------+--------+--------+--------+
|  0xF3  |XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|
+--------+--------+--------+--------+--------+
where XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX is an 32-bit unsigned integer

UINT64 stores 64-bit unsigned integer
+--------+--------+--------+--------+--------+--------+--------+--------+--------+
|  0xF4  |XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|
+--------+--------+--------+--------+--------+--------+--------+--------+--------+
where XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX is an 64-bit unsigned integer
```

### Boolean Family (`FALSE`, `TRUE`)

`BOOL` format stores a true or false in one byte.

```
false:
+--------+
|  0xE0  |
+--------+

true:
+--------+
|  0xE1  |
+--------+
```

### Float Family (`FLOAT32`, `FLOAT64`)

```
FLOAT32 stores IEEE 754 single precision floating point number.
+--------+--------+--------+--------+--------+
|  0xF9  |XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|
+--------+--------+--------+--------+--------+
where XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX is a big-endian IEEE 754 single precision float point number.

FLOAT64 stores IEEE 754 double precision floating point number.
+--------+--------+--------+--------+--------+--------+--------+--------+--------+
|  0xFA  |XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|XXXXXXXX|
+--------+--------+--------+--------+--------+--------+--------+--------+--------+
where XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX_XXXXXXXX is a big-endian
IEEE 754 double precision floating point number
```

### Matrix Family (`MATRIX16`, `MATRIX32`)

`TODO`

### Extension Family (`EXT8`, `EXT32`)

`TODO`

### Null Family (`NULL`)

`NULL` format stores a null/nil/none value in 1 byte.

```
+--------+
|  0xFF  |
+--------+
```

## Future Improvements

- Handling of `TARRAY*[TRUE/FALSE]` and `MATRIX*[TRUE/FALSE]` to pack into binary

- Handling of `TARRAY*`, and `MATRIX*` with item types that are in the 'constant' category
  such as `NULL`, `TRUE`, and `FALSE` which would literally map as a header
  with length information.

- Implement a pure-Python version of the specification as well as a Cython implementation.

## Implementations

- [Python](https://github.com/SethMichaelLarson/mshpack) (WIP)

## License

Apache-2.0
