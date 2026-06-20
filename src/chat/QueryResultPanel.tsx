import ChartRenderer from "@/components/ChartRenderer";
import DataTable from "@/components/DataTable";
import SqlCollapsible from "@/chat/SqlCollapsible";
import ResponseFeedback from "@/chat/ResponseFeedback";
import type { AssistantChatMessage } from "@/chat/types";
import { stageLabel } from "@/chat/errorMessages";

export interface QueryResultPanelProps {
  message: AssistantChatMessage;
}

export default function QueryResultPanel({ message }: QueryResultPanelProps) {
  const isLoading =
    message.stage !== "complete" &&
    message.stage !== "error" &&
    message.stage !== "idle";

  if (isLoading) {
    const showThinking = Boolean(message.thinkingText);
    const showStreamingExplanation =
      !showThinking && Boolean(message.explanation);
    const showSpinner = !showThinking && !showStreamingExplanation;

    return (
      <div className="query-result-panel query-result-panel--loading">
        {showThinking && (
          <div className="thinking-block" aria-live="polite">
            <span className="thinking-block__label">Thinking</span>
            <p className="thinking-block__text">{message.thinkingText}</p>
          </div>
        )}

        {showStreamingExplanation && (
          <p className="query-result-panel__preview query-result-panel__streaming">
            {message.explanation}
          </p>
        )}

        {showSpinner && (
          <div className="loading-indicator">
            <span className="loading-indicator__spinner" aria-hidden="true" />
            <span>{stageLabel(message.stage)}</span>
          </div>
        )}

        {message.sql && (
          <SqlCollapsible
            sql={message.sql}
            explanation={message.explanation}
            tablesReferenced={message.tablesReferenced}
            confidence={message.confidence}
          />
        )}
      </div>
    );
  }

  if (message.stage === "error" && message.error) {
    return (
      <div className={`query-result-panel query-result-panel--error query-result-panel--${message.error.kind}`}>
        <div className="error-banner">
          <h3>{message.error.title}</h3>
          <p>{message.error.message}</p>
          {message.error.rawMessage && (
            <p className="error-banner__detail">{message.error.rawMessage}</p>
          )}
          <p className="error-banner__suggestion">
            <strong>Suggested next step:</strong> {message.error.suggestion}
          </p>
        </div>
        {message.sql && (
          <SqlCollapsible
            sql={message.sql}
            explanation={message.explanation}
            tablesReferenced={message.tablesReferenced}
            confidence={message.confidence}
          />
        )}
      </div>
    );
  }

  const showChart =
    message.queryResult &&
    message.chartSpec &&
    message.chartSpec.chart_type !== "table_only";

  const ambiguousWarning =
    message.error?.kind === "ambiguous_question" ? message.error : null;
  const blockingError =
    message.error && message.error.kind !== "ambiguous_question"
      ? message.error
      : null;

  return (
    <div className="query-result-panel">
      {blockingError && (
        <div className={`error-banner query-result-panel--${blockingError.kind}`}>
          <h3>{blockingError.title}</h3>
          <p>{blockingError.message}</p>
          <p className="error-banner__suggestion">
            <strong>Suggested next step:</strong> {blockingError.suggestion}
          </p>
        </div>
      )}

      {message.explanation && (
        <p className="query-result-panel__summary">{message.explanation}</p>
      )}

      {ambiguousWarning && (
        <div className="warning-banner">
          <strong>{ambiguousWarning.title}</strong>
          <p>{ambiguousWarning.message}</p>
          <p>{ambiguousWarning.suggestion}</p>
        </div>
      )}

      {message.sql && (
        <SqlCollapsible
          sql={message.sql}
          explanation={message.explanation}
          tablesReferenced={message.tablesReferenced}
          confidence={message.confidence}
        />
      )}

      {showChart && message.queryResult && message.chartSpec && (
        <ChartRenderer
          chartSpec={message.chartSpec}
          queryResult={message.queryResult}
        />
      )}

      {message.queryResult && (
        <DataTable
          columns={message.queryResult.columns}
          rows={message.queryResult.rows}
          truncated={message.queryResult.truncated}
          executionMs={message.queryResult.execution_ms}
        />
      )}

      {message.stage === "complete" && message.queryLogId && (
        <ResponseFeedback
          queryLogId={message.queryLogId}
          initialRating={message.feedbackRating}
        />
      )}
    </div>
  );
}
