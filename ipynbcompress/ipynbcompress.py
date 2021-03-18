# coding: utf-8
from base64 import b64decode, b64encode
from PIL import Image
from io import BytesIO
from os import stat
from nbformat import read, write

#taken from https://stackoverflow.com/questions/35859140/remove-transparency-alpha-from-any-image-using-pil
def remove_transparency(im, bg_colour=(255, 255, 255)):
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
        alpha = im.convert('RGBA').split()[-1]
        bg = Image.new("RGBA", im.size, bg_colour + (255,))
        bg.paste(im, mask=alpha)
        return bg.convert('RGB')
    else:
        return im

def compress(filename, output_filename=None, img_width=2048, img_format='png'):
    """Compress images in IPython notebooks.

    Parameters
    ----------
    filename : string
        Notebook to compress. Will take any notebook format.
    output_filename : string
        If you do not want to overwrite your existing notebook, supply an
        filename for the new compressed notebook.
    img_width : int
        Which width images should be resized to.
    img_format : string
        Which compression to use on the images, valid options are
        *png* and *jpeg* (**requires libjpeg**).

    Returns
    -------
    int
        Size of new notebook in bytes.
    """
    orig_filesize = stat(filename).st_size

    # compress images
    nb = read(filename, as_version=4)
    outputs = [cell.get('outputs', []) for cell in nb['cells']]
    # omit empty outputs
    outputs = [o for o in outputs if len(o)]
    # flatten
    outputs = [o for lines in outputs for o in lines]
    for output in outputs:
        data = output.get('data', {})
        if not data:
            continue
        keys = data.copy().keys()
        for key in keys:
            if 'image' in key:
                string = ''.join(data[key])
                bytes_img = b64decode(string)
                io_img = BytesIO(bytes_img)
                img = Image.open(io_img)
                factor = float(img_width) / img.size[0]
                if factor < 1:
                    # only resize large images
                    new_size = [int(s*factor+0.5) for s in img.size]
                    img = img.resize(new_size)
                out = BytesIO()
                if img_format != "png":
                    img = remove_transparency(img)
                img.save(out, img_format)
                out.seek(0)
                mime = 'image/' + img_format
                del data[key]
                data[mime] = b64encode(out.read()).decode('ascii')

    # save notebook
    if not output_filename:
        output_filename = filename
    try:
        output_format = nb.metadata.orig_nbformat
    except AttributeError:
        output_format = 4
    write(nb, output_filename, version=output_format)

    # calculate bytes saved
    bytes_saved = orig_filesize - stat(output_filename).st_size
    if bytes_saved <= 0:
        print('%s: warning: no compression - %s bytes gained' % (filename, -bytes_saved))
    return bytes_saved
