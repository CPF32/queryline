import { Link } from "react-router-dom";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/auth/AuthContext";
import {
  appendConversationMessage,
  createConversation,
  deleteConversation,
  executeQuery,
  fetchActiveDataSources,
  fetchChartSpec,
  fetchQueryFeedback,
  generateSqlWithFallback,
  listConversationMessages,
  listConversations,
  logDiagnosticEvent,
  updateConversation,
} from "@/api/client";
import ChatComposer from "@/chat/ChatComposer";
import ChatHistorySidebar, { type HistoryView } from "@/chat/ChatHistorySidebar";
import ChatMessageList from "@/chat/ChatMessageList";
import Select from "@/components/Select";
import {
  buildChatError,
  mapApiErrorToChatError,
  maybeAmbiguousWarning,
} from "@/chat/errorMessages";
import type {
  AssistantChatMessage,
  ChatMessage,
  UserChatMessage,
} from "@/chat/types";
import { isAssistantMessage } from "@/chat/types";
import type {
  ChartSpec,
  Conversation,
  ConversationMessage,
  ConversationTurn,
  DataSource,
  QueryResult,
} from "@/types/contracts";

const SESSION_STORAGE_KEY = "text-to-sql-analytics.session-id";
const ACTIVE_CONVERSATION_KEY = "text-to-sql-analytics.active-conversation";

function createId(): string {
  return crypto.randomUUID();
}

function getOrCreateSessionId(): string {
  const existing = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) {
    return existing;
  }
  const sessionId = createId();
  sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  return sessionId;
}

function buildConversationHistory(messages: ChatMessage[]): ConversationTurn[] {
  return messages
    .filter((message) => {
      if (message.role === "user") {
        return true;
      }
      return (
        isAssistantMessage(message) &&
        message.stage === "complete" &&
        Boolean(message.explanation || message.sql)
      );
    })
    .map((message) => {
      if (message.role === "user") {
        return { role: "user", content: message.content };
      }
      const parts = [message.explanation, message.sql ? `SQL:\n${message.sql}` : ""]
        .filter(Boolean)
        .join("\n\n");
      return { role: "assistant", content: parts };
    });
}

function assistantPayload(message: AssistantChatMessage): Record<string, unknown> {
  return {
    question: message.question,
    stage: message.stage,
    sql: message.sql,
    explanation: message.explanation,
    tablesReferenced: message.tablesReferenced,
    confidence: message.confidence,
    queryResult: message.queryResult,
    chartSpec: message.chartSpec,
    queryLogId: message.queryLogId,
    feedbackRating: message.feedbackRating,
    error: message.error,
  };
}

function restoreAssistantMessage(
  stored: ConversationMessage,
): AssistantChatMessage | null {
  if (stored.role !== "assistant" || !stored.payload) {
    return null;
  }
  const payload = stored.payload;
  return {
    id: stored.id,
    role: "assistant",
    content: stored.content,
    question: String(payload.question ?? ""),
    stage: (payload.stage as AssistantChatMessage["stage"]) ?? "complete",
    sql: payload.sql as string | undefined,
    explanation: payload.explanation as string | undefined,
    tablesReferenced: payload.tablesReferenced as string[] | undefined,
    confidence: payload.confidence as AssistantChatMessage["confidence"],
    queryResult: payload.queryResult as QueryResult | undefined,
    chartSpec: (payload.chartSpec as ChartSpec | null | undefined) ?? null,
    queryLogId: payload.queryLogId as string | undefined,
    feedbackRating: payload.feedbackRating as AssistantChatMessage["feedbackRating"],
    error: payload.error as AssistantChatMessage["error"],
    createdAt: stored.created_at,
  };
}

function restoreMessages(stored: ConversationMessage[]): ChatMessage[] {
  const restored: ChatMessage[] = [];
  for (const message of stored) {
    if (message.role === "user") {
      restored.push({
        id: message.id,
        role: "user",
        content: message.content,
        createdAt: message.created_at,
      });
      continue;
    }
    const assistant = restoreAssistantMessage(message);
    if (assistant) {
      restored.push(assistant);
    }
  }
  return restored;
}

export default function ChatPage() {
  const { user } = useAuth();
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [selectedDataSourceId, setSelectedDataSourceId] = useState<string>("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyView, setHistoryView] = useState<HistoryView>("active");
  const sessionId = useMemo(() => getOrCreateSessionId(), []);
  const hasRestoredConversation = useRef(false);
  const selectedDataSource = useMemo(
    () => dataSources.find((source) => source.id === selectedDataSourceId),
    [dataSources, selectedDataSourceId],
  );

  const refreshConversations = useCallback(
    async (dataSourceId?: string, archived = historyView === "archived") => {
      if (!dataSourceId) {
        setConversations([]);
        return;
      }
      setHistoryLoading(true);
      try {
        const items = await listConversations({
          data_source_id: dataSourceId,
          archived,
          limit: 100,
        });
        setConversations(items);
      } finally {
        setHistoryLoading(false);
      }
    },
    [historyView],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadDataSources() {
      try {
        const sources = await fetchActiveDataSources();
        if (cancelled) {
          return;
        }
        setDataSources(sources);
        if (sources.length > 0) {
          setSelectedDataSourceId((current) => current || sources[0].id);
        }
      } catch (error) {
        if (!cancelled) {
          setLoadError(
            error instanceof Error
              ? error.message
              : "Failed to load data sources",
          );
        }
      }
    }

    void loadDataSources();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (selectedDataSourceId) {
      void refreshConversations(selectedDataSourceId);
    }
  }, [selectedDataSourceId, historyView, refreshConversations]);

  const loadConversation = useCallback(async (conversationId: string) => {
    if (conversationId === activeConversationId) {
      return;
    }
    const stored = await listConversationMessages(conversationId);
    const restored = restoreMessages(stored);

    const withFeedback = await Promise.all(
      restored.map(async (message) => {
        if (!isAssistantMessage(message) || !message.queryLogId) {
          return message;
        }
        try {
          const feedback = await fetchQueryFeedback(message.queryLogId);
          if (!feedback) {
            return message;
          }
          return { ...message, feedbackRating: feedback.rating };
        } catch {
          return message;
        }
      }),
    );

    setActiveConversationId(conversationId);
    setMessages(withFeedback);
  }, [activeConversationId]);

  useEffect(() => {
    if (hasRestoredConversation.current) {
      return;
    }
    hasRestoredConversation.current = true;
    const savedConversationId = sessionStorage.getItem(ACTIVE_CONVERSATION_KEY);
    if (!savedConversationId) {
      return;
    }
    void loadConversation(savedConversationId);
  }, [loadConversation]);

  useEffect(() => {
    if (activeConversationId) {
      sessionStorage.setItem(ACTIVE_CONVERSATION_KEY, activeConversationId);
      return;
    }
    sessionStorage.removeItem(ACTIVE_CONVERSATION_KEY);
  }, [activeConversationId]);

  const ensureConversation = useCallback(
    async (question: string) => {
      if (activeConversationId) {
        return activeConversationId;
      }
      const conversation = await createConversation({
        data_source_id: selectedDataSourceId,
      });
      setActiveConversationId(conversation.id);
      setConversations((current) => [conversation, ...current]);
      await appendConversationMessage(conversation.id, {
        role: "user",
        content: question,
      });
      return conversation.id;
    },
    [activeConversationId, selectedDataSourceId],
  );

  const persistAssistantMessage = useCallback(
    async (conversationId: string, message: AssistantChatMessage) => {
      await appendConversationMessage(conversationId, {
        role: "assistant",
        content: message.explanation || message.content || message.question,
        payload: assistantPayload(message),
      });
      await refreshConversations(selectedDataSourceId);
    },
    [refreshConversations, selectedDataSourceId],
  );

  const updateAssistantMessage = useCallback(
    (messageId: string, patch: Partial<AssistantChatMessage>) => {
      setMessages((current) =>
        current.map((message) =>
          message.id === messageId && isAssistantMessage(message)
            ? { ...message, ...patch }
            : message,
        ),
      );
    },
    [],
  );

  const handleNewChat = useCallback(() => {
    if (isSubmitting) {
      return;
    }
    sessionStorage.removeItem(ACTIVE_CONVERSATION_KEY);
    setActiveConversationId(null);
    setMessages([]);
    setInput("");
  }, [isSubmitting]);

  const handleDeleteConversation = useCallback(
    async (conversationId: string) => {
      if (!window.confirm("Delete this chat permanently?")) {
        return;
      }
      await deleteConversation(conversationId);
      setConversations((current) =>
        current.filter((conversation) => conversation.id !== conversationId),
      );
      if (activeConversationId === conversationId) {
        handleNewChat();
      }
    },
    [activeConversationId, handleNewChat],
  );

  const handleArchiveConversation = useCallback(
    async (conversationId: string) => {
      await updateConversation(conversationId, { archived: true });
      setConversations((current) =>
        current.filter((conversation) => conversation.id !== conversationId),
      );
      if (activeConversationId === conversationId) {
        handleNewChat();
      }
    },
    [activeConversationId, handleNewChat],
  );

  const handleUnarchiveConversation = useCallback(
    async (conversationId: string) => {
      await updateConversation(conversationId, { archived: false });
      setConversations((current) =>
        current.filter((conversation) => conversation.id !== conversationId),
      );
      if (activeConversationId === conversationId) {
        handleNewChat();
      }
    },
    [activeConversationId, handleNewChat],
  );

  const handleSubmit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      const question = input.trim();
      if (!question || !selectedDataSourceId || isSubmitting) {
        return;
      }

      const userMessage: UserChatMessage = {
        id: createId(),
        role: "user",
        content: question,
        createdAt: new Date().toISOString(),
      };

      const assistantId = createId();
      const assistantMessage: AssistantChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        question,
        stage: "generating_sql",
        createdAt: new Date().toISOString(),
      };

      const history = buildConversationHistory(messages);

      setMessages((current) => [...current, userMessage, assistantMessage]);
      setInput("");
      setIsSubmitting(true);

      let conversationId: string | null = null;
      let assistantToPersist: AssistantChatMessage | null = null;

      try {
        const hadExistingConversation = Boolean(activeConversationId);
        conversationId = await ensureConversation(question);
        if (hadExistingConversation) {
          await appendConversationMessage(conversationId, {
            role: "user",
            content: question,
          });
        }

        let thinkingText = "";
        let explanation = "";

        const generated = await generateSqlWithFallback(
          {
            data_source_id: selectedDataSourceId,
            session_id: sessionId,
            conversation_id: conversationId,
            question,
            conversation_history: history,
          },
          (event) => {
            if (event.type === "thinking") {
              thinkingText += event.delta;
              updateAssistantMessage(assistantId, { thinkingText });
              return;
            }

            if (event.type === "explanation_delta") {
              thinkingText = "";
              explanation += event.delta;
              updateAssistantMessage(assistantId, {
                thinkingText: "",
                explanation,
                content: explanation,
              });
            }
          },
        );

        updateAssistantMessage(assistantId, {
          stage: "executing",
          thinkingText: "",
          sql: generated.sql,
          explanation: generated.explanation,
          tablesReferenced: generated.tables_referenced,
          confidence: generated.confidence,
          content: generated.explanation,
        });

        const executed = await executeQuery({
          data_source_id: selectedDataSourceId,
          session_id: sessionId,
          conversation_id: conversationId,
          sql: generated.sql,
          user_question: question,
          max_rows: 1000,
          timeout_seconds: 30,
        });

        if (executed.query_result.row_count === 0) {
          assistantToPersist = {
            ...assistantMessage,
            stage: "complete",
            sql: generated.sql,
            explanation: generated.explanation,
            tablesReferenced: generated.tables_referenced,
            confidence: generated.confidence,
            content: generated.explanation,
            queryResult: executed.query_result,
            queryLogId: executed.query_log_id,
            chartSpec: null,
            error: buildChatError("no_data"),
          };
          updateAssistantMessage(assistantId, assistantToPersist);
          return;
        }

        updateAssistantMessage(assistantId, {
          stage: "building_chart",
          queryResult: executed.query_result,
          queryLogId: executed.query_log_id,
        });

        let chartSpec = null;
        try {
          const chartResponse = await fetchChartSpec({
            data_source_id: selectedDataSourceId,
            session_id: sessionId,
            conversation_id: conversationId,
            user_question: question,
            sql: generated.sql,
            query_result: executed.query_result,
            query_log_id: executed.query_log_id,
          });
          chartSpec = chartResponse.chart_spec;
        } catch {
          chartSpec = null;
        }

        const ambiguousWarning = maybeAmbiguousWarning(generated.confidence);
        assistantToPersist = {
          ...assistantMessage,
          stage: "complete",
          sql: generated.sql,
          explanation: generated.explanation,
          tablesReferenced: generated.tables_referenced,
          confidence: generated.confidence,
          content: generated.explanation,
          queryResult: executed.query_result,
          queryLogId: executed.query_log_id,
          chartSpec,
          error: ambiguousWarning,
        };

        updateAssistantMessage(assistantId, assistantToPersist);
      } catch (error) {
        const chatError = mapApiErrorToChatError(error);
        void logDiagnosticEvent({
          source: "chat",
          message: chatError.message,
          details: {
            kind: chatError.kind,
            title: chatError.title,
            suggestion: chatError.suggestion,
            underlying:
              error instanceof Error
                ? { name: error.name, message: error.message, stack: error.stack }
                : String(error),
          },
        }).catch(() => undefined);
        assistantToPersist = {
          ...assistantMessage,
          stage: "error",
          error: chatError,
        };
        updateAssistantMessage(assistantId, assistantToPersist);
      } finally {
        setIsSubmitting(false);
      }

      if (assistantToPersist && conversationId) {
        void persistAssistantMessage(conversationId, assistantToPersist);
      }
    },
    [
      activeConversationId,
      ensureConversation,
      input,
      isSubmitting,
      messages,
      persistAssistantMessage,
      selectedDataSourceId,
      sessionId,
      updateAssistantMessage,
    ],
  );

  const formatSourceLabel = (source: DataSource) => source.name;

  return (
    <div className="chat-layout">
      <ChatHistorySidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        loading={historyLoading}
        view={historyView}
        onViewChange={setHistoryView}
        onSelect={(conversationId) => {
          if (isSubmitting) {
            return;
          }
          void loadConversation(conversationId);
        }}
        onNewChat={handleNewChat}
        onArchive={(conversationId) => void handleArchiveConversation(conversationId)}
        onUnarchive={(conversationId) => void handleUnarchiveConversation(conversationId)}
        onDelete={(conversationId) => void handleDeleteConversation(conversationId)}
      />

      <div
        className={`chat-page${!loadError && dataSources.length === 0 ? " chat-page--empty" : ""}`}
      >
        {dataSources.length > 0 && (
          <div className="chat-page__toolbar">
            <span className="chat-page__toolbar-title">Your words. Your data.</span>
            <div className="chat-page__source-controls">
            <Select
              id="chat-source-select"
              className="chat-page__source-select"
              aria-label="Data source"
              value={selectedDataSourceId}
              onChange={(nextValue) => {
                setSelectedDataSourceId(nextValue);
                handleNewChat();
              }}
              disabled={isSubmitting || dataSources.length <= 1}
              options={dataSources.map((source) => ({
                value: source.id,
                label: formatSourceLabel(source),
              }))}
              size="sm"
            />
            </div>
          </div>
        )}

        {loadError && (
          <div className="error-banner error-banner--page">
            <h3>Could not load data sources</h3>
            <p>{loadError}</p>
          </div>
        )}

        {!loadError && dataSources.length === 0 && (
          <div className="chat-empty-state chat-empty-state--page">
            <h2>No data sources yet</h2>
            {user?.is_admin ? (
              <>
                <p>
                  Connect a database in Admin to start asking questions about your data.
                </p>
                <Link to="/admin" className="btn btn--secondary chat-empty-state__action">
                  Go to Admin
                </Link>
              </>
            ) : (
              <p>
                Ask your administrator to connect a database before you can start asking
                questions about your data.
              </p>
            )}
          </div>
        )}

        {dataSources.length > 0 && (
          <>
            <ChatMessageList
              messages={messages}
              dataSourceName={selectedDataSource?.name ?? "your data source"}
            />

            <ChatComposer
              value={input}
              onChange={setInput}
              onSubmit={handleSubmit}
              disabled={!selectedDataSourceId}
              isSubmitting={isSubmitting}
            />
          </>
        )}
      </div>
    </div>
  );
}
