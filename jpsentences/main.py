import pandas as pd

import jpsentences as jp
import jpsentences.helpers as jph

# Read data
df = pd.read_json(jp.external_dir() / "data.json")

# Load Wanikani
wk = jph.Wanikani(False)
wk.worse_assignments()

# Generate extra info
df["romaji"] = df.japanese.apply(jph.Wanikani.romaji)
df["japanese_raw"] = df.japanese
df["japanese"] = df.japanese.apply(wk.furigana)

# Move level column to last
df = df[[c for c in df.columns if c != "level"] + ["level"]]

# Generate tags
df["tags"] = df.japanese_raw.apply(wk.sentence_known).astype(str)

# Grammar rules to consecutive divs
df.grammar = df.grammar.apply(
    lambda x: "".join([f"<div>{i}</div>" for j in x.items() for i in j])
)

# Save CSV
df.to_csv(jp.outputs_dir() / "wk.csv", index=0, header=None)
