import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Discovery Intelligence",
  description: "A field guide for media buyers and brand marketers on where brands appear in AI answers, shopping recommendations and ads.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB">
      <body>
        <a className="skip-link" href="#content">Skip to content</a>
        <div className="page-shell">
          <main id="content">{children}</main>
        </div>
      </body>
    </html>
  );
}
