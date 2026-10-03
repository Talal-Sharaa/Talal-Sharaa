# Fable reading integration

The profile displays up to two books from Talal’s public Currently Reading list,
including covers, authors, and book links. The updater runs every six hours and
can also be run manually. It uses only Python’s standard library.

## Activation

Merge this PR, then open Actions → Update Fable reading → Run workflow.
No secrets, login cookies, or authentication tokens are needed. Keep the Fable
list’s privacy set to **everyone**. The public user/list IDs are configured in
`scripts/update_fable_reading.py`.

## Validation and limitations

The public API was tested without cookies or authorization on 2026-10-03 and
returned LoveStar and 11/22/63. The updater was run against that endpoint and
verified to modify only the Fable README block; a second run was unchanged.

The response currently has no reading-progress data, so percentages are omitted.
If Fable supplies current-page data later, the renderer can display it. Authors
are displayed as returned by Fable, which can include translators.

This is an unofficial API and may change. Failures, unsafe pagination URLs,
redirects, or malformed responses leave the existing README intact. An empty
list clears the displayed books. No private reviews or notes are published.

The retired Goodreads workflow is a manual no-op to prevent competing updates.
Other profile workflows continue independently. If a concurrent README update
causes a rebase conflict, rerun the Fable workflow.
