#!/usr/bin/env python3
"""The decipherment illusion, demonstrated — a reproducible experiment for the Voynich film.

One deliberately simple "decoder", run with the freedoms real Voynich claimants used, on three texts:

  VOYNICH    Currier B text, EVA transliteration (Gaskell & Bowern 2022 repository, voynichese.zip)
  GIBBERISH  meaningless text written by Gaskell & Bowern's 42 volunteers (their repository,
             gibberish_transcriptions.zip, modified MIT licence), re-enciphered into unknown symbols
             so it starts on an equal footing with the Voynich script
  CONTROL+   a real English text (modern-English New Testament, same repository's meaningful.zip),
             enciphered with a random simple substitution — the positive control: proof the decoder
             CAN recover a real text when one is there

The decoder searches for the symbol→letter key that turns the most words into dictionary words.
Freedom levels (cumulative in spirit; each is how some claimant worked):
  F0 strict      one fixed key, a word counts only if it IS an English word
  F1 anagram     letters may be rearranged inside each word (Newbold; Hauer & Kondrak)
  F2 two langs   a word counts if it is English OR Latin (Cheshire's "any Romance language", Bax)
  F3 both        anagram + two languages

The test (what the film asks of every claim): build the key on half the pages (TRAIN), then score the
same fixed key on pages it never saw (TEST), and compare with the gibberish searched the same way.

Outputs: results.json, report.md, and sample "decodings" (sample-lines.md). Seeds are fixed;
re-running reproduces every number.
"""
from __future__ import annotations
import json, random, re, string, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"          # filled by fetch_data.py (downloaded from the original repository)
OUT = HERE / "results"
SEED = 2026
PAGE_WORDS = 200          # a "page" = 200 words
MAX_WORDS = 6000          # same amount of text from every source
ITERS = 6000              # hill-climbing steps per restart
RESTARTS = 3
LETTERS = string.ascii_lowercase


# ------------------------------------------------------------------ data
def load_voynich() -> list[str]:
    t = (DATA / "voynichese" / "Voynichese - Currier B - EVA Basic.txt").read_text(encoding="utf-8", errors="ignore")
    t = re.sub(r"[^a-z\s]", " ", t.lower())          # drop EVA uncertainty marks (!, *, digits)
    return [w for w in t.split() if w]


def load_gibberish() -> list[str]:
    words = []
    for f in sorted((DATA / "gibberish").glob("*.txt")):
        t = re.sub(r"[^a-z\s]", " ", f.read_text(encoding="utf-8", errors="ignore").lower())
        words += [w for w in t.split() if w]
    return words


def load_english() -> list[str]:
    with zipfile.ZipFile(DATA / "meaningful.zip") as z:
        t = z.read("texts/Modern - English - Literary - NT.txt").decode("utf-8", errors="ignore")
    t = re.sub(r"[^a-z\s]", " ", t.lower())
    return [w for w in t.split() if w][:MAX_WORDS * 2]


def load_latin_vocab() -> set[str]:
    with zipfile.ZipFile(DATA / "meaningful.zip") as z:
        t = z.read("texts/Historical - Latin - Literary - NT (Vulgate).txt").decode("utf-8", errors="ignore")
    return {w for w in re.sub(r"[^a-z\s]", " ", t.lower()).split() if len(w) >= 2}


def load_english_vocab() -> set[str]:
    words = Path(__import__("os").environ.get("EN_DICT", "/usr/share/dict/american-english")).read_text(encoding="utf-8", errors="ignore").split()
    return {w.lower() for w in words if w.isalpha() and w.islower() and (len(w) >= 2 or w in ("a", "i"))}


def encipher(words: list[str], rng: random.Random) -> list[str]:
    """Replace each letter by a fresh symbol (Greek letters stand in for an unknown script)."""
    symbols = list("αβγδεζηθικλμνξοπρστυφχψωϊϋ")
    alph = sorted({c for w in words for c in w})
    rng.shuffle(symbols)
    m = dict(zip(alph, symbols))
    return ["".join(m[c] for c in w) for w in words]


# ------------------------------------------------------------------ scoring
class Vocab:
    def __init__(self, langs: list[set[str]]):
        self.exact = set().union(*langs)
        self.sorted = {"".join(sorted(w)) for w in self.exact}


def score(types: list[tuple[str, int]], key: dict[str, str], voc: Vocab, anagram: bool) -> int:
    hits = 0
    for w, n in types:
        d = "".join(key[c] for c in w)
        if (d in voc.exact) or (anagram and "".join(sorted(d)) in voc.sorted):
            hits += n
    return hits


ENGLISH_FREQ = "etaoinshrdlcumwfgypbvkjxqz"
TRIGRAMS: dict[str, float] = {}


def build_trigrams() -> None:
    """Letter-trigram log-probabilities from an English text that is NOT the control text
    (the Secreta Alberti, early-modern English, from the same repository) — the textbook way to score a
    candidate key for a simple substitution cipher."""
    import math
    with zipfile.ZipFile(DATA / "meaningful.zip") as z:
        t = z.read("texts/Historical - English - Technical - Secreta Alberti.txt").decode("utf-8", errors="ignore")
    t = re.sub(r"[^a-z ]", " ", t.lower())
    t = re.sub(r" +", " ", t)
    from collections import Counter
    c = Counter(t[i:i + 3] for i in range(len(t) - 2))
    total = sum(c.values())
    TRIGRAMS.update({k: math.log10(v / total) for k, v in c.items()})
    TRIGRAMS["_floor"] = math.log10(0.01 / total)


def lm_score(types: list[tuple[str, int]], key: dict[str, str]) -> float:
    fl = TRIGRAMS["_floor"]
    tot = 0.0
    for w, n in types:
        d = " " + "".join(key[c] for c in w) + " "
        tot += n * sum(TRIGRAMS.get(d[i:i + 3], fl) for i in range(len(d) - 2))
    return tot


def climb(train: list[str], voc: Vocab, anagram: bool, rng: random.Random,
          strict: bool = False) -> tuple[dict, float]:
    """Hill-climb a key. strict=True: a proper simple-substitution key (one symbol → one distinct letter),
    started from frequency order and searched by swapping two letters — how a code-breaker attacks a simple
    cipher. strict=False (the freedoms): many symbols may share a letter, random start, single-letter moves."""
    from collections import Counter
    types = list(Counter(train).items())
    sym_freq = Counter(c for w in train for c in w)
    symbols = [s for s, _ in sym_freq.most_common()]
    best_key, best = None, float("-inf")      # letter-trigram scores are negative log-probabilities
    restarts = RESTARTS * 3 if strict else RESTARTS
    for r in range(restarts):
        if strict:
            letters = list(ENGLISH_FREQ)
            if r:                                              # later restarts: perturb the frequency start
                for _ in range(3 + r):
                    i, j = rng.randrange(len(letters)), rng.randrange(len(letters))
                    letters[i], letters[j] = letters[j], letters[i]
            key = {s: letters[i] if i < len(letters) else "z" for i, s in enumerate(symbols)}
        else:
            key = {s: rng.choice("etaoinshrdlu") for s in symbols}
        cur = lm_score(types, key) if strict else score(types, key, voc, anagram)
        for _ in range(ITERS):
            if strict:
                a, b = rng.sample(symbols, 2)
                key[a], key[b] = key[b], key[a]
                new = lm_score(types, key)
                if new >= cur:
                    cur = new
                else:
                    key[a], key[b] = key[b], key[a]
            else:
                s = rng.choice(symbols); old = key[s]; key[s] = rng.choice(LETTERS)
                new = score(types, key, voc, anagram)
                if new >= cur:
                    cur = new
                else:
                    key[s] = old
        if cur > best:
            best, best_key = cur, dict(key)
    if strict:   # report the strict key's dictionary-word rate, like every other setting
        return best_key, score(types, best_key, voc, anagram) / len(train)
    return best_key, best / len(train)


def rate(words: list[str], key: dict, voc: Vocab, anagram: bool) -> float:
    from collections import Counter
    k = {c: key.get(c, "z") for w in words for c in w}
    return score(list(Counter(words).items()), k, voc, anagram) / max(1, len(words))


def decode_line(words: list[str], key: dict, voc: Vocab, anagram: bool) -> str:
    out = []
    for w in words:
        d = "".join(key.get(c, "?") for c in w)
        if d in voc.exact:
            out.append(d)
        elif anagram:
            sig = "".join(sorted(d))
            match = next((x for x in voc._by_sig.get(sig, [])), None) if hasattr(voc, "_by_sig") else None
            out.append(match.upper() if match else f"·{d}·")
        else:
            out.append(f"·{d}·")
    return " ".join(out)


# ------------------------------------------------------------------ run
def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--vocab", choices=["big", "kjv"], default="big",
                    help="big = /usr/share/dict (~100k words); kjv = only words in the KJV New Testament (~10k)")
    ap.add_argument("--tag", default="", help="suffix for output files (robustness runs)")
    a = ap.parse_args()
    globals()["SEED"] = a.seed
    rng = random.Random(a.seed)
    la = load_latin_vocab()
    build_trigrams()
    if a.vocab == "big":
        en = load_english_vocab()
    else:
        with zipfile.ZipFile(DATA / "meaningful.zip") as z:
            en = {w for w in re.sub(r"[^a-z\s]", " ", z.read("texts/Historical - English - Literary - NT (KJV).txt")
                  .decode("utf-8", errors="ignore").lower()).split() if len(w) >= 2 or w in ("a", "i")}
    vocabs = {"F0 strict": (Vocab([en]), False), "F1 anagram": (Vocab([en]), True),
              "F2 two langs": (Vocab([en, la]), False), "F3 both": (Vocab([en, la]), True)}
    for v, _ in vocabs.values():
        v._by_sig = {}
        # sorted: when several dictionary words are anagrams of a decoded word, show the alphabetically first one.
        # (Before 2026-11-23 this iterated a set, so the DISPLAYED spelling followed Python's hash order and could
        # change between runs; every count was, and is, independent of it.)
        for w in sorted(v.exact):
            v._by_sig.setdefault("".join(sorted(w)), []).append(w)

    texts = {
        "VOYNICH": load_voynich()[:MAX_WORDS],
        "GIBBERISH": encipher(load_gibberish()[:MAX_WORDS], random.Random(SEED + 1)),
        "CONTROL+ (enciphered English)": encipher(load_english()[:MAX_WORDS], random.Random(SEED + 2)),
    }
    # English word-pair set for the "reads as language" measure (from a different English text than the
    # control, so the control is not scored against itself): the KJV New Testament.
    with zipfile.ZipFile(DATA / "meaningful.zip") as z:
        kjv = re.sub(r"[^a-z\s]", " ", z.read("texts/Historical - English - Literary - NT (KJV).txt")
                     .decode("utf-8", errors="ignore").lower()).split()
    pairs = set(zip(kjv, kjv[1:]))
    results, samples = {}, []
    for name, words in texts.items():
        pages = [words[i:i + PAGE_WORDS] for i in range(0, len(words), PAGE_WORDS)]
        train = [w for p in pages[0::2] for w in p]            # odd pages build the key
        test = [w for p in pages[1::2] for w in p]             # even pages test it
        results[name] = {"words": len(words), "train_words": len(train), "test_words": len(test),
                         "mean_word_length": round(sum(map(len, words)) / len(words), 2),
                         "distinct_word_types": len(set(words)),
                         "top10_share": round(sum(c for _, c in __import__("collections").Counter(words).most_common(10)) / len(words), 3)}
        for fname, (voc, anag) in vocabs.items():
            key, tr = climb(train, voc, anag, random.Random(rng.random()), strict=(fname == "F0 strict"))
            te = rate(test, key, voc, anag)
            dec = ["".join(key.get(c, "?") for c in w) for w in test]
            pair_rate = sum((a, b) in pairs for a, b in zip(dec, dec[1:])) / max(1, len(dec) - 1)
            results[name][fname] = {"train_hit_rate": round(tr, 3), "test_hit_rate": round(te, 3),
                                    "letters_used_by_key": len(set(key.values())),
                                    "test_english_word_pairs": round(pair_rate, 3),
                                    "key": key}
            print(f"{name:32s} {fname:12s} train {tr:6.1%}  test {te:6.1%}  letters {len(set(key.values())):2d}"
                  f"  word-pairs {pair_rate:6.1%}", flush=True)
            if fname in ("F0 strict", "F3 both"):
                line = test[:14]
                samples.append((name, fname, decode_line(line, key, voc, anag)))
    tag = f"_{a.tag}" if a.tag else ""
    (OUT / f"results{tag}.json").write_text(json.dumps({"seed": SEED, "page_words": PAGE_WORDS,
                                                   "iters": ITERS, "restarts": RESTARTS,
                                                   "results": results}, indent=2), encoding="utf-8")
    with open(OUT / f"sample-lines{tag}.md", "w", encoding="utf-8") as f:
        f.write("# Sample decodings (first 14 words of the TEST half, key fixed on TRAIN)\n\n"
                "Lower-case = an exact dictionary word · UPPER-CASE = a dictionary word only after "
                "rearranging letters · ·dots· = no word found\n\n")
        for n, fr, line in samples:
            f.write(f"**{n} · {fr}**  \n{line}\n\n")
    print(f"wrote results{tag}.json, sample-lines{tag}.md (seed {a.seed}, vocab {a.vocab})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
