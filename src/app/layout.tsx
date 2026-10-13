import type { Metadata } from "next";
import { Playfair_Display, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const serifFont = Playfair_Display({
  variable: "--font-serif",
  subsets: ["latin"],
  display: "swap",
  weight: ["500", "600", "700"],
});

const sansFont = Plus_Jakarta_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "ConfIA — CRM B2B & Inteligencia Comercial Ozonoterapia",
  description: "Plataforma de inteligencia comercial, pipeline outbound y posventa de ozonoterapia médica en Perú",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={`${serifFont.variable} ${sansFont.variable} h-full`}>
      <body className="min-h-full font-sans antialiased bg-[#F7F5F0] text-[#0F2F38]">
        {children}
      </body>
    </html>
  );
}
