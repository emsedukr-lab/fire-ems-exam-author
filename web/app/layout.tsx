import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Fire EMS Exam Author Console",
  description: "응급처치학개론 문항 분석과 오답 만다라트 생성을 위한 Next.js 운영 콘솔"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
