import Icon from "@/components/icons/Icon";
import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import { useTheme } from "@/theme/ThemeProvider";

export interface SqlCollapsibleProps {
  sql: string;
  explanation?: string;
  tablesReferenced?: string[];
  confidence?: "high" | "medium" | "low";
  defaultExpanded?: boolean;
}

export default function SqlCollapsible({
  sql,
  explanation,
  tablesReferenced = [],
  confidence,
  defaultExpanded = false,
}: SqlCollapsibleProps) {
  const { theme } = useTheme();
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [showWhy, setShowWhy] = useState(false);
  const hasContext =
    Boolean(explanation) ||
    tablesReferenced.length > 0 ||
    confidence !== undefined;

  const syntaxStyle = theme === "dark" ? oneDark : oneLight;

  return (
    <div className="sql-collapsible">
      <button
        type="button"
        className="sql-collapsible__toggle"
        onClick={() => setExpanded((current) => !current)}
        aria-expanded={expanded}
      >
        <span className="sql-collapsible__chevron">
          <Icon name={expanded ? "chevron-down" : "chevron-right"} size={12} />
        </span>
        <Icon name="sql" size={14} />
        <span>Generated SQL</span>
        {confidence && (
          <span className={`sql-collapsible__confidence sql-collapsible__confidence--${confidence}`}>
            {confidence} confidence
          </span>
        )}
      </button>

      {expanded && (
        <div className="sql-collapsible__body">
          <SyntaxHighlighter
            language="sql"
            style={syntaxStyle}
            customStyle={{
              margin: 0,
              borderRadius: "var(--radius-sm)",
              fontSize: "0.8125rem",
              lineHeight: 1.5,
              background: "var(--bg-subtle)",
            }}
            showLineNumbers
          >
            {sql}
          </SyntaxHighlighter>

          {hasContext && (
            <div className="sql-collapsible__why">
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setShowWhy((current) => !current)}
              >
                {showWhy ? "Hide" : "Why this answer?"}
              </button>

              {showWhy && (
                <div className="sql-collapsible__context">
                  {explanation && <p>{explanation}</p>}
                  {tablesReferenced.length > 0 && (
                    <div>
                      <strong>Tables referenced:</strong>{" "}
                      {tablesReferenced.join(", ")}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
