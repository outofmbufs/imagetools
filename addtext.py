#
# Write a text string onto a PIL Image
#


from PIL import Image, ImageFont, ImageDraw

def addtext(img, x, y, text, *, font=None, size=0,
            rgb=(255, 255, 255), bg=(0, 0, 0, 0),
            bgsize=None, bgpad=(0, 0),
            textoffset=(0, 0), rotate=None):
    """Add text to an image at coordinates (x, y).

    font:       See getfont()
    size:       See getfont()
    rgb:        text color (tuple, with optional alpha).
    bg:         background color (tuple w/opt alpha). Default is transparent.
    bgsize:     size (tuple) for background. Default (None) - text determines.
    bgpad:      tuple (x, y) to pad the computed background area size
    textoffset: tuple (x, y) to position the text within background
    rotate:     text rotation angle in degrees (ccw)
    """

    f = getfont(font, size)

    # Overly-generalized in the simple case but works for all cases:
    # 1) find size of generated text unless a specific background size given
    # 2) Make a new RGBA image of just the text and rotate it accordingly.
    # 3) Copy the affected area of the source image (based on size of #2)
    #    into a new RGBA image (unnecessary if the source is RGBA but needed
    #    in most cases, e.g., jpg, where source is RGB)
    # 4) alpha-composite the images from 2&3 and paste into original

    # 1: determine size of just the text rendering
    if bgsize is None:
        # textsize() has been removed, reimplement via textbbox..
        _, _, w, h = ImageDraw.Draw(img).textbbox((0, 0), text, font=f)
        bgsize = (w, h)

    # 2: make new RBGA image, put text into it, rotate
    paddedsize = (bgsize[0] + bgpad[0], bgsize[1] + bgpad[1])
    txtimg = Image.new('RGBA', paddedsize, color=bg)
    d = ImageDraw.Draw(txtimg)
    d.text(textoffset, text, fill=rgb, font=f)
    if rotate:
        txtimg = txtimg.rotate(rotate, expand=True)

    # 3: make RGBA copy of the background that the text will affect
    i2 = Image.new('RGBA', txtimg.size)
    i2.paste(img.crop(box=(x, y, x + txtimg.size[0], y + txtimg.size[1])))

    # 4: composite the text into that background (copy) and paste it in!
    i2.alpha_composite(txtimg)
    img.paste(i2, (x, y))


def getfont(font=None, size=0):
    """Return an ImageFont object.

    font:     A fontname to load OR an already-loaded ImageFont font object.
              If None, PIL.ImageFont.load_default() will be used.
              If a string AND size is given -> ImageFont.truetype()
              If a string AND no size was given -> ImageFont.load()
              Otherwise it should be an already-loaded ImageFont result
    """
    if font is None:
        f = ImageFont.load_default()
    elif isinstance(font, str):
        if size:
            f = ImageFont.truetype(font, size)
        else:
            # technically you could be asking for truetype with no size
            # and just take the default, but we take that to mean you want
            # a bitmap font (which has the size implied)
            f = ImageFont.load(font)
    else:
        f = font       # caller (presumably) provided necessary object directly
    return f
