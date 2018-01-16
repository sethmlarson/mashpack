# Mashpack

## Motivation

Mashpack is based on a combination of [MessagePack](https://github.com/msgpack/msgpack)
for packing JSON-like objects into binary and [HTTP/2 HPACK](https://http2.github.io/http2-spec/compression.html)
for encoding [variable-length integers](https://http2.github.io/http2-spec/compression.html#rfc.section.5.1)
in order to achieve superior JSON-object compression.

Variable length integers are less efficient at representing numbers compared
to a packed uint32 if both are 32 bits long but when it comes to representing
integers within 0x00000000-0xFFFFFFFF the variable length integer will only use
the space required to represent the integer and therefore optimize for smaller
integers.

Using this method also allows Mashpack to break away from requiring
multiple sizes for each data type compared to MessagePack. (`ARRAY` in Mashpack
is capable of representing MessagePack's `fixarray`, `array16` and `array32`)

Variable length integers also remove the requirement that all collections cannot
be longer than 2\*\*32-1 which is a constraint inherant to MessagePack's collection types.

This repository also serves as a "reference-implementation" of the specification in Python. The specification and
implementation are currently works in progress, feel free to contribute with a pull request!

## Specification

### Data Types Overview

| data type | prefix      | prefix length |
|-----------|-------------|---------------|
| ARRAY     | `b100`      | 3             |
| INT       | `b101`      | 3             |
| MAP       | `b110`      | 3             |
| STR       | `b111`      | 3             |
| RESERVED  | `b0000`     | 4             |
| RESERVED  | `b0001`     | 4             |
| ARRAYT    | `b0010`     | 4             |
| MAPT      | `b0011`     | 4             |
| MATRIX    | `b0100`     | 4             |
| NEGINT    | `b0101`     | 4             |
| BIN       | `b0110`     | 4             |
| NULL      | `b01110000` | 8             |
| TIMESTAMP | `b01110001` | 8             |
| FLOAT32   | `b01110010` | 8             |
| FLOAT64   | `b01110011` | 8             |
| FALSE     | `b01110100` | 8             |
| TRUE      | `b01110101` | 8             |
| RESERVED  | `b01110110` | 8             |
| RESERVED  | `b01110111` | 8             |
| EXT       | `b01111XXX` | 8             |

### Variable-Length Integers

A variable length integer is encoded on one or more bytes in the following format:
Start with a "prefix" which the number of bits to offset into the first byte.
A prefix of zero means to use the whole byte. A prefix of 3 means to use the least
significant 5 bits. Of these bits there are N-1 data bits and 1 stop bit.  If the value
is 1 in the most significant bit (after accounting for prefix) then the integer is complete
otherwise there is another byte to consume. All data is shifted by 7 bits and the next byte
is added and processed similarly.

Within this specification a variable-length integer is labeled as `varint(prefix)`.

Here's what the integer 1283 would look like represented with a prefix of 3:

```
+-----+---------+------------+
| xxx | [0]0011 | [1]0000101 |
+-----+---------+------------+

where
- xxx is the prefix bits that aren't a part of the integer.
- [N] are the stop bits. Notice the first stop bit is 0 indicating continue
  and the second is 1 indicating stop.
- 1283 == (b0000101 << 4) + b0011 == b00001010000011
```

### Arrays (`ARRAY`, `ARRAYT`)

```
ARRAY:
+-----+-----------+============================+
| 100 | varint(3) | N mashpack-encoded objects |
+-----+-----------+============================+

ARRAYT:
+------+-----------+=======================+=========================================+
| 0010 | varint(4) | mashpack object w/ type | N-1 mashpack-encoded objects w/o type |
+------+-----------+=======================+=========================================+
```

### Integers (`INT` and `NEGINT`)

```
INT:
+-----+-----------+
| 101 | varint(3) |
+-----+-----------+

NEGINT:
+------+-----------+
| 0101 | varint(4) |
+------+-----------+
```

### Maps (`MAP`, `MAPT`)

```
MAP:
+-----+-----------+==============================+
| 110 | varint(3) | N*2 mashpack-encoded objects |
+-----+-----------+==============================+

MAPT:
+------+-----------+============================+=====================================+
| 0011 | varint(4) | 2 mashpack objects w/ type | N-2 mshpck-encoded objects w/o type |
+------+-----------+============================+=====================================+
```

### Strings (`STR` and `BIN`)

```
STR:
+-----+-----------+===========================+
| 111 | varint(3) | N bytes of unicode string |
+-----+-----------+===========================+

BIN:
+------+-----------+========================+
| 0110 | varint(4) | N bytes of byte string |
+------+-----------+========================+
```

### Matrix (`MATRIX`)

```
MATRIX:
+------+-----------+-----------+===========================+=================================+
| 0100 | varint(4) | varint(8) | 1 mashpack object w/ type | N*M-1 mashpack objects w/o type |
+------+-----------+-----------+===========================+=================================+
```

### Bools (`TRUE` and `FALSE`)

```
FALSE:
+----------+
| 01110100 |
+----------+

TRUE:
+----------+
| 01110100 |
+----------+
```

### Floats (`FLOAT32` and `FLOAT64`)

```
FLOAT32:
+----------+=================================+
| 01110010 | IEEE 754 single precision float |
+----------+=================================+

FLOAT64:
+----------+=================================+
| 01110011 | IEEE 754 double precision float |
+----------+=================================+
```

### Null (`NULL`)

```
NULL:
+----------+
| 01110000 |
+----------+
```

### Extensions (`EXT`)

```
EXT:
+-------+------------+
| 01111 | varint(5)  |
+-------+------------+
```

## Future Improvements

- `MAPT`, `ARRAYT` for 'typed map' and 'typed array' which the first element
  declares it's type information and then the rest of the elements follow the
  same type information. This allows for getting rid of the type prefix on
  items that are extensible.
  
  This is especially useful for large arrays of integers or floats as it removes
  lots of header information.
  
  Example:
  
  ```
  Encoding [0.0] * 4 comparison between ARRAY and ARRAYT(INT)

  ARRAY
  b100|10100[b01110011[FLOAT],b01110011[FLOAT],b01110011[FLOAT],b01110011[FLOAT]] (37 bytes)
  
  ARRAYT(FLOAT64)
  b0010|1100[b01110011[FLOAT],[FLOAT],[FLOAT],[FLOAT]] (34 bytes)
  ```

- `MATRIX` which is where a list of lists can be condensed into a single list
  and only encode the lengths of the two dimensions. This can be done if the system
  detects `ARRAY[ARRAYT[TYPE]]` and all inner `ARRAYT`s are the same length.
  
  There's also great potential in encoding large arrays as instead of `VARINT(3)` for
  encoding the length of the arrays the length is encoded in `VARINT(7)` which can
  store much larger values. Potential for use in graphics, data science, and machine learning.
  
  Example:
  ```
  Encoding [[1.0], [1.0], [1.0]] comparison between ARRAY[ARRAY] and MATRIX

  ARRAY[ARRAY]
  b100|10011[b100|10001[b01110011[FLOAT],b100|10001[b01110011[FLOAT],b100|10001[b01110011[FLOAT]] (31 bytes)
  
  MATRIX
  b0100|0011,b1000001[b01110011[FLOAT],[FLOAT],[FLOAT]] (27 bytes)
  ```

- Handling of special cases such as `ARRAYT[NONE/TRUE/FALSE]` which would literally map as an `ARRAYT`
  header with length information and the first type and then no other data.
  
- Figure out a good datatypes for `b0000` and `b0001` because they're in a valuable location having 4 prefix bytes.

- User-defined `EXT` types. `b01110000` to `b01110111` are reserved for use by Mashpack.

- Implement a pure-Python version of the specification as well as a Cython implementation.

## Comparison to JSON and MsgPack

TODO

## Implementations

- [Python](https://github.com/SethMichaelLarson/mshpack) (WIP)

## License

Apache-2.0
