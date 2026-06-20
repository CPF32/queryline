import Icon from "@/components/icons/Icon";
import { useSpeechToText } from "@/chat/useSpeechToText";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";
import { useEffect } from "react";

export interface ChatComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
  disabled?: boolean;
  isSubmitting?: boolean;
  placeholder?: string;
}

export default function ChatComposer({
  value,
  onChange,
  onSubmit,
  disabled = false,
  isSubmitting = false,
  placeholder = "Ask a question…",
}: ChatComposerProps) {
  const { showError } = useSnackbar();
  const hasText = value.trim().length > 0;
  const canSend = hasText && !disabled && !isSubmitting;

  const { supported, listening, error, toggle, stop } = useSpeechToText({
    onTranscript: onChange,
  });

  useEffect(() => {
    if (error) {
      showError(error);
    }
  }, [error, showError]);

  const handleSubmit = (event: React.FormEvent) => {
    if (listening) {
      stop();
    }
    onSubmit(event);
  };

  return (
    <form
      className={`chat-composer${hasText ? " chat-composer--has-text" : ""}${isSubmitting ? " chat-composer--submitting" : ""}${listening ? " chat-composer--listening" : ""}`}
      onSubmit={handleSubmit}
    >
      <textarea
        className="chat-composer__input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        rows={1}
        disabled={disabled || isSubmitting || listening}
        aria-label="Question"
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            if (canSend) {
              handleSubmit(event);
            }
          }
        }}
      />

      <div className="chat-composer__actions">
        {supported && (
          <button
            type="button"
            className={`chat-composer__action chat-composer__mic${listening ? " chat-composer__mic--active" : ""}`}
            onClick={() => {
              void toggle(value);
            }}
            disabled={disabled || isSubmitting || listening}
            aria-label={listening ? "Stop voice input" : "Start voice input"}
            title={listening ? "Stop listening" : "Voice input"}
          >
            <Icon name="mic" size={16} aria-hidden />
          </button>
        )}

        <button
          type="submit"
          className="chat-composer__action chat-composer__send"
          disabled={!canSend}
          aria-label={isSubmitting ? "Sending" : "Send question"}
          title="Send"
        >
          {isSubmitting ? (
            <span className="chat-composer__spinner" aria-hidden />
          ) : (
            <span className="chat-composer__send-icon" aria-hidden>
              <Icon name="arrow-up" size={16} />
            </span>
          )}
        </button>
      </div>
    </form>
  );
}
