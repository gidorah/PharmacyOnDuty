// Reads a work order (a GitHub issue) for an agent, keeping only what Onur
// approved or wrote.
//
// The repository is public. Anyone can comment on an issue, and the issue's
// author can edit its body and title after Onur approves it with the
// `agent:implement` label. So:
//   - agents see only Onur's comments (Sandcastle passes every comment);
//   - a job refuses to run when anyone other than Onur edited the body or the
//     title after Onur's latest `agent:implement` label.

import { OWNER_LOGIN, type GitHub, type IssueComment, listComments } from "./github.ts";

export const APPROVAL_LABEL = "agent:implement";

// Factory pull requests use one branch per work order, so a pull request
// leads back to its work order without parsing text an agent wrote.
export const branchForIssue = (issue: number): string => `factory/issue-${issue}`;

export const issueForBranch = (branch: string): number | null => {
  const match = /^factory\/issue-(\d+)$/.exec(branch);
  return match ? Number(match[1]) : null;
};

export interface IssueSnapshot {
  readonly number: number;
  readonly title: string;
  readonly body: string;
  readonly url: string;
  readonly state: string;
  readonly author: string | null;
  readonly bodyEdits: readonly { editedAt: string; editor: string | null }[];
  readonly labelEvents: readonly {
    createdAt: string;
    actor: string | null;
    label: string;
  }[];
  readonly renames: readonly { createdAt: string; actor: string | null }[];
}

const ISSUE_QUERY = `
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      number
      title
      body
      url
      state
      author { login }
      userContentEdits(last: 100) {
        nodes { editedAt editor { login } }
      }
      timelineItems(last: 100, itemTypes: [LABELED_EVENT, RENAMED_TITLE_EVENT]) {
        nodes {
          __typename
          ... on LabeledEvent { createdAt actor { login } label { name } }
          ... on RenamedTitleEvent { createdAt actor { login } }
        }
      }
    }
  }
}`;

interface IssueQueryResult {
  repository: {
    issue: {
      number: number;
      title: string;
      body: string;
      url: string;
      state: string;
      author: { login: string } | null;
      userContentEdits: {
        nodes: { editedAt: string; editor: { login: string } | null }[];
      };
      timelineItems: {
        nodes: {
          __typename: string;
          createdAt?: string;
          actor?: { login: string } | null;
          label?: { name: string };
        }[];
      };
    } | null;
  };
}

/**
 * Body, title, edit history and label history in one GraphQL response, so the
 * edit check and the text the agent reads come from the same moment.
 */
export const fetchIssueSnapshot = (
  github: GitHub,
  number: number,
): IssueSnapshot | null => {
  const [owner, name] = github.repo.split("/");
  let data: IssueQueryResult;
  try {
    data = github.graphql<IssueQueryResult>(ISSUE_QUERY, { owner, name, number });
  } catch (error) {
    // A pull request number, or no such item.
    if (String(error).includes("Could not resolve to an Issue")) return null;
    throw error;
  }
  const issue = data.repository.issue;
  if (!issue) return null;
  const items = issue.timelineItems.nodes;
  return {
    number: issue.number,
    title: issue.title,
    body: issue.body,
    url: issue.url,
    state: issue.state,
    author: issue.author?.login ?? null,
    bodyEdits: issue.userContentEdits.nodes.map((n) => ({
      editedAt: n.editedAt,
      editor: n.editor?.login ?? null,
    })),
    labelEvents: items
      .filter((n) => n.__typename === "LabeledEvent")
      .map((n) => ({
        createdAt: n.createdAt ?? "",
        actor: n.actor?.login ?? null,
        label: n.label?.name ?? "",
      })),
    renames: items
      .filter((n) => n.__typename === "RenamedTitleEvent")
      .map((n) => ({ createdAt: n.createdAt ?? "", actor: n.actor?.login ?? null })),
  };
};

export type ApprovalCheck =
  | { readonly ok: true; readonly approvedAt: string }
  | { readonly ok: false; readonly reason: string };

const after = (a: string, b: string): boolean => Date.parse(a) > Date.parse(b);

/**
 * Onur approved the work order, and nobody else changed its body or title
 * since. Edits by Onur himself are fine: he is the one approving.
 */
export const checkApproval = (
  issue: IssueSnapshot,
  owner = OWNER_LOGIN,
): ApprovalCheck => {
  const approvals = issue.labelEvents
    .filter((e) => e.label === APPROVAL_LABEL && e.actor === owner)
    .map((e) => e.createdAt)
    .sort((a, b) => Date.parse(a) - Date.parse(b));
  const approvedAt = approvals.at(-1);
  if (!approvedAt) {
    return {
      ok: false,
      reason: `#${issue.number} has no \`${APPROVAL_LABEL}\` label added by @${owner}, so it is not an approved work order.`,
    };
  }
  const who = (login: string | null) => (login ? `@${login}` : "a deleted account");
  const problems = [
    ...issue.bodyEdits
      .filter((e) => after(e.editedAt, approvedAt) && e.editor !== owner)
      .map((e) => `${who(e.editor)} edited the body at ${e.editedAt}`),
    ...issue.renames
      .filter((r) => after(r.createdAt, approvedAt) && r.actor !== owner)
      .map((r) => `${who(r.actor)} changed the title at ${r.createdAt}`),
  ];
  if (problems.length > 0) {
    return {
      ok: false,
      reason: [
        `The work order changed after @${owner} approved it at ${approvedAt}:`,
        ...problems.map((p) => `- ${p}`),
        "",
        `Read the current text, then add \`${APPROVAL_LABEL}\` again to approve it.`,
      ].join("\n"),
    };
  }
  return { ok: true, approvedAt };
};

export const ownerComments = (
  comments: readonly IssueComment[],
  owner = OWNER_LOGIN,
): IssueComment[] => comments.filter((c) => c.user?.login === owner);

export const renderWorkOrder = (
  issue: IssueSnapshot,
  approvedAt: string,
  comments: readonly IssueComment[],
  owner = OWNER_LOGIN,
): string => {
  const parts = [
    `# Work order #${issue.number}: ${issue.title}`,
    "",
    `${issue.url}`,
    `Approved by @${owner} at ${approvedAt}.`,
    "",
    "## Work order",
    "",
    issue.body.trim() || "(empty)",
  ];
  const own = ownerComments(comments, owner);
  if (own.length > 0) {
    parts.push("", `## Comments from @${owner}`, "");
    for (const c of own) {
      parts.push(`### ${c.created_at}`, "", c.body.trim(), "");
    }
  }
  parts.push(
    "",
    `(Only @${owner}'s comments are included. Comments from other accounts are left out on purpose.)`,
  );
  return parts.join("\n");
};

export type WorkOrderRead =
  | { readonly ok: true; readonly issue: IssueSnapshot; readonly text: string }
  | { readonly ok: false; readonly reason: string };

/** Everything a job needs before an agent may read the work order. */
export const readWorkOrder = (github: GitHub, number: number): WorkOrderRead => {
  const issue = fetchIssueSnapshot(github, number);
  if (!issue) return { ok: false, reason: `#${number} is not an issue.` };
  const approval = checkApproval(issue);
  if (!approval.ok) return approval;
  const text = renderWorkOrder(issue, approval.approvedAt, listComments(github, number));
  return { ok: true, issue, text };
};
