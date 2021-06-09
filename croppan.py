#!/usr/bin/env python3
#
# Tool to crop/scale/pan through a sequence of images

import argparse
import json
from PIL import Image
from collections import namedtuple
from utils import cropargv, saveimage, formatoutname, computecrop, argtuple

# Pan specification:
#
# JSON structure
#   {"image0": filename,
#    "crop0": "x1, y1, x2, y2",   # see note below about crop formats
#    "image1": filename,          # defaults to image0 if left out
#    "crop1": "x1, y1, x2, y2",   # defaults to crop0 if left out
#    "n": integer                 # defaults to 1 if left out
#   }
#
# This specifies an interpolated crop starting with image0 and ending
# on image1, going from crop0 to crop1 in equal steps, with each image
# duplicated 'n' times along the way (default is 1).
#
# If no interpolation is desired, image1 and crop1 can be omitted
#
# In all but the first pan of a sequence, crop0 can be None to signify
# starting where the previous pan ended (starting at previous crop1)
#
# A sequencce of PanSpecs is applied against a sequence of images, and
# it is expected that the image names present in the PanSpec sequence
# are ordered consistently with respect to the images in the image sequence.
# Typically:
#   * the first Pan will specify an image0 corresponding to the first image
#     and a crop0 corresponding to the desired crop of that image.
#
#   * To pan to a new crop ("newcrop"), starting from imageX and landing
#     on the newcrop at image Y, specify a pan with image0=imageX, crop0=None
#     (starting at the previous i.e., then-current crop) and image1=imageY
#     with crop1=newcrop. The crops will be interpolated from imageX thru
#     imageY, landing on crop1 at imageY.
#
#   * Repeat as desired.
#
# CROP FORMATS
# The crop coordinate format includes certain prefixes, including
# letters such as "S" and "R" but also leading "+" signs that have meaning.
# Therefore, the crop coordinates are specified as a string:
#     "x1,y1,x2,y2"
# and parsed/processed according to cropargv() (really: _parseNRS).

# EXAMPLE:
# This starts with a crop to (0, 10, 200, 210) at F00.jpg and stays with
# that crop until F05.jpg, then pans gradually to (100, 110, 300, 310)
# from F05.jpg to F10.jpg
#
# [{"image0": "F00.jpg", "crop0": "0,10,200,210"},
#  {"image0": "F05.jpg", "crop0": "0,10,200,210",   # crop0 could be None here
#   "image1": "F10.jpg", "crop1": "100,110,300,310"}]

# _PanSpec is the underlying representation (namedtuple), and PanSpec()
# is a thin-wrapper providing some of the defaults semantics

_PanSpec = namedtuple('PanSpec',
                      ('image0', 'crop0',
                       'image1', 'crop1',
                       'n'), defaults=(1,))


def PanSpec(*, image0, crop0, image1=None, crop1=None, n=1):
    return _PanSpec(image0=image0, crop0=crop0,
                    image1=image1 or image0,
                    crop1=crop1 or crop0,
                    n=n)


def gen_panspecs(s):
    """GENERATE one or more PanSpecs from a (presumably) JSON string.

    NOTE: The string (s) can also be a file name.
    """

    for pdict in _pjson_gen(s):
        # parse/process crops represented in string form (vs naked array)
        for crop, name in [(f"crop{i}", f"image{i}") for i in (0, 1)]:
            try:
                cs = pdict[crop]
            except KeyError:
                pass
            else:
                if isinstance(cs, str):
                    pdict[crop] = computecrop(cropargv(cs), pdict[name])

        yield PanSpec(**pdict)


# Using a PanSpec list ('pans') that names only SOME of
# the images in 'names', GENERATE a fully-expanded sequence of tuples:
#         (imagename, crop)
# so that every image has an explicit crop, interpolated from the
# ones given (thus creating a "video pan" effect)

def expand_pans(names, pans):

    px = list(pans)      # will be modifying sequence, need a copy

    # ensure the first image has a PanSpec ... create if needed
    if px[0].image0 != names[0]:
        px.insert(0, PanSpec(image0=names[0], crop0=px[0].crop0))

    # similarly, ensure there is an outgoing target at end
    px.append(PanSpec(image0=None, crop0=px[-1].crop1))

    i4 = (0, 1, 2, 3)         # just shorthand for "all elements of a crop"

    for fnum, fname in enumerate(names):
        if fname == px[0].image0:
            p = px.pop(0)
            reps = p.n
            if p.crop0 is not None:
                curbox = p.crop0
            # compute how many steps up to next waypoint
            try:
                next_at = names.index(p.image1)
            except ValueError:            # no more; therefore no more pan
                deltas = [0, 0, 0, 0]
            else:
                nf = (next_at - fnum + 1) * reps
                # nf - 1 "steps" for the deltas. Consider, for example
                # the case where p.n is 3 and image1 = image0, i.e., the
                # request is to go from crop0 to crop1 with three copies
                # of the single file image0. The first must be crop0,
                # the second must be halfway (divide by 2 when p.n is 3),
                # the third will be all the way i.e., crop1 (or 2 deltas).
                #
                # In the special case of nf being 1, the calculation would
                # divide by zero (which is another way to say "hey, there
                # are no deltas, duh!"). Handle that explicitly.
                #
                if nf == 1:
                    deltas = [0, 0, 0, 0]
                else:
                    deltas = [(p.crop1[i]-curbox[i]) / (nf-1) for i in i4]

        for k in range(reps):
            roundedbox = [int(curbox[i] + 0.5) for i in i4]
            yield (fname, roundedbox)
            curbox = [curbox[i] + deltas[i] for i in i4]

        if fname == p.image1:
            deltas = [0, 0, 0, 0]
            reps = 1
            if p.crop1 is not None:
                curbox = p.crop1     # because above for loop goes one too far


def _pjson_gen(s):
    """GENERATE dicts represending decoded JSON PanSpec objects.

    s can be a filename, in which case it is opened and parsed as JSON
    s can be a simple JSON representation of a single PanSpec
    s can be a JSON sequence of individual PanSpecs

    In all cases the resulting generator yields one or more dictionaries
    suitable for use in constructing a PanSpec, but note that no semantic
    processing has been done yet (see gen_panspecs)
    """

    # first try opening it as a file. There is an assumption here that
    # no JSON representation will also be a filename. Meh.
    try:
        with open(s, 'r') as f:
            s = f.read()
    except FileNotFoundError:
        pass     # s is the JSON string

    j = json.loads(s)
    if isinstance(j, list):
        yield from j
    else:
        yield j


def sizetuple(s):
    return argtuple(s, n=2)


panspechelp = """A file containing PanSpec JSON, OR a direct JSON object.
  The JSON format is:
        { "image0": filename,
          "crop0": cropspec,
          "image1": filename,      # defaults to image0 if omitted
          "crop1": cropspec,       # defaults to crop0 if omitted
          "n": integer}            # defaults to 1

  The string is tried as a filename first; if it can be opened JSON
  will be read from there. Otherwise the string is parsed as JSON itself.

  The coordinate specifications, "cropspec", are (must be) strings,
  even if they are just four integer values (e.g., "0,0,600,800")

  Coordinate values are relative if prefixed with R+ or R- (else absolute).
  For example: "R+10,R+10,R-10,R-10" takes 10 pixels off all four edges.
  The R can be (carefully) omitted (+10 vs R+10) except if x1 is negative.
  If a repcount is given, the same image will be croppanned that many times.

  NOTE: Relative values are converted to absolute values, ONCE,
        by applying them to their anchor images.
    """


def cmd_main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--outprefix', default="pan-")
    parser.add_argument('--outnaming',
                        default="{outprefix}{pp.stem}-{seq:05d}{pp.suffix}")
    parser.add_argument('--outtype', default="JPEG")
    parser.add_argument('--pan', type=str,
                        help=panspechelp, action='append', default=[])
    parser.add_argument('--size', type=sizetuple, default=None)
    parser.add_argument('-v', '--verbose', action="count", default=0)
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args()

    if not args.filenames:
        return

    def vprint(*pargs, **kwargs):
        if args.verbose:
            print(*pargs, **kwargs)

    def vvprint(*pargs, **kwargs):
        if args.verbose > 1:
            print(*pargs, **kwargs)

    pans = []
    for s in args.pan:
        pans += gen_panspecs(s)

    for seq, t in enumerate(expand_pans(args.filenames, pans)):
        fname, cropbox = t
        if args.verbose > 1 or (seq % 250) == 0:
            vprint(f"#{seq:05d}, cropping {fname} to {cropbox}")
        with Image.open(fname) as img:
            cropped = img.crop(box=cropbox)
            if args.size is not None and cropped.size != args.size:
                vvprint(f"resizing because cropped size is {cropped.size}")
                cropped = cropped.resize(args.size)
            outname = formatoutname(fname, args.outnaming,
                                    outprefix=args.outprefix, seq=seq)
            saveimage(cropped, outname, image_format=args.outtype)


if __name__ == "__main__":
    cmd_main()
