# addtext

Add text to images, using the PIL library. See docstring for usage info.


## EXAMPLE
This code:

    img = Image.open('something.jpg')
    addtext(img, 400, 500, 'THIS IS A TEST', rgb=(255, 0, 0))

adds "THIS IS A TEST" in red to the image 'something.jpg' at coordinates 400,500, using a default font at a default size (which is unlikely what you want; see docstring for details on how to control all this).

NOTE: this only alters the in-memory image; it is up to you to save the image.
