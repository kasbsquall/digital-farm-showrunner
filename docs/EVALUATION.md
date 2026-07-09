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

## The loop firing on live infrastructure

The accuracy eval above isolates the QA *judgment*. Separately, the full loop has been run
**end-to-end on real Alibaba Cloud generation** (real keyframes, i2v clips, Qwen3-VL vision,
blended cost), exercising both outcomes:

- **A real 3-attempt regeneration loop.** A deliberately hard gag — "the mud oozes off
  Pepe's squished-flat pancake body", a deformation i2v can't render — was rejected on all
  three takes; on each rejection the Director received the vision-grounded `qa_notes` and
  regenerated (attempt 2's note asked to recast the sheep as the goat and change the action).
  Identity-lock held Pepe on-model across all three takes (consistency **0.8**), the blended
  meter totaled **$0.84** over 3 real video generations, and because QA was never satisfied
  the loop published the **best take as a draft** — the fail-safe that stops unverified
  footage going live. Regeneration + feedback + budget + safe-fallback, all on real infra.
- **A real approved episode.** A 3-shot multi-shot episode was **approved on the first take**
  (consistency **0.9**, blended cost **$0.86**) and is committed to `snapshot.json`
  (published) — the convergence outcome, on real infra.
- **A real *unattended* run — the autonomy claim, demonstrated.** The scheduler
  (`scheduler.run_once`) produced **3 episodes with no per-episode human trigger** (rotating
  idea bank): 2 auto-published on a passing QA verdict (~$0.30 each) and 1 held back as a
  **draft** after QA rejected it on a real retake ($0.57) — total **$1.18**. Full evidence
  (real timestamps ~7–12 min apart, per-episode receipts, QA verdicts) is committed to
  [`deploy_proof/scheduler_run.json`](deploy_proof/scheduler_run.json). This is the
  "runs a channel by itself" claim shown end-to-end, not just wired.

**Honest finding on recovery.** Across many real runs, the loop's behavior on live infra is
bimodal: an achievable gag is approved on take 1, and a gag the video model can't cast/stage
correctly is rejected on *every* take and shipped as a **draft** — it rarely reject-*then*-
approves in a single run. That is expected: the Director's feedback is text, and the i2v
endpoint takes no reference conditioning, so a corrective note can't *force* the generator
on-model (the same limitation identity-lock scores rather than fixes). The loop's real value
on live infra is therefore the **fail-safe** — bounded cost, best-take selection, and "nothing
publishes unwatched" — not guaranteed self-repair. We surface this rather than cherry-pick a
lucky recovery.

## Identity-lock — a second measured gate

Character consistency is also measured, not just asserted. With `IDENTITY_CHECK` enabled,
a `qwen3-vl-plus` pass (`backend/services/vision_client.py::consistency_score()`) scores
each generated keyframe's character against its canonical reference portrait, `0.0–1.0`,
stored per take as `consistency`. Because the `qwen-image` endpoint accepts no reference
image, identity consistency is enforced by *scoring* the result (vision), not by
conditioning the image generator.

On real Alibaba Cloud generation it calibrates cleanly. The score is a *stochastic*
`qwen3-vl` judgment (≈±0.1 across calls), but it separates on-model from off-model
unambiguously. A committed real run over committed OSS images lives in
[`deploy_proof/identity_calibration.json`](deploy_proof/identity_calibration.json):

| Comparison | Score | What it shows |
|---|---|---|
| Pepe keyframe vs. Pepe portrait (match) | **0.8–0.9** | the production gate: on-model |
| Pepe keyframe vs. a *different* character's portrait (mismatch) | **0.0** | the gate cleanly rejects off-model |
| Pepe keyframe vs. Pepe keyframe, **two different episodes** | **0.9–1.0** | cross-episode consistency (shown in the demo) |

(These are not the same comparison — don't conflate the portrait gate with cross-episode drift.)

## Honest caveats

- 14 labeled cases is a smoke-scale eval, not a benchmark; the descriptions are curated to
  probe clear pass/fail and two borderlines.
- Vision descriptions in *this fixture* are hand-written to isolate the *QA judgment*.
  End-to-end, the descriptions come from Qwen3-VL on the real clip — see "The loop firing on
  live infrastructure" above for real runs (a real 3-attempt regeneration loop and a real
  approved episode). The `rejected → rejected → approved` episode seeded in `snapshot.json`
  is a *mock-mode* illustration of the take-history shape, not a real-infra run.
- Next step: scale the fixture to ~50 cases with real Qwen3-VL descriptions and report a
  precision/recall curve across the QA confidence threshold.
