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
  ocr_conf?: number | null;
  color_conf?: number | null;
  plate_valid?: boolean | null;
  image_asset_id?: number | null;
  plate_crop_asset_id?: number | null;
  // Ảnh của mọi camera đã lưu cho lượt này (làn đa camera) — chỉ có khi capture
  // đến từ postInfer của chính panel này (không có trên sự kiện WS/edge).
  images?: { role: string; image_asset_id: number; is_primary: boolean }[];
  duplicate?: boolean;
  // Thời gian từng giai đoạn suy luận (ms) và tài nguyên tiêu thụ. Backend chỉ
  // trả khi dev_mode bật, và chỉ cho lượt chụp từ portal (POST /captures/infer);
  // sự kiện từ edge worker không có vì worker không tự đo.
  timings_ms?: Record<string, number> | null;
  resources?: Record<string, number> | null;
  // Frontend-only: object URL của khung hình vừa chụp ở máy trạm (không qua
  // server), để hiện ngay ảnh đúng khung đã gửi model. Capture từ WS không có.
  local_image_url?: string;
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

/** Bản có lọc theo làn: chạy nhiều làn thì mỗi panel chỉ nhận capture đúng làn
 * đang trực, không bị làn khác đè lên (trước đây `latestByDirection` gộp mọi
 * làn vào chung 1 "in"/1 "out", 2 làn cùng chiều tranh nhau 1 panel).
 * `lane` rỗng/undefined thì không lọc — giữ đúng hành vi cũ khi chưa cấu hình làn. */
export function latestForDirectionAndLane(
  events: GateCapture[], direction: "in" | "out", lane?: string | null,
): GateCapture | null {
  return events.find((e) => e.direction === direction && (!lane || e.lane === lane)) ?? null;
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
    // Trước đây WS rớt là chuyển hẳn sang polling 3 giây vĩnh viễn, không bao giờ
    // thử kết nối lại — mất realtime cho tới khi nhân viên tự tải lại trang.
    let retry: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;

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

    const scheduleReconnect = () => {
      if (closed || retry) return;
      // Giãn dần 1s → 30s để không đập liên tục vào server khi backend đang tắt.
      const delay = Math.min(30000, 1000 * 2 ** attempt);
      attempt += 1;
      retry = setTimeout(() => {
        retry = null;
        connect();
      }, delay);
    };

    function connect() {
      if (closed) return;
      try {
        ws = new WebSocket(wsUrl());
        ws.onopen = () => {
          attempt = 0;
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
          if (!closed) {
            startPolling(); // vẫn có dữ liệu trong lúc chờ kết nối lại
            scheduleReconnect();
          }
        };
      } catch {
        startPolling();
        scheduleReconnect();
      }
    }

    connect();

    return () => {
      closed = true;
      stopPolling();
      if (retry) clearTimeout(retry);
      ws?.close();
    };
  }, [opts?.lane]);

  return { ...state, capturesByDirection: latestByDirection(state.events), connected, degraded };
}
