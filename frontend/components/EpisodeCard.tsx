import type { Episode } from "@/lib/api";

export function EpisodeCard({ ep }: { ep: Episode }) {
  const approved = ep.qa_status === "approved";
  return (
    <article className="card">
      <div className="media">
        {ep.video_tool && <span className="tool-tag">{ep.video_tool}</span>}
        {ep.video_url ? (
          <video src={ep.video_url} controls preload="metadata" />
        ) : (
          <div className="placeholder">{ep.thumbnail_hint ?? "Video en producción…"}</div>
        )}
      </div>
      <div className="body">
        <h3>{ep.title ?? ep.event ?? `Episodio ${ep.id}`}</h3>
        {ep.description && <p className="desc">{ep.description}</p>}
        <div className="meta">
          <span className={`badge ${approved ? "ok" : "draft"}`}>
            {approved ? "✓ Aprobado" : "borrador"}
          </span>
          {ep.characters_used?.map((c) => (
            <span key={c}>· {c}</span>
          ))}
        </div>
      </div>
    </article>
  );
}
