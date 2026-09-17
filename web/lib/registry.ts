import { readFileSync } from "node:fs";
import path from "node:path";
import { parse } from "yaml";
import type { Registry, RegistrySurface } from "@/lib/surfaces";
import generatedRegistry from "./generated-registry.json";

export type { Registry, RegistrySurface } from "@/lib/surfaces";

const REGISTRY_PATH = path.join(process.cwd(), "..", "config", "surfaces.yaml");

export function resolveRegistryPath(): string {
  return process.env.REGISTRY_PATH ?? REGISTRY_PATH;
}

function validate(raw: { version?: number; last_reviewed?: string; surfaces?: RegistrySurface[] }, source: string): Registry {
  const surfaces = raw.surfaces ?? [];
  if (!surfaces.length) throw new Error(`no surfaces found in ${source}`);
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

/**
 * Loads the canonical registry. Build-time (and serverless) environments use
 * the committed generated snapshot so no filesystem path is required; local
 * dev still re-reads config/surfaces.yaml when present.
 */
export function loadRegistry(filePath: string = resolveRegistryPath()): Registry {
  try {
    return validate(generatedRegistry as never, "generated snapshot");
  } catch {
    // Fall back to the live YAML when the generated snapshot is unusable.
    const raw = parse(readFileSync(filePath, "utf8"));
    return validate(raw, filePath);
  }
}
