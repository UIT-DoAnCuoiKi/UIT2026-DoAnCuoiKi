import { ingestEvent, latestByDirection, type GateState, type GateCapture } from "./use-gate-socket";

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

test("latestByDirection picks newest per direction", () => {
  const evts: GateCapture[] = [
    { reading_id: 3, capture_id: "c3", direction: "out", review_state: "confident" },
    { reading_id: 2, capture_id: "c2", direction: "in", review_state: "confident" },
    { reading_id: 1, capture_id: "c1", direction: "in", review_state: "confident" },
  ];
  const r = latestByDirection(evts);
  expect(r.in?.capture_id).toBe("c2");
  expect(r.out?.capture_id).toBe("c3");
});
