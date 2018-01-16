# mshpck

## Motivation

mshpck (Pronounced "mish-pick") is based on a combination of [MessagePack](https://github.com/msgpack/msgpack)
for packing JSON-like objects into binary and [HTTP/2 HPACK](https://http2.github.io/http2-spec/compression.html)
for encoding [variable-length integers](https://http2.github.io/http2-spec/compression.html#rfc.section.5.1)
in order to achieve superior JSON-object compression. mshpck has the same interface as MessagePack including extensions.

By combining these two specifications we're able to achieve a header which is typically the size of
a nybble rather than a whole byte. This enables more dense compression of values, especially within
data structures such as arrays and maps and when using 'singleton' values such as `TRUE`, `FALSE`, and `NULL`
which only take a nybble each.

## Specification

### Data Types Overview

| data type | prefix  | prefix length | nibblable |
|-----------|---------|---------------|-----------|
| array     | `b100`  | 3             | false     |
| int       | `b101`  | 3             | false     |
| map       | `b110`  | 3             | false     |
| str       | `b111`  | 3             | false     |
| false     | `b0000` | 4             | true      |
| true      | `b0001` | 4             | true      |
| float32   | `b0010` | 4             | true      |
| float64   | `b0011` | 4             | true      |
| null      | `b0100` | 4             | true      |
| negint    | `b0101` | 4             | false     |
| bin       | `b0110` | 4             | false     |
| ext       | `b0111` | 4             | false     |

### Variable-Length Integers

A variable length integer is encoded on one or more bytes in the following format:
Start with a "prefix" which the number of bits to offset into the first byte.
A prefix of zero means to use the whole byte. A prefix of 3 means to use the least
significant 5 bits. Of these bits there are N-1 data bits and 1 stop bit.  If the value
is 1 in the most significant bit (after accounting for prefix) then the integer is complete
otherwise there is another byte to consume. All data is shifted by 7 bits and the next byte
is added and processed similarly.

Within this specification a variable-length integer is called a `varint(prefix)`.

Here's what the integer 1283 would look like represented with a prefix of 3:

```
+-----+------------+------------+
| xxx | [0]0000101 | [1]0000011 |
+-----+------------+------------+

where
- xxx is the prefix bits that aren't a part of the integer.
- [N] are the stop bits. Notice the first stop bit is 0 indicating continue
  and the second is 1 indicating stop.
- 1283 == (b0000101 << 7) + b0000011 == b00001010000011
```

### Alignment

mshpck has the chance of aligning data on a nibble boundary instead of a byte boundary
when "nibbleable" data types are combined in a collection with non-nibblable data types.
This can come with a performance penalty for encoding and decoding but can be avoided
in some situations with maps.

One of those situations is when maps do not need to be ordered. In this case
each key-value pair is assesed if it will be guaranteed to hit a byte boundary
and will be encoded first. Then objects that contain collections in their values
and finally objects that are nibblable to reduce the performance penalty.

After encoding an array or map if the encoded object does not hit a byte boundary then the
specification will pad zero bits until the object hits a byte boundary.

### Arrays (`array`)

```
array:
+-----+-----------+==========================+
| 100 | varint(3) | N mshpck-encoded objects |
+-----+-----------+==========================+
```

### Ints (`int` and `negint`)

```
int:
+-----+-----------+
| 101 | varint(3) |
+-----+-----------+

negint:
+------+-----------+
| 0101 | varint(4) |
+------+-----------+
```

### Maps (`map`)

```
map:
+-----+-----------+============================+
| 110 | varint(3) | N*2 mshpck-encoded objects |
+-----+-----------+============================+
```

### Strings (`str` and `bin`)

```
str:
+-----+-----------+===========================+
| 111 | varint(3) | N bytes of unicode string |
+-----+-----------+===========================+

bin:
+------+-----------+========================+
| 0110 | varint(4) | N bytes of byte string |
+------+-----------+========================+
```

### Bools (`true` and `false`)

```
false:
+------+
| 0000 |
+------+

true:
+------+
| 0001 |
+------+
```

### Floats (`float32` and `float64`)

```
float32:
+------+=================================+
| 0010 | IEEE 754 single precision float |
+------+=================================+

float64:
+------+=================================+
| 0011 | IEEE 754 double precision float |
+------+=================================+
```

### Null (`null`)

```
null:
+------+
| 0100 |
+------+
```

### Extensions (`ext`)

```
ext:
+------+-----------+
| 0100 | varint(4) |
+------+-----------+
```

## Implementations

- [Python](https://github.com/SethMichaelLarson/mshpack)

## License

Apache-2.0

