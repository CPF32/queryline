import { useState } from "react";
import { submitQueryFeedback } from "@/api/client";
import { useSnackbar } from "@/components/snackbar/SnackbarProvider";
import type { FeedbackRating } from "@/types/contracts";

export interface ResponseFeedbackProps {
  queryLogId: string;
  initialRating?: FeedbackRating | null;
}

export default function ResponseFeedback({
  queryLogId,
  initialRating = null,
}: ResponseFeedbackProps) {
  const { showSuccess, showError } = useSnackbar();
  const [rating, setRating] = useState<FeedbackRating | null>(initialRating);
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function sendFeedback(nextRating: FeedbackRating, nextComment?: string) {
    setSubmitting(true);
    try {
      await submitQueryFeedback(queryLogId, {
        rating: nextRating,
        comment: nextComment,
      });
      setRating(nextRating);
      showSuccess(
        nextRating === "up"
          ? "Thanks — this helps improve future answers."
          : "Feedback recorded — similar questions will avoid this approach.",
      );
      if (nextRating === "down") {
        setShowComment(false);
      }
    } catch (error) {
      showError(
        error instanceof Error ? error.message : "Could not save feedback",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function handleRating(nextRating: FeedbackRating) {
    if (submitting || rating === nextRating) {
      return;
    }
    if (nextRating === "down" && !showComment) {
      setShowComment(true);
      return;
    }
    void sendFeedback(nextRating, comment.trim() || undefined);
  }

  return (
    <div className="response-feedback">
      <span className="response-feedback__label">Was this helpful?</span>
      <div className="response-feedback__actions">
        <button
          type="button"
          className={`response-feedback__btn response-feedback__btn--yes ${rating === "up" ? "response-feedback__btn--active" : ""}`}
          onClick={() => handleRating("up")}
          disabled={submitting}
        >
          Yes
        </button>
        <button
          type="button"
          className={`response-feedback__btn response-feedback__btn--no ${rating === "down" ? "response-feedback__btn--active" : ""}`}
          onClick={() => handleRating("down")}
          disabled={submitting}
        >
          No
        </button>
      </div>

      {showComment && rating !== "down" && (
        <div className="response-feedback__comment">
          <textarea
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder="What was wrong? (optional)"
            rows={2}
            disabled={submitting}
          />
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={() => void sendFeedback("down", comment.trim() || undefined)}
            disabled={submitting}
          >
            Submit feedback
          </button>
        </div>
      )}
    </div>
  );
}
