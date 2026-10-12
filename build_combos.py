"""Shrink Commander Spellbook's combo export (variants.json.gz) into combos.json for Deckwright.

Usage: python3 build_combos.py variants.json.gz combos.json
Combo data from Commander Spellbook (https://commanderspellbook.com).
"""
import gzip, json, sys

src, out = sys.argv[1], sys.argv[2]
raw = open(src, "rb").read()
if raw[:2] == b"\x1f\x8b":          # still gzipped (some downloads arrive already unpacked)
    raw = gzip.decompress(raw)
doc = json.loads(raw)
variants = doc.get("variants", doc if isinstance(doc, list) else [])

names, name_ix = [], {}
feats, feat_ix = [], {}
temps, temp_ix = [], {}
def ix(table, index, value):
    if value not in index:
        index[value] = len(table); table.append(value)
    return index[value]

rows = []
for v in variants:
    if v.get("status") not in ("OK", "E"):
        continue
    cards = [ix(names, name_ix, u["card"]["name"]) for u in v.get("uses", []) if u.get("card", {}).get("name")]
    if not cards:
        continue
    produces = [ix(feats, feat_ix, p["feature"]["name"]) for p in v.get("produces", []) if p.get("feature", {}).get("name")][:4]
    requires = [ix(temps, temp_ix, t["template"]["name"]) for t in v.get("requires", []) if t.get("template", {}).get("name")]
    legal = (v.get("legalities") or {}).get("commander")
    rows.append([v.get("id", ""), cards, produces, int(v.get("popularity") or 0), requires,
                 v.get("identity") or "C", v.get("manaNeeded") or "", v.get("bracketTag") or "", 1 if legal is not False else 0])

rows.sort(key=lambda r: -r[3])
data = {"t": doc.get("timestamp", ""), "n": names, "f": feats, "p": temps, "c": rows}
with open(out, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
print(f"{len(rows)} combos, {len(names)} cards, {len(feats)} results -> {out}")
