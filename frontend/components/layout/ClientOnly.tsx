"use client";
import { useEffect, useState } from "react";
import Loader from "@/components/loading/Loader";

export default function ClientOnlyLayout({ children }: { children: React.ReactNode }) {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => setIsClient(true), []);

  if (!isClient) return <Loader />;
  return <>{children}</>;
}
