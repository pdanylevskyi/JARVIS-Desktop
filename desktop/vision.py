"""Validate and normalize one user-selected image on the Ubuntu server only."""
import base64
import io
import warnings
MAX_IMAGE_BYTES=10*1024*1024

def image_url(attachment):
    from PIL import Image, ImageOps
    if not isinstance(attachment,dict) or not isinstance(attachment.get('data'),str):
        raise ValueError('Некоректне зображення.')
    if len(attachment['data'])>14_000_000:raise ValueError('Зображення перевищує 10 МБ.')
    raw=base64.b64decode(attachment['data'],validate=True)
    if len(raw)>MAX_IMAGE_BYTES:raise ValueError('Зображення перевищує 10 МБ.')
    with warnings.catch_warnings():
        warnings.simplefilter('error',Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(raw)) as source:
            if source.format not in ('PNG','JPEG','WEBP'):raise ValueError('Оберіть PNG, JPEG або WebP.')
            if source.width*source.height>25_000_000:raise ValueError('Зображення перевищує 25 мегапікселів.')
            source.load();pic=ImageOps.exif_transpose(source).convert('RGBA')
            pic.thumbnail((1600,1600))
            background=Image.new('RGB',pic.size,'white');background.paste(pic,mask=pic.getchannel('A'))
            out=io.BytesIO();background.save(out,format='JPEG',quality=90)
    return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode('ascii')
