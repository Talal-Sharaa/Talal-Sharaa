# Fable reading integration

The profile displays up to two books from Fable's Currently Reading list,
including covers, authors, and page progress when the API supplies it.
The updater runs every six hours and can also be run manually. It uses only
Python's standard library. It preserves the existing README on API errors,
expired credentials, unrecognized list names, and unexpected response shapes.

## One-time setup

1. Sign in at https://fable.co on a desktop browser.
2. Open Developer Tools → Network, then open your book lists.
3. Inspect a request to `api.fable.co/api/v2/users/<UUID>/book_lists`.
4. Copy the user UUID and the JWT value from the Authorization request header.
5. In this repository's Settings → Secrets and variables → Actions, create
   repository secrets named `FABLE_USER_ID` and `FABLE_AUTH_TOKEN`.
   Store the token without the `JWT ` prefix. Do not paste it into an issue,
   pull request, README, or chat.
6. After merging the integration, open Actions → Update Fable reading → Run workflow.
7. Check that the run succeeds and the profile shows your actual current reads.

If list detection fails, copy the Currently Reading list ID from its API URL
and add the repository **variable** `FABLE_READING_LIST_ID`. This optional
override also supports translated or renamed lists.

## Maintenance

This is an unofficial API integration, based on the endpoint and field shapes
used by https://github.com/VV-WIN/fable-xport. Fable may change its API.
Live account validation requires your credentials and has not been performed
as part of implementation. The code must be checked against a live run after setup.
Progress and book links are shown only when supplied by Fable; no percentage
is inferred when page totals are missing. An empty list clears the displayed
books. Only the selected list is fetched; private reviews are not published.

For HTTP 401/403, obtain a fresh JWT and replace `FABLE_AUTH_TOKEN`.
There is no automatic token refresh. Workflow errors never print the token
or API response body. Credentials are sent only to `https://api.fable.co`;
redirects and pagination to other hosts are rejected.

The retired Goodreads workflow is a manual no-op so it cannot overwrite Fable.
Other profile workflows continue independently. If a concurrent README update
causes a rebase conflict, rerun the Fable workflow.
