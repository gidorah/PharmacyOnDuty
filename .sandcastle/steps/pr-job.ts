// The start of every pull request job (review and fix): plain code.
//
// It checks the pull request, records a restart when Onur added the label
// himself, and reads the pipeline's markers for the try counters.

import {
  addLabels,
  comment,
  type GitHub,
  listComments,
  removeLabels,
  runUrl,
  setOutputs,
} from "./github.ts";
import { type DatedMarker, type Marker, markerLine, readMarkers, sinceReset } from "./markers.ts";
import { checkPullRequest, fetchPullRequest, type PullRequest } from "./pr-context.ts";

export interface PrJob {
  readonly pr: PullRequest;
  readonly workOrder: string;
  readonly markers: readonly DatedMarker[];
  /** Markers since Onur's last restart: what the try counters read. */
  readonly current: readonly Marker[];
}

export interface PrJobOptions {
  readonly number: number;
  /** "review" or "fix", for messages. */
  readonly job: string;
  /** The label that starts this job when Onur adds it. */
  readonly label: string;
  /** True when Onur's label started the run, false for a pipeline dispatch. */
  readonly startedByOwner: boolean;
}

export const startPrJob = (github: GitHub, options: PrJobOptions): PrJob | null => {
  const { number, job, label, startedByOwner } = options;
  const pr = fetchPullRequest(github, number);
  const check = checkPullRequest(github, pr);
  if (!check.ok) {
    removeLabels(github, number, [label]);
    if (pr.state === "open") {
      addLabels(github, number, ["agent:blocked"]);
      comment(github, number, [`**The ${job} job refused to run.**`, "", check.reason, "", `Pipeline run: ${runUrl()}`].join("\n"));
    }
    setOutputs({ proceed: false });
    console.log(`Refused: ${check.reason}`);
    return null;
  }
  const labels = pr.labels.map((l) => l.name);
  if (!startedByOwner && (labels.includes("agent:stuck") || labels.includes("agent:blocked"))) {
    // A dispatch that was queued before the item stopped. Onur restarts it.
    setOutputs({ proceed: false });
    console.log(`#${number} is stuck or blocked; a dispatched ${job} does not run. Onur restarts it with a label.`);
    return null;
  }
  removeLabels(github, number, startedByOwner ? [label, "agent:blocked", "agent:stuck"] : [label]);
  if (startedByOwner) {
    comment(
      github,
      number,
      [markerLine({ kind: "reset", label }), `Onur added \`${label}\`, so the ${job} job starts and the try counts start again.`].join("\n"),
    );
  }
  addLabels(github, number, ["agent:in-progress"]);
  const markers = readMarkers(listComments(github, number));
  return { pr, workOrder: check.workOrder, markers, current: sinceReset(markers) };
};
