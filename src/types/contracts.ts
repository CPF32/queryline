/** TypeScript mirrors of CONTRACTS.md domain models and API payloads. */

export interface ApiError {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown> | null;
  };
}

export interface ListMeta {
  total: number;
  limit?: number;
  offset?: number;
}

export interface JsonSchemaProperty {
  type?: string;
  title?: string;
  default?: unknown;
  enum?: string[];
  format?: string;
  description?: string;
}

export interface ConnectionFormSchema {
  type: "object";
  title?: string;
  properties: Record<string, JsonSchemaProperty>;
  required?: string[];
}

export interface ConnectorInfo {
  connector_type: string;
  display_name: string;
  dialect_name: string;
  connection_form_schema: ConnectionFormSchema;
}

export interface DataSource {
  id: string;
  name: string;
  connector_type: string;
  connection_config: Record<string, unknown>;
  is_active: boolean;
  dialect_name: string;
  created_at: string;
  updated_at: string;
  /** Optional extension: last connection test outcome */
  last_test_success?: boolean | null;
  last_test_message?: string | null;
  last_test_at?: string | null;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  latency_ms?: number | null;
}

export interface SchemaColumnDraft {
  column_name: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  ordinal_position: number;
  sample_distinct_values?: string[] | null;
}

export interface SchemaRelationshipDraft {
  constraint_name: string;
  source_table: string;
  source_column: string;
  target_table: string;
  target_column: string;
  relationship_type: string;
}

export type SchemaObjectType = "table" | "view" | "function" | "procedure";

export interface SchemaTableDraft {
  schema_name?: string | null;
  table_name: string;
  object_type?: SchemaObjectType;
  row_count_estimate?: number | null;
  definition?: string | null;
  return_type?: string | null;
  columns: SchemaColumnDraft[];
  relationships: SchemaRelationshipDraft[];
}

export interface SchemaSnapshot {
  tables: SchemaTableDraft[];
}

export interface SchemaImportResult {
  tables_imported: number;
  columns_imported: number;
  relationships_imported: number;
}

export interface SchemaTable {
  id: string;
  data_source_id: string;
  schema_name: string | null;
  table_name: string;
  object_type?: SchemaObjectType;
  display_name: string | null;
  description: string | null;
  is_included_in_prompt: boolean;
  row_count_estimate: number | null;
  definition?: string | null;
  return_type?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SchemaColumn {
  id: string;
  table_id: string;
  column_name: string;
  display_name: string | null;
  description: string | null;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  ordinal_position: number;
  sample_distinct_values: string[] | null;
  created_at: string;
  updated_at: string;
  /** Extension fields for admin metadata */
  is_pii?: boolean;
  is_excluded_from_prompt?: boolean;
}

export interface SchemaRelationship {
  id: string;
  data_source_id: string;
  constraint_name: string;
  source_table_id: string;
  source_column_id: string;
  target_table_id: string;
  target_column_id: string;
  relationship_type: string;
  created_at: string;
  updated_at: string;
}

export interface GlossaryTerm {
  id: string;
  data_source_id: string;
  term: string;
  definition: string;
  sql_expression: string | null;
  created_at: string;
  updated_at: string;
}

export interface SqlExample {
  id: string;
  data_source_id: string;
  question: string;
  sql: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export type ExecutionStatus =
  | "success"
  | "validation_error"
  | "execution_error";

export interface QueryLogEntry {
  id: string;
  data_source_id: string;
  session_id: string;
  user_question: string;
  generated_sql: string;
  execution_status: ExecutionStatus;
  error_message: string | null;
  row_count: number | null;
  execution_ms: number | null;
  chart_spec: Record<string, unknown> | null;
  created_at: string;
}

export interface QueryColumnMeta {
  name: string;
  type: string;
}

export interface QueryResult {
  columns: QueryColumnMeta[];
  rows: unknown[][];
  row_count: number;
  truncated: boolean;
  execution_ms: number;
}

export type ChartType =
  | "bar"
  | "line"
  | "area"
  | "scatter"
  | "pie"
  | "stat_card"
  | "table_only";

export interface ChartSpec {
  chart_type: ChartType;
  x_field: string | null;
  y_fields: string[];
  series_field: string | null;
  aggregation_applied: boolean;
  title: string;
}

export type ConfidenceLevel = "high" | "medium" | "low";

export interface ConversationTurn {
  role: "user" | "assistant";
  content: string;
}

export interface User {
  id: string;
  username: string;
  domain: string | null;
  display_name: string;
  is_admin: boolean;
  is_owner: boolean;
  theme: "light" | "dark";
  created_at: string;
  last_seen_at: string;
}

export interface SetupStatus {
  complete: boolean;
  wizard_required: boolean;
  ollama_self_host: boolean | null;
  owner_username: string | null;
  owner_domain: string | null;
  is_desktop: boolean;
  platform: string;
  default_ollama_base_url: string;
}

export interface OllamaModelRecommendation {
  model: string;
  label: string;
  reason: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  data_source_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export interface ConversationMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sequence: number;
  created_at: string;
  payload: Record<string, unknown> | null;
}

export type FeedbackRating = "up" | "down";

export interface QueryFeedback {
  id: string;
  query_log_id: string;
  user_id: string;
  rating: FeedbackRating;
  comment: string | null;
  created_at: string;
}

export interface GenerateSqlRequest {
  data_source_id: string;
  session_id: string;
  question: string;
  conversation_id?: string | null;
  conversation_history: ConversationTurn[];
}

export interface GenerateSqlResponse {
  sql: string;
  explanation: string;
  tables_referenced: string[];
  confidence: ConfidenceLevel;
}

export interface ExecuteQueryRequest {
  data_source_id: string;
  session_id: string;
  sql: string;
  max_rows?: number;
  timeout_seconds?: number;
  user_question: string;
  conversation_id?: string | null;
}

export interface ExecuteQueryResponse {
  query_result: QueryResult;
  query_log_id: string;
}

export interface ChartSpecRequest {
  data_source_id: string;
  session_id: string;
  user_question: string;
  sql: string;
  query_result: QueryResult;
  query_log_id?: string;
  conversation_id?: string | null;
}

export interface ChartSpecResponse {
  chart_spec: ChartSpec;
}

export interface ApiSuccess<T> {
  data: T;
}

export interface ApiListSuccess<T> {
  data: T[];
  meta: ListMeta;
}

export type LlmProvider = "anthropic" | "gemini" | "openai" | "ollama";

export interface LlmSettings {
  provider: LlmProvider;
  anthropic_model: string;
  gemini_model: string;
  openai_model: string;
  ollama_base_url: string;
  ollama_model: string;
  anthropic_api_key_set: boolean;
  gemini_api_key_set: boolean;
  openai_api_key_set: boolean;
  configured: boolean;
  env_file_path: string;
}

export interface LlmTestResult {
  success: boolean;
  message: string;
  latency_ms?: number | null;
}
