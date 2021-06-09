#!/usr/bin/env python3


import argparse
from PIL import Image
from utils import commapair, rgbaspec, formatoutname, saveimage

from addtext import addtext


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
    parser.add_argument('--outprefix', default="t-")
    parser.add_argument('--outnaming', default=None)
    parser.add_argument('--outtype', default="JPEG")
    parser.add_argument('--inplace', action='store_true')
    parser.add_argument('--textoffset', type=commapair, default='0,0')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args()

    if args.inplace and args.outnaming:
        print("can't specify both --inplace and --outnaming")
        exit(1)
        
    if args.inplace:
        outnamefmt = "{}"
    else:
        outnamefmt = args.outnaming or "{outprefix}{pp.name}"

    for fn in args.filenames:
        with Image.open(fn) as img:
            addtext(img, args.x, args.y, args.text,
                    font=args.fontname, size=args.size, rgb=args.color,
                    bg=args.bg, bgsize=args.bgsize, bgpad=args.padbg,
                    textoffset=args.textoffset,
                    rotate=args.rotate)

            outname = formatoutname(fn, outnamefmt, outprefix=args.outprefix)
            saveimage(img, outname, image_format=args.outtype)


if __name__ == "__main__":
    cmd_main()
