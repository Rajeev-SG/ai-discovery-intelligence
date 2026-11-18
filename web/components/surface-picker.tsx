"use client";

import { useRouter } from "next/navigation";
import styles from "./surface-field-guide.module.css";

export type SurfaceChoice = { slug: string; name: string };

/**
 * Compact surface switcher for phones. The desktop pill row is a wall of chips
 * that fills the first screen at 390px, so below 640px it is replaced by one
 * native select: a single line, a real label, and the platform picker on touch.
 * Navigation happens on change (a client concern), and Next applies BASE_PATH.
 */
export function SurfacePicker({
  slug,
  published,
  comingSoon,
}: {
  slug?: string;
  published: SurfaceChoice[];
  comingSoon: SurfaceChoice[];
}) {
  const router = useRouter();

  return (
    <div className={styles.picker}>
      <label className={styles.pickerLabel} htmlFor="surface-picker">
        AI surface
      </label>
      <select
        id="surface-picker"
        className={styles.pickerSelect}
        value={slug ?? ""}
        onChange={(event) => {
          if (event.target.value) router.push(`/surfaces/${event.target.value}`);
        }}
      >
        <option value="">Choose a surface</option>
        <optgroup label="Field guides">
          {published.map(({ slug: id, name }) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </optgroup>
        {comingSoon.length > 0 && (
          <optgroup label="Coming soon">
            {comingSoon.map(({ slug: id, name }) => (
              <option key={id} value={`coming-soon:${id}`} disabled>
                {name}
              </option>
            ))}
          </optgroup>
        )}
      </select>
    </div>
  );
}
