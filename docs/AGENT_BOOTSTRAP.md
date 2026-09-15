# Agent bootstrap

## Single prompt

Use this prompt from any fresh coding-agent session:

> Clone/open `Rajeev-SG/ai-discovery-intelligence`. Read `AGENTS.md` and all documents it requires. Inspect all open GitHub issues, then work through the numbered implementation issues in dependency order autonomously. For every issue, use the adopted mature OSS components rather than building generic infrastructure yourself, satisfy every acceptance criterion, run tests, and produce the issue's required real product proof using live/free source data. Add the proof to the PR/issue before closing it. Continue to the next unblocked issue without waiting for me. If blocked only by credentials or external access, complete everything else, document the exact blocker and move to the next independent issue.

## Expected agent loop

1. Pull latest `main`.
2. Read the issue and linked architecture docs.
3. Inspect existing implementation before writing anything.
4. Confirm adopted OSS covers each generic requirement.
5. Implement the smallest vertical slice that creates useful output.
6. Test deterministically.
7. Run the product against real free sources.
8. Capture proof: example record, rendered page, brief, diff, URL, screenshot, or exported artifact.
9. Update docs/config.
10. Open/merge PR according to repository policy and close the issue only with proof.
11. Move to the next unblocked numbered issue.

## What “useful product output” means

Good: “The source pipeline ingested Similarweb's September AI referral report, extracted the stated 770.7M monthly referrals, linked the methodology, and the observation plane renders it under Channel Importance with Medium-High agency confidence.”

Bad: “RSS parser implemented; 18 tests pass.”
