import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { SidebarShell } from "@/components/sidebar/SidebarShell";
import { TopNavigation } from "@/components/navigation/TopNavigation";

const fixture = vi.hoisted(() => ({ push: vi.fn(), close: vi.fn() }));

vi.mock("next/navigation", () => ({
  usePathname: () => "/co-writer",
  useRouter: () => ({ push: fixture.push }),
}));
vi.mock("next/image", () => ({ default: () => null }));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key, i18n: { language: "en" } }),
}));
vi.mock("@/context/AppShellContext", () => ({
  useAppShell: () => ({ sidebarCollapsed: false, setSidebarCollapsed: vi.fn() }),
}));
vi.mock("@/components/layout/AppShell", () => ({
  useSidebarDrawer: () => ({ close: fixture.close }),
}));
vi.mock("@/hooks/useDevice", () => ({
  useDevice: () => ({ isMobile: false }),
}));
vi.mock("@/components/sidebar/VersionBadge", () => ({
  VersionBadge: () => null,
}));
vi.mock("@/components/access/CapabilityAccessContext", () => ({
  useCapabilityAccess: () => ({ has: () => true }),
}));
vi.mock("@/vendor/thinking-orbs", () => ({
  ThinkingOrb: () => null,
}));

beforeEach(() => {
  fixture.push.mockClear();
  fixture.close.mockClear();
});

it("loads conversation history while navigation remains usable, then preserves session actions", async () => {
  const onSelect = vi.fn();
  const onRename = vi.fn();
  const onOrganize = vi.fn();
  const { container } = render(
    <SidebarShell
      showSessions
      sessions={[
        {
          id: "session-1",
          session_id: "session-1",
          title: "Retained session",
          created_at: 1,
          updated_at: 1,
          message_count: 1,
          last_message: "Hello",
        },
      ]}
      onSelectSession={onSelect}
      onRenameSession={onRename}
      onDeleteSession={vi.fn()}
      onOrganizeSession={onOrganize}
    />,
  );
  expect(container.querySelector('[aria-busy="true"]')).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Co-Writer" })).toHaveAttribute("href", "/co-writer");

  fireEvent.click(await screen.findByText("Retained session"));
  expect(onSelect).toHaveBeenCalledWith("session-1");
  expect(fixture.close).toHaveBeenCalled();
  expect(container.querySelector('[aria-busy="true"]')).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "Conversation actions" }));
  fireEvent.click(screen.getByRole("menuitem", { name: "Pin" }));
  expect(onOrganize).toHaveBeenCalledWith("session-1", { pinned: true });

  fireEvent.click(screen.getByRole("button", { name: "Conversation actions" }));
  fireEvent.click(screen.getByRole("menuitem", { name: "Rename chat" }));
  const input = screen.getByDisplayValue("Retained session");
  fireEvent.change(input, { target: { value: "Renamed session" } });
  await act(async () => {
    fireEvent.keyDown(input, { key: "Enter" });
  });
  expect(onRename).toHaveBeenCalledWith("session-1", "Renamed session");
});

it("keeps upstream session organization available from the Qlearn top navigation", async () => {
  const onNewChat = vi.fn();
  const onSelect = vi.fn();
  const onRename = vi.fn();
  const onOrganize = vi.fn();

  render(
    <TopNavigation
      showSessions
      sessions={[
        {
          id: "session-1",
          session_id: "session-1",
          title: "Retained session",
          created_at: 1,
          updated_at: 1,
          message_count: 1,
          last_message: "Hello",
        },
      ]}
      onNewChat={onNewChat}
      onSelectSession={onSelect}
      onRenameSession={onRename}
      onDeleteSession={vi.fn()}
      onOrganizeSession={onOrganize}
      recycleBinSlot={<div>Recycle bin</div>}
    />,
  );

  expect(screen.getAllByRole("link", { name: "Home" })[0]).toHaveAttribute(
    "href",
    "/chat",
  );
  fireEvent.click(screen.getAllByRole("button", { name: "New chat" })[0]);
  expect(onNewChat).toHaveBeenCalledOnce();
  expect(fixture.push).toHaveBeenCalledWith("/chat");

  fireEvent.click(screen.getAllByRole("button", { name: "Recents" })[0]);
  expect((await screen.findAllByText("Retained session")).length).toBeGreaterThan(0);
  expect(screen.getAllByText("Recycle bin").length).toBeGreaterThan(0);

  fireEvent.click(
    screen.getAllByRole("button", { name: "Conversation actions" })[0],
  );
  fireEvent.click(screen.getAllByRole("menuitem", { name: "Pin" })[0]);
  expect(onOrganize).toHaveBeenCalledWith("session-1", { pinned: true });
});
