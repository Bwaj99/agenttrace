import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentTrace",
  description: "Local-first observability and replay for LLM agent pipelines.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
        {children}
      </body>
    </html>
  );
}
