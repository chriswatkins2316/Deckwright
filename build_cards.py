"""Build cards.js for Deckwright from a Scryfall Oracle Cards bulk file (.json, .jsonl or .gz). Usage: python3 build_cards.py oracle-cards-YYYYMMDD.json cards.js"""
import gzip, json, re, sys, os

SRC, OUT = sys.argv[1], sys.argv[2]
SKIP_LAYOUTS = {"token", "double_faced_token", "emblem", "art_series", "planar", "scheme", "vanguard", "front_card"}
SKIP_SET_TYPES = {"memorabilia", "token", "minigame"}
BITS = {"standard": 1, "pioneer": 2, "modern": 4, "legacy": 8, "commander": 16}
# MTG Arena: format bits (only for cards on Arena), plus "digital only" and "on Arena"
ABITS = {"standard": 1, "alchemy": 2, "historic": 4, "timeless": 8, "explorer": 16, "standardbrawl": 32, "brawl": 64}
A_DIGITAL, A_ON = 128, 256
ARENA_ONLY_FMTS = ("alchemy", "historic", "timeless", "brawl", "standardbrawl")
RARITY = {"common": "c", "uncommon": "u", "rare": "r", "mythic": "m", "special": "r", "bonus": "m"}
WUBRG = "WUBRG"

def strip_reminder(t):
    return re.sub(r"\s*\([^)]*\)", "", (t or "").replace("\n", " ")).strip()

def records(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as fh:
        head = fh.read(1); fh.seek(0)
        if head == "[":
            yield from json.load(fh)
        else:
            for line in fh:
                line = line.strip().rstrip(",")
                if line and line not in ("[", "]"):
                    yield json.loads(line)

cards, seen, latest, banned, digital = [], set(), "", {}, set()
for d in records(SRC):
    if d.get("layout") in SKIP_LAYOUTS or d.get("set_type") in SKIP_SET_TYPES: continue
    leg = d.get("legalities", {})
    # Arena: Scryfall only marks Arena formats legal for cards that are on Arena
    on_arena = "arena" in d.get("games", []) or any(leg.get(f) in ("legal", "restricted", "banned") for f in ARENA_ONLY_FMTS)
    # the sample printing can be digital even for paper cards, so check paper legality too
    paper = "paper" in d.get("games", []) or leg.get("vintage") in ("legal", "restricted", "banned")
    if not paper:
        digital.add(d["name"])
        if not on_arena: continue          # MTGO-only and the like
    name = d["name"]
    if name in seen: continue
    seen.add(name)
    faces = d.get("card_faces") or [d]
    front = faces[0]
    cost = d.get("mana_cost") or front.get("mana_cost", "")
    type_line = front.get("type_line") or d.get("type_line", "")
    colors = d.get("colors") if d.get("colors") is not None else front.get("colors", [])
    ident = d.get("color_identity", [])
    if len(faces) > 1 and d.get("card_faces"):
        oracle = " // ".join(strip_reminder(f.get("oracle_text")) for f in faces)
    else:
        oracle = strip_reminder(d.get("oracle_text"))
    p, t = front.get("power", d.get("power")), front.get("toughness", d.get("toughness"))
    pt = f"{p}/{t}" if p is not None and t is not None else (front.get("loyalty") or d.get("loyalty") or front.get("defense") or d.get("defense") or "")
    flags = sum(b for f, b in BITS.items() if leg.get(f) in ("legal", "restricted")) if paper else 0
    aflags = (sum(b for f, b in ABITS.items() if leg.get(f) in ("legal", "restricted")) + A_ON if on_arena else 0) + (0 if paper else A_DIGITAL)
    for f in BITS:
        if paper and leg.get(f) == "banned": banned.setdefault(f, []).append(name)
    for f in ABITS:
        if on_arena and leg.get(f) == "banned": banned.setdefault("arena_" + f, []).append(name)
    tl_front = type_line
    if ("Legendary" in tl_front and "Creature" in tl_front) or "can be your commander" in (d.get("oracle_text") or front.get("oracle_text") or ""):
        flags += 32
    if d.get("game_changer"): flags += 64
    cmc = d.get("cmc", 0) or 0
    pr = d.get("prices") or {}
    num = lambda k: float(pr[k]) if pr.get(k) else 0.0
    usd = (num("usd") or num("usd_foil") or num("usd_etched")) if paper else 0.0
    foil = (num("usd_foil") or num("usd_etched") or num("usd")) if paper else 0.0
    cards.append([name, cost, int(cmc) if float(cmc).is_integer() else cmc, type_line,
                  "".join(c for c in WUBRG if c in colors), "".join(c for c in WUBRG if c in ident),
                  oracle, pt, flags, round(usd, 2), round(foil, 2), aflags, RARITY.get(d.get("rarity"), "c")])
    latest = max(latest, d.get("released_at", ""))

cards.sort(key=lambda c: c[0])
date = re.search(r"(\d{8})", os.path.basename(SRC))
meta = {"source": "Scryfall", "date": f"{date.group(1)[:4]}-{date.group(1)[4:6]}-{date.group(1)[6:]}" if date else "",
        "priceDate": f"{date.group(1)[:4]}-{date.group(1)[4:6]}-{date.group(1)[6:]}" if date else "", "count": len(cards), "banned": {f: sorted(v) for f, v in banned.items()}, "digital": sorted(digital), "arena": 1}
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("window.MTG_DB=" + json.dumps({"meta": meta, "cards": cards}, ensure_ascii=False, separators=(",", ":")) + ";")
print(len(cards), "cards", os.path.getsize(OUT) // 1024, "KB", meta)
