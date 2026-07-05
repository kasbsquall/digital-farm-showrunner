"use client";

import { useState, type KeyboardEvent } from "react";
import { type Episode, ossThumb } from "@/lib/api";

function activateOnKey(fn: () => void) {
  return (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fn();
    }
  };
}

function splitPrompt(vp: string | null): { keyframe: string; motion: string } {
  if (!vp) return { keyframe: "", motion: "" };
  const m = vp.split(/MOTION:/i);
  return {
    keyframe: (m[0] ?? "").replace(/KEYFRAME:/i, "").trim(),
    motion: (m[1] ?? "").trim(),
  };
}

function BTSModal({ ep, onClose }: { ep: Episode; onClose: () => void }) {
  const { keyframe, motion } = splitPrompt(ep.video_prompt);
  const approved = ep.qa_status === "approved";
  const steps = [
    { img: "/agents/scriptwriter.png", who: "Scriptwriter", model: "qwen3.7", body: (
      <><span className="k">Event</span>{ep.event}<span className="k">Script</span>{ep.script}</>
    ) },
    { img: "/agents/director.png", who: "Production Director", model: "qwen3.7", body: (
      <><span className="k">Keyframe (seed image)</span>{keyframe}<span className="k">5-second action</span>{motion}</>
    ) },
    { img: "/set/clapper.png", who: "Keyframe → Video → Vision", model: "qwen-image · happyhorse-i2v · qwen3-vl", body: (
      <><span className="k">What the AI actually sees</span>{ep.video_description || "—"}</>
    ) },
    { img: "/agents/qa.png", who: "Quality Control", model: "qwen3.7", body: (
      <><span className="k">Verdict</span>{approved ? "✓ Approved" : "✗ Rejected"} — {ep.qa_notes} <i>({ep.qa_attempts} attempt{ep.qa_attempts === 1 ? "" : "s"})</i></>
    ) },
    { img: "/agents/packager.png", who: "Packager", model: "qwen3.7", body: (
      <><span className="k">Title</span><b>{ep.title}</b><span className="k">Description</span>{ep.description}</>
    ) },
  ];
  return (
    <div className="modal-scrim" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="How it was made" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <span className="eyebrow">Behind the scenes</span>
            <h3>How it was made</h3>
          </div>
          <button className="modal-x" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <img className="modal-hero" src={ossThumb(ep.thumbnail_url, 900)} alt="" />
        <div className="bts-timeline">
          {steps.map((s, i) => (
            <div className="bts-step" key={i}>
              <div className="bts-avatar">
                {s.img ? <img src={s.img} alt="" /> : <span>🎬</span>}
                <span className="bts-n">{i + 1}</span>
              </div>
              <div className="bts-content">
                <div className="bts-name">{s.who} <span className="bts-model">{s.model}</span></div>
                <div className="bts-out">{s.body}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function CinemaFeed({
  episodes,
  chars,
}: {
  episodes: Episode[];
  chars: Record<string, string | null>;
}) {
  const [selId, setSelId] = useState<number | null>(episodes[0]?.id ?? null);
  const [playing, setPlaying] = useState(false);
  const [showBTS, setShowBTS] = useState(false);

  if (episodes.length === 0)
    return <p className="empty">No episodes yet — produce the first one in The Studio ↑</p>;

  const sel = episodes.find((e) => e.id === selId) ?? episodes[0];
  const approved = sel.qa_status === "approved";
  const selTitle = sel.title ?? sel.event ?? `Episode ${sel.id}`;

  function pick(id: number) {
    setSelId(id);
    setPlaying(false);
    setShowBTS(false);
  }

  async function share() {
    const url = sel.video_url ?? window.location.href;
    const text = `${selTitle} — a claymation farm drama made by AI on MUCKFLIX`;
    try {
      if (navigator.share) {
        await navigator.share({ title: "MUCKFLIX", text, url });
      } else {
        await navigator.clipboard.writeText(`${text} ${url}`);
        alert("Link copied to clipboard!");
      }
    } catch {
      /* user cancelled */
    }
  }

  return (
    <div className="cinema">
      <div className="stage-wrap">
        <div
          className="screen"
          role="button"
          tabIndex={0}
          aria-label={`Play: ${selTitle}`}
          onClick={() => sel.video_url && setPlaying(true)}
          onKeyDown={activateOnKey(() => sel.video_url && setPlaying(true))}
        >
          {playing && sel.video_url ? (
            <video key={sel.id} src={sel.video_url} poster={ossThumb(sel.thumbnail_url, 1280)} controls autoPlay />
          ) : (
            <>
              <img className="poster" src={ossThumb(sel.thumbnail_url, 1280)} alt={selTitle} />
              {sel.video_url && (
                <div className="bigplay">
                  <span>▶</span>
                </div>
              )}
            </>
          )}
        </div>
        <div className="stage-meta">
          <div className="toolrow">
            {sel.video_tool && <span className="tag">{sel.video_tool}</span>}
            <span className={`badge ${approved ? "ok" : "draft"}`}>
              {approved ? "✓ QA approved" : "Draft"}
            </span>
            <button className="bts-toggle" onClick={() => setShowBTS((v) => !v)}>
              {showBTS ? "Hide the making-of" : "🎬 How it was made"}
            </button>
          </div>
          <h3>{selTitle}</h3>
          <div className="byline">
            {sel.creator ? <span>Idea by <b>{sel.creator}</b></span> : <span>Auto-generated</span>}
            <button className="share-btn" onClick={share}>↗ Share</button>
          </div>
          {sel.description && <p>{sel.description}</p>}
          <div className="cast-mini">
            {(sel.characters_used ?? []).map((n) =>
              chars[n] ? <img key={n} src={ossThumb(chars[n], 64)} alt={n} title={n} /> : null
            )}
          </div>
        </div>
      </div>

      {showBTS && <BTSModal ep={sel} onClose={() => setShowBTS(false)} />}

      <div className="playlist">
        {episodes.map((ep) => {
          const t = ep.title ?? ep.event ?? `Episode ${ep.id}`;
          return (
            <div
              key={ep.id}
              className={`plitem ${ep.id === sel.id ? "active" : ""}`}
              role="button"
              tabIndex={0}
              aria-label={t}
              aria-current={ep.id === sel.id}
              onClick={() => pick(ep.id)}
              onKeyDown={activateOnKey(() => pick(ep.id))}
            >
              <img className="thumb" src={ossThumb(ep.thumbnail_url, 200)} alt={t} />
              <div className="pt">{t}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
