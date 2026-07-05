export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Episode = {
  id: number;
  title: string | null;
  event: string | null;
  script: string | null;
  characters_used: string[] | null;
  video_prompt: string | null;
  video_tool: string | null;
  video_url: string | null;
  qa_status: string;
  qa_notes: string | null;
  qa_attempts: number | null;
  thumbnail_hint: string | null;
  description: string | null;
  status: string;
};

export async function getEpisodes(): Promise<Episode[]> {
  const res = await fetch(`${API}/episodes`, { cache: "no-store" });
  if (!res.ok) throw new Error("No se pudo cargar el feed");
  return res.json();
}

export async function generateEpisode(): Promise<Episode> {
  const res = await fetch(`${API}/episodes/generate`, { method: "POST" });
  if (!res.ok) throw new Error("Falló la generación del episodio");
  return res.json();
}
