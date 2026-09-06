/**
 * Root layout for the AgentTrace Next.js app.
 *
 * Planned (Phase 5): global styles (Tailwind), page shell/nav, and
 * shared metadata (title: "AgentTrace").
 */

// TODO(Phase 5): implement the root layout, import globals.css once
// Tailwind is wired up.
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
