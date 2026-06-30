import type {
  ApiError,
  ApiListSuccess,
  ApiSuccess,
  ChartSpecRequest,
  ChartSpecResponse,
  ConnectionFormSchema,
  ConnectionTestResult,
  ConnectorInfo,
  Conversation,
  ConversationMessage,
  DataSource,
  ExecuteQueryRequest,
  ExecuteQueryResponse,
  FeedbackRating,
  GenerateSqlRequest,
  GenerateSqlResponse,
  GlossaryTerm,
  QueryFeedback,
  QueryLogEntry,
  SchemaColumn,
  SchemaImportResult,
  SchemaObjectType,
  SchemaRelationship,
  SchemaSnapshot,
  SchemaTable,
  SqlExample,
  LlmSettings,
  LlmTestResult,
  LlmProvider,
  OllamaModelRecommendation,
  SetupStatus,
  User,
} from "@/types/contracts";

const API_BASE = "/api/v1";

export function isDesktopApp(): boolean {
  return typeof window.desktopApp !== "undefined";
}

declare global {
  interface Window {
    desktopApp?: {
      platform: string;
      systemUser?: string | null;
      pickSqliteFile?: () => Promise<string | null>;
      getSystemSpecs?: () => Promise<{
        platform: string;
        arch: string;
        totalRamGb: number;
        freeRamGb: number;
        cpuCount: number;
        cpuModel: string;
      }>;
      recommendOllamaModel?: (totalRamGb: number) => Promise<OllamaModelRecommendation>;
      getOllamaStatus?: (baseUrl?: string) => Promise<{
        installed: boolean;
        running: boolean;
        baseUrl: string;
      }>;
      installOllama?: () => Promise<{ installed: boolean }>;
      startOllama?: (baseUrl?: string) => Promise<{
        installed: boolean;
        running: boolean;
        baseUrl: string;
      }>;
      pullOllamaModel?: (model: string) => Promise<{ model: string; complete: boolean }>;
      onOllamaProgress?: (
        callback: (progress: { phase: string; message: string }) => void,
      ) => () => void;
      getAppVersion?: () => Promise<string>;
      getAppUpdateStatus?: () => Promise<{
        phase: string;
        version?: string;
        currentVersion?: string;
        percent?: number;
        message?: string;
        releaseNotes?: string | null;
        source?: string;
      }>;
      checkForAppUpdate?: (manual?: boolean) => Promise<{ checking: boolean; error?: string }>;
      downloadAppUpdate?: () => Promise<{ started: boolean }>;
      installAppUpdate?: () => Promise<{ installed: boolean }>;
      onAppUpdateStatus?: (
        callback: (status: {
          phase: string;
          version?: string;
          percent?: number;
          message?: string;
          releaseNotes?: string | null;
        }) => void,
      ) => () => void;
      versions: {
        node: string;
        chrome: string;
        electron: string;
      };
    };
  }
}

function buildAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const systemUser = window.desktopApp?.systemUser;
  if (systemUser) {
    headers["X-System-User"] = systemUser;
  }
  return headers;
}

export class ApiRequestError extends Error {
  readonly code: string;
  readonly details: Record<string, unknown> | null;
  readonly status: number;

  constructor(
    status: number,
    code: string,
    message: string,
    details: Record<string, unknown> | null = null,
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function parseJson<T>(response: Response): Promise<T> {
  const text = await response.text();
  if (!text) {
    return {} as T;
  }
  return JSON.parse(text) as T;
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = await parseJson<ApiError>(response);
    const err = body.error ?? {
      code: "UNKNOWN_ERROR",
      message: response.statusText || "Request failed",
      details: null,
    };
    throw new ApiRequestError(
      response.status,
      err.code,
      err.message,
      err.details,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return parseJson<T>(response);
}

async function unwrapData<T>(path: string, init?: RequestInit): Promise<T> {
  const result = await request<ApiSuccess<T>>(path, init);
  return result.data;
}

async function unwrapList<T>(path: string, init?: RequestInit): Promise<T[]> {
  const result = await request<ApiListSuccess<T>>(path, init);
  return result.data;
}

// --- Setup ---

export async function getSetupStatus(): Promise<SetupStatus> {
  return unwrapData("/setup/status");
}

export async function getOllamaRecommendation(ramGb: number): Promise<OllamaModelRecommendation> {
  return unwrapData(`/setup/ollama-recommendation?ram_gb=${encodeURIComponent(String(ramGb))}`);
}

export async function completeSetup(payload: {
  ollama_self_host: boolean;
  provider?: LlmProvider;
  ollama_base_url?: string;
  ollama_model?: string;
}): Promise<SetupStatus> {
  return unwrapData("/setup/complete", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- Auth ---

export interface SystemIdentity {
  username: string;
  domain: string | null;
  display_name: string;
}

export function getDesktopSystemUser(): string | null {
  const value = window.desktopApp?.systemUser?.trim();
  return value || null;
}

export async function fetchSystemIdentity(): Promise<SystemIdentity | null> {
  try {
    return await unwrapData<SystemIdentity | null>("/auth/system-identity");
  } catch {
    return null;
  }
}

export async function fetchCurrentUser(): Promise<User> {
  return unwrapData("/auth/me");
}

export async function login(credentials: {
  username: string;
  password: string;
  domain?: string;
}): Promise<User> {
  return unwrapData("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export async function logout(): Promise<void> {
  await unwrapData<{ signed_out: boolean }>("/auth/logout", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function updateCurrentUserProfile(body: {
  display_name?: string;
  theme?: "light" | "dark";
}): Promise<User> {
  return unwrapData("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function listUsers(
  params: { limit?: number; offset?: number } = {},
): Promise<User[]> {
  const search = new URLSearchParams();
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  const query = search.toString();
  const suffix = query ? `?${query}` : "";
  return unwrapList(`/users${suffix}`);
}

export async function createUser(body: {
  username: string;
  domain?: string | null;
  display_name: string;
  is_admin?: boolean;
}): Promise<User> {
  return unwrapData("/users", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateUser(
  userId: string,
  body: {
    username?: string;
    domain?: string | null;
    display_name?: string;
    is_admin?: boolean;
    theme?: "light" | "dark";
  },
): Promise<User> {
  return unwrapData(`/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteUser(userId: string): Promise<void> {
  await request(`/users/${userId}`, { method: "DELETE" });
}

// --- Conversations ---

export async function listConversations(
  params: {
    data_source_id?: string;
    archived?: boolean;
    limit?: number;
    offset?: number;
  } = {},
): Promise<Conversation[]> {
  const search = new URLSearchParams();
  if (params.data_source_id) search.set("data_source_id", params.data_source_id);
  if (params.archived !== undefined) search.set("archived", String(params.archived));
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  const query = search.toString();
  const suffix = query ? `?${query}` : "";
  return unwrapList(`/conversations${suffix}`);
}

export async function createConversation(body: {
  data_source_id: string;
  title?: string | null;
}): Promise<Conversation> {
  return unwrapData("/conversations", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await request(`/conversations/${conversationId}`, { method: "DELETE" });
}

export async function updateConversation(
  conversationId: string,
  body: { title?: string; archived?: boolean },
): Promise<Conversation> {
  return unwrapData(`/conversations/${conversationId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function listConversationMessages(
  conversationId: string,
): Promise<ConversationMessage[]> {
  return unwrapData(`/conversations/${conversationId}/messages`);
}

export async function appendConversationMessage(
  conversationId: string,
  body: {
    role: "user" | "assistant";
    content: string;
    payload?: Record<string, unknown> | null;
  },
): Promise<ConversationMessage> {
  return unwrapData(`/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function submitQueryFeedback(
  queryLogId: string,
  body: { rating: FeedbackRating; comment?: string | null },
): Promise<QueryFeedback> {
  return unwrapData(`/query-log/${queryLogId}/feedback`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchQueryFeedback(
  queryLogId: string,
): Promise<QueryFeedback | null> {
  return unwrapData(`/query-log/${queryLogId}/feedback`);
}

// --- Chat ---

export async function fetchActiveDataSources(): Promise<DataSource[]> {
  const result = await request<ApiListSuccess<DataSource>>("/data-sources");
  return result.data.filter((source) => source.is_active);
}

export async function generateSql(
  payload: GenerateSqlRequest,
): Promise<GenerateSqlResponse> {
  return unwrapData("/chat/generate-sql", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type SqlStreamEvent =
  | { type: "thinking"; delta: string }
  | { type: "explanation_delta"; delta: string }
  | { type: "complete"; data: GenerateSqlResponse }
  | {
      type: "error";
      code: string;
      message: string;
      details?: Record<string, unknown> | null;
    };

function splitSseBuffer(buffer: string): { events: string[]; remainder: string } {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const parts = normalized.split("\n\n");
  const remainder = parts.pop() ?? "";
  return { events: parts, remainder };
}

function parseSseEvent(raw: string): SqlStreamEvent | null {
  const line = raw
    .split("\n")
    .find((entry) => entry.startsWith("data:"));
  if (!line) {
    return null;
  }
  const json = line.slice(5).trim();
  if (!json) {
    return null;
  }
  try {
    return JSON.parse(json) as SqlStreamEvent;
  } catch {
    throw new ApiRequestError(
      500,
      "stream_failed",
      "Received a malformed response while generating SQL.",
      null,
    );
  }
}

export async function generateSqlStream(
  payload: GenerateSqlRequest,
  onEvent: (event: SqlStreamEvent) => void,
): Promise<GenerateSqlResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/chat/generate-sql/stream`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...buildAuthHeaders(),
      },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    throw new ApiRequestError(
      0,
      "stream_interrupted",
      error instanceof Error ? error.message : "Stream interrupted",
      null,
    );
  }

  if (!response.ok) {
    const body = await parseJson<ApiError>(response);
    const err = body.error ?? {
      code: "UNKNOWN_ERROR",
      message: response.statusText || "Request failed",
      details: null,
    };
    throw new ApiRequestError(
      response.status,
      err.code,
      err.message,
      err.details,
    );
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new ApiRequestError(500, "stream_failed", "No response body", null);
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let result: GenerateSqlResponse | null = null;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const { events, remainder } = splitSseBuffer(buffer);
      buffer = remainder;

      for (const rawEvent of events) {
        const event = parseSseEvent(rawEvent);
        if (!event) {
          continue;
        }
        onEvent(event);
        if (event.type === "complete") {
          result = event.data;
        }
        if (event.type === "error") {
          throw new ApiRequestError(
            422,
            event.code,
            event.message,
            event.details ?? null,
          );
        }
      }
    }
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw error;
    }
    throw new ApiRequestError(
      0,
      "stream_interrupted",
      error instanceof Error ? error.message : "Stream interrupted",
      null,
    );
  }

  if (buffer.trim()) {
    const event = parseSseEvent(buffer);
    if (event) {
      onEvent(event);
      if (event.type === "complete") {
        result = event.data;
      }
      if (event.type === "error") {
        throw new ApiRequestError(
          422,
          event.code,
          event.message,
          event.details ?? null,
        );
      }
    }
  }

  if (!result) {
    throw new ApiRequestError(
      500,
      "stream_incomplete",
      "The response stream ended before SQL generation finished.",
      null,
    );
  }

  return result;
}

function isStreamTransportError(error: unknown): boolean {
  if (error instanceof ApiRequestError) {
    const code = error.code.toUpperCase();
    return (
      code === "STREAM_INTERRUPTED" ||
      code === "STREAM_FAILED" ||
      code === "STREAM_INCOMPLETE"
    );
  }
  if (error instanceof Error) {
    const lower = error.message.toLowerCase();
    return (
      lower.includes("network error") ||
      lower.includes("failed to fetch") ||
      lower.includes("load failed") ||
      lower.includes("networkerror") ||
      lower.includes("aborted")
    );
  }
  return false;
}

/** Try streaming generation; fall back to a regular POST if the stream drops. */
export async function generateSqlWithFallback(
  payload: GenerateSqlRequest,
  onEvent: (event: SqlStreamEvent) => void,
): Promise<GenerateSqlResponse> {
  try {
    return await generateSqlStream(payload, onEvent);
  } catch (error) {
    if (!isStreamTransportError(error)) {
      throw error;
    }
    const result = await generateSql(payload);
    if (result.explanation) {
      onEvent({ type: "explanation_delta", delta: result.explanation });
    }
    return result;
  }
}

export async function executeQuery(
  payload: ExecuteQueryRequest,
): Promise<ExecuteQueryResponse> {
  return unwrapData("/chat/execute", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function executeSql(
  payload: ExecuteQueryRequest,
): Promise<ExecuteQueryResponse> {
  return executeQuery(payload);
}

export async function fetchChartSpec(
  payload: ChartSpecRequest,
): Promise<ChartSpecResponse> {
  return unwrapData("/chat/chart-spec", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function transcribeAudio(blob: Blob): Promise<string> {
  const formData = new FormData();
  const extension = blob.type.includes("mp4")
    ? "m4a"
    : blob.type.includes("ogg")
      ? "ogg"
      : "webm";
  formData.append("audio", blob, `recording.${extension}`);

  const response = await fetch(`${API_BASE}/chat/transcribe`, {
    method: "POST",
    credentials: "same-origin",
    headers: buildAuthHeaders(),
    body: formData,
  });

  if (!response.ok) {
    const body = await parseJson<ApiError>(response);
    const err = body.error ?? {
      code: "UNKNOWN_ERROR",
      message: response.statusText || "Request failed",
      details: null,
    };
    throw new ApiRequestError(
      response.status,
      err.code,
      err.message,
      err.details,
    );
  }

  const result = await parseJson<ApiSuccess<{ text: string }>>(response);
  return result.data.text;
}

// --- Data sources ---

export async function getConnectors(): Promise<ConnectorInfo[]> {
  return unwrapData("/connectors");
}

export async function getConnectionFormSchema(
  connectorType: string,
): Promise<ConnectionFormSchema> {
  return unwrapData(`/connectors/${encodeURIComponent(connectorType)}/connection-form-schema`);
}

export async function listDataSources(): Promise<ApiListSuccess<DataSource>> {
  return request<ApiListSuccess<DataSource>>("/data-sources");
}

export async function getDataSource(dataSourceId: string): Promise<DataSource> {
  return unwrapData(`/data-sources/${dataSourceId}`);
}

export async function createDataSource(body: {
  name: string;
  connector_type: string;
  connection_config: Record<string, unknown>;
  is_active: boolean;
}): Promise<DataSource> {
  return unwrapData("/data-sources", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteDataSource(dataSourceId: string): Promise<void> {
  await request(`/data-sources/${dataSourceId}`, { method: "DELETE" });
}

export async function testConnection(body: {
  connector_type: string;
  connection_config: Record<string, unknown>;
}): Promise<ConnectionTestResult> {
  return unwrapData("/data-sources/test-connection", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function testSavedConnection(
  dataSourceId: string,
): Promise<ConnectionTestResult> {
  return unwrapData(`/data-sources/${dataSourceId}/test-connection`, {
    method: "POST",
  });
}

// --- Schema ---

export function tableKey(
  schemaName: string | null | undefined,
  tableName: string,
): string {
  return schemaName ? `${schemaName}.${tableName}` : tableName;
}

export function schemaObjectKey(
  schemaName: string | null | undefined,
  objectName: string,
  objectType: SchemaObjectType = "table",
): string {
  return `${objectType}:${tableKey(schemaName, objectName)}`;
}

export function schemaObjectTypeLabel(objectType: SchemaObjectType): string {
  switch (objectType) {
    case "view":
      return "View";
    case "function":
      return "Function";
    case "procedure":
      return "Procedure";
    default:
      return "Table";
  }
}

export async function introspectSchema(
  dataSourceId: string,
): Promise<SchemaSnapshot> {
  return unwrapData(`/data-sources/${dataSourceId}/schema/introspect`, {
    method: "POST",
  });
}

export async function importSchema(
  dataSourceId: string,
  body: {
    mode: "merge" | "replace";
    include_tables?: string[];
    exclude_tables?: string[] | null;
  },
): Promise<SchemaImportResult> {
  return unwrapData(`/data-sources/${dataSourceId}/schema/import`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listSchemaTables(
  dataSourceId: string,
): Promise<SchemaTable[]> {
  return unwrapList(`/data-sources/${dataSourceId}/schema/tables`);
}

export async function updateSchemaTable(
  dataSourceId: string,
  tableId: string,
  body: Partial<{
    display_name: string | null;
    description: string | null;
    is_included_in_prompt: boolean;
  }>,
): Promise<SchemaTable> {
  return unwrapData(`/data-sources/${dataSourceId}/schema/tables/${tableId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function listSchemaColumns(
  dataSourceId: string,
  tableId: string,
): Promise<SchemaColumn[]> {
  return unwrapList(
    `/data-sources/${dataSourceId}/schema/tables/${tableId}/columns`,
  );
}

export async function updateSchemaColumn(
  dataSourceId: string,
  columnId: string,
  body: Partial<{
    display_name: string | null;
    description: string | null;
    is_pii: boolean;
    is_excluded_from_prompt: boolean;
  }>,
): Promise<SchemaColumn> {
  return unwrapData(`/data-sources/${dataSourceId}/schema/columns/${columnId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function listSchemaRelationships(
  dataSourceId: string,
): Promise<SchemaRelationship[]> {
  return unwrapList(`/data-sources/${dataSourceId}/schema/relationships`);
}

export async function createSchemaRelationship(
  dataSourceId: string,
  body: {
    constraint_name: string;
    source_table_id: string;
    source_column_id: string;
    target_table_id: string;
    target_column_id: string;
    relationship_type: string;
  },
): Promise<SchemaRelationship> {
  return unwrapData(`/data-sources/${dataSourceId}/schema/relationships`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function deleteSchemaRelationship(
  dataSourceId: string,
  relationshipId: string,
): Promise<void> {
  await request(
    `/data-sources/${dataSourceId}/schema/relationships/${relationshipId}`,
    { method: "DELETE" },
  );
}

// --- Glossary ---

export async function listGlossaryTerms(
  dataSourceId: string,
): Promise<GlossaryTerm[]> {
  return unwrapList(`/data-sources/${dataSourceId}/glossary`);
}

export async function createGlossaryTerm(
  dataSourceId: string,
  body: {
    term: string;
    definition: string;
    sql_expression?: string | null;
  },
): Promise<GlossaryTerm> {
  return unwrapData(`/data-sources/${dataSourceId}/glossary`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateGlossaryTerm(
  dataSourceId: string,
  termId: string,
  body: {
    term: string;
    definition: string;
    sql_expression?: string | null;
  },
): Promise<GlossaryTerm> {
  return unwrapData(`/data-sources/${dataSourceId}/glossary/${termId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function deleteGlossaryTerm(
  dataSourceId: string,
  termId: string,
): Promise<void> {
  await request(`/data-sources/${dataSourceId}/glossary/${termId}`, {
    method: "DELETE",
  });
}

// --- Examples ---

export async function listExamples(dataSourceId: string): Promise<SqlExample[]> {
  return unwrapList(`/data-sources/${dataSourceId}/examples`);
}

export async function createExample(
  dataSourceId: string,
  body: {
    question: string;
    sql: string;
    notes?: string | null;
  },
): Promise<SqlExample> {
  return unwrapData(`/data-sources/${dataSourceId}/examples`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateExample(
  dataSourceId: string,
  exampleId: string,
  body: {
    question: string;
    sql: string;
    notes?: string | null;
  },
): Promise<SqlExample> {
  return unwrapData(`/data-sources/${dataSourceId}/examples/${exampleId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function deleteExample(
  dataSourceId: string,
  exampleId: string,
): Promise<void> {
  await request(`/data-sources/${dataSourceId}/examples/${exampleId}`, {
    method: "DELETE",
  });
}

// --- Query log ---

export async function listQueryLog(
  dataSourceId: string,
  params: { limit?: number; offset?: number; session_id?: string } = {},
): Promise<ApiListSuccess<QueryLogEntry>> {
  const search = new URLSearchParams();
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  if (params.offset !== undefined) search.set("offset", String(params.offset));
  if (params.session_id) search.set("session_id", params.session_id);
  const query = search.toString();
  const suffix = query ? `?${query}` : "";
  return request<ApiListSuccess<QueryLogEntry>>(
    `/data-sources/${dataSourceId}/query-log${suffix}`,
  );
}

// --- LLM settings ---

export async function getLlmSettings(): Promise<LlmSettings> {
  return unwrapData("/llm-settings");
}

export async function updateLlmSettings(body: {
  provider: LlmProvider;
  anthropic_api_key?: string;
  anthropic_model?: string;
  gemini_api_key?: string;
  gemini_model?: string;
  openai_api_key?: string;
  openai_model?: string;
  ollama_base_url?: string;
  ollama_model?: string;
}): Promise<LlmSettings> {
  return unwrapData("/llm-settings", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function testLlmSettings(body: {
  provider: LlmProvider;
  anthropic_api_key?: string;
  anthropic_model?: string;
  gemini_api_key?: string;
  gemini_model?: string;
  openai_api_key?: string;
  openai_model?: string;
  ollama_base_url?: string;
  ollama_model?: string;
}): Promise<LlmTestResult> {
  return unwrapData("/llm-settings/test", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
