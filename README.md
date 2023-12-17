# colorForth Decoder

## Introduction
This repository contains the `colorforth_decoder.py` Python script, which allows you to decode the source blocks of a [colorForth](https://en.wikipedia.org/wiki/ColorForth) binary image into HTML or plain text format.

## Usage
```
python colorforth_decoder.py path_to_colorforth_image.img
```

The only required argument is the path to the binary image file you want to decode.
Note that this binary image file must have a length a multiple of 1024 (i.e., it must consist of one or more 1024 byte blocks).

The script will print the formatted output (in html format by default) as stdout.

You can configure the block numbers you'd like to start and end at, the desired output format, and the desired character set through command line flags.
These flags are described in the help text for the program: `python colorforth_decoder.py -h`.

## Further details
### About colorForth 
You can find more information about colorForth from [the wikipedia page](https://en.wikipedia.org/wiki/ColorForth),
the [archive of Chuck Moore's original colorforth.com website](https://web.archive.org/web/20160414102635/http://colorforth.com/),
[the mirror of that original website at github.io](https://colorforth.github.io/),
and the [website for Howerd Oakford's more recent work on colorForth](https://www.inventio.co.uk/cf2023/index.html).
This script was tested with Howerd Oakford's versions of colorForth (cf2019, cf2023).

### About the colorForth source blocks
You can see details on how colorForth source blocks are encoded at the pages for [pre-parsed Words](https://web.archive.org/web/20160331114618/http://colorforth.com/parsed.html) and
[character encoding](https://web.archive.org/web/20151017223655/http://www.colorforth.com/chars.html).
Take note that there seems to be variation in the character ordering and character set between flavors of colorForth. For example, the precise ordering of characters j, k, z, 0, 1, and 2 seem to vary, and some flavors swap in `'` for `:`.
This program uses the character set used by Howerd Oakford's colorForth versions by default, but you can change this with the `-c` flag.

### The output formats
The HTML output format produces colored HTML output that mirrors the appearance of the editor in colorForth itself.

The text format uses the convention `c|abc123` , where the first character before the pipe (|) indicates the color of the token, and the characters of the token follow the pipe.

**Take note**: In both formats, decimal numbers stored as numbers are shown prepended with a `#`.
This is done so that numbers represented as numbers are distinguishable from text consisting of only digits (i.e., a string or word that happens to only use numeric digits).
This convention is unique to this decoder, and is not done in the colorForth editor. Hex-formatted numbers are prepended with `$`, just as in the colorForth editor.




