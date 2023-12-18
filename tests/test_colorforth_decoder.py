from colorforth_decoder import BlockDecoder
import struct


def test_decode_numbers():
    test_value = 12789
    encoded = test_value << 1
    encoded = encoded | 1  # hex display
    encoded = encoded << 4
    encoded = encoded | 8  # yellow
    test_bytes = list(struct.pack('<i', encoded))
    test_bytes += [0] * (1024 - len(test_bytes))  # complete to 1024 length

    decoder = BlockDecoder(test_bytes)
    decoder.create_text_representation()
    out_lines = decoder.output_text.split('\n')
    hex_value = hex(test_value)[2:]
    assert out_lines[1] == f'y|${hex_value}'


def test_decode_long_number():
    test_value = 0  # the actual number comes in the next word
    encoded = test_value << 1
    encoded = encoded | 0  # decimal display
    encoded = encoded << 4
    encoded = encoded | 2  # yellow for long num
    test_bytes = list(struct.pack('<i', encoded))

    test_value_2 = 0b1100000000000000000000000000000  # too big to fit in a single 32 bit encoding (>27 bits)
    test_bytes += list(struct.pack('<i', test_value_2))

    test_bytes += [0] * (1024 - len(test_bytes))  # complete to 1024 length

    decoder = BlockDecoder(test_bytes)
    decoder.create_text_representation()
    out_lines = decoder.output_text.split('\n')
    assert out_lines[1] == f'y|#{test_value_2}'


def test_decode_letters():
    encoded = 0
    encoded = encoded | 1  # r
    encoded = encoded << 4
    encoded = encoded | 2  # t
    encoded = encoded << 4
    encoded = encoded | 3  # o
    encoded = encoded << 4
    encoded = encoded | 4  # e
    encoded = encoded << 4
    encoded = encoded | 5  # a
    encoded = encoded << 4
    encoded = encoded | 6  # n
    encoded = encoded << 4
    encoded = encoded | 7  # i
    encoded = encoded << 4
    encoded = encoded | 9  # white

    test_bytes = list(struct.pack('<i', encoded))

    test_bytes += [0]*(1024-len(test_bytes))  # complete to 1024 length
    test_bytes = bytes(test_bytes)

    decoder = BlockDecoder(test_bytes)
    decoder.create_text_representation()
    out_lines = decoder.output_text.split('\n')

    assert out_lines[1] == 'w|rtoeani'


def test_magenta():
    variable = 1  # r
    variable = variable << (7*4)
    variable = variable | 0xc

    value = 12345

    test_bytes = list(struct.pack('<i', variable))
    test_bytes += list(struct.pack('<i', value))
    test_bytes += [0] * (1024 - len(test_bytes))  # complete to 1024 length

    decoder = BlockDecoder(test_bytes)
    decoder.create_text_representation()
    out_lines = decoder.output_text.split('\n')

    assert out_lines[1] == 'm|r m|12345'
