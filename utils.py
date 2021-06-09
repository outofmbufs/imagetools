# general utility functions useful in this motley collection of tools

import pathlib
from collections import ChainMap
from PIL import Image, ImageColor


# support for parsing argument tuples - e.g., x,y pairs, etc
def argtuple(s, *dflts, n=None, seps=(',',), type=int):
    """Return tuple of 'type' from a,b,c,d... format.
    Raises ValueError if s cannot be parsed or converted (per type())

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
    """argparse a simple comma-separated pair (e.g., "100,300")"""
    return argtuple(s, n=2)


def rgbaspec(s, minval=0, maxval=255, alpha=255):
    """Return tuple of ints from various color specification formats.

    First tries ImageColor.getrgb, which (at this writing) accepts:
          '#rrggbb'
          '#rrggbbaa'
          .. various color names (e.g., 'red')
    Then tries, in order:
          None or '' will be accepted as (0, 0, 0, 0) i.e., transparent
          rr.gg.bb[.aa]
          rr,gg,bb[,aa]

    If no alpha is given, a 4-tuple will always be returned and the
    alpha value defaults to 255 (no transparency).

    If alpha is explicitly set to None, a 3-tuple will be returned IF
    no alpha is present in s.

    minval and maxval will be applied to all values in the resulting tuple
    and raise ValueError if exceeded.
    """

    try:
        rgba = ImageColor.getrgb(s)
    except ValueError:
        rgba = None

    if rgba is None and (s is None or len(s) == 0):
        rgba = (0, 0, 0, 0)

    if rgba is None:
        # accepts R.G.B[.A] or R,G,B[,A]
        rgba = argtuple(s, seps=('.', ','))
        if len(rgba) not in (1, 3, 4):
            raise ValueError(f"unknown color specifier {s}")

    # if only one value was given interpret as gray
    if len(rgba) == 1:
        rgba *= 3

    # alpha default rules as per docstring
    if alpha is not None and len(rgba) == 3:
        rgba = (*rgba, alpha)

    for v in rgba:
        if minval is not None and v < minval:
            raise ValueError(f"{v} (from '{s}') below minval ({minval})")
        if maxval is not None and v > maxval:
            raise ValueError(f"{v} (from '{s}') above maxval ({maxval})")
    return rgba


# Parse ONE coordinate (out of four in a cropargv).
# Note that what this returns is a function to be applied (later)
# against an image coordinate value, not a value itself.
#
# Allowed syntax:
#  * Entirely digits - a simple coordinate value.
#  * A leading explicit sign, '+' or '-', creates a value that
#    will be interpreted relative to 0 0 (if '+') or max,max (if '-')
#  * As a substitute (because a leading '-' can be a problem in some
#    command argument syntax positions), a leading 'R' or 'r' functions
#    the same as a leading '+' or '-'. It is recommended to include the '+'
#    e.g., 'R+10' for positive values, though not necessary. The '-' of course
#    is necessary for negative values: 'R-10'
#  * A leading 'S' indicates a size, rather than a coordinate. It will be
#    added to the first coordinate ("upper-left" in Image-speak).
#    S cannot appear in the first coordinate spec.
#
#    For example:
#
#        10,30,S1200,S1600
#
#    is a way to specify a 1200x1600 box originating at 10,30.
#    Without the S notation, that has to be specified:
#        10,30,1210,1630
#
def _parseNRS(s):
    s = s.strip()
    if s[0] in 'Rr+-':
        if s[0] in 'Rr':
            s = s[1:]
        r = int(s)
        if r > 0:
            return lambda u, z: 0 + r    # (could eliminate the "0 +")
        elif r == 0:
            return lambda u, z: 0 if u is None else z
        else:
            return lambda u, z: z + r    # r negative!
    elif s[0] in 'Ss':
        r = int(s[1:])
        return lambda u, z: u + r
    else:
        return lambda u, z: int(s)


# Crop specification:
#      x1,y1,x2,y2
#
# See _parseNRS for formats for specifying relative vs absolute
#
def cropargv(s):
    return argtuple(s, '+0', n=4, type=_parseNRS)


def computecrop(cspec, img):
    """Return crop box computed from cropspec 'cspec' on 'img'."""
    try:
        sz0, sz1 = img.size
    except AttributeError:
        if img is None:
            # unnamed crop specs can't use 'R' specification
            sz0 = None
            sz1 = None
        else:
            try:
                with Image.open(img) as img_opened:
                    return computecrop(cspec, img_opened)
            # treat nonexistent img names same as 'img is None'; the test
            # code relies on this; not clear how useful otherwise. Meh.
            except FileNotFoundError:
                return computecrop(cspec, None)

    c0 = cspec[0](None, sz0)
    c1 = cspec[1](None, sz1)
    return (c0, c1, cspec[2](c0, sz0), cspec[3](c1, sz1))


def saveimage(img, outname, image_format="JPEG"):
    if image_format != "JPEG":
        raise ValueError(f"output format {image_format} not implemented.")

    saveargs = {k: img.info.get(k) for k in ('exif', 'icc_profile')}
    img.save(outname, quality="maximum", **saveargs)


def formatoutname(src, fmt, *, autoleading=True, **params):
    """Return an output filename according to fmt.format() on src & params.

    pathlib is used to create a Path object:
        pp = pathlib.Path(src)
    The constructions {pp.foo} may be used in the fmt to access any
    defined attribute of pp. For example:
        {pp.suffix}
    in the fmt will be filled in with pathlib.Path(src).suffix

    If autoleading is False, the resulting string is returned as-is.
    If autoleading is True (the default), the resulting string is
    processed via pp.with_name() and returned (in other words: the leading
    directories are preserved and only the name part is modified). This is
    usually the Right Thing To Do.

    EXAMPLE: to add xxx- to the front of a name, use this:
        fmt="xxx-{pp.name}"

    For convenience, pp.name is also supplied to format as a positional
    parameter, allowing {} in fmt to refer to it, so this fmt is equivalent:
        fmt = "xxx-{}"
    """
    pp = pathlib.Path(src)
    paramsplus = ChainMap(params, {'src': src, 'pp': pp})
    rslt = fmt.format(pp.name, **paramsplus)
    if autoleading:
        rslt = pp.with_name(rslt)
    return str(rslt)


if __name__ == "__main__":
    import unittest
    from types import SimpleNamespace

    class TestMethods(unittest.TestCase):

        # if rx is a subclass of Exception then
        #     assertRaises(rx, f, *args, **kwargs)
        # else
        #     assertEqual(rslt, f(*args, **kwargs)
        def eqex(self, rx, f, *args, **kwargs):
            isx = False
            try:
                isx = issubclass(rx, Exception)
            except TypeError:
                pass

            if isx:
                self.assertRaises(rx, f, *args, **kwargs)
            else:
                self.assertEqual(rx, f(*args, **kwargs))

        def test_argtuple_v(self):
            testcases = (
                # input string, result, args, kwargs
                ("1,2,3",  (1, 2, 3), (), {}),
                ("1, 2,3", (1, 2, 3), (), {}),
                ("4.6",  (4, 6), (), dict(seps='.')),
                ("1.2. 3", (1, 2, 3), (), dict(seps=".")),
                ("1.2,3", ("1", "2,3"), (), dict(seps=".,", type=str)),
                ("1", ValueError, (), dict(n=3)),
                ("1,2,3,4", ValueError, (), dict(n=3)),
                ("1", (1, 200, 300), (100, 200, 300), {}),
                ("1, 2", (1, 2, 300), (100, 200, 300), {}),
                ("1, 2, 3", (1, 2, 3), (100, 200, 300), {}),
                ("1", (1, 255, 255), (255,), dict(n=3))
            )
            for tc in testcases:
                with self.subTest(tc=tc):
                    s, rslt, args, kwargs = tc
                    self.eqex(rslt, argtuple, s, *args, **kwargs)

        def test_commapair(self):
            testcases = (
                ("100,300", (100, 300)),
                ("   100    ,  300  ", (100, 300)),
                ("1", ValueError),
                ("1,2,3", ValueError)
            )

            for tc in testcases:
                s, rx = tc
                with self.subTest(tc=tc):
                    self.eqex(rx, commapair, s)

        def test_rgbaspec(self):
            green = ImageColor.getrgb("green")
            testcases = (
                ("green", green + (255,), {}),
                ("green", green, dict(alpha=None)),
                ("green", green + (17,), dict(alpha=17)),
                ("1,2,3,4", (1, 2, 3, 4), {}),
                ("#102030", (0x10, 0x20, 0x30), dict(alpha=None)),
                ("4.5.6", (4, 5, 6, 255), {}),
                ("red like bozo's nose", ValueError, {})
                )

            for tc in testcases:
                with self.subTest(tc=tc):
                    s, rslt, kwargs = tc
                    self.eqex(rslt, rgbaspec, s, **kwargs)

        def test_fmtname(self):
            testcases = (
                # srcname, fmt, params, result
                ('/clowns/bozo', 'bigtop-{}', {}, '/clowns/bigtop-bozo'),
                ('/clowns/bozo', 'bigtop-{}', {'autoleading': False},
                 'bigtop-bozo'),
                ('/clowns/bozo', '{prefix}{}', {'prefix': 'banana-'},
                 '/clowns/banana-bozo'),
                ('/clowns/bozo.jpg', '{pp.stem}-1{pp.suffix}', {},
                 '/clowns/bozo-1.jpg')
                )
            for c in testcases:
                with self.subTest(c=c):
                    src, fmt, params, rslt = c
                    self.assertEqual(rslt, formatoutname(src, fmt, **params))

        def test_crops(self):
            img = SimpleNamespace(size=(1200, 1600))  # mocked up Image()
            testcases = (
                # cropspec, result
                ("0,0,1,1", (0, 0, 1, 1)),
                ("+10, +11, R0, R0", (10, 11, img.size[0], img.size[1])),
                ("10, 20, R-100, S50", (10, 20, img.size[0]-100, 70)),
                ("10, 10,S100,S200", (10, 10, 110, 210)),
                # this tests the defaulting
                ("", (0, 0, img.size[0], img.size[1]))
                )

            for c in testcases:
                spec, rslt = c
                with self.subTest(c=c):
                    self.assertEqual(rslt, computecrop(cropargv(spec), img))

        def test_badcrops(self):
            testcases = ("0,RR,7,8", "1,2,3,4,5")
            for c in testcases:
                with self.subTest(c=c):
                    self.assertRaises(ValueError, cropargv, c)

    unittest.main()
