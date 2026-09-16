import { readFileSync } from "node:fs";
import path from "node:path";
import { parse } from "yaml";
import type { Registry, RegistrySurface } from "@/lib/surfaces";

export type { Registry, RegistrySurface } from "@/lib/surfaces";

const REGISTRY_PATH = path.join(process.cwd(), "..", "config", "surfaces.yaml");

export function resolveRegistryPath(): string {
  return process.env.REGISTRY_PATH ?? REGISTRY_PATH;
}

/**
 * Loads the canonical registry from config/surfaces.yaml. Server-only: it
 * performs filesystem access, so client components must import the projection
 * helpers from `@/lib/surfaces` instead.
 */
export function loadRegistry(filePath: string = resolveRegistryPath()): Registry {
  const raw = parse(readFileSync(filePath, "utf8")) as {
    version?: number;
    last_reviewed?: string;
    surfaces?: RegistrySurface[];
  };
  const surfaces = raw.surfaces ?? [];
  if (!surfaces.length) throw new Error(`no surfaces found in ${filePath}`);
  for (const surface of surfaces) {
    for (const required of ["id", "vendor", "name", "family", "type", "tier"] as const) {
      if (!surface[required]) {
        throw new Error(`surface ${surface.id ?? "<unknown>"} missing required field ${required}`);
      }
    }
  }
  const ids = surfaces.map((s) => s.id);
  if (new Set(ids).size !== ids.length) throw new Error("duplicate surface ids in registry");
  return {
    version: raw.version ?? 1,
    lastReviewed: raw.last_reviewed ?? "unknown",
    surfaces,
  };
}
