import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Toaster } from "sonner";
import { PageTranslator } from "@/components/page-translator";

import "./globals.css";

export const metadata: Metadata = {
  title: "PressRadar",
  description: "Turn media opportunities into timely, relevant pitches.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <PageTranslator>
          <a className="skip-link" href="#main-content">
            Skip to main content
          </a>
          {children}
        </PageTranslator>
        <Toaster
          richColors
          closeButton
          position="top-right"
          toastOptions={{
            closeButtonAriaLabel: "Dismiss notification",
          }}
        />
      </body>
    </html>
  );
}
