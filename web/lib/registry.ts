import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { parse } from "yaml";
import generated from "./generated-registry.json";
import type { Registry, RegistrySurface } from "@/lib/surfaces";

export type { Registry, RegistrySurface } from "@/lib/surfaces";

/** The canonical registry in the monorepo (present in local dev and CI). */
const MONOREPO_REGISTRY_PATH = path.join(process.cwd(), "..", "config", "surfaces.yaml");

/**
 * Resolve the registry file. Precedence:
 * 1. `REGISTRY_PATH` (explicit override);
 * 2. the monorepo `config/surfaces.yaml` when present;
 * 3. the vendored `generated-registry.json`, so a `web/`-root deploy (Vercel) that
 *    cannot see `../config` still serves the canonical surface set.
 */
export function resolveRegistryPath(): string {
  if (process.env.REGISTRY_PATH) return process.env.REGISTRY_PATH;
  return existsSync(MONOREPO_REGISTRY_PATH) ? MONOREPO_REGISTRY_PATH : "";
}

/** True when the monorepo YAML is the active source; false for the vendored copy. */
export function usingVendoredRegistry(): boolean {
  return resolveRegistryPath() === "";
}

/**
 * Loads the canonical registry from config/surfaces.yaml. Server-only: it
 * performs filesystem access, so client components must import the projection
 * helpers from `@/lib/surfaces` instead.
 */
export function loadRegistry(filePath: string = resolveRegistryPath()): Registry {
  const raw = (
    filePath
      ? parse(readFileSync(filePath, "utf8"))
      : (generated as { version?: number; lastReviewed?: string; surfaces?: RegistrySurface[] })
  ) as {
    version?: number;
    last_reviewed?: string;
    lastReviewed?: string;
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
    lastReviewed: raw.last_reviewed ?? raw.lastReviewed ?? "unknown",
    surfaces,
  };
}
