import { git } from "./common.ts";

const MAX_DIFF_CHARS = 200_000;

/** A diff for a prompt, cut when it is too long to be useful. */
export const diffFor = (cwd: string, range: string): string => {
  const diff = git(cwd, ["diff", "--no-color", range]);
  return diff.length > MAX_DIFF_CHARS
    ? `${diff.slice(0, MAX_DIFF_CHARS)}\n[... diff cut at ${MAX_DIFF_CHARS} characters; read the files for the rest ...]`
    : diff || "(empty diff)";
};
