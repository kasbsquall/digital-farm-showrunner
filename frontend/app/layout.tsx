import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MUCKFLIX · The Digital Farm Showrunner",
  description: "Micro-dramas de granja en arcilla generados por un pipeline de 4 agentes de IA.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
