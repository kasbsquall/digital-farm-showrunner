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

export function CinemaFeed({
  episodes,
  chars,
}: {
  episodes: Episode[];
  chars: Record<string, string | null>;
}) {
  const [selId, setSelId] = useState<number | null>(episodes[0]?.id ?? null);
  const [playing, setPlaying] = useState(false);

  if (episodes.length === 0)
    return <p className="empty">Aún no hay episodios — produce el primero en el Estudio ↑</p>;

  const sel = episodes.find((e) => e.id === selId) ?? episodes[0];
  const approved = sel.qa_status === "approved";
  const selTitle = sel.title ?? sel.event ?? `Episodio ${sel.id}`;

  function pick(id: number) {
    setSelId(id);
    setPlaying(false);
  }

  return (
    <div className="cinema">
      <div className="stage-wrap">
        <div
          className="screen"
          role="button"
          tabIndex={0}
          aria-label={`Reproducir: ${selTitle}`}
          onClick={() => sel.video_url && setPlaying(true)}
          onKeyDown={activateOnKey(() => sel.video_url && setPlaying(true))}
        >
          {playing && sel.video_url ? (
            <video
              key={sel.id}
              src={sel.video_url}
              poster={ossThumb(sel.thumbnail_url, 1280)}
              controls
              autoPlay
            />
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
              {approved ? "✓ Aprobado por QA" : "Borrador"}
            </span>
          </div>
          <h3>{selTitle}</h3>
          {sel.description && <p>{sel.description}</p>}
          <div className="cast-mini">
            {(sel.characters_used ?? []).map((n) =>
              chars[n] ? <img key={n} src={ossThumb(chars[n], 64)} alt={n} title={n} /> : null
            )}
          </div>
        </div>
      </div>

      <div className="playlist">
        {episodes.map((ep) => {
          const t = ep.title ?? ep.event ?? `Episodio ${ep.id}`;
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
