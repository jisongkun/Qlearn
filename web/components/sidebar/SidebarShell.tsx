"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useAppShell } from "@/context/AppShellContext";
import {
  BadgeCheck,
  BookMarked,
  BrainCircuit,
  ChevronDown,
  Compass,
  Database,
  FilePenLine,
  GraduationCap,
  Lock,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  SlidersHorizontal,
  UsersRound,
  type LucideIcon,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import SessionList from "@/components/SessionList";
import { useSidebarDrawer } from "@/components/layout/AppShell";
import { useDevice } from "@/hooks/useDevice";
import type { SessionSummary } from "@/lib/session-api";
import { Tooltip } from "@/components/ui/Tooltip";
import { useCapabilityAccess } from "@/components/access/CapabilityAccessContext";
import type { Capability } from "@/lib/capability-routes";
import {
  BrandLockup,
  BrandMark,
  PRODUCT_NAME_ZH,
} from "@/components/common/BrandLockup";

interface NavEntry {
  href: string;
  label: string;
  icon: LucideIcon;
  tooltipKey?: string;
  /** Model capability this feature needs; locked when the user lacks it. */
  requires?: Capability;
}

const PRIMARY_NAV: NavEntry[] = [
  {
    href: "/home",
    label: "Home",
    icon: Compass,
    tooltipKey: "Home tooltip",
    requires: "llm",
  },
  {
    href: "/partners",
    label: "Partners",
    icon: UsersRound,
    tooltipKey: "Partners tooltip",
    requires: "llm",
  },
  {
    // My Agents is its own top-level feature (pulled out of the Learning
    // Space): connect a live local Claude Code / Codex to consult in chat,
    // and manage imported agent conversations. Ungated — managing connections
    // and imports needs no per-user model grant.
    href: "/agents",
    label: "My Agents",
    icon: Network,
    tooltipKey: "Agents tooltip",
  },
  {
    href: "/co-writer",
    label: "Co-Writer",
    icon: FilePenLine,
    tooltipKey: "Co-Writer tooltip",
    requires: "llm",
  },
  {
    href: "/book",
    label: "Book",
    icon: BookMarked,
    tooltipKey: "Book tooltip",
    requires: "llm",
  },
  {
    href: "/space",
    label: "Learning Space",
    icon: GraduationCap,
    tooltipKey: "Space tooltip",
  },
];

const SECONDARY_NAV: NavEntry[] = [
  {
    // Memory is its own top-level console (pulled out of the Learning Space):
    // a place to inspect and curate the tutor's long-term memory, not a daily
    // workspace. Never gated — memory has no per-user model requirement.
    href: "/memory",
    label: "Memory",
    icon: BrainCircuit,
    tooltipKey: "Memory tooltip",
  },
  {
    // Knowledge Center sits just above Settings: it's a console for managing
    // KBs and retrieval engines, not a daily workspace. Never gated — embedding
    // / search are shared admin infrastructure, no per-user model grant needed.
    href: "/knowledge",
    label: "Knowledge Center",
    icon: Database,
    tooltipKey: "Knowledge tooltip",
  },
  { href: "/settings", label: "Settings", icon: SlidersHorizontal },
];
const RECENTS_COLLAPSED_KEY = "deeptutor.sidebar.recentsCollapsed";
const PRODUCT_CREDITS = {
  author: "Songkun Ji",
  university: "北京信息科技大学",
  organization: "北京全学教育",
} as const;

interface SidebarShellProps {
  sessions?: SessionSummary[];
  activeSessionId?: string | null;
  loadingSessions?: boolean;
  showSessions?: boolean;
  /** Clicking the Chat nav item resets to a fresh session via this handler. */
  onNewChat?: () => void;
  onSelectSession?: (sessionId: string) => void | Promise<void>;
  onRenameSession?: (sessionId: string, title: string) => void | Promise<void>;
  onDeleteSession?: (sessionId: string) => void | Promise<void>;
  /**
   * Footer content rendered below the nav. Pass a render function to receive
   * the current ``collapsed`` state so footer items (e.g. Admin / Sign out) can
   * switch to their icon-only variant when the rail is collapsed.
   */
  footerSlot?: ReactNode | ((collapsed: boolean) => ReactNode);
}

export function SidebarShell({
  sessions = [],
  activeSessionId = null,
  loadingSessions = false,
  showSessions = false,
  onNewChat,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
  footerSlot,
}: SidebarShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useTranslation();
  const { has } = useCapabilityAccess();
  const { sidebarCollapsed, setSidebarCollapsed: setCollapsed } = useAppShell();
  const { isMobile } = useDevice();
  const drawer = useSidebarDrawer();

  // Inside the mobile drawer the icon-only rail is pointless — the panel is
  // already hidden when you don't want it, so it always opens fully expanded
  // regardless of the persisted desktop preference.
  const collapsed = sidebarCollapsed && !isMobile;

  /** Dismiss the drawer on nav clicks that actually navigate in-place. */
  const closeDrawerOnNav = (event: React.MouseEvent) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button === 1)
      return;
    drawer?.close();
  };

  const navLocked = (item: NavEntry) =>
    item.requires ? !has(item.requires) : false;
  const lockedTooltip = t("Locked — contact your administrator to get access.");
  const renderedFooter =
    typeof footerSlot === "function" ? footerSlot(collapsed) : footerSlot;
  const [recentsCollapsed, setRecentsCollapsed] = useState(false);

  // Hydrate Recents collapse from localStorage after first render to stay SSR-safe.
  useEffect(() => {
    if (typeof window === "undefined") return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRecentsCollapsed(
      window.localStorage.getItem(RECENTS_COLLAPSED_KEY) === "1",
    );
  }, []);

  const toggleRecents = () => {
    setRecentsCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(RECENTS_COLLAPSED_KEY, next ? "1" : "0");
      }
      return next;
    });
  };

  const handleHomeClick = (event: React.MouseEvent) => {
    // Always reset to a fresh session (mirrors the old "New Chat" affordance);
    // let modifier-clicks fall through to default Link behavior so middle-click
    // open-in-new-tab still works.
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button === 1)
      return;
    event.preventDefault();
    drawer?.close();
    onNewChat?.();
    router.push("/home");
  };

  /* ---- Collapsed state ---- */
  if (collapsed) {
    return (
      <aside className="group/sb relative flex h-dvh w-16 shrink-0 flex-col items-center border-r border-[var(--border)] bg-[var(--secondary)] py-3 transition-all duration-[var(--q-motion-base)]">
        {/* Header: logo + collapse toggle (toggle replaces logo on hover) */}
        <div className="relative mb-2 flex h-9 w-9 items-center justify-center">
          <Link
            href="/"
            aria-label={PRODUCT_NAME_ZH}
            className="flex items-center justify-center transition-opacity duration-150 group-hover/sb:opacity-0"
          >
            <BrandMark size={22} />
          </Link>
          <button
            onClick={() => setCollapsed(false)}
            className="absolute inset-0 flex items-center justify-center rounded-lg text-[var(--muted-foreground)] opacity-0 transition-all duration-150 hover:bg-[var(--background)]/60 hover:text-[var(--foreground)] group-hover/sb:opacity-100"
            aria-label={t("Expand sidebar")}
          >
            <PanelLeftOpen size={16} />
          </button>
        </div>

        {/* Primary nav */}
        <nav className="mt-1 flex w-full flex-col items-center gap-1 px-1.5">
          {PRIMARY_NAV.map((item) => {
            const active = pathname.startsWith(item.href);
            const locked = navLocked(item);
            const description = locked
              ? lockedTooltip
              : item.tooltipKey
                ? t(item.tooltipKey)
                : undefined;
            if (locked) {
              return (
                <Tooltip
                  key={item.href}
                  label={t(item.label)}
                  description={description}
                  side="right"
                >
                  <div
                    aria-label={`${t(item.label)} — ${lockedTooltip}`}
                    aria-disabled
                    className="relative flex h-9 w-9 cursor-not-allowed items-center justify-center rounded-xl text-[var(--muted-foreground)]/40"
                  >
                    <item.icon size={18} strokeWidth={1.6} />
                    <Lock
                      size={10}
                      strokeWidth={2}
                      className="absolute bottom-1 right-1 text-[var(--muted-foreground)]/70"
                    />
                  </div>
                </Tooltip>
              );
            }
            return (
              <Tooltip
                key={item.href}
                label={t(item.label)}
                description={description}
                side="right"
              >
                <Link
                  href={item.href}
                  onClick={item.href === "/home" ? handleHomeClick : undefined}
                  aria-label={t(item.label)}
                  className={`relative flex h-9 w-9 items-center justify-center rounded-xl transition-all duration-150 ${
                    active
                      ? "bg-[var(--accent)] text-[var(--primary)] shadow-[var(--q-shadow-quiet)]"
                      : "text-[var(--foreground)]/85 hover:bg-[var(--background)]/60 hover:text-[var(--foreground)]"
                  }`}
                >
                  <item.icon size={18} strokeWidth={active ? 2 : 1.6} />
                </Link>
              </Tooltip>
            );
          })}
        </nav>

        <div className="flex-1" />

        {/* Secondary nav + footer */}
        <div className="flex w-full flex-col items-center gap-1 px-1.5">
          <div className="my-1 h-px w-7 bg-[var(--border)]/40" />
          {SECONDARY_NAV.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                title={t(item.label) as string}
                className={`relative flex h-9 w-9 items-center justify-center rounded-xl transition-all duration-150 ${
                  active
                    ? "bg-[var(--accent)] text-[var(--primary)] shadow-[var(--q-shadow-quiet)]"
                    : "text-[var(--foreground)]/85 hover:bg-[var(--background)]/60 hover:text-[var(--foreground)]"
                }`}
              >
                <item.icon size={18} strokeWidth={active ? 2 : 1.6} />
              </Link>
            );
          })}
          {renderedFooter}
          <Tooltip
            label={PRODUCT_CREDITS.author}
            description={`${PRODUCT_CREDITS.university} · ${PRODUCT_CREDITS.organization}`}
            side="right"
          >
            <div
              aria-label={`${PRODUCT_CREDITS.author} · ${PRODUCT_CREDITS.university} · ${PRODUCT_CREDITS.organization}`}
              className="mt-1 flex h-9 w-9 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] shadow-[var(--q-shadow-quiet)]"
            >
              <BadgeCheck size={16} strokeWidth={1.7} />
            </div>
          </Tooltip>
        </div>
      </aside>
    );
  }

  /* ---- Expanded state ---- */
  return (
    <aside className="flex h-dvh w-[248px] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--secondary)] transition-all duration-[var(--q-motion-base)]">
      {/* Header: logo + collapse toggle */}
      <div className="flex h-16 items-center justify-between px-5">
        <Link
          href="/"
          aria-label={PRODUCT_NAME_ZH}
          className="group flex items-center"
        >
          <BrandLockup
            tagline={t("Intelligent Learning Space")}
            markSize={22}
            className="transition-transform duration-200 group-hover:scale-[1.02]"
          />
        </Link>
        {/* The rail is a desktop affordance; in the drawer the scrim and the
            top-bar toggle already own "make this go away". */}
        <button
          onClick={() => setCollapsed(true)}
          className="rounded-md p-1 text-[var(--muted-foreground)] transition-colors hover:text-[var(--foreground)] max-md:hidden"
          aria-label={t("Collapse sidebar")}
        >
          <PanelLeftClose size={15} />
        </button>
      </div>

      {/* Primary nav */}
      <nav className="px-3 pt-2">
        <div className="space-y-1">
          {PRIMARY_NAV.map((item) => {
            const active = pathname.startsWith(item.href);
            const locked = navLocked(item);
            if (locked) {
              return (
                <Tooltip
                  key={item.href}
                  label={t(item.label)}
                  description={lockedTooltip}
                  side="right"
                >
                  <div
                    aria-label={`${t(item.label)} — ${lockedTooltip}`}
                    aria-disabled
                    className="flex cursor-not-allowed items-center gap-2.5 rounded-[var(--q-radius-control)] px-3 py-2.5 text-[13.5px] text-[var(--muted-foreground)]/40"
                  >
                    <item.icon size={16} strokeWidth={1.5} />
                    <span>{t(item.label)}</span>
                    <Lock size={13} strokeWidth={1.8} className="ml-auto" />
                  </div>
                </Tooltip>
              );
            }
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={
                  item.href === "/home" ? handleHomeClick : closeDrawerOnNav
                }
                className={`flex items-center gap-2.5 rounded-[var(--q-radius-control)] px-3 py-2.5 text-[13.5px] transition-[background-color,color,transform] duration-[var(--q-motion-fast)] ${
                  active
                    ? "bg-[var(--accent)] font-semibold text-[var(--primary)] shadow-[var(--q-shadow-quiet)]"
                    : "text-[var(--foreground)]/82 hover:translate-x-0.5 hover:bg-[var(--background)]/70 hover:text-[var(--foreground)] motion-reduce:transform-none"
                }`}
              >
                <item.icon size={16} strokeWidth={active ? 1.9 : 1.5} />
                <span>{t(item.label)}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Chat history — its own region below the nav, takes remaining height */}
      {showSessions && onSelectSession && onRenameSession && onDeleteSession ? (
        <section
          className={`mt-5 flex min-h-0 flex-col ${
            recentsCollapsed ? "" : "flex-1"
          }`}
        >
          <button
            type="button"
            onClick={toggleRecents}
            className="group/recents mx-3 flex items-center justify-between rounded-md px-2 py-1 text-left text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--muted-foreground)]/70 transition-colors hover:bg-[var(--background)]/50 hover:text-[var(--muted-foreground)]"
            aria-expanded={!recentsCollapsed}
            aria-label={
              recentsCollapsed
                ? (t("Show recents") as string)
                : (t("Hide recents") as string)
            }
          >
            <span>{t("Recents")}</span>
            <ChevronDown
              size={13}
              strokeWidth={1.7}
              className={`transition-all duration-200 ${
                recentsCollapsed
                  ? "-rotate-90 opacity-60"
                  : "rotate-0 opacity-0 group-hover/recents:opacity-60"
              }`}
            />
          </button>
          {!recentsCollapsed && (
            <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-2 pt-1">
              <SessionList
                sessions={sessions}
                activeSessionId={activeSessionId}
                loading={loadingSessions}
                onSelect={(sessionId) => {
                  drawer?.close();
                  return onSelectSession(sessionId);
                }}
                onRename={onRenameSession}
                onDelete={onDeleteSession}
                compact
              />
            </div>
          )}
        </section>
      ) : null}

      {/* When recents is collapsed or unavailable, fill the gap above the footer. */}
      {(!showSessions ||
        !onSelectSession ||
        !onRenameSession ||
        !onDeleteSession ||
        recentsCollapsed) && <div className="flex-1" />}

      {/* Secondary nav + footer */}
      <div className="border-t border-[var(--border)] px-3 py-3">
        {SECONDARY_NAV.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={closeDrawerOnNav}
              className={`flex items-center gap-2.5 rounded-[var(--q-radius-control)] px-3 py-2 text-[13.5px] transition-colors ${
                active
                  ? "bg-[var(--accent)] font-semibold text-[var(--primary)]"
                  : "text-[var(--foreground)]/85 hover:bg-[var(--background)]/60 hover:text-[var(--foreground)]"
              }`}
            >
              <item.icon size={16} strokeWidth={active ? 1.9 : 1.5} />
              <span>{t(item.label)}</span>
            </Link>
          );
        })}
        {renderedFooter}
        <div className="mt-2 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2.5 shadow-[var(--q-shadow-quiet)]">
          <div className="flex items-center gap-2 text-[11px] font-semibold text-[var(--foreground)]">
            <BadgeCheck
              size={14}
              strokeWidth={1.8}
              className="text-[var(--primary)]"
            />
            <span>{PRODUCT_CREDITS.author}</span>
          </div>
          <p className="mt-1.5 text-[9.5px] leading-relaxed text-[var(--muted-foreground)]">
            {PRODUCT_CREDITS.university}
          </p>
          <p className="text-[9.5px] leading-relaxed text-[var(--muted-foreground)]">
            {PRODUCT_CREDITS.organization}
          </p>
        </div>
      </div>
    </aside>
  );
}
