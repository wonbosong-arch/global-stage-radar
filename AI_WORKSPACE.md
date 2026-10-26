# AI Workspace Ownership & Change Rules

**Workspace owner:** ChatGPT-assisted migration work  
**Target integration branch:** `data-validation-mvp`  
**Current working branch:** `migration/main-to-data-validation-mvp`  
**Last updated:** 2026-10-26

## Scope boundary
- This branch and its pull request are the designated workspace for the current ChatGPT-assisted migration.
- Do not make unrelated edits to `main`, `data-validation-mvp`, the existing Streamlit apps, deployment settings, secrets, or PR #46.
- Keep migration work on this branch and propose changes to `data-validation-mvp` through a draft pull request.
- Do not merge this migration PR until dependencies, workflows, data files, and automated tests have been reviewed.
- Preserve existing branches and use additive commits; never force-push or reset the original branch as part of this work.
- Scheduled workflows must not write to `main` unless that behavior has been explicitly reviewed and approved.

## Important limitation
This file is a visible coordination marker, **not a technical lock**. Other AI tools or collaborators can still edit the branch. To enforce a boundary, the repository owner must configure GitHub branch rules/rulesets requiring pull requests and restrict direct pushes; use separate branches for each agent and review every PR.

## Current migration status
- Core dashboard files are staged in this branch.
- Candidate collection and report workflows and their dependent modules/data are not yet fully migrated.
- Hosted app behavior and live KIS API have not been manually validated; user requested skipping manual validation for now.
