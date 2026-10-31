import type { HTMLAttributes } from "react";
import { BookOpenCheck } from "lucide-react";

export const PRODUCT_NAME = "QLearn";
export const PRODUCT_NAME_ZH = "全学 · 智能学习空间";

interface BrandMarkProps extends HTMLAttributes<HTMLSpanElement> {
  size?: number;
}

/** QLearn-owned wordmark primitives. Kept presentation-only so
 * upstream DeepTutor assets and runtime contracts remain untouched. */
export function BrandMark({
  size = 24,
  className = "",
  style,
  ...props
}: BrandMarkProps) {
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center rounded-[9px] bg-[var(--foreground)] text-[var(--background)] shadow-[var(--q-shadow-quiet)] ${className}`}
      style={{ width: size, height: size, ...style }}
      {...props}
    >
      <BookOpenCheck size={size * 0.56} strokeWidth={1.8} />
    </span>
  );
}

interface BrandLockupProps extends HTMLAttributes<HTMLSpanElement> {
  tagline?: string;
  markSize?: number;
}

export function BrandLockup({
  tagline,
  markSize = 24,
  className = "",
  ...props
}: BrandLockupProps) {
  return (
    <span
      className={`inline-flex min-w-0 items-center gap-2 ${className}`}
      {...props}
    >
      <BrandMark size={markSize} />
      <span className="min-w-0 leading-none">
        <span className="block truncate font-sans text-[13.5px] font-semibold tracking-[-0.025em] text-[var(--foreground)]">
          {PRODUCT_NAME_ZH}
        </span>
        <span className="mt-1 block truncate text-[9px] font-medium tracking-[0.075em] text-[var(--muted-foreground)]">
          {tagline ? `${PRODUCT_NAME} · ${tagline}` : PRODUCT_NAME}
        </span>
      </span>
    </span>
  );
}
