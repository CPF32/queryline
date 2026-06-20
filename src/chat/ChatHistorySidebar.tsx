import Icon from "@/components/icons/Icon";
import AppBrand from "@/components/AppBrand";
import Tooltip from "@/components/Tooltip";
import UserMenu from "@/components/UserMenu";
import { useEffect, useMemo, useState } from "react";
import type { Conversation } from "@/types/contracts";

export type HistoryView = "active" | "archived";

type RailSelection = "new" | "history" | "archive";

export interface ChatHistorySidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  loading: boolean;
  view: HistoryView;
  onViewChange: (view: HistoryView) => void;
  onSelect: (conversationId: string) => void;
  onNewChat: () => void;
  onArchive: (conversationId: string) => void;
  onUnarchive: (conversationId: string) => void;
  onDelete: (conversationId: string) => void;
}

type DateGroup = "Today" | "Yesterday" | "Previous 7 days" | "Older";

const SIDEBAR_COLLAPSED_KEY = "text-to-sql-analytics.chat-sidebar-collapsed";

function getInitialCollapsed(): boolean {
  return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
}

function getDateGroup(iso: string): DateGroup {
  const date = new Date(iso);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);
  const startOfWeek = new Date(startOfToday);
  startOfWeek.setDate(startOfWeek.getDate() - 7);

  if (date >= startOfToday) return "Today";
  if (date >= startOfYesterday) return "Yesterday";
  if (date >= startOfWeek) return "Previous 7 days";
  return "Older";
}

const GROUP_ORDER: DateGroup[] = [
  "Today",
  "Yesterday",
  "Previous 7 days",
  "Older",
];

function groupConversations(conversations: Conversation[]) {
  const groups = new Map<DateGroup, Conversation[]>();
  for (const conversation of conversations) {
    const group = getDateGroup(conversation.updated_at);
    const list = groups.get(group) ?? [];
    list.push(conversation);
    groups.set(group, list);
  }
  return GROUP_ORDER.filter((group) => groups.has(group)).map((group) => ({
    group,
    items: groups.get(group)!,
  }));
}

export default function ChatHistorySidebar({
  conversations,
  activeConversationId,
  loading,
  view,
  onViewChange,
  onSelect,
  onNewChat,
  onArchive,
  onUnarchive,
  onDelete,
}: ChatHistorySidebarProps) {
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(getInitialCollapsed);
  const [selectedRail, setSelectedRail] = useState<RailSelection>("new");
  const grouped = useMemo(() => groupConversations(conversations), [conversations]);
  const isArchivedView = view === "archived";

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  useEffect(() => {
    if (activeConversationId) {
      setSelectedRail(view === "archived" ? "archive" : "history");
      return;
    }
    if (view === "archived") {
      setSelectedRail("archive");
      return;
    }
    setSelectedRail("new");
  }, [activeConversationId, view]);

  useEffect(() => {
    if (!menuOpenId) {
      return;
    }
    const close = () => setMenuOpenId(null);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [menuOpenId]);

  const handleViewSelect = (nextView: HistoryView) => {
    const nextRail: RailSelection = nextView === "archived" ? "archive" : "history";
    if (collapsed) {
      setCollapsed(false);
      setSelectedRail(nextRail);
      onViewChange(nextView);
      return;
    }
    if (view === nextView && selectedRail === nextRail) {
      setCollapsed(true);
      return;
    }
    setSelectedRail(nextRail);
    onViewChange(nextView);
  };

  const handleNewChatClick = () => {
    setSelectedRail("new");
    onNewChat();
  };

  const handleConversationSelect = (conversationId: string) => {
    setSelectedRail("history");
    onSelect(conversationId);
  };

  return (
    <aside className={`chat-sidebar${collapsed ? " chat-sidebar--collapsed" : ""}`}>
      <div className="chat-sidebar__header">
        <AppBrand to="/" collapseText textCollapsed={collapsed} />
      </div>

      <div className="chat-sidebar__main">
        <nav className="chat-sidebar__rail" aria-label="Chat navigation">
          <Tooltip label="New chat">
            <button
              type="button"
              className={`chat-sidebar__rail-btn${selectedRail === "new" ? " chat-sidebar__rail-btn--active" : ""}`}
              onClick={handleNewChatClick}
              aria-label="New chat"
              aria-pressed={selectedRail === "new"}
            >
              <Icon name="plus" size={18} />
            </button>
          </Tooltip>

          <Tooltip label="Chat history">
            <button
              type="button"
              className={`chat-sidebar__rail-btn${selectedRail === "history" ? " chat-sidebar__rail-btn--active" : ""}`}
              onClick={() => handleViewSelect("active")}
              aria-label="Chat history"
              aria-pressed={selectedRail === "history"}
            >
              <Icon name="chat" size={18} />
            </button>
          </Tooltip>

          <Tooltip label="Archived chats">
            <button
              type="button"
              className={`chat-sidebar__rail-btn${selectedRail === "archive" ? " chat-sidebar__rail-btn--active" : ""}`}
              onClick={() => handleViewSelect("archived")}
              aria-label="Archived chats"
              aria-pressed={selectedRail === "archive"}
            >
              <Icon name="archive" size={18} />
            </button>
          </Tooltip>

          <div className="chat-sidebar__rail-spacer" aria-hidden />

          <button
            type="button"
            className="chat-sidebar__rail-btn chat-sidebar__rail-btn--toggle"
            onClick={() => setCollapsed((current) => !current)}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
          >
            <Icon name={collapsed ? "chevron-right" : "chevron-left"} size={18} />
          </button>
        </nav>

        <div className="chat-sidebar__panel" aria-hidden={collapsed}>
          <div className="chat-sidebar__panel-header">
            <h2 className="chat-sidebar__panel-title">
              {isArchivedView ? "Archived" : "Chats"}
            </h2>
          </div>

          <div className="chat-history__body">
            {loading ? (
              <p className="chat-history__status">Loading…</p>
            ) : conversations.length === 0 ? (
              <p className="chat-history__status">
                {isArchivedView ? "No archived chats." : "No chats yet. Start a new conversation."}
              </p>
            ) : (
              grouped.map(({ group, items }) => (
                <section key={group} className="chat-history__group">
                  <h3 className="chat-history__group-label">{group}</h3>
                  <ul className="chat-history__list">
                    {items.map((conversation) => (
                      <li key={conversation.id} className="chat-history__row">
                        <button
                          type="button"
                          className={`chat-history__item ${
                            conversation.id === activeConversationId
                              ? "chat-history__item--active"
                              : ""
                          }`}
                          onClick={() => handleConversationSelect(conversation.id)}
                        >
                          <span className="chat-history__item-title">{conversation.title}</span>
                        </button>
                        <div className="chat-history__actions">
                          <button
                            type="button"
                            className="chat-history__menu-btn"
                            onClick={(event) => {
                              event.stopPropagation();
                              setMenuOpenId((current) =>
                                current === conversation.id ? null : conversation.id,
                              );
                            }}
                            aria-label="Conversation options"
                          >
                            <Icon name="more" size={16} />
                          </button>
                          {menuOpenId === conversation.id && (
                            <div
                              className="chat-history__menu"
                              onMouseDown={(event) => event.stopPropagation()}
                            >
                              {isArchivedView ? (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setMenuOpenId(null);
                                    onUnarchive(conversation.id);
                                  }}
                                >
                                  <Icon name="restore" size={14} />
                                  Restore
                                </button>
                              ) : (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setMenuOpenId(null);
                                    onArchive(conversation.id);
                                  }}
                                >
                                  <Icon name="archive" size={14} />
                                  Archive
                                </button>
                              )}
                              <button
                                type="button"
                                className="chat-history__menu-danger"
                                onClick={() => {
                                  setMenuOpenId(null);
                                  onDelete(conversation.id);
                                }}
                              >
                                <Icon name="trash" size={14} />
                                Delete
                              </button>
                            </div>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </section>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="chat-sidebar__footer">
        <UserMenu placement="sidebar" expanded={!collapsed} />
      </div>
    </aside>
  );
}
