import sys
from PIL import Image, ImageDraw
import json
import os.path
import numpy as np
import math

# main params
backgroundImageColor = (67, 101, 138)
backgroundImageNetColor = (89, 123, 160)
backgroundImageNetSize = 20
elementFillColor = (67, 101, 138)
elementLineColor = (200, 200, 200)
structureImageScale = 30.0
minImageWidth = 300
maxImageWidth = 1024
minImageHeight = 300
maxImageHeight = 768

drawElementsTable = {
    "foundation.prefab": [0, 8, 1, -1.5, -1.5, 1.5, -1.5, 1.5, 1.5, -1.5, 1.5],
    "foundation.triangle.prefab": [0, 6, 1, -1.5, 0, 1.5, 0, 0, 2.62],
    "wall.prefab": [1, 4, 5, 0, -1.5, 0, 1.5],
    "wall.doorway.prefab": [1, 4, 5, 0, -1.5, 0, -0.7,
                            1, 4, 5, 0, 0.7, 0, 1.5],
}

class Vector(object):
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

    def __array__(self, dtype=None):
        if dtype:
            return np.array([self.x, self.y, self.z], dtype=dtype)
        else:
            return np.array([self.x, self.y, self.z])

    def __str__(self):
        return "(" + str(self.x) + ", " + str(self.y) + ", " + str(self.z) + ")"

    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y, self.z + other.z)

    def rotate(self, rotationMatix):
        v1 = np.array([[self.x], [self.y], [self.z]])
        v2 = rotationMatix * v1
        return Vector(float(v2[0]), float(v2[1]), float(v2[2]))

class StructureElement(object):
    def __init__(self, data):
        self.ownerid = data["ownerid"]
        self.prefabname = data["prefabname"]
        self.shortname = self.prefabname.rsplit('/', 1)[-1]
        self.skinid = data["skinid"]
        self.pos = Vector(0, 0, 0)
        if "pos" in data:
            pos = data["pos"]
            self.pos = Vector(float(pos["x"]), float(pos["y"]), float(pos["z"]))
        self.rot = Vector(0,0,0)
        if "rot" in data:
            rot = data["rot"]
            self.rot = Vector(float(rot["x"]), float(rot["y"]), float(rot["z"]))
        rx = np.matrix([[1, 0, 0],
                        [0, math.cos(self.rot.x), -math.sin(self.rot.x)],
                        [0, math.sin(self.rot.x), math.cos(self.rot.x)]])
        ry = np.matrix([[math.cos(self.rot.y), 0, math.sin(self.rot.y)],
                        [0, 1, 0],
                        [-math.sin(self.rot.y), 0, math.cos(self.rot.y)]])
        rz = np.matrix([[math.cos(self.rot.z), -math.sin(self.rot.z), 0],
                        [math.sin(self.rot.z), math.cos(self.rot.z), 0],
                        [0, 0, 1]])
        self.rotationMatix = rx * ry * rz

class StructureLoader(object):
    def __init__(self, filename):
        self.filename = filename
        self.data = json.loads("{}")
        self.elements = []
        self.positon = Vector(0, 0, 0)
        try:
            f = open(self.filename, encoding = 'utf-8')
            self.data = json.load(f)
            self.valid = True
        except Exception as e:
            print("StructureLoader:" + str(e))
            self.valid = False
        finally:
            f.close()
        self.parseData()

    def __str__(self):
        return self.filename

    def parseData(self):
        self.positon = Vector(0, 0, 0)
        if "default" in self.data:
            defaultData = self.data["default"]
            if "position" in defaultData:
                pos = defaultData["position"]
                self.positon = Vector(float(pos["x"]), float(pos["y"]), float(pos["z"]))
        if "entities" in self.data:
            for elementData in self.data["entities"]:
                element = StructureElement(elementData)
                self.elements.append(element)
            self.elements.sort(reverse=True, key=lambda val: "foundation" in val.shortname)

    def getMin(self):
        if len(loader.elements) <= 0:
            return Vector(0, 0, 0)
        f = loader.elements[0]
        min = Vector(f.pos.x, f.pos.y, f.pos.z)
        for e in loader.elements:
            if min.x > e.pos.x:
                min.x = e.pos.x
            if min.y > e.pos.y:
                min.y = e.pos.y
            if min.z > e.pos.z:
                min.z = e.pos.z
        return min

    def getMax(self):
        if len(loader.elements) <= 0:
            return Vector(0, 0, 0)
        f = loader.elements[0]
        max = Vector(f.pos.x, f.pos.y, f.pos.z)
        for e in loader.elements:
            if max.x < e.pos.x:
                max.x = e.pos.x
            if max.y < e.pos.y:
                max.y = e.pos.y
            if max.z < e.pos.z:
                max.z = e.pos.z
        return max

class StructureDrawer(object):
    def __init__(self, loader):
        self.loader = loader
        min = loader.getMin()
        max = loader.getMax()
        size = Vector(max.x - min.x, max.y - min.y, max.z - min.z)
        self.offset = Vector(-0.5*(max.x + min.x), -0.5*(max.y + min.y), -0.5*(max.z + min.z))
        self.width = int(size.x * structureImageScale)
        self.height = int(size.z * structureImageScale)
        if self.width < minImageWidth:
            self.width = minImageWidth
        if self.height < minImageHeight:
            self.height = minImageHeight
        if self.width > maxImageWidth:
            self.width = maxImageWidth
        if self.height > maxImageHeight:
            self.height = maxImageHeight
        self.pivotX = self.width * 0.5
        self.pivotY = self.height * 0.5
        self.image = Image.new('RGB', (self.width, self.height), color = backgroundImageColor)
        self.draw = draw = ImageDraw.Draw(self.image)
        print("size: " + str(self.width) + ", " + str(self.height))

    def drawBackground(self):
        im = self.image
        for x in range(0, self.width, backgroundImageNetSize):
            self.draw.line((x, 0, x, self.height), fill = backgroundImageNetColor)
        for y in range(0, self.height, backgroundImageNetSize):
            self.draw.line((0, y, self.width, y), fill = backgroundImageNetColor)

    def toImageCoords(self, v):
        return (float(v.x * structureImageScale + self.pivotX), float(-v.z * structureImageScale + self.pivotY))

    def drawElement(self, e):
        ep = Vector(e.pos.x + self.offset.x, e.pos.y + self.offset.y, e.pos.z + self.offset.z)
        if e.shortname in drawElementsTable:
            dl = drawElementsTable[e.shortname]
            i = 0
            while i < len(dl):
                figure = int(dl[i])
                count = int(dl[i + 1])
                width = int(dl[i + 2])
                xy = []
                j = 0
                while j < count:
                    pp = Vector(dl[i + 3 + j], 0.0, dl[i + 4 + j]).rotate(e.rotationMatix) + ep
                    ip = self.toImageCoords(pp)
                    xy.append(ip)
                    j += 2
                if figure == 0:
                    self.draw.polygon(xy, fill = elementFillColor, outline = elementLineColor, width = width)
                if figure == 1:
                    self.draw.line(xy, fill = elementLineColor, width = width)
                i += 3 + count
        return

    def drawElements(self):
        for e in loader.elements:
            self.drawElement(e)

    def save(self, name):
        self.image.save(name, "PNG")

if len(sys.argv) < 2:
    print("Usage: python drawcopypaste.py (input.json filename) [output image filename default is as input].")
    exit(0)

if not os.path.exists(sys.argv[1]):
    print("Input file not exists")
    exit(0)

loader = StructureLoader(sys.argv[1])
if not loader.valid:
    print("Input file unknown format")
    exit(0)

# print info
print(loader.positon)
for e in loader.elements:
    print("pref " + str(e.shortname))
    print("pos " + str(e.pos))
    print("rot " + str(e.rot))

drawer = StructureDrawer(loader)
drawer.drawBackground()
drawer.drawElements()
drawer.save("new.png")