# Python meetup runbook

| Time | Segment |
| --- | --- |
| 0–7 min | Open with the two Jogja pages. Ask where a selector is enough. Show `table#table1 tbody tr`, then explain wrapper induction and automatic extraction. |
| 7–12 min | Open the `Event` schema and run the event replay. Point out the publication date and the event date. Show the festival’s missing start time. |
| 12–15 min | Show the path from the DIY index through Kota Yogyakarta and Mantrijeron to NPSN 20403484. Open the original detail fixture and the exported record. |
| 15–24 min | Reproduce the row-order failure, give the agent 90 seconds, review its diff, then rerun the tests and replay the school page. |
| 24–27 min | Compare per-extraction model calls with model-assisted maintenance. Discuss using a fresh sample to detect drift and a saved fixture to reproduce it. |
| 27–30 min | Q&A. |

## Before the meetup

- Run `uv sync --locked`, then run the full crawl in the README. Save the export and the final crawl summary. Verify five city and regency branches, equal discovered and exported counts, and unique NPSNs. Investigate any reported failed pages before presenting the export as complete.
- Configure and rehearse the [Zyte Agentic Web Data skills for your coding agent](https://docs.zyte.com/zyte-web-data/install.html). Keep the agent in the stage copy of the project.
- To record real Instructor results, configure the provider’s credentials in your environment and set `INSTRUCTOR_PROVIDER` to the provider/model identifier. Run `uv run --locked python demo/events.py --record` and compare both results with the source. The recording is kept locally. Without a recording the replay explicitly labels its hand-checked reference output.
- Rehearse the commands below with Wi-Fi off. The stage agent needs its normal model connection. The fixture tests, event replay, and prepared repair run offline.

## Stage copy and replay

Run these commands from the repository root before going on stage.

```sh
source_dir=$PWD
stage_dir=$(mktemp -d)
cp -R diy_scraper fixtures tests pyproject.toml uv.lock .python-version scrapy.cfg README.md "$stage_dir/"
mkdir "$stage_dir/demo"
cp demo/events.py demo/events.json demo/event_expected.json "$stage_dir/demo/"
if test -f demo/event_recording.json; then
  cp demo/event_recording.json "$stage_dir/demo/"
fi
cd "$stage_dir"
uv sync --locked
git init -q
git apply "$source_dir/demo/positional-parser.patch"
git add diy_scraper/pages.py
```

The stage copy starts with the intentionally positional parser staged as the baseline. An ordinary `git diff` after the agent works will show its unstaged repair.

```sh
uv run --offline --locked python demo/events.py
uv run --offline --locked python -m web_poet.testing rerun fixtures/diy_scraper.pages.SchoolPage/gedongkiwo
uv run --offline --locked python -m pytest -q --web-poet-test-per-item
```

Only the reordered fixture should fail. The original is a trimmed capture of the [SD Negeri Gedongkiwo detail page](https://referensi.data.kemendikdasmen.go.id/pendidikan/npsn/20403484). The simulated change moves the complete education form and level rows while keeping their values attached to their labels.

Give the agent this prompt.

> Inspect the original and reordered Gedongkiwo fixtures. Fix the classification extraction in `diy_scraper/pages.py` so both fixtures pass. Edit only that file. Keep the fixture expectations and output keys fixed. Use the local files, run the tests offline, and show the diff.

If the agent stalls, stop its turn and copy the prepared repair into the stage directory.

```sh
cp "$source_dir/diy_scraper/pages.py" diy_scraper/pages.py
```

Review and verify the fix.

```sh
git diff -- diy_scraper/pages.py
uv run --offline --locked python -m pytest -q --web-poet-test-per-item
uv run --offline --locked python -m web_poet.testing rerun fixtures/diy_scraper.pages.SchoolPage/gedongkiwo-reordered
```

The classification values should read `SD` and `DIKDAS` in their original fields. For the complete JSONL record, show NPSN `20403484` from the saved crawl.
