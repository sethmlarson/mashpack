# Mashpack

## Specification

### Data Types Overview

| Data Type | Prefix      | Prefix Length |
|-----------|-------------|---------------|
| PMAP      | `b00xxxxxx` | 2             |
| PSTR      | `b01xxxxxx` | 2             |
| PARRAY    | `b100xxxxx` | 3             |
| PBIN      | `b101xxxxx` | 3             |
| PUINT     | `b110xxxxx` | 3             |
| FALSE     | `b11100000` | 8             |
| TRUE      | `b11100001` | 8             |
| MAP16     | `b11101000` | 8             |
| MAP32     | `b11101001` | 8             |
| STR16     | `b11100010` | 8             |
| STR32     | `b11100011` | 8             |
| STR64     | `b11100100` | 8             |
| ARRAY8    | `b11110000` | 8             |
| ARRAY16   | `b11101010` | 8             |
| ARRAY32   | `b11101011` | 8             |
| TARRAY8   | `b11101100` | 8             |
| TARRAY16  | `b11101101` | 8             |
| TARRAY32  | `b11101110` | 8             |
| BIN8      | `b11101111` | 8             |
| BIN16     | `b11100101` | 8             |
| BIN32     | `b11100110` | 8             |
| BIN64     | `b11100111` | 8             |
| INT8      | `b11110010` | 8             |
| INT16     | `b11110011` | 8             |
| INT32     | `b11110100` | 8             |
| INT64     | `b11110101` | 8             |
| UINT8     | `b11110110` | 8             |
| UINT16    | `b11110111` | 8             |
| UINT32    | `b11111000` | 8             |
| UINT64    | `b11111001` | 8             |
| FLOAT32   | `b11101100` | 8             |
| FLOAT64   | `b11101101` | 8             |
| TIMESTAMP | `b11101010` | 8             |
| MATRIX16  | `b11111110` | 8             |
| MATRIX32  | `b11101011` | 8             |
| EXT8      | `b11110001` | 8             |
| EXT32     | `b11101110` | 8             |
| NULL      | `b11111111` | 8             |

## Future Improvements

- `MATRIX` which is where a list of lists can be condensed into a single list
  and only encode the lengths of the two dimensions. This can be done if the system
  detects `ARRAY[ARRAY[TYPE]]` and all inner `ARRAY`s are the same length.
  
  There's also great potential in encoding large arrays as instead of `VARINT(3) + VARINT(3) * N` for
  encoding the length of the arrays the length is encoded in `VARINT(4) + VARINT(0)` which can
  store much larger values.
  
  Potential for use in graphics, data science, and machine learning due to densely packed
  data for storage in database/memory-store such as Redis or Memcached as well as when
  being transmitted over the wire in a protocol.
  
  Example:
  ```
  Encoding [[1.0], [1.0], [1.0]] comparison between ARRAY[ARRAY] and MATRIX

  ARRAY[ARRAY]
  b100|10011[b100|10001[b01110011[FLOAT],b100|10001[b01110011[FLOAT],b100|10001[b01110011[FLOAT]] (31 bytes)
  
  MATRIX
  b1110|1011,b1000001[b01110011[FLOAT],[FLOAT],[FLOAT]] (27 bytes, 13% savings)
  ```

- Handling of `TARRAY*[TRUE/FALSE]` to pack into binary

- Handling of special cases such as `MATRIX[NONE/TRUE/FALSE]` which would literally map as a header
  with length information and the first type and then no other data.

- User-defined `EXT` types.

- Implement a pure-Python version of the specification as well as a Cython implementation.

## Implementations

- [Python](https://github.com/SethMichaelLarson/mshpack) (WIP)

## License

Apache-2.0
