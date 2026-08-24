import { ingestEvent, type GateState, type GateCapture } from "./use-gate-socket";

const evt = (id: string): GateCapture => ({
  reading_id: Number(id.slice(1)),
  capture_id: id,
  direction: "in",
  review_state: "confident",
  plate_text: "51F",
  vehicle_group: "car",
});

test("dedupes by capture_id and keeps newest first", () => {
  let s: GateState = { capture: null, events: [] };
  s = ingestEvent(s, evt("c1"));
  s = ingestEvent(s, evt("c2"));
  s = ingestEvent(s, evt("c1")); // duplicate fully ignored (no resurface, no re-append)
  expect(s.events.map((e) => e.capture_id)).toEqual(["c2", "c1"]);
  expect(s.capture?.capture_id).toBe("c2");
});

test("caps event history at 30", () => {
  let s: GateState = { capture: null, events: [] };
  for (let i = 0; i < 40; i++) s = ingestEvent(s, evt(`c${i}`));
  expect(s.events.length).toBe(30);
});
