# Personal analysis on the verified private deployment

The operating app is deployed from `data-validation-mvp`, `app.py`, at
`global-stage-radar-kmb524zemj5vawb3ipampm.streamlit.app`.

Before enabling password-free analysis on 2026-11-12, the owner set Community
Cloud Sharing to **Only specific people can view this app**. The saved viewer
list was empty and GitHub showed zero collaborators. A signed-out normal URL
and the direct `/~/+/` app route in a completely new, unsigned-in Chrome
Incognito window showed **You do not have access to this app or it does not
exist / Please sign in**. The owner separately demonstrated signed-in access.
No credentials, cookies, tokens, or raw market observations are recorded here.

The Community Cloud private-app gateway authenticates the owner. The hostname
check in `private_analysis_access.py` only selects this preverified deployment;
it does not authenticate a browser or prove that an arbitrary host is private.
Missing/unrecognized deployment context retains the original analysis password.
Community Cloud settings are external to this repository and cannot be read
through `st.user` in current Streamlit. Keep the operating app private, and
repeat both permission and fresh anonymous-session checks before changing
hosting or this deployment selector. Never make this app public with this
analysis exception enabled.

On the verified deployment, ordinary analysis reads existing snapshots without
an extra KIS password. It does not set `kis_authenticated`, construct a KIS
client, call a provider, or register an export just because analysis is open.
Existing all-access sessions are migrated to locked management once. The
collapsed management panel still verifies the existing server-side
`APP_PASSWORD` before enabling collection, custom-universe upload, raw management
tables, CSV downloads, or chart image exports. Missing passwords leave those
operations locked. Locking management again keeps analysis available.

Nasdaq upload/write authentication, encrypted private review authentication,
China source-rights gates, provider priority, and secret handling remain separate.
Browser preferences never carry either privilege. No actual CSV, operating
symbol activation, `main`, Secrets, or provider credential is changed.

Verification includes behavioral tests for denied/unavailable deployment context,
URL privilege forgery, locked export payload registration, raw-frame suppression,
wrong password, management unlock/relock, migration of old privileges, and the
existing research list/3x3/navigation/selection/period sequence in both roles.
Final-head CI and hosted verification are reported separately from these design
and predeployment access checks.
