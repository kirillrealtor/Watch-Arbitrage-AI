import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ChronoArb",
  description: "B2B dealer acquisition intelligence platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <main>{children}</main>
      </body>
    </html>
  );
}
