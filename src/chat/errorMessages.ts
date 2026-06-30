import { ApiRequestError } from "@/api/client";
import type { ChatErrorKind, ChatErrorState } from "@/chat/types";
import type { ConfidenceLevel } from "@/types/contracts";

interface ErrorTemplate {
  title: string;
  message: string;
  suggestion: string;
}

const ERROR_TEMPLATES: Record<ChatErrorKind, ErrorTemplate> = {
  validation_rejected: {
    title: "SQL validation rejected",
    message:
      "The generated query could not be run safely. Only read-only SELECT statements are allowed.",
    suggestion:
      "Rephrase your question or ask for a simpler aggregation, such as a count or sum over one table.",
  },
  execution_timeout: {
    title: "Query timed out",
    message:
      "The database took too long to respond. The query may be scanning too much data.",
    suggestion:
      "Try narrowing the date range, filtering to fewer rows, or asking for a smaller summary first.",
  },
  execution_failed: {
    title: "Query execution failed",
    message:
      "The database returned an error while running the generated SQL.",
    suggestion:
      "Check that the tables and columns you mean exist, or ask a follow-up to refine the query.",
  },
  no_data: {
    title: "No data returned",
    message:
      "The query ran successfully but returned zero rows for the filters or time range you asked about.",
    suggestion:
      "Broaden your filters, pick a different period, or ask what values exist in a key column.",
  },
  ambiguous_question: {
    title: "Question needs clarification",
    message:
      "Your question could map to more than one metric or table, so confidence in the answer is low.",
    suggestion:
      "Specify the metric, time range, or table you mean — for example, “revenue by month in 2026.”",
  },
  generation_failed: {
    title: "Could not generate SQL",
    message:
      "We couldn't translate that question into a query using the configured schema and glossary.",
    suggestion:
      "Try breaking the question into smaller parts or naming the business term you care about.",
  },
  llm_quota: {
    title: "AI quota exceeded",
    message:
      "The configured language model rejected the request because your API quota is exhausted.",
    suggestion:
      "Wait a minute and retry, switch GEMINI_MODEL in .env (e.g. gemini-2.0-flash-lite), enable billing in Google AI Studio, or set LLM_PROVIDER=anthropic.",
  },
  chart_failed: {
    title: "Chart could not be built",
    message:
      "Results are shown in the table below, but automatic chart selection failed.",
    suggestion:
      "Review the table data or ask for a specific breakdown that is easier to visualize.",
  },
  network: {
    title: "Connection problem",
    message: "The app could not reach the analytics API.",
    suggestion: "Check your network connection and try again in a moment.",
  },
};

function isTransportFailure(message: string | undefined): boolean {
  if (!message) {
    return false;
  }
  const lower = message.toLowerCase();
  return (
    lower.includes("network error") ||
    lower.includes("failed to fetch") ||
    lower.includes("load failed") ||
    lower.includes("networkerror") ||
    lower.includes("aborted") ||
    lower.includes("stream")
  );
}

function buildTransportChatError(rawMessage?: string): ChatErrorState {
  const isDesktop = typeof window !== "undefined" && Boolean(window.desktopApp);
  return {
    kind: "network",
    title: "Connection lost during chat",
    message: isDesktop
      ? "The connection to the local Queryline backend was interrupted while generating SQL."
      : "The connection to the analytics API was interrupted while generating SQL.",
    suggestion: isDesktop
      ? "Quit and reopen Queryline, then try a short question. If Ollama runs on another machine, confirm that server is reachable and the model supports tool calling."
      : "Ensure the backend is running, then try a shorter question. If Ollama is remote, check latency and firewall rules.",
    rawMessage,
  };
}

export function buildChatError(
  kind: ChatErrorKind,
  rawMessage?: string,
): ChatErrorState {
  const template = ERROR_TEMPLATES[kind];
  return {
    kind,
    ...template,
    rawMessage,
  };
}

export function mapApiErrorToChatError(error: unknown): ChatErrorState {
  if (!(error instanceof ApiRequestError)) {
    const rawMessage = error instanceof Error ? error.message : undefined;
    if (isTransportFailure(rawMessage)) {
      return buildTransportChatError(rawMessage);
    }
    return buildChatError("network", rawMessage);
  }

  const code = error.code.toUpperCase();
  const message = error.message.toLowerCase();

  if (
    code === "STREAM_INCOMPLETE" ||
    code === "STREAM_INTERRUPTED" ||
    code === "STREAM_FAILED"
  ) {
    return buildChatError("generation_failed", error.message);
  }

  if (
    code.includes("VALIDATION") ||
    code === "SQL_VALIDATION_ERROR" ||
    message.includes("validation")
  ) {
    return buildChatError("validation_rejected", error.message);
  }

  if (
    code.includes("TIMEOUT") ||
    message.includes("timeout") ||
    message.includes("timed out")
  ) {
    return buildChatError("execution_timeout", error.message);
  }

  if (code.includes("AMBIGU") || message.includes("ambiguous")) {
    return buildChatError("ambiguous_question", error.message);
  }

  if (
    code.includes("GENERATION") ||
    message.includes("generate") ||
    message.includes("gemini")
  ) {
    if (
      message.includes("quota") ||
      message.includes("429") ||
      message.includes("resource_exhausted")
    ) {
      return buildChatError("llm_quota", error.message);
    }
    return buildChatError("generation_failed", error.message);
  }

  return buildChatError("execution_failed", error.message);
}

export function maybeAmbiguousWarning(
  confidence: ConfidenceLevel | undefined,
): ChatErrorState | undefined {
  if (confidence !== "low") {
    return undefined;
  }
  return buildChatError("ambiguous_question");
}

export function stageLabel(stage: string): string {
  switch (stage) {
    case "generating_sql":
      return "Generating SQL…";
    case "executing":
      return "Running query…";
    case "building_chart":
      return "Building visualization…";
    default:
      return "Working…";
  }
}
