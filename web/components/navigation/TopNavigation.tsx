"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { usePathname, useRouter } from "next/navigation";
import {
  BadgeCheck,
  ChevronDown,
  History,
  Lock,
  Menu,
  Plus,
  UserRound,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
  type ReactNode,
  type RefObject,
} from "react";
import { useTranslation } from "react-i18next";
import { useCapabilityAccess } from "@/components/access/CapabilityAccessContext";
import {
  BrandLockup,
  PRODUCT_NAME_ZH,
} from "@/components/common/BrandLockup";
import SessionList from "@/components/SessionList";
import type {
  SessionOrganizationPatch,
  SessionSummary,
} from "@/lib/session-api";
import type { StudyCourse } from "@/lib/courses-api";
import type { MasteryTopicLabel } from "@/lib/learning-api";
import type { ReadingCollectionLabel } from "@/lib/reading-workspace-api";
import {
  PRIMARY_NAV,
  SECONDARY_NAV,
  isNavActive,
  type NavEntry,
} from "@/components/sidebar/nav-entries";
import {
  mergeManualOrder,
  readSessionOrder,
  writeSessionOrder,
} from "@/lib/sidebar-layout";

const OrganizedSessionList = dynamic(
  () => import("@/components/courses/OrganizedSessionList"),
  { ssr: false },
);

// Qlearn keeps My Agents out of the primary bar by design, while preserving
// its route and all upstream data/transport behavior.
const TOP_PRIMARY_NAV = PRIMARY_NAV.filter((item) => item.href !== "/agents");

const PRODUCT_CREDITS = {
  author: "Songkun Ji",
  university: "北京信息科技大学",
  organization: "北京全学教育",
} as const;

interface TopNavigationProps {
  sessions?: SessionSummary[];
  activeSessionId?: string | null;
  liveSessionIds?: ReadonlySet<string>;
  loadingSessions?: boolean;
  showSessions?: boolean;
  onNewChat?: () => void;
  onSelectSession?: (sessionId: string) => void | Promise<void>;
  onRenameSession?: (sessionId: string, title: string) => void | Promise<void>;
  onDeleteSession?: (sessionId: string) => void | Promise<void>;
  courses?: StudyCourse[];
  masteryTopics?: MasteryTopicLabel[];
  readingCollections?: ReadingCollectionLabel[];
  onOrganizeSession?: (
    sessionId: string,
    patch: SessionOrganizationPatch,
  ) => void | Promise<void>;
  recycleBinSlot?: ReactNode;
  accountSlot?: ReactNode;
}

export function TopNavigation({
  sessions = [],
  activeSessionId = null,
  liveSessionIds,
  loadingSessions = false,
  showSessions = false,
  onNewChat,
  onSelectSession,
  onRenameSession,
  onDeleteSession,
  masteryTopics = [],
  readingCollections = [],
  onOrganizeSession,
  recycleBinSlot,
  accountSlot,
}: TopNavigationProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { t } = useTranslation();
  const { has } = useCapabilityAccess();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const mobileHistoryRef = useRef<HTMLDivElement>(null);
  const desktopHistoryRef = useRef<HTMLDivElement>(null);
  const mobileRecentsScrollRef = useRef<HTMLDivElement>(null);
  const desktopRecentsScrollRef = useRef<HTMLDivElement>(null);
  const accountRef = useRef<HTMLDivElement>(null);
  const [sessionOrder, setSessionOrder] = useState<string[]>([]);
  const sessionOrderRef = useRef<string[]>([]);
  const [trackedPathname, setTrackedPathname] = useState(pathname);

  if (trackedPathname !== pathname) {
    setTrackedPathname(pathname);
    setMobileOpen(false);
    setHistoryOpen(false);
    setAccountOpen(false);
  }

  useEffect(() => {
    const stored = readSessionOrder();
    sessionOrderRef.current = stored;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSessionOrder(stored);
  }, []);

  const handleReorderSessions = useCallback((nextIds: string[]) => {
    const merged = mergeManualOrder(sessionOrderRef.current, nextIds);
    sessionOrderRef.current = merged;
    setSessionOrder(merged);
    writeSessionOrder(merged);
  }, []);

  const handleResetSessionOrder = useCallback(() => {
    sessionOrderRef.current = [];
    setSessionOrder([]);
    writeSessionOrder([]);
  }, []);

  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (
        !mobileHistoryRef.current?.contains(target) &&
        !desktopHistoryRef.current?.contains(target)
      ) {
        setHistoryOpen(false);
      }
      if (!accountRef.current?.contains(target)) setAccountOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileOpen(false);
        setHistoryOpen(false);
        setAccountOpen(false);
      }
    };
    window.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  const navLocked = (item: NavEntry) =>
    item.requires ? !has(item.requires) : false;
  const lockedTooltip = t("Locked — contact your administrator to get access.");

  const startNewChat = (event?: ReactMouseEvent) => {
    if (
      event &&
      (event.metaKey || event.ctrlKey || event.shiftKey || event.button === 1)
    ) {
      return;
    }
    event?.preventDefault();
    setMobileOpen(false);
    setHistoryOpen(false);
    setAccountOpen(false);
    onNewChat?.();
    router.push("/chat");
  };

  const selectSession = (sessionId: string) => {
    setHistoryOpen(false);
    return onSelectSession?.(sessionId);
  };

  const visibleSessions = sessions.filter(
    (session) =>
      !session.preferences?.archived && !session.preferences?.parent_session_id,
  );

  const renderNavItem = (item: NavEntry, mobile = false) => {
    const active = isNavActive(pathname, item.href);
    const locked = navLocked(item);
    const Icon = item.icon;

    if (locked) {
      return (
        <div
          key={item.href}
          aria-disabled="true"
          title={lockedTooltip}
          className={
            mobile
              ? "flex cursor-not-allowed items-center gap-2.5 rounded-xl px-3 py-3 text-sm text-[var(--muted-foreground)]/45"
              : "flex h-9 cursor-not-allowed items-center gap-2 rounded-xl px-3 text-[13px] text-[var(--muted-foreground)]/45"
          }
        >
          <Icon size={16} strokeWidth={1.6} />
          <span>{t(item.label)}</span>
          <Lock size={11} className="ml-auto" />
        </div>
      );
    }

    return (
      <Link
        key={item.href}
        href={item.href}
        onClick={
          item.href === "/chat"
            ? startNewChat
            : mobile
              ? () => setMobileOpen(false)
              : undefined
        }
        aria-current={active ? "page" : undefined}
        className={
          mobile
            ? `flex items-center gap-2.5 rounded-xl px-3 py-3 text-sm transition-colors ${
                active
                  ? "bg-[var(--accent)] font-semibold text-[var(--primary)]"
                  : "text-[var(--foreground)]/80 hover:bg-[var(--muted)]/60"
              }`
            : `group relative flex h-9 items-center gap-2 rounded-xl px-3 text-[13px] transition-colors ${
                active
                  ? "bg-[var(--foreground)] font-semibold text-[var(--background)] shadow-[var(--q-shadow-quiet)]"
                  : "text-[var(--foreground)]/72 hover:bg-[var(--muted)]/70 hover:text-[var(--foreground)]"
              }`
        }
      >
        <Icon size={16} strokeWidth={active ? 1.9 : 1.6} />
        <span className={mobile ? "" : "max-xl:hidden"}>{t(item.label)}</span>
      </Link>
    );
  };

  const sessionControlsAvailable =
    showSessions &&
    onSelectSession &&
    onRenameSession &&
    onDeleteSession;

  const renderSessionHistory = (
    scrollRef: RefObject<HTMLDivElement | null>,
    className: string,
  ) => (
    <div ref={scrollRef} className={className}>
      {loadingSessions ? (
        <SessionList
          sessions={[]}
          activeSessionId={activeSessionId}
          loading
          onSelect={selectSession}
          onRename={onRenameSession!}
          onDelete={onDeleteSession!}
          compact
        />
      ) : onOrganizeSession ? (
        <OrganizedSessionList
          sessions={visibleSessions}
          courses={[]}
          masteryTopics={masteryTopics}
          readingCollections={readingCollections}
          activeSessionId={activeSessionId}
          liveSessionIds={liveSessionIds}
          manualOrder={sessionOrder}
          onReorder={handleReorderSessions}
          onResetOrder={handleResetSessionOrder}
          scrollRef={scrollRef}
          onSelect={selectSession}
          onRename={onRenameSession!}
          onDelete={onDeleteSession!}
          onOrganize={onOrganizeSession}
        />
      ) : (
        <SessionList
          sessions={visibleSessions}
          activeSessionId={activeSessionId}
          onSelect={selectSession}
          onRename={onRenameSession!}
          onDelete={onDeleteSession!}
          compact
        />
      )}
    </div>
  );

  return (
    <header className="relative z-30 shrink-0 border-b border-[var(--border)] bg-[color-mix(in_srgb,var(--background)_92%,transparent)] backdrop-blur-xl">
      <div className="flex h-16 items-center gap-3 px-4 sm:px-5">
        <Link
          href="/"
          aria-label={PRODUCT_NAME_ZH}
          className="mr-1 shrink-0 rounded-xl outline-none ring-offset-2 focus-visible:ring-2 focus-visible:ring-[var(--primary)]/35"
        >
          <BrandLockup markSize={24} />
        </Link>

        <nav
          aria-label={t("Main navigation")}
          className="hidden min-w-0 flex-1 items-center justify-center gap-1 md:flex"
        >
          {TOP_PRIMARY_NAV.map((item) => renderNavItem(item))}
        </nav>

        <div className="ml-auto hidden shrink-0 items-center gap-1 md:flex">
          {sessionControlsAvailable ? (
            <button
              type="button"
              onClick={() => startNewChat()}
              title={t("New chat")}
              aria-label={t("New chat")}
              className="flex h-9 items-center gap-2 rounded-xl px-3 text-[13px] font-medium text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)]/65 hover:text-[var(--foreground)]"
            >
              <Plus size={17} strokeWidth={1.8} />
              <span className="max-xl:hidden">{t("New chat")}</span>
            </button>
          ) : null}

          {sessionControlsAvailable ? (
            <div ref={desktopHistoryRef} className="relative">
              <button
                type="button"
                onClick={() => {
                  setAccountOpen(false);
                  setHistoryOpen((open) => !open);
                }}
                title={t("Recents")}
                aria-label={t("Recents")}
                aria-expanded={historyOpen}
                className={`flex h-9 items-center gap-2 rounded-xl px-3 text-[13px] transition-colors ${
                  historyOpen
                    ? "bg-[var(--accent)] font-semibold text-[var(--primary)]"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]/65 hover:text-[var(--foreground)]"
                }`}
              >
                <History size={17} strokeWidth={1.7} />
                <span className="max-xl:hidden">{t("Recents")}</span>
              </button>
              {historyOpen ? (
                <div className="absolute right-0 top-12 w-80 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-2 shadow-[var(--q-shadow-floating)]">
                  <div className="flex items-center justify-between px-2 pb-2 pt-1">
                    <span className="text-xs font-semibold text-[var(--foreground)]">
                      {t("Recents")}
                    </span>
                    <button
                      type="button"
                      onClick={() => startNewChat()}
                      className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-[var(--primary)] hover:bg-[var(--accent)]"
                    >
                      <Plus size={13} /> {t("New chat")}
                    </button>
                  </div>
                  {renderSessionHistory(
                    desktopRecentsScrollRef,
                    "max-h-[min(32rem,calc(100dvh-6rem))] overflow-y-auto",
                  )}
                  {recycleBinSlot ? (
                    <div className="border-t border-[var(--border)]/50 pt-1">
                      {recycleBinSlot}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          {SECONDARY_NAV.map((item) => {
            const active = isNavActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                title={t(item.label)}
                aria-label={t(item.label)}
                aria-current={active ? "page" : undefined}
                className={`flex h-9 w-9 items-center justify-center rounded-xl transition-colors ${
                  active
                    ? "bg-[var(--accent)] text-[var(--primary)]"
                    : "text-[var(--muted-foreground)] hover:bg-[var(--muted)]/65 hover:text-[var(--foreground)]"
                }`}
              >
                <Icon size={17} strokeWidth={active ? 1.9 : 1.6} />
              </Link>
            );
          })}

          <div ref={accountRef} className="relative ml-1">
            <button
              type="button"
              onClick={() => {
                setHistoryOpen(false);
                setAccountOpen((open) => !open);
              }}
              aria-label={t("Account")}
              aria-expanded={accountOpen}
              className="flex h-9 items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--card)] px-2.5 text-[var(--foreground)] shadow-[var(--q-shadow-quiet)] transition-colors hover:bg-[var(--muted)]/55"
            >
              <UserRound size={16} strokeWidth={1.7} />
              <ChevronDown size={12} strokeWidth={1.8} />
            </button>
            {accountOpen ? (
              <div className="absolute right-0 top-12 w-64 rounded-2xl border border-[var(--border)] bg-[var(--card)] p-2 shadow-[var(--q-shadow-floating)]">
                <div className="space-y-0.5" onClick={() => setAccountOpen(false)}>
                  {accountSlot}
                </div>
                <div className="mt-2 border-t border-[var(--border)] px-3 py-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-[var(--foreground)]">
                    <BadgeCheck size={15} className="text-[var(--primary)]" />
                    {PRODUCT_CREDITS.author}
                  </div>
                  <p className="mt-1 text-[10px] leading-relaxed text-[var(--muted-foreground)]">
                    {PRODUCT_CREDITS.university} · {PRODUCT_CREDITS.organization}
                  </p>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        {sessionControlsAvailable ? (
          <button
            type="button"
            onClick={() => startNewChat()}
            title={t("New chat")}
            aria-label={t("New chat")}
            className="ml-auto flex h-11 w-11 items-center justify-center rounded-xl text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)]/65 hover:text-[var(--foreground)] md:hidden"
          >
            <Plus size={18} strokeWidth={1.8} />
          </button>
        ) : null}

        {sessionControlsAvailable ? (
          <div ref={mobileHistoryRef} className="relative md:hidden">
            <button
              type="button"
              onClick={() => {
                setMobileOpen(false);
                setHistoryOpen((open) => !open);
              }}
              aria-label={t("Recents")}
              aria-expanded={historyOpen}
              className="flex h-11 w-11 items-center justify-center rounded-xl text-[var(--muted-foreground)] transition-colors hover:bg-[var(--muted)]/65 hover:text-[var(--foreground)]"
            >
              <History size={18} strokeWidth={1.7} />
            </button>
            {historyOpen ? (
              <div className="fixed inset-x-4 top-[4.5rem] w-auto rounded-2xl border border-[var(--border)] bg-[var(--card)] p-2 shadow-[var(--q-shadow-floating)]">
                <div className="flex items-center justify-between px-2 pb-2 pt-1">
                  <span className="text-xs font-semibold text-[var(--foreground)]">
                    {t("Recents")}
                  </span>
                  <button
                    type="button"
                    onClick={() => startNewChat()}
                    className="flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-[var(--primary)] hover:bg-[var(--accent)]"
                  >
                    <Plus size={13} /> {t("New chat")}
                  </button>
                </div>
                {renderSessionHistory(
                  mobileRecentsScrollRef,
                  "max-h-[60vh] overflow-y-auto",
                )}
                {recycleBinSlot ? (
                  <div className="border-t border-[var(--border)]/50 pt-1">
                    {recycleBinSlot}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        <button
          type="button"
          onClick={() => {
            setHistoryOpen(false);
            setMobileOpen((open) => !open);
          }}
          aria-label={t("Open navigation")}
          aria-expanded={mobileOpen}
          className="flex h-11 w-11 items-center justify-center rounded-xl text-[var(--foreground)] transition-colors hover:bg-[var(--muted)]/65 md:hidden"
        >
          {mobileOpen ? <X size={19} /> : <Menu size={19} />}
        </button>
      </div>

      {mobileOpen ? (
        <div className="absolute inset-x-0 top-16 max-h-[calc(100dvh-4rem)] overflow-y-auto border-b border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--q-shadow-floating)] md:hidden">
          <nav aria-label={t("Main navigation")} className="grid grid-cols-2 gap-1">
            {TOP_PRIMARY_NAV.map((item) => renderNavItem(item, true))}
          </nav>
          <div className="my-3 h-px bg-[var(--border)]" />
          <nav aria-label={t("Utility navigation")} className="grid grid-cols-2 gap-1">
            {SECONDARY_NAV.map((item) => renderNavItem(item, true))}
          </nav>
          <div className="mt-3 border-t border-[var(--border)] pt-3">
            <div className="space-y-0.5" onClick={() => setMobileOpen(false)}>
              {accountSlot}
            </div>
            <p className="px-3 pt-3 text-[10px] text-[var(--muted-foreground)]">
              {PRODUCT_CREDITS.author} · {PRODUCT_CREDITS.organization}
            </p>
          </div>
        </div>
      ) : null}
    </header>
  );
}
