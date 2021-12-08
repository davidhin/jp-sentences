"""Get wanikani vocab and build sample sentences."""
import os
import pickle as pkl
import re

import pykakasi
import requests

import jpsentences as jp


class Wanikani:
    """All-purpose Wanikani class."""

    def __init__(self, sync=True):
        """Init class."""
        self.headers = {"Authorization": f"Bearer {os.getenv('WANIKANI')}"}
        self.sync = sync
        self.subjects = self.download_all("https://api.wanikani.com/v2/subjects")
        self.reviews = self.download_all("https://api.wanikani.com/v2/reviews")
        self.assignments = self.download_all("https://api.wanikani.com/v2/assignments")
        self.known_kanji = self.get_known_kanji()

    def get_kanji(text):
        """Get Kanji from text.

        Example:
        get_kanji("毎日九時間ぐらい勉強します")
        >>> ['毎', '日', '九', '時', '間', '勉', '強']
        """
        return re.findall(r"[㐀-䶵一-鿋豈-頻]", text)

    def romaji(text):
        """Get hiragana/romaji from kanji sentence.

        Example:
        romaji("この問題用紙は、全部で三頁あります")
        >>> 'kono mondai youshi ha, zenbu de san peeji arimasu'
        """
        kks = pykakasi.kakasi()
        result = kks.convert(text)
        return " ".join([i["hepburn"] for i in result])

    def get_wk_user(self):
        """Get WK User info."""
        data = requests.get("https://api.wanikani.com/v2/user", headers=self.headers)
        return data.json()

    def download_all(self, url: str):
        """Download all Wanikani subject info."""
        data = []
        savefile = jp.cache_dir() / str(jp.hashstr(url))
        if not self.sync and os.path.exists(savefile):
            with open(savefile, "rb") as f:
                return pkl.load(f)
        while url:
            ret = requests.get(url, headers=self.headers).json()
            url = ret["pages"]["next_url"]
            data += ret["data"]
            print(url)
        with open(savefile, "wb") as f:
            pkl.dump(data, f)
        return data

    def get_known_kanji(self):
        """Get all kanji with srs >= 0."""
        known_kanji = set()
        for i in self.assignments:
            if i["data"]["subject_type"] == "kanji" and i["data"]["srs_stage"]:
                subject_id = i["data"]["subject_id"]
                known_kanji.add(self.subject(subject_id)["data"]["characters"])
        return known_kanji

    def get_furigana(self, text):
        """Return furigana replacements.

        Example:
        get_furigana("毎日九時間ぐらい勉強します")
        >>> {'毎日': '毎日[まいにち] ', '九時': '九時[くじ] ', '間': '間[かん] '}
        """
        kks = pykakasi.kakasi()
        result = kks.convert(text)
        suffix_removal = ["て", "で", "く", "か", "、"]
        replacements = {}
        for item in result:
            if not set(Wanikani.get_kanji(item["orig"])).issubset(self.known_kanji):
                if len(item["orig"]) > 1:
                    for sr in suffix_removal:
                        if item["orig"][-1] == sr and item["hira"][-1] == sr:
                            item["orig"] = item["orig"][:-1]
                            item["hira"] = item["hira"][:-1]
                furi = "{}[{}] ".format(item["orig"], item["hira"])
                replacements[item["orig"]] = furi
        return replacements

    def furigana(self, text):
        """Return original string with relevant furigana insertions."""
        fg = self.get_furigana(text)
        ret = text
        for r in fg.items():
            if r[0] not in ret:
                print("PYKAKASI ERROR:", r)
            ret = ret.replace(r[0].strip(), r[1].strip())
        return ret

    def subject(self, id):
        """Get subject data by subject ID."""
        for i in self.subjects:
            if i["id"] == id:
                return i
