#!/usr/bin/env python3


import argparse
from PIL import Image
from os import path

from addtext import addtext

# support for parsing RGB tuples, x,y pairs, etc for argparse arguments
def argtuple(s, *dflts, n=None, seps=(',',), type=int):
    """Return tuple of 'type' from a,b,c,d... format.

    seps:  separators. Each is tried, in order, stopping when s.split()
           results in multiple fields or once all have been tried.
           Default is comma.
    type:  conversion function to apply to each string from s.split()
    n:     enforced tuple length. Interacts with dflts. If n is None and
           no dflts are given, the resulting length is "whatever"
    dflts: default values for unspecified fields. If n is None, it is
           determined by len(dflts). If n > 1 and len(dflts) == 1 then that
           single default value will be used for all fields.
    """

    if len(dflts) > 0:
        if n is None:
            n = len(dflts)
        if n > 1:
            if len(dflts) == 1:
                dflts = [dflts[0]] * n
            elif len(dflts) != n:
                raise ValueError(f"n is {n} but len(dflts) is {len(dflts)}")
    if s:
        for sep in seps:
            a = s.split(sep)
            if len(a) > 1:
                break
    else:
        a = []

    if n is not None:
        alen = len(a)
        if alen > n:
            raise ValueError(f"too many fields in {s}")
        if alen < n:
            if len(dflts) == 0:
                raise ValueError(f"too few fields in {s}")
            a += dflts[alen:]
    return tuple(map(type, a))


def commapair(s):
    return argtuple(s, n=2)


def rgbaspec(s, minval=0, maxval=255, alpha=255):
    """Return tuple of ints from 'nnn.nnn.nnn[.aaa]' or #rrggbb[aa] (hex)"""

    # accept None (or zero-length string) as black / transparent
    if not s:
        s = '#00000000'

    # Note: various conversion exceptions deliberately just bubble out

    if s[0] == '#':
        if len(s) != 7 and len(s) != 9:
            raise ValueError(f"{s} is not #rrggbb or #rrggbbaa format")
        if len(s) == 9:
            alpha = int(s[7:9], 16)
        rgba4 = (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16), alpha)
    else:
        # accepts R.G.B[.A] or R,G,B[,A]
        rgba4 = argtuple(s, seps=('.', ','))
        # some defaulting rules...
        if len(rgba4) == 1:
            rgba4 = (rgba4[0], rgba4[0], rgba4[0])   # gray
        if len(rgba4) == 3:
            rgba4 = (*rgba4, alpha)                  # no alpha - use default
        if len(rgba4) != 4:
            raise ValueError(f"{s} is not in R.G.B[.A] format")

    return rgba4


def saveimage(img, outname, image_format="JPEG"):
    if image_format != "JPEG":
        raise ValueError(f"output format {image_format} not implemented.")

    saveargs = {k: img.info.get(k) for k in ('exif', 'icc_profile')}
    img.save(outname, quality=95, **saveargs)


def formatoutname(infilename, fmt):
    """Return an output filename according to fmt:

    PREPEND={xxx}     add 'xxx' in front of the basename
    """
    head, tail = path.split(infilename)

    if fmt.startswith('PREPEND='):
        tail = fmt[fmt.find('{') + 1:fmt.find('}')] + tail
        return path.join(head, tail)
    raise ValueError(f"unknown outname format {fmt}")


def cmd_main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-x', type=int, default=100)
    parser.add_argument('-y', type=int, default=150)
    parser.add_argument('-t', '--text', type=str)
    parser.add_argument('-r', '--rotate', type=float, default=0.0)
    parser.add_argument('-c', '--color', type=rgbaspec, default='#ffffff')
    parser.add_argument('-b', '--bg', type=rgbaspec, default=None)
    parser.add_argument('-n', '--fontname', default='Courier New.ttf')
    parser.add_argument('-z', '--size', type=int, default=64)
    parser.add_argument('-p', '--padbg', type=commapair, default='0,0')
    parser.add_argument('--bgsize', type=commapair)
    parser.add_argument('--outnaming', default="PREPEND={t-}")
    parser.add_argument('--outtype', default="JPEG")
    parser.add_argument('--inplace', action='store_true')
    parser.add_argument('--textoffset', type=commapair, default='0,0')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args()

    for fn in args.filenames:
        img = Image.open(fn)
        addtext(img, args.x, args.y, args.text,
                font=args.fontname, size=args.size, rgb=args.color,
                bg=args.bg, bgsize=args.bgsize, bgpad=args.padbg,
                textoffset=args.textoffset,
                rotate=args.rotate)

        outname = fn if args.inplace else formatoutname(fn, args.outnaming)
        saveimage(img, outname, image_format=args.outtype)
        img.close()


if __name__ == "__main__":
    cmd_main()
