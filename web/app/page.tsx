import { SurfaceFieldGuide } from "@/components/surface-field-guide";
import { loadSurfaceGuides } from "@/lib/surface-guides";

export default function Home() {
  const guides = loadSurfaceGuides();
  const guide = guides.get("chatgpt");
  if (!guide) throw new Error("Missing the ChatGPT surface guide");

  return <SurfaceFieldGuide slug="chatgpt" guide={guide} guides={guides} />;
}
