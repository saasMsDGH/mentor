// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("API_INTERNAL_URL", "");
  vi.stubEnv("NEXT_PUBLIC_API_URL", "");
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("API origin separation", () => {
  it("keeps browser calls on /api even with a private backend configured", async () => {
    vi.stubGlobal("window", {});
    vi.stubEnv("API_INTERNAL_URL", "http://mentor-api:8000/api");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://legacy.example/api");
    expect((await import("./base-url")).API_BASE).toBe("/api");
  });
  it("uses the private backend for server calls", async () => {
    vi.stubEnv("API_INTERNAL_URL", "http://mentor-api:8000/api");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://legacy.example/api");
    expect((await import("./base-url")).API_BASE).toBe("http://mentor-api:8000/api");
  });
  it("preserves the configured legacy server endpoint", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://legacy.example/api");
    expect((await import("./base-url")).API_BASE).toBe("https://legacy.example/api");
  });
  it("preserves the relative default", async () => {
    expect((await import("./base-url")).API_BASE).toBe("/api");
  });
});
