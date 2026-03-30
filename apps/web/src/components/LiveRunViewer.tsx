"use client";

import { useEffect, useRef, useState } from "react";

import styles from "./interactive.module.css";

type TraceEvent = {
  id: string;
  run_id: string;
  sequence_number: number;
  step_key: string;
  title: string;
  message: string;
  level: string;
  created_at: string;
};

type RunStatus = {
  status: string;
};

function levelClass(level: string): string {
  switch (level) {
    case "warning":
      return styles.levelWarning;
    case "error":
      return styles.levelError;
    default:
      return styles.levelInfo;
  }
}

export default function LiveRunViewer({
  caseId,
  runId,
  initialStatus,
}: {
  caseId: string;
  runId: string;
  initialStatus: string;
}) {
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [status, setStatus] = useState(initialStatus);
  const [connected, setConnected] = useState(false);
  const streamRef = useRef<HTMLDivElement>(null);

  const isTerminal =
    status === "completed" || status === "failed" || status === "cancelled";

  useEffect(() => {
    if (isTerminal) return;

    let es: EventSource | null = null;

    try {
      es = new EventSource(
        `/api/v1/cases/${caseId}/runs/${runId}/stream`,
      );

      es.onopen = () => {
        setConnected(true);
      };

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as TraceEvent | RunStatus;
          if ("sequence_number" in data) {
            setEvents((prev) => {
              const exists = prev.some((ev) => ev.id === data.id);
              if (exists) return prev;
              return [...prev, data];
            });
          }
          if ("status" in data) {
            setStatus(data.status);
          }
        } catch {
          // Ignore malformed SSE data
        }
      };

      es.onerror = () => {
        setConnected(false);
        es?.close();
      };
    } catch {
      // SSE not supported or connection failed
    }

    return () => {
      es?.close();
    };
  }, [caseId, runId, isTerminal]);

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div>
      {!isTerminal && (
        <div className={styles.connecting}>
          <span className={styles.dot} />
          <span>{connected ? "Connected — streaming live events" : "Connecting to event stream..."}</span>
        </div>
      )}

      {isTerminal && events.length === 0 && (
        <p style={{ color: "var(--muted)", padding: "14px" }}>
          Run is {status}. No live events to display.
        </p>
      )}

      {events.length > 0 && (
        <div className={styles.eventStream} ref={streamRef}>
          {events.map((event) => (
            <div key={event.id} className={styles.eventItem}>
              <span className={styles.eventSeq}>
                #{event.sequence_number}
              </span>
              <div>
                <div className={styles.eventTitle}>{event.title}</div>
                <div className={styles.eventMessage}>{event.message}</div>
              </div>
              <span className={levelClass(event.level)}>
                {event.level}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
