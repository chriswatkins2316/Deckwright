# Deckwright

Build Magic: The Gathering decks from the paper cards you own.

- Import a ManaBox CSV export of your collection.
- **Build**: Claude builds Commander, Standard, Pioneer, Modern, Legacy or casual decks using only your cards.
- **Check**: paste any decklist to see what you own, what you still need, and get stand-ins from your collection.
- Works offline once installed (Claude, card pictures and card updates need a connection).

Your API key, collection and decks are stored only in the browser on your device. Nothing personal is in this repository.

## Hosting on GitHub Pages

1. Upload every file in this folder to the root of a public GitHub repository.
2. In the repository, open **Settings → Pages**, set **Source** to *Deploy from a branch*, pick `main` and `/ (root)`, and save.
3. After a minute or two the app is live at `https://<your-username>.github.io/<repository-name>/`.

## Updating the app

When any file changes, raise `VERSION` in `sw.js` (for example `deckwright-v2`) so installed copies pick up the new files.

Card data comes from [Scryfall](https://scryfall.com). Deckwright is unofficial Fan Content permitted under the Wizards of the Coast Fan Content Policy and is not approved or endorsed by Wizards.
