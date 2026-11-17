import { SurfaceDirectory } from "@/components/surface-field-guide";
import { loadSurfaceGuides } from "@/lib/surface-guides";

export default function Home() {
  return <SurfaceDirectory guides={loadSurfaceGuides()} />;
}
