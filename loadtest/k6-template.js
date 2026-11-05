// k6 template: mixed read-path load with ramping arrival rate. Replace MIX with your endpoints.
// Exclude LLM-bound endpoints: their ceiling is the provider TPM, not your service.
import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:18080";
const TARGET = Number(__ENV.TARGET_RPS || 100);
const HEADERS = { headers: { "X-User-Email": __ENV.USER_EMAIL || "loadtest@example.com" } };

const profiles = {
  // Smoke: 1 minute at 5 RPS, checks the stand works.
  smoke: { executor: "constant-arrival-rate", rate: 5, timeUnit: "1s", duration: "1m", preAllocatedVUs: 10, maxVUs: 50 },
  // Ramp: steps to TARGET_RPS, 1 minute per step, to find where p95 and errors break.
  ramp: {
    executor: "ramping-arrival-rate", startRate: 10, timeUnit: "1s", preAllocatedVUs: 50, maxVUs: 400,
    stages: [
      { target: Math.round(TARGET * 0.25), duration: "30s" }, { target: Math.round(TARGET * 0.25), duration: "1m" },
      { target: Math.round(TARGET * 0.5), duration: "30s" }, { target: Math.round(TARGET * 0.5), duration: "1m" },
      { target: TARGET, duration: "30s" }, { target: TARGET, duration: "2m" },
    ],
  },
};

export const options = {
  scenarios: { main: profiles[__ENV.PROFILE || "ramp"] },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<300"],
    "http_req_duration{ep:projects}": ["p(95)<500"],
  },
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "p(99)", "max"],
};

// Weighted request mix of a typical session.
const MIX = [
  [0.30, "health", "/api/health"],
  [0.20, "me", "/api/me"],
  [0.30, "projects", "/api/projects"],
  [0.10, "version", "/api/version"],
  [0.10, "spa", "/"],
];

export default function () {
  let r = Math.random();
  for (const [w, ep, path] of MIX) {
    if ((r -= w) <= 0) {
      const res = http.get(BASE + path, Object.assign({ tags: { ep } }, HEADERS));
      check(res, { "status 2xx": (x) => x.status >= 200 && x.status < 300 });
      return;
    }
  }
}
