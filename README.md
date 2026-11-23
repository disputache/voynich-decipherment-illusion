# The decipherment illusion, demonstrated

Code and results for the experiment shown in the Disputache film **"No, AI Did Not Decode the Voynich Manuscript"**
(chapter 4, *Why the words appear*).

**This is a demonstration, not a study.** One deliberately simple machine, run with the freedoms that Voynich
"decoders" have allowed themselves, on three texts of the same length:

| Input | What it is |
|---|---|
| **Manuscript** | 6,000 words of the Voynich manuscript (Currier B, EVA transliteration) |
| **Nonsense** | 6,000 words of meaningless text written by Gaskell & Bowern's volunteers, re-enciphered into unknown symbols |
| **Control** | 6,000 words of real English (a modern-English New Testament), disguised with a simple substitution cipher — proof the machine *can* read a real text when there is one |

The machine searches for the symbol → letter key that turns the most words into dictionary words, at four levels
of freedom:

| Setting | Freedom | Who worked this way |
|---|---|---|
| `F0 strict` | one fixed key; a word counts only if it **is** an English word | — |
| `F1 anagram` | letters may be rearranged inside each word | Newbold; Hauer & Kondrak |
| `F2 two langs` | a word counts if it is English **or** Latin | Cheshire (any Romance language), Bax |
| `F3 both` | anagram + two languages | — |

Every key is built on half the pages (**fit**) and scored on the other half (**unseen**).

## What it shows (seed 2026, `/usr/share/dict` English list) — `results/results_v4-seed2026-big.json`

| % real words on unseen pages | strict key | full freedom (`F3`) |
|---|---|---|
| Control (real English, enciphered) | **94.0** | 79.2 |
| Manuscript | **11.2** | **81.2** |
| Nonsense | **8.2** | **57.0** |

- With a strict key, the machine reads the real text almost perfectly and finds almost nothing in the other two.
- Given the decoders' freedom, it finds "words" in the manuscript and in nonsense written by people who meant nothing.
- **Testing on unseen pages does not catch it**: fit and unseen rates stay together (manuscript 81.5 / 81.2,
  nonsense 60.4 / 57.0).
- What does catch it: the words don't make sentences. On unseen pages, **65.4 %** of neighbouring words in the real
  text (strict key) form ordinary English pairs; in the manuscript's fully free "translation", **0.2 %**
  (`test_english_word_pairs`). And that free key uses only **7** letters of the alphabet (`letters_used_by_key`).

A second run with a different seed and a much smaller vocabulary (`results/results_v4-seed7-kjv.json`, KJV New
Testament words only) moves the exact numbers but not the pattern.

## What it does not show

Nothing here says whether the Voynich manuscript means anything. A small, repetitive vocabulary is easy to map onto
dictionary words, which is why the manuscript scores more "words" than the nonsense. The point is narrower: **a
free enough search finds words in almost anything, and the unseen-pages test alone won't tell you.**

## Reproduce

```bash
python3 fetch_data.py                                      # downloads the three datasets from the original repository (pinned, checksummed)
python3 illusion_demo.py --seed 2026 --vocab big --tag v4-seed2026-big
python3 illusion_demo.py --seed 7    --vocab kjv --tag v4-seed7-kjv
```

**Reproducibility, checked 2026-11-23:** running the code in this repository from scratch (fresh download, seed 2026,
`big` vocabulary) produces a results file **byte-identical** to `results/results_v4-seed2026-big.json`. One thing
can differ: in `sample-lines`, an UPPER-CASE word is one dictionary anagram of the decoded letters, and several may
exist (SAT / STA, TITANS / TAINTS, SITTER / TRISTE). The run shown in the film picked among them in Python's hash
order; this code now picks the alphabetically first, so a re-run may spell some of them differently. The counts never
depended on that choice. The sample lines in `results/` are the ones from the run shown in the film.

Python 3 standard library only. The `big` vocabulary is the system word list at `/usr/share/dict/american-english`
(Debian `wamerican` 2020.12.07-2, SHA-256 `9f513f1c…4066a32`); point `EN_DICT` at another list to try your own. A full
run takes a few minutes. Seeds are fixed: the same inputs reproduce the same numbers.

## Data and credits

The three datasets come from **Daniel E. Gaskell & Claire L. Bowern**, <https://github.com/danielgaskell/voynich>
(commit `d076a7d`), and are **not redistributed here** — `fetch_data.py` downloads them from the source. Their
gibberish transcriptions are © 2022 Gaskell & Bowern under a modified MIT licence that asks publications using them to
cite:

> Gaskell, Daniel E., Claire L. Bowern, 2022. Gibberish after all? Voynichese is statistically similar to
> human-produced samples of meaningless text. *CEUR Workshop Proceedings*, International Conference on the Voynich
> Manuscript 2022, University of Malta.

The Voynichese and meaningful-text datasets carry their own terms; see that repository's documentation.

The film's full source list is in [`SOURCES.md`](SOURCES.md).

## Licence

The code in this repository (`illusion_demo.py`, `fetch_data.py`) is MIT-licensed — see [`LICENSE`](LICENSE). The
results files are our outputs and may be reused with credit to Disputache.
