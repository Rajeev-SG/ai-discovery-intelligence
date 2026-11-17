import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SurfaceFieldGuide } from "@/components/surface-field-guide";
import { loadSurfaceGuides } from "@/lib/surface-guides";

type Props = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return [...loadSurfaceGuides().keys()].map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const guide = loadSurfaceGuides().get(slug);
  if (!guide) notFound();

  return { title: `${guide.name} — AI Discovery Intelligence`, description: guide.summary };
}

export default async function SurfacePage({ params }: Props) {
  const { slug } = await params;
  const guides = loadSurfaceGuides();
  const guide = guides.get(slug);
  if (!guide) notFound();

  return <SurfaceFieldGuide slug={slug} guide={guide} guides={guides} />;
}
