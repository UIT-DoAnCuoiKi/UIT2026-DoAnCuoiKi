import { reviewStateMeta, sessionStatusMeta } from "./status";

test("review_state maps to token + label", () => {
  expect(reviewStateMeta("confident").token).toBe("st-green");
  expect(reviewStateMeta("needs_review").token).toBe("st-amber");
  expect(reviewStateMeta("disputed").token).toBe("st-red");
  expect(reviewStateMeta("manual").token).toBe("st-purple");
  expect(reviewStateMeta("confident").label).toBe("Tin cậy");
});

test("session status maps", () => {
  expect(sessionStatusMeta("completed").token).toBe("st-green");
  expect(sessionStatusMeta("in_lot").token).toBe("st-blue");
  expect(sessionStatusMeta("disputed").token).toBe("st-red");
  expect(sessionStatusMeta("pending_manual").token).toBe("st-purple");
});

test("unknown falls back to grey", () => {
  expect(reviewStateMeta("weird").token).toBe("st-grey");
  expect(sessionStatusMeta("weird").token).toBe("st-grey");
});
