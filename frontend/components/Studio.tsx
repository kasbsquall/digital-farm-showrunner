"use client";

import { useEffect, useRef, useState } from "react";
import { streamEpisode } from "@/lib/api";

type Status = "idle" | "active" | "done" | "reject";

const STAGES = [
  { key: "scriptwriter", role: "Scriptwriter", tag: "qwen3.7 · text", img: "/agents/scriptwriter.png" },
  { key: "director", role: "Production Director", tag: "qwen3.7 · keyframe", img: "/agents/director.png" },
  { key: "video", role: "Keyframe → Video → Vision", tag: "qwen-image · happyhorse-i2v · qwen3-vl", img: "" },
  { key: "qa", role: "Quality Control", tag: "qwen3.7 · text", img: "/agents/qa.png" },
  { key: "packager", role: "Packager", tag: "qwen3.7 · publish", img: "/agents/packager.png" },
] as const;

type Data = {
  script?: { event: string; script: string };
  director?: { keyframe_prompt: string; motion_prompt: string; video_tool: string };
  video?: { video_url: string; video_description: string };
  qa?: { qa_status: string; qa_notes: string };
  pack?: { title: string; description: string; thumbnail_url: string };
};

export function Studio({ onDone }: { onDone: () => void }) {
  const [idea, setIdea] = useState("");
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<Record<string, Status>>({});
  const [data, setData] = useState<Data>({});
  const [regen, setRegen] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  // Close the SSE connection if the component unmounts mid-stream.
  useEffect(() => () => esRef.current?.close(), []);

  function setStage(key: string, s: Status) {
    setStatus((prev) => ({ ...prev, [key]: s }));
  }

  function start() {
    esRef.current?.close(); // never leave a previous stream open
    setRunning(true);
    setError(null);
    setRegen(0);
    setData({});
    setStatus({ scriptwriter: "active" });

    const es = streamEpisode(idea);
    esRef.current = es;

    // Ignore events from a stale connection (a newer run replaced this one).
    const on = (name: string, fn: (d: any) => void) =>
      es.addEventListener(name, (e) => {
        if (esRef.current !== es) return;
        fn(JSON.parse((e as MessageEvent).data));
      });

    on("scriptwriter", (d) => {
      setData((p) => ({ ...p, script: d.story }));
      setStage("scriptwriter", "done");
      setStage("director", "active");
    });
    on("director", (d) => {
      setData((p) => ({ ...p, director: d.direction }));
      setStage("director", "done");
      setStage("video", "active");
    });
    on("video", (d) => {
      setData((p) => ({ ...p, video: d }));
      setStage("video", "done");
      setStage("qa", "active");
    });
    on("qa", (d) => {
      const approved = d.qa?.qa_status === "approved";
      setData((p) => ({ ...p, qa: d.qa }));
      setStage("qa", approved ? "done" : "reject");
      if (approved) {
        setStage("packager", "active");
      } else {
        setRegen((r) => r + 1);
        setStage("director", "active");
      }
    });
    on("packager", (d) => {
      setData((p) => ({ ...p, pack: { ...d.pack, thumbnail_url: d.thumbnail_url } }));
      setStage("qa", "done");
      setStage("packager", "done");
    });
    on("done", () => {
      es.close();
      setRunning(false);
      onDone();
    });
    on("failed", (d) => {
      es.close();
      setRunning(false);
      setError(d.message ?? "Falló la generación");
    });
    es.onerror = () => {
      if (esRef.current !== es) return;
      es.close();
      setRunning(false);
      setError("Lost connection to the studio (is the backend running?).");
    };
  }

  return (
    <section className="studio">
      <div className="panel">
        <h3>The Studio</h3>
        <p className="hint">Type an idea, or leave it blank and let the agents improvise.</p>
        <div className="field">
          <label htmlFor="episode-idea">Episode idea (optional)</label>
          <textarea
            id="episode-idea"
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="e.g. Bruno starts a strike against the sunrise…"
            disabled={running}
          />
        </div>
        <button className="btn" onClick={start} disabled={running}>
          {running ? "● Rolling live…" : "🎬 Produce episode"}
        </button>
        {error && <p className="err">⚠ {error}</p>}
      </div>

      <div className="wizard">
        {STAGES.map((st, i) => {
          const s = status[st.key] ?? "idle";
          return (
            <div className="stage" key={st.key} data-state={s} data-n={i + 1}>
              <div className="role">
                {st.img && <img className="agent-av" src={st.img} alt="" />}
                {st.role} <span className="rtag">{st.tag}</span>
              </div>
              <StageBody k={st.key} data={data} regen={regen} />
            </div>
          );
        })}
      </div>
    </section>
  );
}

function StageBody({ k, data, regen }: { k: string; data: Data; regen: number }) {
  if (k === "scriptwriter" && data.script)
    return (
      <div className="out">
        <span className="k">Event</span>
        {data.script.event}
        <span className="k">Script</span>
        {data.script.script}
      </div>
    );
  if (k === "director" && data.director)
    return (
      <div className="out">
        <span className="k">Keyframe (seed image)</span>
        {data.director.keyframe_prompt}
        <span className="k">5-second action</span>
        {data.director.motion_prompt}
        {regen > 0 && <div className="regen">↻ regeneration #{regen}</div>}
      </div>
    );
  if (k === "video" && data.video)
    return (
      <div className="out">
        <span className="k">What the AI sees in the video</span>
        {data.video.video_description || "(video in demo mode)"}
        {data.video.video_url && (
          <video className="wizard-video" src={data.video.video_url} controls preload="metadata" />
        )}
      </div>
    );
  if (k === "qa" && data.qa)
    return (
      <div className="out">
        <span className="k">Verdict</span>
        {data.qa.qa_status === "approved" ? "✓ Approved" : "✗ Rejected"} — {data.qa.qa_notes}
      </div>
    );
  if (k === "packager" && data.pack)
    return (
      <div className="out">
        <span className="k">Title</span>
        {data.pack.title}
        {data.pack.thumbnail_url && (
          <img className="wizard-img" src={data.pack.thumbnail_url} alt="episode thumbnail" />
        )}
      </div>
    );
  return null;
}
