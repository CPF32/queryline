import type {
  ChartSpec,
  ConfidenceLevel,
  QueryResult,
} from "@/types/contracts";

export type ChatPipelineStage =
  | "idle"
  | "generating_sql"
  | "executing"
  | "building_chart"
  | "complete"
  | "error";

export type ChatErrorKind =
  | "validation_rejected"
  | "execution_timeout"
  | "execution_failed"
  | "no_data"
  | "ambiguous_question"
  | "generation_failed"
  | "llm_quota"
  | "chart_failed"
  | "network";

export interface ChatErrorState {
  kind: ChatErrorKind;
  title: string;
  message: string;
  suggestion: string;
  rawMessage?: string;
}

export interface UserChatMessage {
  id: string;
  role: "user";
  content: string;
  createdAt: string;
}

export interface AssistantChatMessage {
  id: string;
  role: "assistant";
  content: string;
  question: string;
  stage: ChatPipelineStage;
  thinkingText?: string;
  sql?: string;
  explanation?: string;
  tablesReferenced?: string[];
  confidence?: ConfidenceLevel;
  queryResult?: QueryResult;
  chartSpec?: ChartSpec | null;
  queryLogId?: string;
  feedbackRating?: "up" | "down" | null;
  error?: ChatErrorState;
  createdAt: string;
}

export type ChatMessage = UserChatMessage | AssistantChatMessage;

export function isAssistantMessage(
  message: ChatMessage,
): message is AssistantChatMessage {
  return message.role === "assistant";
}
