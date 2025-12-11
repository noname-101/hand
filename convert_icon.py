"""Convert icon.jpg to a Windows .ico file containing multiple sizes.

Usage:
    python convert_icon.py [input_image] [output_icon]

If not provided, defaults to './icon.jpg' -> './icon.ico'.
Requires Pillow (pip install Pillow)
"""
from PIL import Image
import sys
from pathlib import Path


def convert_to_ico(src: Path, dst: Path):
    # sizes commonly used in Windows icons
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img = Image.open(src).convert('RGBA')

    # ensure square canvas by padding with transparent background if needed
    max_side = max(img.width, img.height)
    if img.width != img.height:
        square = Image.new('RGBA', (max_side, max_side), (0, 0, 0, 0))
        paste = ((max_side - img.width) // 2, (max_side - img.height) // 2)
        square.paste(img, paste)
        img = square

    # generate resized frames
    icons = [img.resize(s, Image.LANCZOS) for s in sizes]

    # save as .ico
    img.save(dst, format='ICO', sizes=[i.size for i in icons])


def main(argv):
    src = Path(argv[1]) if len(argv) > 1 else Path('icon.jpg')
    dst = Path(argv[2]) if len(argv) > 2 else Path('icon.ico')

    if not src.exists():
        print(f"Source image not found: {src}")
        return 2

    try:
        convert_to_ico(src, dst)
        print(f"Wrote: {dst.resolve()}")
        return 0
    except Exception as e:
        print('Conversion failed:', e)
        return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
