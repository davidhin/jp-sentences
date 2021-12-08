import pandas as pd

import jpsentences as jp
import jpsentences.helpers as jph

# Read data
df = pd.read_json(jp.external_dir() / "data.json")

# Generate extra info
wk = jph.Wanikani(False)
df["romaji"] = df.japanese.apply(jph.Wanikani.romaji)
df["japanese"] = df.japanese.apply(wk.furigana)

# Move level column to last
df = df[[c for c in df.columns if c != "level"] + ["level"]]

# Save CSV
df.to_csv(jp.outputs_dir() / "wk.csv", index=0)
