import requests

API_URL = "https://api.polyhaven.com"


class Asset:
    def __init__(self, name, info, files):
        self.name = name
        self.info = info
        self.files = files

    def to_csv(self):
        return (
                self.info["name"]
                + ","
                + self.name
                + ","
                + f'=HYPERLINK("https://polyhaven.com/a/{self.name}")'
                + ","
                + f'=IMAGE("https://cdn.polyhaven.com/asset_img/thumbs/{self.name}.png?width=285&height=285")'
        )


def get_file_list(asset_name):
    return requests.get(API_URL + f"/files/{asset_name}").json()


assetList = requests.get(API_URL + "/assets/", params={"type": "textures"}).json()

assets = []
for a in assetList:
    assets.append(Asset(a, assetList[a], "").to_csv())

out = open("./texture_list.csv", "w")
out.write("\n".join(assets))
out.close()
