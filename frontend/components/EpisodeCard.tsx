"use client";

import { useState } from "react";
import { type Episode, ossThumb } from "@/lib/api";

export function EpisodeCard({ ep, chars }: { ep: Episode; chars: Record<string, string | null> }) {
  const [playing, setPlaying] = useState(false);
  const approved = ep.qa_status === "approved";
  const poster = ossThumb(ep.thumbnail_url, 720);

  return (
    <article className="card">
      <div className="media" onClick={() => ep.video_url && setPlaying(true)}>
        {ep.video_tool && <span className="tool-tag">{ep.video_tool}</span>}
        {playing && ep.video_url ? (
          <video src={ep.video_url} poster={poster} controls autoPlay />
        ) : (
          <>
            {poster ? (
              <img src={poster} alt={ep.title ?? ""} loading="lazy" />
            ) : (
              <video src={ep.video_url ?? undefined} preload="metadata" />
            )}
            {ep.video_url && (
              <div className="play">
                <span>▶</span>
              </div>
            )}
          </>
        )}
      </div>
      <div className="body">
        <h3>{ep.title ?? ep.event ?? `Episodio ${ep.id}`}</h3>
        {ep.description && <p className="desc">{ep.description}</p>}
        <div className="meta">
          <span className={`badge ${approved ? "ok" : "draft"}`}>
            {approved ? "APROBADO" : "BORRADOR"}
          </span>
          <div className="avatars">
            {(ep.characters_used ?? []).slice(0, 4).map((name) =>
              chars[name] ? (
                <img key={name} src={ossThumb(chars[name], 64)} alt={name} title={name} loading="lazy" />
              ) : null
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
