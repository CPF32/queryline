import { useCallback, useEffect, useRef, useState } from "react";

function getSpeechRecognitionClass(): SpeechRecognitionConstructor | null {
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

function isVoiceInputSupported(): boolean {
  return getSpeechRecognitionClass() !== null;
}

export interface UseSpeechToTextOptions {
  onTranscript: (text: string) => void;
}

export function useSpeechToText({ onTranscript }: UseSpeechToTextOptions) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const baseTextRef = useRef("");
  const finalTranscriptRef = useRef("");
  const stoppingRef = useRef(false);

  const stop = useCallback(() => {
    if (!recognitionRef.current) {
      setListening(false);
      return;
    }
    stoppingRef.current = true;
    recognitionRef.current.stop();
  }, []);

  useEffect(() => {
    setSupported(isVoiceInputSupported());
    return () => {
      if (recognitionRef.current) {
        stoppingRef.current = true;
        recognitionRef.current.stop();
      }
      recognitionRef.current = null;
    };
  }, []);

  const mergeTranscript = useCallback(
    (interim: string) => {
      const base = baseTextRef.current;
      const committed = finalTranscriptRef.current;
      const spoken = `${committed}${interim}`.trim();
      if (!base) {
        onTranscript(spoken);
        return;
      }
      if (!spoken) {
        onTranscript(base);
        return;
      }
      onTranscript(`${base} ${spoken}`.trim());
    },
    [onTranscript],
  );

  const startListening = useCallback(
    (currentInput: string) => {
      const Recognition = getSpeechRecognitionClass();
      if (!Recognition) {
        setError("Voice input is not supported in this browser.");
        return;
      }

      if (recognitionRef.current) {
        return;
      }

      setError(null);
      stoppingRef.current = false;
      baseTextRef.current = currentInput.trim();
      finalTranscriptRef.current = "";

      const recognition = new Recognition();
      recognition.lang = navigator.language || "en-US";
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onresult = (event) => {
        let interim = "";
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const result = event.results[index];
          const transcript = result[0]?.transcript ?? "";
          if (result.isFinal) {
            finalTranscriptRef.current += transcript;
          } else {
            interim += transcript;
          }
        }
        mergeTranscript(interim);
      };

      recognition.onerror = (event) => {
        if (event.error === "aborted" || stoppingRef.current) {
          return;
        }
        if (event.error === "no-speech") {
          setError("No speech was detected. Try speaking again.");
        } else if (event.error === "not-allowed") {
          setError(
            "Microphone access was denied. Allow the microphone in your browser or system settings.",
          );
        } else {
          setError("Could not capture voice input.");
        }
        setListening(false);
        recognitionRef.current = null;
      };

      recognition.onend = () => {
        setListening(false);
        recognitionRef.current = null;
        stoppingRef.current = false;
      };

      try {
        recognition.start();
      } catch {
        setError("Could not start voice input.");
        recognitionRef.current = null;
        stoppingRef.current = false;
        return;
      }

      recognitionRef.current = recognition;
      setListening(true);
    },
    [mergeTranscript],
  );

  const toggle = useCallback(
    (currentInput: string) => {
      if (listening) {
        stop();
        return;
      }

      startListening(currentInput);
    },
    [listening, startListening, stop],
  );

  return { supported, listening, error, toggle, stop };
}
