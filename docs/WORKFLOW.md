# Workflow: campaigns, streams and two-hour parts

Status: a plan. Each step says whether it exists yet. Written 2026-11-21.

## How it ran in SnipRiot (as the owner described it)

1. Look at the campaigns in the Content Rewards account, and apply to the ones that fit.
2. Look at the streamers who are live under a topic, for example GTA VI.
3. Download their streams automatically.
4. Work in two-hour parts: cut the moments, edit, clip, and have them ready.

## How Clipz Hub does it

| Step | Automatic? | Who decides | Status |
| --- | --- | --- | --- |
| Campaign list: the campaigns you are in or want, with rules and deadlines | You add them, the app keeps the list | You | Planned |
| Application help: drafted answers and a requirements check | Drafts only | You press Apply yourself | Planned |
| Topic search: live and recent streams for a topic | Read-only, through the official YouTube and Twitch APIs. Needs free API keys you create | You create the keys | Planned |
| Getting the stream file | Only where the stream's rules allow it | You, or a tool after review | Not built |
| Two-hour parts: scan each part for moments | Yes | You run it | Built (`core.moments --chunk-hours 2`) |
| Cut, caption, style and render | Yes | You approve each clip | Built for two styles |
| Post text: hook, caption, hashtags | Yes | You approve | Built (rules) |
| Posting | No | You | Manual, by design |

## Limits

- **Downloading streams automatically is the riskiest part.** Platform terms and campaign rules
  decide what is allowed. Until you confirm, for each stream source, that downloading is allowed,
  Clipz Hub will not capture streams by itself. Before a company depends on this, the terms need a
  review.
- **Applying to campaigns is an action on your account.** Clipz Hub drafts; you submit.
- **API keys and passwords** are never pasted into chat and never stored in the repository.
- **Every clip needs your approval** before it is marked ready.
