"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTranslation } from "react-i18next";
import {
  ArrowUpRight,
  ClipboardList,
  GraduationCap,
  History,
  NotebookPen,
  Plug,
  Terminal,
  UserRound,
  Wand2,
  type LucideIcon,
} from "lucide-react";

import { SPACE_MCP_SURFACE, loadMcpSurface } from "@/components/mcp/surface";
import { getCliApps } from "@/lib/cli-apps-api";
import { listSessions } from "@/lib/session-api";
import { listNotebooks, listNotebookEntries } from "@/lib/notebook-api";
import { listPersonas } from "@/lib/personas-api";
import { listSkills } from "@/lib/skills-api";
import { fetchAllProgress } from "@/lib/learning-api";

/**
 * Learning Space dashboard — the hub of `/space`.
 *
 * Replaces the old "land directly in a section behind a side list" flow with a
 * single overview the learner enters from. Each tile is a real entry point that
 * shows a live count so the space feels inhabited, then routes into the full
 * section page (which keeps the mini-nav for lateral movement).
 */

type Lang = { zh: string; en: string };

type DashKey =
  | "chat_history"
  | "notebooks"
  | "question_bank"
  | "personas"
  | "skills"
  | "mcp"
  | "cli_apps"
  | "mastery_path";

interface DashboardItem {
  key: DashKey;
  href: string;
  icon: LucideIcon;
  title: Lang;
  blurb: Lang;
  /** Unit shown after the live count, e.g. "168 conversations". */
  unit: Lang;
  /** Icon-tile accent — full class strings so Tailwind keeps them. */
  tile: string;
  load: () => Promise<number>;
}

interface DashboardGroup {
  label: Lang;
  items: DashboardItem[];
}

const GROUPS: DashboardGroup[] = [
  {
    label: { zh: "对话与资料", en: "Conversations & Materials" },
    items: [
      {
        key: "chat_history",
        href: "/space/chat-history",
        icon: History,
        title: { zh: "聊天历史", en: "Chat History" },
        blurb: {
          zh: "回顾并继续此前的对话。",
          en: "Review and reopen previous conversations.",
        },
        unit: { zh: "段对话", en: "conversations" },
        tile: "bg-sky-500/10 text-sky-600 dark:text-sky-400",
        load: async () => (await listSessions(200, 0, { force: true })).length,
      },
      {
        key: "notebooks",
        href: "/space/notebooks",
        icon: NotebookPen,
        title: { zh: "笔记本", en: "Notebooks" },
        blurb: {
          zh: "整理来自对话、研究、智能写作等的产出。",
          en: "Organize saved outputs from chat, research, Co-Writer, and more.",
        },
        unit: { zh: "个笔记本", en: "notebooks" },
        tile: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
        load: async () => (await listNotebooks()).length,
      },
      {
        key: "question_bank",
        href: "/space/questions",
        icon: ClipboardList,
        title: { zh: "题库", en: "Question Bank" },
        blurb: {
          zh: "跨会话回顾和整理测验题目。",
          en: "Review and organize quiz questions across sessions.",
        },
        unit: { zh: "道题", en: "questions" },
        tile: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
        load: async () => (await listNotebookEntries({ limit: 1 })).total,
      },
    ],
  },
  {
    label: { zh: "个性化", en: "Personalization" },
    items: [
      {
        key: "mastery_path",
        href: "/space/learning",
        icon: GraduationCap,
        title: { zh: "精通之路", en: "Mastery Path" },
        blurb: {
          zh: "掌握式学习：硬门槛与间隔复习。",
          en: "Mastery-based learning: hard gate and spaced review.",
        },
        unit: { zh: "条路径", en: "paths" },
        tile: "bg-teal-500/10 text-teal-600 dark:text-teal-400",
        load: async () =>
          (await fetchAllProgress()).summaries.filter((s) => s.kp_count > 0)
            .length,
      },
      {
        key: "personas",
        href: "/space/personas",
        icon: UserRound,
        title: { zh: "Personas", en: "Personas" },
        blurb: {
          zh: "可在每轮对话中套用的行为预设。",
          en: "Behavior presets you can apply per chat turn.",
        },
        unit: { zh: "个预设", en: "personas" },
        tile: "bg-rose-500/10 text-rose-600 dark:text-rose-400",
        load: async () => (await listPersonas()).length,
      },
      {
        key: "skills",
        href: "/space/skills",
        icon: Wand2,
        title: { zh: "技能", en: "Skills" },
        blurb: {
          zh: "模型按需读取的能力手册。",
          en: "Capability playbooks the model reads on demand.",
        },
        unit: { zh: "个技能", en: "skills" },
        tile: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
        load: async () => (await listSkills()).length,
      },
      {
        key: "mcp",
        href: "/space/mcp",
        icon: Plug,
        title: { zh: "MCP 服务", en: "MCP Services" },
        blurb: {
          zh: "连接托管 MCP 服务，把它们的工具带进对话。",
          en: "Connect hosted MCP services and bring their tools into chat.",
        },
        unit: { zh: "个服务", en: "services" },
        tile: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
        // The account's own servers only: the deployment's are shown on the page
        // but are not this reader's to count.
        load: async () =>
          Object.keys((await loadMcpSurface(SPACE_MCP_SURFACE)).servers).length,
      },
      {
        key: "cli_apps",
        href: "/space/cli-apps",
        icon: Terminal,
        title: { zh: "CLI 应用", en: "CLI Apps" },
        blurb: {
          zh: "来自 CLI-Anything 目录的命令行工具，启用后对话可直接调用。",
          en: "Command-line tools from the CLI-Anything catalog, callable from chat.",
        },
        unit: { zh: "个应用", en: "apps" },
        tile: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
        // What this reader can actually use, not what the deployment installed:
        // an app they were not granted is visible on the page but is not theirs.
        load: async () =>
          (await getCliApps()).apps.filter((app) => app.granted && app.enabled)
            .length,
      },
    ],
  },
];

const ALL_ITEMS = GROUPS.flatMap((g) => g.items);

export default function SpaceDashboard() {
  const { i18n } = useTranslation();
  const zh = i18n.language?.toLowerCase().startsWith("zh");
  const tr = useCallback((l: Lang) => (zh ? l.zh : l.en), [zh]);

  const [counts, setCounts] = useState<Partial<Record<DashKey, number>>>({});

  useEffect(() => {
    let cancelled = false;
    // Each tile loads independently so one slow/failed endpoint never blanks
    // the whole dashboard.
    for (const item of ALL_ITEMS) {
      item
        .load()
        .then((n) => {
          if (!cancelled) setCounts((prev) => ({ ...prev, [item.key]: n }));
        })
        .catch(() => {
          /* leave undefined → tile just omits the count */
        });
    }
    return () => {
      cancelled = true;
    };
  }, []);

  const loadedValues = Object.values(counts).filter(
    (value): value is number => typeof value === "number",
  );
  const totalItems = loadedValues.reduce((sum, value) => sum + value, 0);

  return (
    <div className="pb-8">
      <header className="mb-10 grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-end">
        <div>
          <p className="mb-3 text-[10px] font-semibold tracking-[0.16em] text-[var(--primary)]">
            {tr({ zh: "全学 · 智能学习空间", en: "QLEARN · LEARNING SPACE" })}
          </p>
          <h1 className="max-w-3xl font-serif text-[clamp(2rem,5vw,2.75rem)] font-medium leading-[1.12] tracking-[-0.04em] text-[var(--foreground)]">
            {tr({
              zh: "你的学习，正在形成体系。",
              en: "Your learning is becoming a system.",
            })}
          </h1>
          <p className="mt-3 max-w-2xl text-[13px] leading-relaxed text-[var(--muted-foreground)] sm:text-[14px]">
            {tr({
              zh: "从对话、资料和练习中积累可持续的理解与进度。所有入口继续使用原有数据和权限。",
              en: "Turn conversations, materials, and practice into durable understanding and visible progress.",
            })}
          </p>
        </div>

        <div className="rounded-[18px] bg-[var(--foreground)] px-5 py-4 text-[var(--background)] shadow-[var(--q-shadow-card)]">
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] opacity-70">
            {tr({ zh: "学习空间概览", en: "Workspace overview" })}
          </p>
          <div className="mt-3 flex items-end justify-between gap-5">
            <div>
              <p className="text-[28px] font-semibold leading-none tabular-nums">
                {totalItems.toLocaleString()}
              </p>
              <p className="mt-1.5 text-[10px] opacity-65">
                {tr({ zh: "项内容已整理", en: "items organized" })}
              </p>
            </div>
            <div className="text-right">
              <p className="text-[18px] font-semibold leading-none tabular-nums">
                {loadedValues.length}/{ALL_ITEMS.length}
              </p>
              <p className="mt-1.5 text-[10px] opacity-65">
                {tr({ zh: "区域已同步", en: "areas synced" })}
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="space-y-10">
        {GROUPS.map((group) => (
          <section key={group.label.en}>
            <h2 className="mb-4 px-0.5 font-serif text-[18px] font-medium tracking-[-0.02em] text-[var(--foreground)]">
              {tr(group.label)}
            </h2>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {group.items.map((item) => (
                <DashboardCard
                  key={item.key}
                  item={item}
                  count={counts[item.key]}
                  tr={tr}
                />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function DashboardCard({
  item,
  count,
  tr,
}: {
  item: DashboardItem;
  count: number | undefined;
  tr: (l: Lang) => string;
}) {
  const Icon = item.icon;
  const loaded = count !== undefined;
  const formatted = useMemo(
    () => (loaded ? count.toLocaleString() : ""),
    [loaded, count],
  );

  return (
    <Link
      href={item.href}
      className="group relative flex min-h-[176px] flex-col rounded-[16px] border border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--q-shadow-quiet)] transition-[border-color,background-color,box-shadow,transform] duration-[var(--q-motion-base)] ease-[var(--q-ease-out)] hover:-translate-y-1 hover:border-[color-mix(in_srgb,var(--primary)_38%,var(--border))] hover:bg-[color-mix(in_srgb,var(--card)_96%,var(--primary))] hover:shadow-[var(--q-shadow-card)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] motion-reduce:transform-none"
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] transition-transform duration-[var(--q-motion-fast)] group-hover:scale-105 motion-reduce:transform-none ${item.tile}`}
        >
          <Icon size={18} strokeWidth={1.7} />
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-[14.5px] font-medium leading-tight tracking-tight text-[var(--foreground)]">
            {tr(item.title)}
          </h3>
          <div className="mt-1 flex items-baseline gap-1.5">
            {loaded ? (
              <>
                <span className="text-[20px] font-semibold leading-none tabular-nums text-[var(--foreground)]">
                  {formatted}
                </span>
                <span className="text-[12px] text-[var(--muted-foreground)]">
                  {tr(item.unit)}
                </span>
              </>
            ) : (
              <span className="my-[3px] h-3.5 w-12 animate-pulse rounded bg-[var(--muted)]" />
            )}
          </div>
        </div>
        <ArrowUpRight
          size={16}
          className="shrink-0 text-[var(--muted-foreground)]/40 transition-[color,transform] duration-[var(--q-motion-fast)] group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-[var(--primary)] motion-reduce:transform-none"
        />
      </div>
      <p className="mt-auto pt-5 text-[12.5px] leading-relaxed text-[var(--muted-foreground)]">
        {tr(item.blurb)}
      </p>
    </Link>
  );
}
