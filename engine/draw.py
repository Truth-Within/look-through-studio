"""Supersampled drawing layer: draw big, reduce, paste (clean anti-aliased outlines, no alpha fringe)."""
from PIL import Image, ImageDraw

BLACK = (22, 22, 30)


class Layer:
    def __init__(self, frame, box, S=2):
        x0, y0, x1, y1 = box
        W, H = frame.size
        self.x0, self.y0 = max(0, int(x0)), max(0, int(y0))
        self.x1, self.y1 = min(W, int(x1) + 1), min(H, int(y1) + 1)
        self.S, self.frame = S, frame
        self.w, self.h = max(1, self.x1 - self.x0), max(1, self.y1 - self.y0)
        crop = frame.crop((self.x0, self.y0, self.x0 + self.w, self.y0 + self.h))
        self.img = crop.resize((self.w * S, self.h * S), Image.NEAREST)
        self.d = ImageDraw.Draw(self.img)

    def p(self, pt):
        return ((pt[0] - self.x0) * self.S, (pt[1] - self.y0) * self.S)

    def cap(self, a, b, w, color):
        pa, pb, r = self.p(a), self.p(b), w * self.S / 2
        self.d.line([pa, pb], fill=color, width=max(1, int(w * self.S)))
        for x, y in (pa, pb):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=color)

    def circle(self, c, r, fill=None, outline=None, ow=0):
        x, y = self.p(c)
        R = r * self.S
        if outline is not None:
            Ro = R + ow * self.S
            self.d.ellipse([x - Ro, y - Ro, x + Ro, y + Ro], fill=outline)
        if fill is not None:
            self.d.ellipse([x - R, y - R, x + R, y + R], fill=fill)

    def ellipse(self, c, rx, ry, fill=None, outline=None, ow=0):
        x, y = self.p(c)
        if outline is not None:
            self.d.ellipse([x - (rx + ow) * self.S, y - (ry + ow) * self.S, x + (rx + ow) * self.S, y + (ry + ow) * self.S], fill=outline)
        if fill is not None:
            self.d.ellipse([x - rx * self.S, y - ry * self.S, x + rx * self.S, y + ry * self.S], fill=fill)

    def ring(self, c, rx, ry, color, w):
        x, y = self.p(c)
        self.d.ellipse([x - rx * self.S, y - ry * self.S, x + rx * self.S, y + ry * self.S], outline=color, width=max(1, int(w * self.S)))

    def poly(self, pts, fill=None, outline=None, ow=0):
        if len(pts) < 3:
            return
        q = [self.p(t) for t in pts]
        if outline is not None and ow > 0:
            self.d.polygon(q, fill=fill)
            self.d.line(q + [q[0]], fill=outline, width=max(1, int(ow * 2 * self.S)), joint="curve")
            if fill is not None:
                self.d.polygon(q, fill=fill)
                self.d.line(q + [q[0]], fill=outline, width=max(1, int(ow * self.S)), joint="curve")
        elif fill is not None:
            self.d.polygon(q, fill=fill)

    def line(self, pts, w, color):
        q = [self.p(t) for t in pts]
        self.d.line(q, fill=color, width=max(1, int(w * self.S)), joint="curve")

    def text(self, pt, s, font, fill, anchor="mm"):
        self.d.text(self.p(pt), s, font=font, fill=fill, anchor=anchor)

    def finish(self):
        small = self.img.reduce(self.S) if self.S > 1 else self.img
        self.frame.paste(small, (self.x0, self.y0))


def hull(points):
    """Convex hull (monotone chain) of 2D points."""
    pts = sorted(set((round(x, 2), round(y, 2)) for x, y in points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]
