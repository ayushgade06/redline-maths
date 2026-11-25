# Real handwritten photos (to be added by the author)

Put at least 6 photos of your own handwritten worked solutions here, each with a deliberate mistake, and describe them in `labels.json`:

```json
[{"file": "p1.jpg", "lines": ["2(x - 3) = 10", "2x - 3 = 10", "x = 13/2"], "first_error": 1, "misconception": "DIST_FIRST_ONLY"}]
```

Then extend `eval/run.py`'s `live_sheets()` to read this folder (it currently measures the synthetic sample sheets in `web/public/samples/`), and run `RUN_LIVE=1 python eval/run.py`. Publish the numbers as measured.
