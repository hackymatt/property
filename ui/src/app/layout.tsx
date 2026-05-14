import type { Metadata } from "next";
import ThemeRegistry from "./ThemeRegistry";
import QueryProvider from "./QueryProvider";
import "./globals.css";

export const metadata: Metadata = { title: "Property Admin" };

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <ThemeRegistry>{children}</ThemeRegistry>
        </QueryProvider>
      </body>
    </html>
  );
}
