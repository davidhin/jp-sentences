"""Get wanikani vocab and build sample sentences."""
import os
import pickle as pkl
import re

import pandas as pd
import pykakasi
import requests
import sqlalchemy

import jpsentences as jp


class Wanikani:
    """All-purpose Wanikani class."""

    def __init__(self, sync=True):
        """Init class."""
        self.headers = {"Authorization": f"Bearer {os.getenv('WANIKANI')}"}
        self.sync = sync
        self.subjects = self.download_all("https://api.wanikani.com/v2/subjects")
        df = pd.json_normalize(self.subjects)
        df.columns = [i.replace("data.", "") for i in df.columns]
        self.subjects = {i["id"]: i for i in self.subjects}
        self.sql = sqlalchemy.create_engine("sqlite://", echo=False)
        df[["id", "object", "level", "characters"]].to_sql("subjects", con=self.sql)
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

    def furigana(self, text):
        """Return furigana replacements.

        Example:
        get_furigana("毎日九時間ぐらい勉強します")
        >>> {'毎日': '毎日[まいにち] ', '九時': '九時[くじ] ', '間': '間[かん] '}
        """
        kks = pykakasi.kakasi()
        result = kks.convert(text)
        final = ""
        for r in result:
            if not set(Wanikani.get_kanji(r["orig"])).issubset(self.known_kanji):
                final += f" {r['orig']}[{r['hira']}]"
            else:
                final += r["orig"]
        return final

    def subject(self, id):
        """Get subject data by subject ID."""
        return self.subjects[id]

    def kanji(self, kanji):
        """Get kanji info."""
        where = f"characters == '{kanji}' and object == 'kanji'"
        id = self.sql.execute(f"SELECT id FROM subjects where {where}").first()
        return "Not found" if not id else self.subjects[id[0]]

    def vocab(self, vocab):
        """Get vocab info."""
        where = f"characters == '{vocab}' and object == 'vocabulary'"
        id = self.sql.execute(f"SELECT id FROM subjects where {where}").first()
        return "Not found" if not id else self.subjects[id[0]]

    def worse_assignments(self):
        """View worse assignments in WaniKani."""
        df = pd.DataFrame.from_records([i["data"] for i in self.reviews])
        df = df.rename(columns={"incorrect_meaning_answers": "meaning"})
        df = df.rename(columns={"incorrect_reading_answers": "reading"})
        df["total"] = df.meaning + df.reading
        df = df[df.total > 0]
        df = df.groupby("subject_id").sum().reset_index()
        df["data"] = df.subject_id.apply(lambda x: self.subject(x))
        df["chars"] = df.data.apply(lambda x: x["data"]["characters"])
        df["object"] = df.data.apply(lambda x: x["object"])
        df["level"] = df.data.apply(lambda x: x["data"]["level"])
        keep = ["level", "object", "chars", "meaning", "reading", "total"]
        df = df[keep].sort_values("total", ascending=0)
        df.to_csv(jp.outputs_dir() / "worse_assignments.csv", index=0)
        return df

    def vocab_data_template(self, vocab):
        """Get template JSON string for vocab data."""
        ret = []
        vdata = self.vocab(vocab)
        for sent in vdata["data"]["context_sentences"]:
            ret.append(
                {
                    "id": "",
                    "vocab": vocab,
                    "japanese": sent["ja"],
                    "english": sent["en"],
                    "englishlit": "",
                    "grammar": {"": ""},
                    "level": vdata["data"]["level"],
                }
            )
        return ret

    def sentence_known(self, text):
        """Return False if sentence contains unknown kanji."""
        kanji = set(Wanikani.get_kanji(text))
        if len(kanji.difference(self.known_kanji)) > 0:
            return "Unknown_Kanji"
        return "Known_Kanji"
