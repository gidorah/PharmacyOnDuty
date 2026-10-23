// An in-memory stand-in for the `gh` wrapper, for unit tests.

import type { GitHub } from "../steps/github.ts";

type Handler = (body: unknown) => unknown;

export class FakeGitHub implements GitHub {
  readonly repo = "gidorah/PharmacyOnDuty";
  readonly calls: { method: string; path: string; body?: unknown }[] = [];
  readonly ghCalls: string[][] = [];
  private readonly routes = new Map<string, Handler>();
  graphqlResult: unknown = null;
  onGh: (args: string[]) => string = () => "";

  /** Register a response for `METHOD path` (the path without the repo prefix). */
  on(method: string, path: string, handler: Handler | unknown): this {
    this.routes.set(
      `${method} ${path}`,
      typeof handler === "function" ? (handler as Handler) : () => handler,
    );
    return this;
  }

  private strip(path: string): string {
    return path.replace(`repos/${this.repo}/`, "");
  }

  api<T>(path: string, options?: { method?: string; body?: unknown }): T {
    const method = options?.method ?? "GET";
    const short = this.strip(path);
    this.calls.push({ method, path: short, body: options?.body });
    const handler = this.routes.get(`${method} ${short}`);
    if (!handler) throw new Error(`No fake route for ${method} ${short}`);
    return handler(options?.body) as T;
  }

  paginate<T>(path: string): T[] {
    return this.api<T[]>(path);
  }

  graphql<T>(): T {
    return this.graphqlResult as T;
  }

  gh(args: string[]): string {
    this.ghCalls.push(args);
    return this.onGh(args);
  }
}
