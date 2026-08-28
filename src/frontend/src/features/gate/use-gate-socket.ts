import { useEffect, useRef, useState } from "react";
import { latestCapture } from "@/api/generated/captures/captures";

export type GateCapture = {
  reading_id: number;
  capture_id: string;
  direction: string;
  lane?: string | null;
  review_state: string;
  plate_text?: string | null;
  vehicle_group?: string | null;
  vehicle_type?: string | null;
  color?: string | null;
  plate_valid?: boolean | null;
  image_asset_id?: number | null;
  duplicate?: boolean;
};

export type GateState = { capture: GateCapture | null; events: GateCapture[] };

const MAX = 30;

// Idempotent reducer: dedupe by capture_id, newest first, capped history.
export function ingestEvent(state: GateState, evt: GateCapture): GateState {
  if (state.events.some((e) => e.capture_id === evt.capture_id)) return state;
  const events = [evt, ...state.events].slice(0, MAX);
  return { capture: evt, events };
}

export function latestByDirection(events: GateCapture[]): { in: GateCapture | null; out: GateCapture | null } {
  return {
    in: events.find((e) => e.direction === "in") ?? null,
    out: events.find((e) => e.direction === "out") ?? null,
  };
}

function wsUrl(): string {
  const base =
    (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_BASE ??
    "http://localhost:8000";
  return base.replace(/^http/, "ws") + "/ws/gate";
}

export function useGateSocket(opts?: { lane?: string }): GateState & {
  connected: boolean;
  degraded: boolean;
  capturesByDirection: { in: GateCapture | null; out: GateCapture | null };
} {
  const [state, setState] = useState<GateState>({ capture: null, events: [] });
  const [connected, setConnected] = useState(false);
  const [degraded, setDegraded] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;

    const startPolling = () => {
      if (pollRef.current) return;
      setDegraded(true);
      pollRef.current = setInterval(async () => {
        try {
          const c = (await latestCapture(
            opts?.lane ? { lane: opts.lane } : undefined,
          )) as GateCapture | null;
          if (c && c.capture_id) setState((s) => ingestEvent(s, c));
        } catch {
          /* keep polling */
        }
      }, 3000);
    };
    const stopPolling = () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };

    try {
      ws = new WebSocket(wsUrl());
      ws.onopen = () => {
        setConnected(true);
        setDegraded(false);
        stopPolling();
      };
      ws.onmessage = (m) => {
        try {
          const evt = JSON.parse(m.data) as GateCapture;
          setState((s) => ingestEvent(s, evt));
        } catch {
          /* ignore malformed */
        }
      };
      ws.onerror = () => {
        if (!closed) startPolling();
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closed) startPolling();
      };
    } catch {
      startPolling();
    }

    return () => {
      closed = true;
      stopPolling();
      ws?.close();
    };
  }, [opts?.lane]);

  return { ...state, capturesByDirection: latestByDirection(state.events), connected, degraded };
}
