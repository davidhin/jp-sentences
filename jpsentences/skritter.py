import os

import requests
from tqdm import tqdm


class WanikaniAPI:
    def __init__(self, types):
        api = os.getenv("WANIKANI")
        session = requests.Session()
        session.headers.update({"authorization": f"Bearer {api}"})
        self.session = session
        self.type = types

    def get_kanjis(self, level):
        ret = self.session.get(
            f"https://api.wanikani.com/v2/subjects?levels={level}&types={self.type}"
        ).json()["data"]
        ret_data = []
        for r in ret:
            meaning = ", ".join([i["meaning"] for i in r["data"]["meanings"]])
            mnemonic = r["data"]["meaning_mnemonic"]
            try:
                mnemonic += " " + r["data"]["meaning_hint"]
            except Exception as E:
                pass
            mnemonic = mnemonic.replace("<radical>", "<strong>")
            mnemonic = mnemonic.replace("</radical>", "</strong>")
            data = {
                "kanji": r["data"]["characters"],
                "meaning": meaning,
                "mnemonic": mnemonic,
            }
            if data["kanji"]:
                ret_data.append(data)
        return ret_data


class SkritterAPI:
    def __init__(self, type="kanji"):
        session = requests.Session()
        auth = session.post(
            "https://legacy.skritter.com/api/v0/oauth2/token",
            data={
                "client_id": "skritterweb",
                "grant_type": "password",
                "password": os.getenv("SKRITTER_PW"),
                "username": "davidhin",
            },
            headers={
                "content-type": "application/json",
                "authorization": f"basic {os.getenv('SKRITTER')}",
            },
        )
        token = auth.json()["access_token"]
        session.headers.update({"authorization": f"bearer {token}"})
        self.session = session
        if type == "kanji":
            self.pid = "4886514592514048"  # kanji
        elif type == "radical":
            self.pid = "4601157258969088"  # radical
        self.wk = WanikaniAPI(type)

    def get_kanji(self, kanji):
        url = f"https://legacy.skritter.com/api/v0/vocabs?q={kanji}&lang=ja"
        for i in self.session.get(url).json()["Vocabs"]:
            if i["writing"] == kanji:
                ret = i
                ret["vocabId"] = ret["id"]
                return ret
        print("Not found:", kanji)
        return None

    def get_sections(self):
        return self.session.get(
            f"https://legacy.skritter.com/api/v0/vocablists/{self.pid}",
        ).json()["VocabList"]["sections"]

    def add_section(self, name):
        sections = self.get_sections()
        exists = [i["name"] for i in sections]
        if name in exists:
            return f"{name} exists already."
        return self.session.put(
            f"https://legacy.skritter.com/api/v0/vocablists/{self.pid}",
            json={"id": self.pid, "sections": sections + [{"name": name}]},
        ).json()

    def custom_kanji(self, id, meaning, mnemonic):
        self.session.put(
            f"https://legacy.skritter.com/api/v0/vocabs/{id}",
            json={
                "customDefinition": meaning,
                "id": id,
                "mnemonic": {
                    "public": False,
                    "text": mnemonic,
                },
            },
        ).json()

    def wk_rows(self, level):
        kanjis = self.wk.get_kanjis(level)
        skritter_rows = []
        for kanji in tqdm(kanjis):
            skdata = self.get_kanji(kanji["kanji"])
            if not skdata:
                continue
            self.custom_kanji(skdata["id"], kanji["meaning"], kanji["mnemonic"])
            skritter_rows.append(skdata)
        return skritter_rows

    def set_data_for_vocablist(self, pid, vocablist_id, rows):
        return self.session.put(
            f"https://legacy.skritter.com/api/v0/vocablists/{pid}/sections/{vocablist_id}",
            json={"id": vocablist_id, "rows": rows},
        ).json()

    def get_section_id(self, name):
        return [i for i in self.get_sections() if i["name"] == name][0]["id"]

    def add_wk_level_to_skritter(self, level):
        api.add_section(f"Level {level}")
        section_id = self.get_section_id(f"Level {level}")
        return self.set_data_for_vocablist(self.pid, section_id, self.wk_rows(level))


for i in range(1, 31):
    api = SkritterAPI("kanji")
    api.add_wk_level_to_skritter(i)
    api = SkritterAPI("radical")
    api.add_wk_level_to_skritter(i)
