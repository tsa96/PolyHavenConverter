import argparse
import hashlib
import os
import subprocess
import pandas
import requests
from pathlib import Path
from wand.image import Image

DO_HASH_CHECK = True

# At 1k this will download about 1GB from PolyHaven, please use sparingly, add make use for caching
RESOLUTION = "1k"
FORMAT = "png"
PH_MAPS = {
    "Diffuse": "diffuse",
    "arm": "arm",
    "nor_dx": "normal",
    "Displacement": "height",
}
OUT_DIR_NAME = 'polyhaven/'
DEFAULT_PARALLAX_DEPTH = 0.01

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRaGNDH2LaMQ2LJIIqVOc3wl6X3V4jdAtG_eYf04DSgzt7qaWyTeTmqCH7CPBKi2hN8-NL5MBPzUYmD/pub?gid=0&single=true&output=csv "
API_URL = "https://api.polyhaven.com"


def get_spreadsheet_data():
    return pandas.read_csv(SHEET_URL, index_col=False)


def get_texture_files():
    df = get_spreadsheet_data()

    for index, row in df.iterrows():
        if not row.get("Use"):
            continue

        tex_id = row.get("ID")
        texfiles = get_file_list(tex_id)

        print(tex_id)

        for key in PH_MAPS:
            if key not in texfiles:
                continue

            tex_dir = os.getcwd() + "/downloads/" + tex_id
            Path(tex_dir).mkdir(exist_ok=True)

            out_name = f"{tex_id}_{PH_MAPS[key]}.{FORMAT}"
            out_path = tex_dir + "/" + out_name
            tex_url = texfiles[key][RESOLUTION][FORMAT]["url"]

            if Path(out_path).is_file():
                if not DO_HASH_CHECK:
                    continue
                with open(out_path, "rb") as f:
                    b = f.read()
                    file_hash = hashlib.md5(b).hexdigest()
                    remote_hash = texfiles[key][RESOLUTION][FORMAT]["md5"]

                    if file_hash == remote_hash:
                        print(f"  File {out_name} already exists and passes hash check, skipping")
                    else:
                        print(f"  File {out_name} already exists but failed hash check, redownloading")
                        download_file(tex_url, out_path)
            else:
                download_file(tex_url, out_path)


def convert_downloaded():
    download_dir = os.getcwd() + "/downloads/"
    out_dir = os.getcwd() + '/' + OUT_DIR_NAME

    for directory in os.listdir(download_dir):
        tex_dir = download_dir + directory + "/"

        file_list = os.listdir(tex_dir)

        tex_id = remove_file_extension_and_type(file_list[0])

        with Image(filename=f"{tex_dir}{tex_id}_arm.{FORMAT}") as img, open(
                f"{tex_dir}{tex_id}_mrao.{FORMAT}", "wb"
        ) as out:
            print(f"Making MRAO map, writing to {tex_id}_mrao.{FORMAT}")
            # Switch R and B
            img.color_matrix([[0, 0, 1],
                              [0, 1, 0],
                              [1, 0, 0]])
            img.save(out)

        # can't get this shit to work
        # with Image(filename=f"{tex_dir}{tex_id}_normal.{FORMAT}") as normal, \
        #      Image(filename=f"{tex_dir}{tex_id}_height.{FORMAT}") as height, \
        #      open(f"{tex_dir}{tex_id}_hormal.{FORMAT}", "wb") as out_file:
        #     normal.composite_channel("alpha",height,"copy_alpha")
        #     normal.save(out_file)

        # fuck it
        print(f"Making hormal map, writing to {tex_id}_hormal.{FORMAT}")
        subprocess.run(
            f"magick convert {tex_dir}{tex_id}_normal.{FORMAT} {tex_dir}{tex_id}_height.{FORMAT} -alpha Off -compose "
            f"CopyOpacity -composite {tex_dir}{tex_id}_hormal.{FORMAT} "
        )

        for tex_type in ['diffuse', 'hormal', 'mrao']:
            name = f"{tex_id}_{tex_type}.{FORMAT}"

            if Path(tex_dir + name).is_file() and args.forceconvert:
                continue

            compression = 'bgr888' if tex_type == 'hormal' else 'dxt1'
            subprocess.run(f"VTFCmd.exe -file {name} "
                           f"-format {compression} -output {out_dir}")


def parse_sheet_vmts():
    df = get_spreadsheet_data()

    print(df)

    for index, row in df.iterrows():
        if not row.get("Use"):
            continue

        tex_id = row.get("ID")
        hsl_dict = row.get("HSL")

        if hsl_dict and not pandas.isna(hsl_dict):
            for hsl_item in hsl_dict.split(';'):
                hsl = hsl_item.split(':')
                name = hsl[0]
                val = hsl[1]
                with VMT(f"{tex_id}_{name}", tex_id) as vmt:
                    vmt.add_param("hsl", val)
        else:
            with VMT(tex_id, tex_id) as _:
                pass


# probs overkill but felt like learning something new
class VMT:
    def add_param(self, key, value):
        self.params[key] = value

    def __write_param(self, key, value):
        indent = " " * (4 + (self.max_len - len(key)))
        self.file.write(f"    \"${key}\"{indent}\"{value}\"\n")

    def __init__(self, file_name, tex_name, params=None):
        if params is None:
            params = {}

        self.file_name = file_name
        self.tex_name: str = tex_name
        self.params: dict = params
        self.out_dir: str = os.getcwd() + '/' + OUT_DIR_NAME
        self.max_len: int = 0

    def __enter__(self):
        self.file = open(f"{self.out_dir}{self.file_name}.vmt", "w")
        self.file.write("PBR\n{\n")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.max_len = len(max(list(self.params.keys()) + ['basetexture', 'bumpmap', 'mraotexture'], key=len))

        print(f"Writing {self.file_name}")

        self.__write_param("basetexture", OUT_DIR_NAME + self.tex_name + "_diffuse")
        self.__write_param("bumpmap", OUT_DIR_NAME + self.tex_name + "_hormal")
        self.__write_param("mraotexture", OUT_DIR_NAME + self.tex_name + "_mrao")

        if self.params is not None:
            self.file.write("\n")
            for k, v in self.params.items():
                self.__write_param(k, v)

        self.__write_param("envmap", "env_cubemap")
        self.__write_param("parallax", "1")
        self.__write_param("parallaxdepth", f"{DEFAULT_PARALLAX_DEPTH}")

        self.file.write("}\n")
        self.file.close()


def get_file_list(asset_name: str):
    return requests.get(API_URL + f"/files/{asset_name}").json()


def download_file(url: str, out_name: str):
    print(f"  Downloading file {url}, writing to {out_name}")

    response = requests.get(url)
    with open(out_name, "wb") as f:
        f.write(response.content)


def remove_file_extension(file_name: str) -> str:
    return file_name.removesuffix("." + FORMAT)


def remove_file_extension_and_type(file_name: str) -> str:
    return "_".join(remove_file_extension(file_name).split("_")[:-1])


def get_type_from_filename(file_name: str) -> str:
    return remove_file_extension(file_name).split("_")[-1]


parser = argparse.ArgumentParser()
parser.add_argument("exec", help="the part of the program to run [download, convert, vmf, all]")
parser.add_argument("--forceconvert", help="perform VTF conversion even if file exists", action="store_true")

args = parser.parse_args()

match args.exec:
    case "get":
        get_texture_files()
    case "convert":
        convert_downloaded()
    case "vmt":
        parse_sheet_vmts()
    case "all":
        get_texture_files()
        convert_downloaded()
