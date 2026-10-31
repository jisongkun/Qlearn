"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowUpRight,
  BookOpenText,
  History,
  Lightbulb,
  ListChecks,
  NotebookTabs,
  Presentation,
  Telescope,
} from "lucide-react";
import { useTranslation } from "react-i18next";

const STARTERS = [
  {
    title: "Explain a concept",
    description: "Build intuition first, then connect it to the formal idea.",
    prompt: "Explain this concept from intuition to formal definition: ",
    capability: "chat",
    icon: Lightbulb,
  },
  {
    title: "Solve a hard problem",
    description: "Break the solution into steps and check the reasoning.",
    prompt: "Help me solve this step by step and verify each key step: ",
    capability: "deep_solve",
    icon: ListChecks,
  },
  {
    title: "Research a topic",
    description: "Find reliable material and turn it into a clear report.",
    prompt: "Research this topic and give me a structured report with sources: ",
    capability: "deep_research",
    icon: Telescope,
  },
  {
    title: "Create a visualization",
    description: "Use a diagram, chart, or animation to make it concrete.",
    prompt: "Create a visualization that helps me understand: ",
    capability: "visualize",
    icon: Presentation,
  },
] as const;

const COMPANION_ACTIONS = [
  {
    href: "/space/chat-history",
    title: "Continue learning",
    description: "Resume a previous conversation.",
    icon: History,
    placement:
      "right-0 top-[12%] sm:right-[2%] lg:-right-1 lg:top-[15%]",
  },
  {
    href: "/knowledge-bases",
    title: "Knowledge Center",
    description: "Learn from your saved materials.",
    icon: BookOpenText,
    placement: "left-0 top-[48%] sm:left-[2%] lg:-left-2",
  },
  {
    href: "/notebooks",
    title: "My Notebooks",
    description: "Review your notebook records.",
    icon: NotebookTabs,
    placement:
      "bottom-[7%] right-[2%] sm:right-[5%] lg:bottom-[10%] lg:right-0",
  },
] as const;

export default function WelcomeCanvas({
  greeting,
  onSelectStarter,
}: {
  greeting: string;
  onSelectStarter: (prompt: string, capability: string) => void;
}) {
  const { t } = useTranslation();
  const reduceMotion = useReducedMotion();
  const enter = (delay: number, x = 0) => ({
    initial: reduceMotion ? false : { opacity: 0, x, y: x ? 0 : 14 },
    animate: { opacity: 1, x: 0, y: 0 },
    transition: reduceMotion
      ? { duration: 0 }
      : { duration: 0.48, delay, ease: [0.16, 1, 0.3, 1] as const },
  });

  return (
    <div className="min-h-0 w-full flex-1 overflow-hidden px-4 py-4 sm:px-6 lg:px-8">
      <div className="mx-auto grid h-full min-h-0 w-full max-w-[1120px] items-start gap-6 lg:grid-cols-12 lg:gap-8 lg:pt-8 xl:gap-10">
        <section className="relative z-10 flex flex-col justify-center py-2 lg:col-span-6">
          <motion.p
            {...enter(0)}
            className="mb-3 text-[10.5px] font-semibold tracking-[0.15em] text-[var(--primary)]"
          >
            {t("QLearn · Your intelligent learning space")}
          </motion.p>

          <motion.h1
            {...enter(0.05)}
            className="max-w-[580px] text-[clamp(2.25rem,4.1vw,3.3rem)] font-semibold leading-[1.01] tracking-[-0.055em] text-[var(--foreground)]"
          >
            {greeting}
          </motion.h1>

          <motion.p
            {...enter(0.1)}
            className="mt-3.5 max-w-[500px] text-[13px] leading-6 text-[var(--muted-foreground)] sm:text-[14px]"
          >
            {t("Start with a question, a file, or where you left off.")}
          </motion.p>

          <div className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-2 [@media(max-height:500px)]:hidden">
            {STARTERS.map((starter, index) => {
              const Icon = starter.icon;
              return (
                <motion.button
                  key={starter.title}
                  type="button"
                  {...enter(0.18 + index * 0.055)}
                  onClick={() =>
                    onSelectStarter(t(starter.prompt), starter.capability)
                  }
                  className="group flex min-h-[76px] items-start gap-2.5 rounded-[16px] border border-[var(--border)] bg-[color-mix(in_srgb,var(--card)_86%,transparent)] px-3.5 py-3 text-left shadow-[var(--q-shadow-quiet)] backdrop-blur-xl transition-[border-color,background-color,box-shadow,transform] duration-[var(--q-motion-fast)] hover:-translate-y-0.5 hover:border-[color-mix(in_srgb,var(--primary)_44%,var(--border))] hover:bg-[var(--card)] hover:shadow-[var(--q-shadow-card)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] motion-reduce:transform-none"
                >
                  <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-[12px] bg-[var(--accent)] text-[var(--primary)] transition-transform duration-[var(--q-motion-fast)] group-hover:scale-105 motion-reduce:transform-none">
                    <Icon size={17} strokeWidth={1.7} aria-hidden />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2 text-[13.5px] font-semibold leading-snug text-[var(--foreground)]">
                      {t(starter.title)}
                      <ArrowUpRight
                        size={14}
                        strokeWidth={1.7}
                        aria-hidden
                        className="shrink-0 text-[var(--muted-foreground)] transition-[color,transform] duration-[var(--q-motion-fast)] group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-[var(--primary)] motion-reduce:transform-none"
                      />
                    </span>
                    <span className="mt-1 block text-[11.5px] leading-relaxed text-[var(--muted-foreground)]">
                      {t(starter.description)}
                    </span>
                  </span>
                </motion.button>
              );
            })}
          </div>
        </section>

        <motion.section
          {...enter(0.12, 18)}
          className="relative hidden min-h-[420px] overflow-hidden lg:col-span-6 lg:block xl:min-h-[460px]"
          aria-label={t("QLearn learning companion")}
        >
          <motion.div
            className="absolute inset-[7%] flex items-center justify-center overflow-hidden rounded-[32px] border border-transparent bg-white sm:inset-[5%] dark:border-white/10 dark:shadow-[0_24px_80px_-36px_rgba(0,0,0,0.88)]"
          >
            <video
              className="h-full w-full select-none object-contain mix-blend-multiply"
              src="/qlearn/hero-robot.mp4"
              poster="/qlearn/hero-robot-poster.jpg"
              autoPlay={!reduceMotion}
              loop
              muted
              playsInline
              preload="auto"
              controls={false}
              aria-hidden="true"
            />
          </motion.div>

          {COMPANION_ACTIONS.map((action, index) => {
            const Icon = action.icon;
            return (
              <motion.div
                key={action.href}
                {...enter(0.34 + index * 0.09, index === 1 ? -12 : 12)}
                className={`absolute z-10 ${action.placement}`}
              >
                <motion.div>
                  <Link
                    href={action.href}
                    className="group flex min-w-[164px] items-center gap-2.5 rounded-[18px] border border-white/80 bg-white/[0.78] px-3 py-2.5 text-left shadow-[0_16px_36px_-24px_rgba(15,23,42,0.55),inset_0_1px_0_rgba(255,255,255,0.94)] backdrop-blur-2xl transition-[background-color,border-color,box-shadow,transform] duration-[var(--q-motion-fast)] hover:-translate-y-0.5 hover:border-[color-mix(in_srgb,var(--primary)_35%,white)] hover:bg-white/[0.92] hover:shadow-[0_20px_44px_-24px_rgba(15,23,42,0.62),inset_0_1px_0_rgba(255,255,255,0.96)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] motion-reduce:transform-none"
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[11px] bg-[var(--primary)] text-[var(--primary-foreground)] shadow-sm">
                      <Icon size={15} strokeWidth={1.8} aria-hidden />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-[12px] font-semibold leading-tight text-[#171717]">
                        {t(action.title)}
                      </span>
                      <span className="mt-0.5 block max-w-[138px] truncate text-[9.5px] leading-tight text-[#6b7280]">
                        {t(action.description)}
                      </span>
                    </span>
                  </Link>
                </motion.div>
              </motion.div>
            );
          })}
        </motion.section>
      </div>
    </div>
  );
}
