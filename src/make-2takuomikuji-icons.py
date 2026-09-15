#!/usr/bin/env python3
"""カバネリチャレンジおみくじ用のアイコンを書き出す。

    python3 src/make-2takuomikuji-icons.py

アプリ内の実際の「おみくじ」札（朱色の二重枠＋縦書き文字）を
そのままアイコン化した自作デザイン。

書き出し先は kabaneri-unato/2takuomikuji/:
  apple-touch-icon.png (180) / icon-192.png / icon-512.png
  icon-maskable-512.png … Android用。周囲を切り取られても中身が残るよう内側に寄せてある
"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))       # src/
DEST = os.path.join(os.path.dirname(BASE), 'kabaneri-unato', '2takuomikuji')

MINCHO = '/System/Library/Fonts/ヒラギノ明朝 ProN.ttc'          # index 2 = W6

S = 720          # アイコンの下描きサイズ（各サイズへ縮小する）

NAVY_TOP = (18, 27, 55)
NAVY_BOTTOM = (5, 10, 22)
CARD_TOP = (247, 237, 218)
CARD_BOTTOM = (239, 221, 188)
RED = (181, 34, 47)
RED_DARK = (138, 22, 32)
INK = (58, 38, 20)


def mincho(px):
    return ImageFont.truetype(MINCHO, px, index=2)


def vgrad(size, top, bottom):
    w, h = size
    g = Image.new('RGB', (1, h))
    px = g.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return g.resize((w, h), Image.BICUBIC)


def rounded_rect(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def vertical_text(img, xy, text, font, fill):
    """1文字ずつ積んで縦書きにする（中央そろえ）"""
    d = ImageDraw.Draw(img)
    heights = []
    for ch in text:
        l, t, r, b = d.textbbox((0, 0), ch, font=font)
        heights.append(b - t)
    gap = font.size * 0.12
    total = sum(heights) + gap * (len(text) - 1)
    y = xy[1] - total / 2
    for ch, h in zip(text, heights):
        l, t, r, b = d.textbbox((0, 0), ch, font=font)
        w = r - l
        d.text((xy[0] - w / 2 - l, y - t), ch, font=font, fill=fill)
        y += h + gap


def card_icon(scale=1.0):
    """おみくじ札のアイコン本体。scale を下げると内側に縮む（マスカブル用）"""
    bg = vgrad((S, S), NAVY_TOP, NAVY_BOTTOM).convert('RGB')

    n = int(S * scale)
    layer = Image.new('RGB', (n, n), NAVY_BOTTOM)

    margin = int(n * 0.10)
    outer = (margin, margin, n - margin, n - margin)
    d = ImageDraw.Draw(layer)
    rounded_rect(d, outer, radius=int(n * 0.045), fill=RED_DARK)

    border_w = int(n * 0.045)
    inner = (outer[0] + border_w, outer[1] + border_w,
             outer[2] - border_w, outer[3] - border_w)

    grad = vgrad((inner[2] - inner[0], inner[3] - inner[1]), CARD_TOP, CARD_BOTTOM)
    mask = Image.new('L', (inner[2] - inner[0], inner[3] - inner[1]), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, inner[2] - inner[0] - 1, inner[3] - inner[1] - 1),
        radius=int(n * 0.025), fill=255)
    layer.paste(grad, (inner[0], inner[1]), mask)

    d = ImageDraw.Draw(layer)
    rounded_rect(d, inner, radius=int(n * 0.025), outline=RED, width=max(2, int(n * 0.006)))

    cx = (inner[0] + inner[2]) / 2
    cy = (inner[1] + inner[3]) / 2
    vertical_text(layer, (cx, cy), 'おみくじ', mincho(int(n * 0.155)), RED_DARK)

    if scale != 1.0:
        pad = Image.new('RGB', (S, S), NAVY_BOTTOM)
        pad.paste(bg, (0, 0))
        pad.paste(layer, ((S - n) // 2, (S - n) // 2))
        return pad

    return layer


def main():
    os.makedirs(DEST, exist_ok=True)
    out = [
        ('apple-touch-icon.png', card_icon(), 180),
        ('icon-192.png', card_icon(), 192),
        ('icon-512.png', card_icon(), 512),
        ('icon-maskable-512.png', card_icon(scale=0.78), 512),
    ]
    for name, im, size in out:
        im.resize((size, size), Image.LANCZOS).save(os.path.join(DEST, name))
        print(f'{name} ({size}px)')


if __name__ == '__main__':
    main()
