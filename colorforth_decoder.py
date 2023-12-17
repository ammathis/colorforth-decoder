from argparse import ArgumentParser, Namespace, ArgumentTypeError
from typing import List, Iterator
import logging
from collections import namedtuple
from pathlib import Path

logger = logging.getLogger()

Result = namedtuple('Result', ['content', 'error'])


class BlockDecoder:
    CHARSETS = {
        # per https://web.archive.org/web/20080531121851/http://www.colorforth.com/chars.html
        'legacy': ' rtoeanismcylgfwdvpbhxuqkzj34567891-0.2/;:!+@*,?',
        # per https://www.greenarraychips.com/home/documents/greg/cf-characters.htm
        'greenarray': ' rtoeanismcylgfwdvpbhxuq0123456789j-k.z/;\'!+@*,?',
        # apparent set in cf2019 and family
        'howerd': ' rtoeanismcylgfwdvpbhxuq0123456789j-k.z/;:!+@*,?'
    }

    CONTINUE_VAL = '<CONTINUE>'

    function_code_to_color = {
        0: CONTINUE_VAL,
        1: 'yellow',
        3: 'red',
        4: 'green',
        7: 'cyan',
        9: 'white',
        0xa: 'white',
        0xb: 'white',
        0xc: 'magenta',
        0xd: 'silver',
        0xe: 'blue',
        8: 'yellow',
        6: 'green',
        2: 'yellow',
        5: 'green'
    }

    def __init__(self, blocks: bytes, starting_block_num: int = 0):
        self.current_block: bytes = None
        self.starting_block_num = starting_block_num
        self.cursor: int = None
        self.extracted = None
        self.output_text = None
        self.output_html = None
        self.decode_all_blocks(blocks)


    @classmethod
    def unpack_chars(cls, bits):
        cursor = 0
        extracted = []

        code_chars = cls.CHARSETS['howerd']

        code_ints = list(range(0,8)) + list(range(16,24)) + list(range(96,128))
        code_map = {k: ('' if v == ' ' else v) for k, v in zip(code_ints, code_chars)}

        while cursor < len(bits) - 1:  # there needs to be at least 2 bits at end to determine length?
            length_prefix = bits[cursor:cursor+2]

            if length_prefix in ['00', '01']:
                letter_code = bits[cursor:cursor + 4]
                letter_code += '0'*(4-len(letter_code))
            elif length_prefix == '10':
                letter_code = bits[cursor:cursor + 5]
                letter_code += '0' * (5-len(letter_code))
            elif length_prefix == '11':
                letter_code = bits[cursor:cursor + 7]
                letter_code += '0' * (7-len(letter_code))

            letter_int = int(letter_code, 2)
            try:
                decoded = code_map[letter_int]
            except KeyError as e:
                raise
            extracted.append(decoded)

            cursor += len(letter_code)

        return ''.join(extracted)  # consider rstrip

    @classmethod
    def process_text(cls, function_code: int, next_word_bits: str):
        char_bits = next_word_bits[:-4]
        unpacked = cls.unpack_chars(char_bits)
        if function_code == 0xa:
            text = unpacked.capitalize()
        elif function_code == 0xb:
            text = unpacked.upper()
        else:
            text = unpacked  # leave lowercase

        return text

    @classmethod
    def twos_complement(cls, value: int, num_bits):
        # Sourced from https://stackoverflow.com/questions/32030412/twos-complement-sign-extension-python
        sign_bit = 1 << (num_bits - 1)
        return (value & (sign_bit - 1)) - (value & sign_bit)

    @classmethod
    def process_number(cls, number_parsed: int, is_hex: bool, num_bits: int):
        signed_parsed = cls.twos_complement(number_parsed, num_bits)

        if is_hex:
            return '$' + hex(signed_parsed)[2:]
        else:
            return '#' + str(signed_parsed)

    @classmethod
    def process_short_number(cls, function_code: int, next_word_bits: str):
        is_hex = int(next_word_bits[-5], 2) > 0
        number_bits = next_word_bits[:-5]
        number_parsed = int(number_bits, 2)
        return cls.process_number(number_parsed, is_hex, len(number_bits))

    @classmethod
    def process_long_number(cls, function_code: int, next_word_bits: str, second_word_bits: str):
        is_hex = int(next_word_bits[-5], 2) > 0
        number_bits = second_word_bits
        number_parsed = int(number_bits, 2)
        return cls.process_number(number_parsed, is_hex, len(number_bits))

    @staticmethod
    def extract_function_code(bits: str) -> int:
        """
        Extract function code from the last/lowest 4 bits of a given bit string (of 0,1)
        :param bits:
        :return:
        """
        return int(bits[-4:], 2)

    def consume_next_word(self) -> List[str]:
        """
        Consume the next 32-bit word
        :return:
        """
        next_word = self.current_block[self.cursor:self.cursor + 4]
        next_word_bits = ''.join(reversed([f'{i:08b}' for i in next_word]))  # map from little endian to big endian order
        self.cursor += 4
        return next_word_bits

    def has_next_word(self) -> bool:
        return self.cursor < 1024

    def decode_raw(self) -> Iterator[str]:
        """
        Decode an entire block, leaving continuation words as-is
        :return: The decoded tokens
        """

        while self.has_next_word():

            next_word_bits = self.consume_next_word()
            function_code = self.extract_function_code(next_word_bits)

            if function_code in [0, 1, 3, 4, 7, 9, 0xa, 0xb, 0xc, 0xd, 0xe]:
                extracted_val = self.process_text(function_code, next_word_bits)
            elif function_code in [6, 8]:
                extracted_val = self.process_short_number(function_code, next_word_bits)
            elif function_code in [2, 5]:
                if self.has_next_word():
                    second_word_bits = self.consume_next_word()
                else:
                    # Weird edge case. We appear to need a second word to complete the number, but we're at the end of
                    # our block. Default to zero I guess?
                    second_word_bits = '0'*32
                try:
                    extracted_val = self.process_long_number(function_code, next_word_bits, second_word_bits)
                except ValueError as e:
                    raise
            else:
                logger.warning(f'Unrecognized function code: {function_code}!')
                extracted_val = '???'

            color = self.function_code_to_color.get(function_code, '???')
            yield color, extracted_val

    def decode_with_cont_handling(self) -> Iterator[str]:
        """
        Decode an entire block, handling the continuation words
        :return: The decoded tokens
        """

        working_color = None
        working_value = None
        for current_color, current_value in self.decode_raw():
            if working_color is None:
                # we're just starting
                working_color = current_color
                working_value = current_value
            else:
                if current_color != self.CONTINUE_VAL:
                    # We know the working value has been completed
                    yield working_color, working_value
                    working_color = current_color
                    working_value = current_value
                else:
                    # We have to append current to the working value
                    working_value = working_value + current_value

        yield working_color, working_value

    def create_text_representation(self):
        self.output_text = ''
        for block_num, block_result in enumerate(self.extracted):
            self.output_text += f'## Block {block_num + self.starting_block_num} ##\n'
            if block_result.error is not None:
                self.output_text += f'## Invalid Block? Error: {block_result.error} ##'
            else:
                self.output_text += ' '.join(('\n' if color == 'red' else '')+f'{color[0]}|{value}' for color, value in block_result.content) + '\n'

    def create_html_representation(self):
        self.output_html = ''
        self.output_html += '<!DOCTYPE html>\n<html>\n<head>\n<style>\n' \
                            'body {background-color: black; font-family: monospace; color: Orange}' \
                            '.red {color: red} .yellow {color: yellow} .green {color: green} .cyan {color: cyan}' \
                            '.white {color: white} .magenta {color: magenta} ' \
                            '.blue {color: blue} .silver {color: silver}' \
                            '</style>\n</head>\n<body>\n'

        for block_num, block_result in enumerate(self.extracted):
            self.output_html += f'<h1>## Block {block_num + self.starting_block_num} ##</h1>'
            if block_result.error is not None:
                self.output_html += f'<div>## Invalid Block? Error: {block_result.error} ##</div>'
            else:
                self.output_html += '<div>' + ' '.join(('<br>' if color == 'red' else '') + f'<span class="{color}">{value}</span>' for color, value in block_result.content)
        self.output_html += '</div>\n</body>\n</html'

    def decode_current_block(self):
        try:
            self.extracted.append(Result(content=list(self.decode_with_cont_handling()), error=None))
        except ValueError as e:
            self.extracted.append(Result(content=None, error=str(e)))

    def decode_all_blocks(self, blocks: bytes):
        assert len(blocks) % 1024 == 0
        num_blocks = len(blocks) // 1024

        self.extracted = []

        for block_num in range(num_blocks):
            self.current_block = blocks[1024*block_num:1024*(block_num+1)]
            self.cursor = 0
            self.decode_current_block()


def integer_with_minimum(min_value):
    def type_checker(arg: str) -> int:
        parsed = int(arg)
        if parsed < min_value:
            raise ArgumentTypeError(f'Argument must be >= {min_value}: {arg}')
        return parsed
    return type_checker


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument('path', type=Path)
    parser.add_argument('-s', '--start', type=integer_with_minimum(0), default=0, help='Starting block number to parse')
    parser.add_argument('-e', '--end', type=integer_with_minimum(-1), default=-1, help='Ending block number to parse (inclusive). -1 means through last block.')
    parser.add_argument('-f', '--format', type=str, choices=['html', 'text'], default='html', help='Output Format')
    parser.add_argument('-c', '--charset', type=str, choices=BlockDecoder.CHARSETS.keys(), default='howerd', help='Which ColorForth charset to use. Defaults to howerd.')
    args = parser.parse_args()
    return args


def extract_blocks(args: Namespace) -> bytes:
    with args.path.open('rb') as infile:
        all_blocks = infile.read()

    all_blocks_len = len(all_blocks)
    if all_blocks_len % 1024 != 0:
        raise ValueError(f'Provided file {args.path} does not have a length of multiple 1024! Length is {all_blocks_len}.')

    last_block = (len(all_blocks) // 1024) - 1
    if args.end is None or args.end == -1:
        end_block = last_block   # last block
    else:
        if args.end > last_block:
            raise ValueError(f'Provided end block {args.end} is past the last block of the provided file {last_block}')
        end_block = args.end

    start_block = args.start

    subset_blocks = all_blocks[1024 * start_block:1024 * (end_block + 1)]
    return subset_blocks


def main():
    args = parse_args()
    blocks_to_process = extract_blocks(args)
    decoder = BlockDecoder(blocks_to_process, starting_block_num=args.start)

    if args.format == 'html':
        decoder.create_html_representation()
        output = decoder.output_html
    elif args.format == 'text':
        decoder.create_text_representation()
        output = decoder.output_text
    else:
        raise NotImplementedError(f'Output format {args.format} not implemented')

    print(output)


if __name__ == '__main__':
    main()
