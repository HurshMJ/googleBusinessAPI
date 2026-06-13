---
name: repo-discord-digest
description: Summarize a chosen repository's recent commits and post a graceful, skimmable digest into a Discord channel using the web app's managed webhooks. Use when asked to share what changed in a repo to Discord, send a release/commit digest, or post a "what shipped" update.
---

# repo-discord-digest

Build a human-readable digest of a repository's recent changes and deliver it to
a Discord channel through the TriAgentLoop web app's managed Discord webhooks.
You — the agent running this skill — gather the commits and **write the summary
yourself**; there is no summariser binary to call. Delivery reuses the web
app's existing managed-webhook endpoints, so the bot token and webhook URLs
never pass through this skill.

## When to use

- The user asks to post "what changed", a commit digest, a release summary, or a
  "what shipped this week" update for a repo into Discord.
- The user wants a readable rollup of recent commits sent to a team channel.

## When not to use

- The user wants the raw `git log` or a diff, not a written summary — run the git
  command directly instead.
- The user wants to send a single file or arbitrary terminal text to Discord —
  that is the web app's existing Discord output, not this skill.
- The web app and its managed Discord config are unavailable and the user has no
  raw webhook URL to fall back to — stop and report (see Stop conditions).

## Inputs

- **Skill argument = the target repo.** Resolve it as one of three cases:
  1. **Blank** → default to `${TAL_PROJECT_ROOT:-.}` (the current project repo).
  2. **A local path** (absolute or relative, points at a git work tree) → read it
     locally with `git`.
  3. **A GitHub `owner/repo` slug** → read it remotely with `gh` (no clone).
  If the argument is ambiguous (e.g. a bare word that could be a path or a slug),
  ask the user which they mean before proceeding.

## Workflow steps

### 1. Resolve the target repo

Classify the argument per the three cases above. For a local path, confirm it is
a git work tree (`git -C <path> rev-parse --git-dir`). For a slug, confirm
access and auth with `gh repo view <owner>/<repo>` before any data calls; if
that fails, surface the `gh` auth/access error rather than summarising nothing.

### 2. Pick the change window

Default order:
1. Commits since the most recent tag, if the repo has tags
   (`git -C <path> describe --tags --abbrev=0` for the base locally; for GitHub,
   the latest tag via `gh api repos/<owner>/<repo>/tags`).
2. Otherwise the last ~20 commits.
3. Otherwise a ref range or date the user supplies (e.g. `since=2026-06-01`, or
   `v1.2.0..HEAD`).

State the window you chose in the digest header so the reader knows the scope.

### 3. Gather commits and changes

- **Local** (`git`):
  - `git -C <path> log <range> --stat` for per-commit subjects + changed files.
  - `git -C <path> log <range> --shortstat` (or `git -C <path> diff --shortstat
    <base>..<head>`) for the aggregate files-changed / insertions / deletions
    totals.
- **GitHub-only** (`gh`, no clone):
  - `gh api repos/<owner>/<repo>/commits` (paginate as needed) for the commit
    list and subjects within the window.
  - `gh api repos/<owner>/<repo>/compare/<base>...<head>` for an aggregate
    diffstat (`files`, `additions`, `deletions`, `total_commits`).

### 4. Write the summary yourself

- Group commits by Conventional Commit type: `feat`, `fix`, `docs`, `refactor`,
  `test`, `chore` (bucket anything untyped under a sensible heading like
  "Other").
- Lead with a header line: repo name + the change window + commit count + files
  changed + total `+`/`-` line counts.
- Use skimmable Discord markdown — short bold section headers and bullet lists,
  not a wall of text. Keep it readable, not a raw log dump.
- The server auto-chunks at Discord's 2000-character limit, so you may send the
  full message; do not pre-truncate it.

### 5. Choose the Discord channel

- `GET http://localhost:${TAL_WEB_PORT:-3000}/api/discord` returns
  `{ enabled, botConfigured, activeId, webhooks: [{ id, label, channelId,
  channelName }] }`. The response never contains a webhook URL or the bot token.
- If `enabled` is false or `webhooks` is empty, follow the fallbacks below.
- Let the user pick a webhook by `label` / `channelName`. If their pick's `id`
  differs from `activeId`, switch the target:
  `POST http://localhost:${TAL_WEB_PORT:-3000}/api/discord/webhooks/active` with
  body `{ "id": "<picked id>" }`.

### 6. Confirmation gate, then deliver

- **Preview** the drafted digest text and the resolved target channel
  (label / channel name) to the user, and post only on explicit confirmation.
- Skip the confirmation **only** under `FAST_AUTO`.
- Deliver:
  `POST http://localhost:${TAL_WEB_PORT:-3000}/api/discord/send` with body
  `{ "text": "<full digest>" }`. A `200` with `{ "ok": true }` means delivered;
  the server chunks long messages itself.

### 7. Fallbacks

- **Web app unreachable** (connection refused on the `/api/discord` GET): tell
  the user to start the web app from the project's `web/` directory and retry.
- **Discord disabled or no webhook** (`enabled` false or empty `webhooks`): tell
  the user to enable Discord and add a webhook in the web app's Settings.
- **No managed config at all**: as a last resort, post directly to a raw Discord
  webhook URL the user supplies for this run — splitting the message into
  ≤2000-character chunks yourself, since the managed auto-chunking is bypassed.

## Secret discipline

- **Never print, echo, or log the bot token or any webhook URL** — not in the
  digest, not in status output, not in the handoff record. The managed endpoints
  are sanitised by design (they return only `id` / `label` / `channelId` /
  `channelName`); preserve that containment when using a raw fallback URL by
  keeping the URL out of all output.

## Validation and evidence

- Confirm the source data was actually read: show the commit count and the
  aggregate diffstat you gathered (`git log --shortstat` output or the
  `gh ... compare` totals), not just a claim.
- Confirm delivery from the real response: a `200` / `{ "ok": true }` from
  `POST /api/discord/send`, or — when previewing only — the drafted text plus the
  resolved channel label. A digest that was composed but never posted is not a
  completed delivery; say so explicitly.

## Stop and escalation conditions

- Repo argument is ambiguous (could be a path or a slug) → ask the user.
- `gh repo view` fails for a slug (no access / not authenticated) → surface the
  error and stop; do not post an empty or guessed digest.
- The web app is unreachable, Discord is disabled, or there is no webhook and the
  user supplies no raw URL → report the fallback steps and stop.
- The user does not confirm the preview (outside `FAST_AUTO`) → do not post.

## Reporting

End with a compact handoff: append the appropriate record to the topic's handoff
log, then emit 3–5 bullets covering status (digest drafted / posted), the target
channel, the change window and commit count, and any blockers — never including a
token or webhook URL.
