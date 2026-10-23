// What a review or fix agent may read about a pull request. Plain code.
//
// The repository is public, so the pull request jobs accept only pull
// requests from this repository's branches, opened by the pipeline, by Onur
// or by Dependabot. The agent reads the work order and Onur's comments, never
// other accounts' comments.

import {
  BOT_LOGIN,
  type GitHub,
  type IssueComment,
  listComments,
  OWNER_LOGIN,
} from "./github.ts";
import { issueForBranch, ownerComments, readWorkOrder } from "./work-order.ts";

export const DEPENDABOT_LOGIN = "dependabot[bot]";

export interface PullRequest {
  readonly number: number;
  readonly state: string;
  readonly draft: boolean;
  readonly title: string;
  readonly body: string | null;
  readonly html_url: string;
  readonly user: { readonly login: string };
  readonly head: { readonly ref: string; readonly sha: string; readonly repo: { readonly full_name: string } | null };
  readonly base: { readonly ref: string; readonly sha: string };
  readonly labels: readonly { readonly name: string }[];
}

export const fetchPullRequest = (github: GitHub, number: number): PullRequest =>
  github.api<PullRequest>(`repos/${github.repo}/pulls/${number}`);

export type PullRequestCheck =
  | { readonly ok: true; readonly workOrder: string; readonly issue: number | null }
  | { readonly ok: false; readonly reason: string };

/**
 * Whether a pull request job may run, and the work order its agent reads.
 *
 * - Factory pull requests (branch `factory/issue-<n>`, opened by the
 *   pipeline): the issue, with the same approval and edit check as the build.
 * - Onur's own pull requests: their description is the work order.
 * - Dependabot's: no work order. Their description is release notes from the
 *   package's authors, so the agent does not read it.
 */
export const checkPullRequest = (github: GitHub, pr: PullRequest): PullRequestCheck => {
  if (pr.state !== "open") return { ok: false, reason: `#${pr.number} is not open.` };
  if (pr.base.ref !== "main") return { ok: false, reason: `#${pr.number} does not target main.` };
  if (pr.head.repo?.full_name !== github.repo) {
    return { ok: false, reason: `#${pr.number} comes from another repository. Factory jobs run only on this repository's branches.` };
  }
  const author = pr.user.login;
  if (author === BOT_LOGIN) {
    const issue = issueForBranch(pr.head.ref);
    if (issue === null) {
      return { ok: false, reason: `#${pr.number} was opened by the pipeline but its branch \`${pr.head.ref}\` names no work order.` };
    }
    const read = readWorkOrder(github, issue);
    if (!read.ok) return read;
    return { ok: true, workOrder: read.text, issue };
  }
  if (author === OWNER_LOGIN) {
    return {
      ok: true,
      issue: null,
      workOrder: [`# Pull request #${pr.number}: ${pr.title}`, "", "## Description by @gidorah", "", pr.body?.trim() || "(empty)"].join("\n"),
    };
  }
  if (author === DEPENDABOT_LOGIN) {
    return {
      ok: true,
      issue: null,
      workOrder: [
        `# Dependabot pull request #${pr.number}: ${pr.title}`,
        "",
        "There is no work order. The change is a dependency update. Follow Onur's comments below, if any.",
      ].join("\n"),
    };
  }
  return { ok: false, reason: `#${pr.number} was opened by @${author}. Factory jobs run only on pull requests by the pipeline, @${OWNER_LOGIN} or Dependabot.` };
};

interface ReviewComment {
  readonly user: { readonly login: string } | null;
  readonly body: string;
  readonly path: string;
  readonly line: number | null;
  readonly original_line: number | null;
  readonly created_at: string;
}

interface Review {
  readonly user: { readonly login: string } | null;
  readonly body: string | null;
  readonly state: string;
  readonly submitted_at: string | null;
}

/** Onur's comments on the pull request: the conversation, line comments and review bodies. */
export const renderOwnerComments = (
  conversation: readonly IssueComment[],
  lineComments: readonly ReviewComment[],
  reviews: readonly Review[],
  owner = OWNER_LOGIN,
): string => {
  const parts: string[] = [];
  for (const c of ownerComments(conversation, owner)) {
    parts.push(`### Comment, ${c.created_at}`, "", c.body.trim(), "");
  }
  for (const r of reviews.filter((r) => r.user?.login === owner && r.body?.trim())) {
    parts.push(`### Review (${r.state}), ${r.submitted_at ?? ""}`, "", (r.body ?? "").trim(), "");
  }
  for (const c of lineComments.filter((c) => c.user?.login === owner)) {
    parts.push(`### On \`${c.path}\` line ${c.line ?? c.original_line ?? "?"}, ${c.created_at}`, "", c.body.trim(), "");
  }
  return parts.length > 0
    ? parts.join("\n")
    : `(No comments from @${owner}. Comments from other accounts are left out on purpose.)`;
};

export const fetchOwnerComments = (github: GitHub, number: number): string =>
  renderOwnerComments(
    listComments(github, number),
    github.paginate<ReviewComment>(`repos/${github.repo}/pulls/${number}/comments?per_page=100`),
    github.paginate<Review>(`repos/${github.repo}/pulls/${number}/reviews?per_page=100`),
  );
