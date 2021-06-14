# tests for croppan
import json
import os
import tempfile
import unittest

from croppan import expand_pans, gen_panspecs, PanSpec
from contextlib import contextmanager


class TestMethods(unittest.TestCase):
    NDN = 200        # number of dummy names.
    DN = None        # the actual dummy names

    @classmethod
    def makedummynames(cls):
        if cls.NDN < 10:
            raise ValueError(f"NDN ({cls.NDN}) too small. Minimum is 10.")

        # find a directory name that does not exist, starting with "/X"
        # (almost always sufficient) and adding additional X's as necessary
        d = "/X"
        while True:
            try:
                with open(d) as _:
                    pass
            except FileNotFoundError:
                break
            except IsADirectoryError:
                pass
            d += "X"

        # make the dummynames with the non-existent directory prefix
        cls.DN = [d + f"/F{i:03d}" for i in range(cls.NDN)]

    def setUp(self):
        if self.DN is None:
            self.makedummynames()

    @staticmethod
    def cbstr(cropbox):
        """Return a string suitable for gen_waypoints from a crop box"""
        return f"{cropbox[0]},{cropbox[1]},{cropbox[2]},{cropbox[3]}"

    def checkallnames(self, cropspecs):
        self.assertEqual(len(cropspecs), len(self.DN))
        for i, t in enumerate(cropspecs):
            self.assertEqual(t[0], self.DN[i])

    def test0(self):
        # test basic interpolation
        crop_A = [0, 10, 200, 210]
        crop_B = [2, 12, 202, 212]
        crop_M = [1, 11, 201, 211]   # hand-calculated midpoint

        p = PanSpec(image0=self.DN[0], crop0=crop_A,
                    image1=self.DN[2], crop1=crop_B)
        crops = [crop_A, crop_M, crop_B]
        for i, t in enumerate(expand_pans(self.DN, [p])):
            self.assertEqual(t[0], self.DN[i])
            if i < len(crops):
                self.assertEqual(t[1], crops[i])
            else:
                self.assertEqual(t[1], crop_B)

    def test1(self):
        # like test0, just more, and using JSON input format
        halfNDN = self.NDN // 2

        crop_A = [0, 10, 200, 210]
        crop_B = [x + halfNDN for x in crop_A]

        pans = list(gen_panspecs(json.dumps(
            [{'image0': self.DN[0], 'crop0': self.cbstr(crop_A),
              'image1': self.DN[halfNDN], 'crop1': self.cbstr(crop_B)}])))
        xp = list(expand_pans(self.DN, pans))

        # all the file names should be in the resulting expansion
        self.checkallnames(xp)

        # the crop box should have been interpolated one unit at a time
        for i in range(halfNDN):
            self.assertEqual(xp[i][1], [x + i for x in crop_A])

        # and the rest should be all the last one
        for i in range(halfNDN+1, self.NDN):
            self.assertEqual(xp[i][1], crop_B)

    def test2(self):
        # test basic interpolation not starting at the first file
        offset = 3
        npan = 4

        crop_A = [0, 10, 200, 210]
        crop_B = [x + npan for x in crop_A]

        pans = [PanSpec(image0=self.DN[offset], crop0=crop_A,
                        image1=self.DN[offset+npan], crop1=crop_B)]

        xp = list(expand_pans(self.DN, pans))

        # all the file names should be in the resulting expansion
        self.checkallnames(xp)

        # the initial images,  including the start of the pan, should all
        # be crop_A (inferred initial crop)
        for i in range(offset+1):
            with self.subTest(i=i):
                self.assertEqual(xp[i][1], crop_A)

        # the next npan should all increase by 1 (based on how crop_B was made)
        for i in range(npan):
            self.assertEqual(xp[i+offset][1],
                             [crop_A[k] + i for k in (0, 1, 2, 3)])

    def test3(self):
        # like test1 but go up to a midpoint and then back down

        # want an even number of test cases
        if (self.NDN // 2) * 2 != self.NDN:
            ntests = self.NDN - 1
        else:
            ntests = self.NDN

        halfNDN = ntests // 2

        crop_A = [0, 10, 200, 210]
        crop_B = [x + halfNDN - 1 for x in crop_A]
        crop_C = crop_A

        pans = list(gen_panspecs(json.dumps(
            [{'image0': self.DN[0], 'crop0': self.cbstr(crop_A),
              'image1': self.DN[halfNDN-1], 'crop1': self.cbstr(crop_B)},
             {'image0': self.DN[halfNDN], 'crop0': None,
              'image1': self.DN[ntests-1], 'crop1': self.cbstr(crop_C)}])))

        xp = list(expand_pans(self.DN, pans))
        self.checkallnames(xp)

        # the way up...
        for i in range(halfNDN):
            with self.subTest(i=i):
                self.assertEqual(xp[i][1], [x + i for x in crop_A])

        # and the way back down...
        for i in range(halfNDN, ntests):
            with self.subTest(i=i):
                self.assertEqual(xp[i][1],
                                 [x - (i - halfNDN) for x in crop_B])

    def test4(self):
        # test the repeat 'n' times single file form
        repeater = 20
        crop0 = [0, 10, 200, 210]
        crop1 = [x + repeater - 1 for x in crop0]
        pans = [PanSpec(image0=self.DN[0],
                        crop0=crop0, crop1=crop1, n=repeater),
                PanSpec(image0=self.DN[1], crop0=crop1)]
        xp = list(expand_pans(self.DN, pans))

        # the result should have 'repeater' copies of the
        # first file name and then the rest of them. Based on that,
        # this construction should pass checkallnames():
        self.checkallnames([xp[0]] + xp[repeater:])

        # The results should pan 1 unit at a time
        # over those first 'repeater' copies of the image and
        # then be at crop1 for the remainder
        for i, t in enumerate(xp):
            with self.subTest(i=i, t=t):
                if i < repeater:
                    self.assertEqual(t[1], [x + i for x in crop0])
                    self.assertEqual(t[0], self.DN[0])
                else:
                    self.assertEqual(t[1], crop1)
                    self.assertEqual(t[0], self.DN[i + 1 - repeater])

    def test5(self):
        # Three edge cases - just one pan at:
        #     - the very beginning
        #     - the very end
        #     - somewhere in the middle
        crop0 = [0, 10, 200, 210]
        for nth in (0, 5, self.NDN-1):
            with self.subTest(nth=nth):
                pans = [PanSpec(image0=self.DN[nth], crop0=crop0)]
                xp = list(expand_pans(self.DN, pans))
                self.checkallnames(xp)
                # every cropbox should just be crop0
                for t in xp:
                    self.assertEqual(t[1], crop0)

    def test6(self):
        # every file has an individual crop box
        crop_A = [0, 10, 200, 210]
        pans = [PanSpec(image0=fn, crop0=[x + k for x in crop_A])
                for k, fn in enumerate(self.DN)]
        xp = list(expand_pans(self.DN, pans))
        self.checkallnames(xp)

        for i, t in enumerate(xp):
            self.assertEqual(t[1], [x + i for x in crop_A])

    def test7(self):
        # every file has an individual crop box using the None form
        # for all but the first (it's illegal on the first)
        crop_A = [0, 10, 200, 210]
        pans = [PanSpec(image0=self.DN[0], crop0=crop_A)]
        pans += [PanSpec(image0=fn, crop0=None) for fn in self.DN[1:]]
        xp = list(expand_pans(self.DN, pans))
        self.checkallnames(xp)
        for i, t in enumerate(xp):
            self.assertEqual(t[0], self.DN[i])
            self.assertEqual(t[1], crop_A)

    # context manager encapsulates "delete the temp file when done"
    @contextmanager
    def _tempfile(self):
        tfd, tfname = tempfile.mkstemp(text=True)
        try:
            yield tfd, tfname
        finally:
            # Close the file descriptor, but don't bomb if the file was
            # closed already (which the test does Because Reasons)
            try:
                os.close(tfd)
            except OSError:
                pass
            os.remove(tfname)

    def test8(self):
        # test the file form of gen_panspecs
        with self._tempfile() as (tfd, tfname):
            os.write(tfd, b'{"image0": "abc", "crop0": "0,1,2,3"}')
            os.close(tfd)
            pans = list(gen_panspecs(tfname))
        self.assertEqual(len(pans), 1)

        with self._tempfile() as (tfd, tfname):
            os.write(tfd, b'[{"image0": "abc", "crop0": "0,1,2,3"},'
                          b'{"image0": "def", "crop0": "3,2,1,0"}]')
            os.close(tfd)
            pans = list(gen_panspecs(tfname))
        self.assertEqual(len(pans), 2)
        j1, j2 = pans
        self.assertEqual(j1.image0, "abc")
        self.assertEqual(j1.crop0, (0, 1, 2, 3))
        self.assertEqual(j2.image0, "def")
        self.assertEqual(j2.crop0, (3, 2, 1, 0))


unittest.main()
