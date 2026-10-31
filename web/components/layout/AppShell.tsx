"use client";

import { createContext, useContext } from "react";
import type { ReactNode } from "react";

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
 * The app frame shared by both route groups. The `sidebar` prop name stays
 * stable for upstream compatibility, but Qlearn presents that navigation as a
 * responsive top bar so content can use the full viewport width.
 */
export default function AppShell({ sidebar, children }: AppShellProps) {
  return (
    <SidebarDrawerContext.Provider value={null}>
      <div className="flex h-dvh flex-col overflow-hidden bg-[var(--background)]">
        {sidebar}
        <main className="qlearn-workspace flex min-w-0 flex-1 flex-col overflow-hidden">
          <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
        </main>
      </div>
    </SidebarDrawerContext.Provider>
  );
}
