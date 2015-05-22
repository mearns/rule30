#! /usr/bin/env python
# vim: set fileencoding=utf-8: set encoding=utf-8:

import sys
import random
import hashlib
import math
from PIL import Image, ImageDraw, ImageFilter, ImageChops

import collections

class Ring(collections.Sequence):
    def __init__(self, data):
        self._data = list(data)
        self._length = len(self._data)

    def __len__(self):
        return self._length

    def __iter__(self):
        return iter(self._data)

    def get_index(self, idx):
        while idx < 0:
            idx += self._length
        idx = idx % self._length
        return idx

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            start = idx.start or 0
            stop = idx.stop or self.__length
            step = idx.step or 1
            idxs = range(start, stop, step)
            return [self._data[self.get_index(i)] for i in idxs]
        return self._data[self.get_index(idx)]

    def __setitem__(self, idx, val):
        self._data[self.get_index(idx)] = val

    def replace(self, data):
        if len(data) != self._length:
            raise ValueError('Incorrect length')
        self._data = list(data)

    def tuple(self):
        return tuple(self._data)


class Automaton(object):
    def __init__(self, seed, toggle=0, erase=0, fill=0, rand=None):
        self._row = Ring([1 if c else 0 for c in seed])
        self._toggle = toggle
        self._erase = erase
        self._fill = fill
        self._random = rand or random

    def next(self):
        length = len(self._row)
        rlength = range(length)
        next_gen = [0]*length
        for i in rlength:
            n = self._row[i]
            w = self._row[i-1]
            e = self._row[i+1]
            val = 4*w + 2*n + e

            reach = 5
            limit = 8
            s = sum(self._row[i-reach:i+reach+1])

            if val in (4, 3, 2, 1) and s < limit:
                next_gen[i] = 1

            if random.random() < self._toggle:
                next_gen[i] = 0 if next_gen[i] else 1
            elif next_gen[i] == 1:
                if random.random() < self._erase:
                    next_gen[i] = 0
            elif next_gen[i] == 0:
                if random.random() < self._fill:
                    next_gen[i] = 1

        old = self._row
        self._row.replace(next_gen)
        return old

    def peek(self):
        return tuple(self._row)

    def __iter__(self):
        return self

    def show(self, generations=1):
        for i in xrange(generations):
            row = self.next()
            for cell in row:
                sys.stdout.write('%d ' % cell)
            sys.stdout.write('\n')


    @classmethod
    def random(cls, breadth, chance=0.40, toggle=0, erase=0, fill=0, rand=None):
        seed = [1 if random.random() < chance else 0 for i in xrange(breadth)]
        return cls(seed, toggle, erase, fill, rand)

    @classmethod
    def from_hash(cls, data, hash_func=None, breadth=None, toggle=0, erase=0, fill=0, rand=None):
        hash_func = hash_func or hashlib.sha256()
        hash_func.update(data)
        digest = hash_func.digest()
        bits = []
        r8 = range(8)
        breadth = breadth or len(digest*8)
        for c in digest:
            b = ord(c)
            for i in r8:
                bits.append(b >> 7)
                b = (b << 1) & 0xFF
            if len(bits) >= breadth:
                break
        return cls(bits[:breadth], toggle, erase, fill, rand)
        
        
def blend(im1, im2, w1=0.5, w2=0.5):
    p1 = im1.load()
    p2 = im2.load()
    sz = im1.size
    im = Image.new('RGB', sz)
    pix = im.load()

    for i in xrange(sz[0]):
        for j in xrange(sz[1]):
            pix[i,j] = tuple(int(float(p1[i,j][k])*w1 + float(p2[i,j][k])*w2) for k in (0,1,2))

    return im

    
if __name__ == '__main__':


    lifetime = 6
    conquerable = 0
    amiable = 100
    breadth = 40
    generations = 700
    gs = 20
    bs = 20
    gf = 25
    bf = 25

    TWO_PI = 2.0*math.pi


    a = Automaton.from_hash('This is a test', breadth=breadth)

    breadth = len(a.peek())
    im = Image.new('RGB', [gs*generations, bs*breadth], 0x223300)
    draw = ImageDraw.Draw(im)

    #phase_shift = 2.0*math.pi/3.0 #(120 deg out of phase)
    phase_shift = 1.0
    midpoint = 170.0
    color_range = 85.0
    def get_color(v, phase=0):
        age = float(v) / float(lifetime)
        factor = math.pow(age, 2.0)
        b = 140 + (115.0*math.sin(math.pi*age + 0.0*phase_shift + phase))
        g = midpoint + (color_range*math.sin(math.pi*age + 1.0*phase_shift + phase))
        r = midpoint + (color_range*math.sin(math.pi*age + 2.0*phase_shift + phase))
        r, g, b, = (int(c*factor) for c in (r,g,b))
        return b << 16 | g << 8 | r

    def get_constant_drain(ring, idx, dist, power=None):
        return 1.0

    def get_weighted_drain(ring, idx, dist, power=-1.0):
        s = 1.0
        for i in xrange(1, dist+1):
            if ring[idx+i] or ring[idx-i]:
                weight = math.pow(float(i+1), power)
                s += weight
        return s

    get_drain = get_constant_drain

        

    gen = [0] * breadth
    for i in xrange(generations):
        row_phase = TWO_PI/5.0 + (float(i) / float(generations)) * TWO_PI
        row = Ring(a.next())
        for j, c in enumerate(row):
            if c == 1 and (gen[j] <= conquerable or gen[j] >= amiable):
                gen[j] = float(lifetime)

            if gen[j] > 0:
                phase = row_phase + (float(j) / float(breadth) * (TWO_PI / 5.0))
                color = get_color(gen[j], phase)
                if gs > 1 or bs > 1:
                    draw.ellipse([gs*i, bs*j, (gs*i)+gf, (bs*j)+bf], fill=color)
                else:
                    im.putpixel([i, j], color)
                drain = get_drain(row, j, 1, -3.0)
                gen[j] -= drain

    #im = im.filter(ImageFilter.BLUR).filter(ImageFilter.SHARPEN)
    im = im.filter(ImageFilter.GaussianBlur(radius=6))
    im = im.resize([5*generations, 5*breadth], Image.LANCZOS)
    im.save('test_output.png', 'PNG')


