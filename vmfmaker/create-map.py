import random
import string
from vmfmaker.PyVMF import *

grid_max = 2**13 - 2048  # Make room for skybox
size = 256
gap = 256
letter_gap = 512

x = -grid_max
y = -grid_max
z = 0

environment = {
    "classname": "light_environment",
    "_ambient": "255 255 255 20",
    "_ambienthdr": "-1 -1 -1 1",
    "_ambientscalehdr": "1",
    "_light": "255 255 255 200",
    "_lighthdr": "-1 -1 -1 1",
    "_lightscalehdr": "1",
    "angles": "0 0 0",
    "pitch": "0",
    "sunspreadangle": "5",
    "origin": "0 0 64",
}

vmf = new_vmf()

skybox = SolidGenerator.room(
    w=(2**14) - 128,
    h=(2**14) - 128,
    l=(2**13) - 128,
    thick=32,
    vertex=Vertex(0, 0, 0),
)

light_env = Entity(dic=environment)
playerspawn = Entity(
    dic={"classname": "info_player_start", "origin": f"{x} {y} {z + size * 2}"}
)

for brush in skybox:
    brush.set_texture("tools/toolsskybox")

vmf.add_entities(light_env, playerspawn)
for s in skybox:
    vmf.add_solids(s)

test_array = []
for i in range(100):
    test_array.append("".join(random.choice(string.ascii_lowercase) for j in range(10)))

sorted_textures = [[] for _ in range(26)]

for t in test_array:
    sorted_textures[ord(t[0]) - 97].append(t)

print(sorted_textures)

for letter in sorted_textures:
    for texture in letter:
        cube = SolidGenerator.cube(
            vertex=Vertex(x, y, z), h=size, w=size, l=size, center=True
        )
        cube.set_texture("shadertest/pbr_concrete")
        vmf.add_solids(cube)

        x += size + gap
    x = -grid_max
    y += letter_gap

vmf.export("./output.vmf")
