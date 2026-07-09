"""Commit the identity-lock calibration as a REAL artifact (not prose): run the actual
qwen3-vl consistency_score over committed OSS images and record the numbers + URLs."""
import io
import json
import pathlib

from config import settings
from services import oss_client, vision_client


def main() -> None:
    assert not settings.use_mock, "Refusing: need real Qwen for a real calibration."
    snap = json.loads(pathlib.Path("database/snapshot.json").read_text(encoding="utf-8"))
    chars = {c["name"]: c for c in snap["characters"]}
    pepe_portrait = chars["Pepe"]["image_url"]
    other_name = next(n for n in ("Kiki", "Momo", "Bex", "Nina") if n in chars)
    other_portrait = chars[other_name]["image_url"]

    # two Pepe keyframes from two different APPROVED episodes (a rejected take's thumbnail
    # may be dominated by another character, which is exactly what the gate should catch —
    # but for a clean calibration we compare on-model, published frames).
    pepe_eps = [e for e in snap["episodes"]
                if "Pepe" in (e.get("characters_used") or []) and e.get("thumbnail_url")
                and e.get("status") == "published" and e.get("qa_status") == "approved"]

    def best_consistency(e: dict) -> float:
        return max((t.get("consistency") or 0.0) for t in (e.get("takes") or [{}])) if e.get("takes") else 0.0

    # most on-model published keyframe first (highest stored consistency) as the reference
    pepe_eps.sort(key=best_consistency, reverse=True)
    kf_a = pepe_eps[0]["thumbnail_url"]
    kf_b = next((e["thumbnail_url"] for e in pepe_eps[1:]
                 if e["thumbnail_url"] != kf_a), pepe_eps[0]["thumbnail_url"])

    results = [
        {"comparison": "Pepe keyframe vs. Pepe canonical portrait (MATCH — the production gate)",
         "image_1": kf_a, "image_2": pepe_portrait,
         "score": vision_client.consistency_score(kf_a, pepe_portrait)},
        {"comparison": f"Pepe keyframe vs. {other_name}'s portrait (MISMATCH — gate rejects off-model)",
         "image_1": kf_a, "image_2": other_portrait,
         "score": vision_client.consistency_score(kf_a, other_portrait)},
        {"comparison": "Pepe keyframe vs. Pepe keyframe, two different episodes (cross-episode consistency)",
         "image_1": kf_a, "image_2": kf_b,
         "score": vision_client.consistency_score(kf_a, kf_b)},
    ]
    for r in results:
        r["score"] = round(float(r["score"]), 3)
        print(f"{r['score']:.3f}  {r['comparison']}", flush=True)

    out = {
        "model": settings.vision_model,
        "method": ("backend/services/vision_client.py::consistency_score() — qwen3-vl scores "
                   "0.0-1.0 how well the character in image 1 matches image 2 (species, colors, "
                   "distinctive features). These are REAL scores over committed OSS images, not prose."),
        "identity_min_gate": settings.identity_min,
        "results": results,
    }
    pathlib.Path("../docs/deploy_proof/identity_calibration.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("saved -> docs/deploy_proof/identity_calibration.json", flush=True)


if __name__ == "__main__":
    main()
