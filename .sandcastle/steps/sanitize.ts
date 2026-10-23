// Agent text that plain steps post as comments.
//
// The pipeline's comments carry hidden markers (`<!-- factory:... -->`) that
// later jobs read to count tries. Comments are posted by the built-in token,
// so an agent's text appears under the same account as the markers. Two rules
// keep an agent from forging one:
//   1. Readers accept a marker only at the very start of a comment, which
//      plain code always writes itself.
//   2. This function breaks every HTML comment opener in agent text.
// It also breaks @-mentions, so agent text cannot notify other accounts.

export const sanitizeAgentText = (text: string): string =>
  text
    .replaceAll("<!--", "&lt;!--")
    .replace(/(^|[^\w`])@(?=[A-Za-z0-9])/g, "$1@​");
