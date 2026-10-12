"""Build precons.json (every preconstructed deck's card list) for Deckwright from MTGJSON's AllDeckFiles archive.

Usage: python3 build_precons.py AllDeckFiles.tar.gz precons.json
Deck data from MTGJSON (https://mtgjson.com).
"""
import json, sys, tarfile, zipfile, datetime

src, out = sys.argv[1], sys.argv[2]

def deck_files():
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            for n in z.namelist():
                if n.endswith(".json"):
                    yield json.loads(z.read(n))
    else:
        with tarfile.open(src, "r:*") as t:
            for m in t:
                if m.isfile() and m.name.endswith(".json"):
                    yield json.load(t.extractfile(m))

names, name_ix = [], {}
def nix(n):
    if n not in name_ix:
        name_ix[n] = len(names); names.append(n)
    return name_ix[n]

def cards(lst):
    rows = []
    for c in lst or []:
        if not c.get("name"):
            continue
        rows.append([nix(c["name"]), int(c.get("count") or 1), str(c.get("setCode") or "").lower(), str(c.get("number") or ""), 1 if c.get("isFoil") else 0])
    return rows

decks = []
for doc in deck_files():
    d = doc.get("data", doc)
    if not isinstance(d, dict) or not d.get("name") or not d.get("releaseDate"):
        continue
    main = cards(d.get("mainBoard"))
    if not main:
        continue
    decks.append([d["name"], str(d.get("code") or "").upper(), d.get("type") or "", d["releaseDate"],
                  cards(d.get("commander")), main, cards(d.get("sideBoard"))])

decks.sort(key=lambda x: (x[3], x[0]), reverse=True)
with open(out, "w", encoding="utf-8") as fh:
    json.dump({"t": datetime.date.today().isoformat(), "n": names, "d": decks}, fh, ensure_ascii=False, separators=(",", ":"))
print(f"{len(decks)} decks, {len(names)} different cards -> {out}")
