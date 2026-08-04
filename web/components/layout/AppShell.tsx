"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useDevice } from "@/hooks/useDevice";
import type { ReactNode } from "react";
import {
  BrandLockup,
  PRODUCT_NAME_ZH,
} from "@/components/common/BrandLockup";

/* Lets the sidebar dismiss the drawer after a nav click without every layout
   threading a callback down through WorkspaceSidebar/UtilitySidebar. Null on
   desktop and anywhere outside AppShell, so `drawer?.close()` is a no-op there
   rather than a crash. */
const SidebarDrawerContext = createContext<{ close: () => void } | null>(null);

export function useSidebarDrawer() {
  return useContext(SidebarDrawerContext);
}

interface AppShellProps {
  /** The route group's sidebar (workspace or utility). */
  sidebar: ReactNode;
  children: ReactNode;
}

/**
 * The app frame, shared by the (workspace) and (utility) route groups.
 *
 * Two layouts, picked by width:
 *
 *   >= 768px  sidebar and content are siblings in a flex row — unchanged from
 *             what this app has always rendered.
 *   <  768px  the sidebar leaves the flow entirely and becomes an overlay
 *             drawer behind a scrim, with a compact top bar owning the toggle.
 *             A 220px fixed column against a 390px viewport leaves 170px of
 *             content, and the overflow is clipped rather than scrollable.
 *
 * The split is expressed in CSS (`max-md:` / `md:`), not in `useDevice()`, so
 * the very first server-rendered paint is already correct on a phone. JS only
 * owns the part that is stateful anyway: whether the drawer is open.
 */
export default function AppShell({ sidebar, children }: AppShellProps) {
  const { t } = useTranslation();
  const pathname = usePathname();
  const { isMobile } = useDevice();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const close = useCallback(() => setDrawerOpen(false), []);

  // Any route change hands the screen back to the content. Compared during
  // render rather than in an effect (same pattern as SessionViewerPanel's
  // session reset) so the drawer never paints open over the new route.
  const [trackedPathname, setTrackedPathname] = useState(pathname);
  if (trackedPathname !== pathname) {
    setTrackedPathname(pathname);
    setDrawerOpen(false);
  }

  useEffect(() => {
    if (!drawerOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawerOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen]);

  return (
    <SidebarDrawerContext.Provider value={{ close }}>
      {/* dvh, not vh: iOS Safari's 100vh includes the retracted address bar, so
          a vh-sized shell pushes the composer under it. */}
      <div className="flex h-dvh overflow-hidden bg-[var(--background)]">
        {drawerOpen ? (
          <div
            onClick={close}
            aria-hidden
            className="fixed inset-0 z-40 bg-[var(--overlay)] backdrop-blur-[2px] md:hidden"
          />
        ) : null}

        {/* `inert` (not just translate-x) while closed: a drawer parked
            off-screen still holds ~20 focusable nav items, and without this
            Tab walks the user into a sidebar they cannot see. This is the
            half `max-md:` cannot express, hence useDevice(). */}
        <div
          inert={isMobile && !drawerOpen ? true : undefined}
          className={`max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-50 max-md:shadow-[var(--q-shadow-floating)] max-md:transition-transform max-md:duration-[var(--q-motion-base)] max-md:ease-[var(--q-ease-out)] ${
            drawerOpen ? "max-md:translate-x-0" : "max-md:-translate-x-full"
          }`}
        >
          {sidebar}
        </div>

        <main className="qlearn-workspace flex min-w-0 flex-1 flex-col overflow-hidden">
          <div className="flex h-14 shrink-0 items-center gap-2 border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--background)_88%,transparent)] px-3 backdrop-blur-xl md:hidden">
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              aria-label={t("Open navigation")}
              aria-expanded={drawerOpen}
              className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--q-radius-control)] text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)]/65 hover:text-[var(--foreground)]"
            >
              <Menu size={18} strokeWidth={1.7} />
            </button>
            <Link href="/" aria-label={PRODUCT_NAME_ZH}>
              <BrandLockup markSize={20} />
            </Link>
          </div>

          <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
        </main>
      </div>
    </SidebarDrawerContext.Provider>
  );
}
