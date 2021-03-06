# IMAGE TOOLS
An assortment of utilities inspired by needs while making a timelapse movie.

addtext: puts text onto images (thin wrapper over PIL functions)

croppan: crops a sequence of images, and interpolates between multiple crop points

# addtext

Add text to images, using the PIL library. See docstring for usage info.


## EXAMPLE
This code:

    img = Image.open('something.jpg')
    addtext(img, 400, 500, 'THIS IS A TEST', rgb=(255, 0, 0))

adds "THIS IS A TEST" in red to the image 'something.jpg' at coordinates 400,500, using a default font at a default size (which is unlikely what you want; see docstring for details on how to control all this).

NOTE: this only alters the in-memory image; it is up to you to save the image.

The basic functionality is provided by the `text` method from ImageDraw; however, `addtext` additionally handles:

* Transparency (alpha channel) whether or not the underlying image has an alpha channel.
* Optional solid background around text
* Arbitrary text rotation

## COMMAND LINE UTILITY
textcmd.py is a command-line utility that drives addtext().

# croppan.py

Perform a seqeunce of crops against a sequence of images, panning from one crop to the next by interpolation.
