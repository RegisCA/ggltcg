---
name: wrap-session
description: >-
  End-of-session environment hygiene for the ggltcg repo. Run this to safely
  close out a working session: confirm no background subagents are still
  running, get back onto an up-to-date `main`, prune branches whose PRs have
  merged, and reset the `gh` account to RegisCA. Use whenever the user signals
  they're wrapping up — "let's wrap up", "end the session", "clean up before I
  go", "back to main", "we're done for today" — or asks to tidy the environment
  for the next session. This is environment cleanup ONLY; it deliberately does
  not write memories or update handoff docs (do those separately, they need
  judgment).
---

# Wrap Session

Close out a ggltcg working session leaving a clean environment for the next one:
on an up-to-date `main`, no merged branch clutter, the `gh` account back to
`RegisCA`, and nothing half-finished silently left behind.

The guiding principle: **report first, act only on what's provably safe.** The
report exists to catch the cases where cleanup would destroy something you want
to keep — uncommitted work, a stash, a branch whose PR was closed rather than
merged. Never let the convenience of "tidy up" delete signal.

## Phase 1 — Status report (read-only, never destructive)

Gather and show the user the full picture before touching anything. Run these
and summarize:

```bash
git branch                                    # where am I, what's local
git status --short                            # uncommitted / untracked work
git stash list                                # stray stashes
git fetch origin --quiet && git status -sb    # is main behind its remote?
gh auth status 2>&1 | grep -iB1 "Active account: true"   # which account is live
```

Then, for **every local branch except `main`**, determine its PR state — this
drives what's safe to delete in Phase 2:

```bash
for b in $(git branch --format='%(refname:short)' | grep -v '^main$'); do
  echo "$b: $(gh pr list --head "$b" --state all --json number,state -q '.[] | "#\(.number) \(.state)"' | tr '\n' ' ')"
done
```

**The one thing no command can tell you: are any background subagents still
running?** In this repo agents share the working tree, so a loose one can still
be writing files, committing, or even switching your `gh` account after you
think the session is over. You cannot verify this with git — reason from the
session itself: has every agent you spawned reported completion? If you started
one in the background and haven't seen it finish, say so and stop here. Don't
run Phase 2 with an agent still live.

Surface anything that needs a human decision rather than proceeding silently:

- **Uncommitted or untracked work** (`git status`) — this is a decision, not
  cleanup. Ask; never `checkout .`/`reset --hard`/`clean` it away.
- **Stashes** — list them; never auto-drop (recovered work has hidden here before).
- **Branches with a CLOSED-unmerged PR or NO PR** — these are *not* safe to
  delete. A closed-unmerged PR often means the user killed a bad approach on
  purpose; a branch with no PR may be unpushed work. Name them and let the user
  decide.

## Phase 2 — Cleanup (only once Phase 1 is clean)

Proceed only when: no background agent is running, the working tree is clean (or
the user has explicitly OK'd leaving/handling the changes), and you've listed
any judgment-call branches for the user.

```bash
gh auth switch -u RegisCA        # sessions end on RegisCA; regisca-bot is only for creating PRs
git checkout main
git pull origin main --ff-only   # fast-forward only — a non-ff failure is a signal, not something to force
git remote prune origin          # drop remote-tracking refs for deleted branches
```

**Deleting merged branches — mind the squash-merge trap.** This repo merges PRs
via squash, so `git branch --merged main` will report merged branches as *NOT
merged* (their commits never appear on `main` verbatim). Do not rely on it, and
do not reach for `git branch -D` blindly to work around the resulting
"not fully merged" error — that flag will just as happily delete genuinely
unmerged work.

Instead, trust the PR state you gathered in Phase 1: a branch whose PR shows
`MERGED` is safe to force-delete; anything else is a Phase-1 judgment call.

```bash
# For each branch confirmed MERGED in Phase 1:
git branch -D <branch>
```

If you want the check inline, gate the delete on the PR being merged:

```bash
for b in $(git branch --format='%(refname:short)' | grep -v '^main$'); do
  state=$(gh pr list --head "$b" --state all --json state -q '.[0].state')
  if [ "$state" = "MERGED" ]; then
    git branch -D "$b" && echo "deleted $b (PR merged)"
  else
    echo "KEEP $b (PR state: ${state:-none}) — needs your call"
  fi
done
```

## What this skill will not do

- **Push anything.** Cleanup is local-only.
- **Discard uncommitted changes or stashes.**
- **Delete a branch without a merged PR.**
- **Run while a background agent is still active.**
- **Write memories or update handoff/plan docs.** That's deliberate, judgment-
  heavy work the user does separately — bundling it here would make the skill
  something you hesitate to run.

## Finish

Report the end state plainly: current branch (`main`), whether it fast-forwarded
and to what commit, which branches were deleted (with their PR numbers), which
were kept and why, and the active `gh` account. If anything was left for the
user to decide, restate it as the open item.
