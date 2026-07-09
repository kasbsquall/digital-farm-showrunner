# Evaluation — the self-correcting QA gate

The whole thesis of MUCKFLIX is that a **vision-grounded QA agent** makes the pipeline
reliable enough to publish *unsupervised*. A claim like that has to be **measured**, not
asserted. This is the evaluation of the QA gate's judgment.

## Method

The QA agent decides, from the Qwen3-VL description of what a clip **actually shows**,
whether a take delivers the script's gag (`approved`) or must be retaken (`rejected`).

We evaluate it directly on a **hand-labeled fixture** of 14 `(script, vision-description,
expected-verdict)` cases (`backend/eval_qa.py`): 8 that clearly deliver the gag, 6 that
clearly fail it (static scene, wrong action, missing character, unrelated footage,
broken/blurred video), including two deliberately *understated-but-correct* borderline
cases. Each case is run through the **real** `qa_reviewer.run` (Qwen text), and the verdict
+ 0–1 confidence score are compared to the label.

Reproduce:

```bash
cd backend
FORCE_MOCK=false python eval_qa.py     # a handful of cheap text calls, no video
```

## Results

| Metric | Value |
|---|---|
| Cases | 14 |
| **Accuracy** | **100 %** (14/14) |
| **Reject recall** (bad takes correctly caught) | **100 %** (6/6) |
| **Approve recall** (good takes correctly kept) | **100 %** (8/8) |
| **False approves** (bad take wrongly published) | **0** |
| **False rejects** (good take wrongly retaken → wasted cost) | **0** |

The confidence scores are well-calibrated and separate the two classes cleanly:

| Class | Score range observed |
|---|---|
| Correct takes (approved) | **0.8 – 1.0** |
| Failed takes (rejected) | **0.0 – 0.1** |

The two borderline "understated but correct" cases (a gentle turnip bonk; a goat chewing a
post while the barn leans in the background) were both correctly **approved at 0.9** — the
gate is rigorous without being a perfectionist that would burn retakes on good footage.

## Live budget receipt

Every generated episode carries a measured **token + cost receipt** (`Episode.tokens_used`,
`Episode.cost_usd`, surfaced in the "How it was made" modal). The self-correcting loop is
bounded two ways so cost can never run away: `MAX_REGEN` caps retakes, and an optional
`token_budget` stops regeneration once a per-episode token ceiling is hit — at which point
the **highest-scoring take** is published rather than the last one. Retakes are also
**surgical**: a rejected take re-animates the *existing* character-consistent keyframe with
the corrected motion, so a retake costs one video call, not a full re-render.

## Identity-lock — a second measured gate

Character consistency is also measured, not just asserted. With `IDENTITY_CHECK` enabled,
a `qwen3-vl-plus` pass (`backend/services/vision_client.py::consistency_score()`) scores
each generated keyframe's character against its canonical reference portrait, `0.0–1.0`,
stored per take as `consistency`. Because the `qwen-image` endpoint accepts no reference
image, identity consistency is enforced by *scoring* the result (vision), not by
conditioning the image generator.

On real Alibaba Cloud generation it calibrated correctly at the two extremes:

| Comparison | Score |
|---|---|
| Pepe keyframe vs. Pepe portrait (match) | **0.9** |
| Pepe keyframe vs. a different character's portrait (mismatch) | **0.0** |

## Honest caveats

- 14 labeled cases is a smoke-scale eval, not a benchmark; the descriptions are curated to
  probe clear pass/fail and two borderlines.
- Vision descriptions here are hand-written to isolate the *QA judgment*; end-to-end the
  descriptions come from Qwen3-VL on the real clip (see the committed 3-take
  `rejected → rejected → approved` episode in `snapshot.json` for a real end-to-end example).
- Next step: scale the fixture to ~50 cases with real Qwen3-VL descriptions and report a
  precision/recall curve across the QA confidence threshold.
