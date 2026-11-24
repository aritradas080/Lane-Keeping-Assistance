# Classical Lane Keeping Assistance

Offline perception project using Python, OpenCV and NumPy. The pipeline highlights the current lane with a red area, yellow left boundary, cyan right boundary, white lane centre, and separate confidence/status labels. It does not control a vehicle.

## Layout

- `codes/`: processing and video inspection scripts
- `configs/`: camera geometry for each source clip
- `video_source/`: original videos, kept unchanged
- `outputs/`: annotated MP4s, preview frames, bird's-eye masks and contact sheets
- `metrics/`: per-frame CSV files, aggregate JSON diagnostics and evaluation notes

## Run on Windows PowerShell

Input videos are supplied separately. Place the daylight files at `video_source/l1.mp4` and `video_source/l2.mp4`, and the rain file at `test/rain_dark.mp4`. The recorded metrics are included for reference; input footage and generated media remain local and are excluded by `.gitignore`.

Run from this project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe codes/inspect_videos.py
.\.venv\Scripts\python.exe codes/lka_pipeline.py --seconds 20
```

The delivered videos cover both complete clips. After a full run, reproduce the checks and report with:

```powershell
.\.venv\Scripts\python.exe codes/test_pipeline.py
.\.venv\Scripts\python.exe codes/evaluate_outputs.py
```

`evaluate_outputs.py` expects full-length outputs; a deliberately shortened run will fail its frame-count check.

Process all frames of both configured videos by omitting `--seconds`. Process a specific segment with:

```powershell
.\.venv\Scripts\python.exe codes/lka_pipeline.py --video video_source/l1.mp4 --start 10 --seconds 20
```

Each run replaces the outputs and metrics for that clip. The MP4 contains the original frame rate and resolution, without audio. Create the virtual environment locally using the commands above; activation is unnecessary with these commands. Source footage and generated media are not included in the public repository.

## Method

1. Gaussian smoothing and HLS white/yellow thresholds with local brightness contrast.
2. Camera-specific trapezoidal road region transformed to a 640 x 480 bird's-eye view.
3. Bottom-half histograms initialise left/right sliding windows; previous curves guide tracking. For the supplied road convention, the right boundary uses white candidates to suppress yellow vegetation.
4. Iterative residual rejection fits quadratic curves `x(y)` to marking pixels.
5. Reject weak support, insufficient vertical coverage, large temporal jumps and implausible lane pairs. Smooth accepted fits across time.
6. Brief detection losses reuse the previous fit for at most 0.35 seconds, draw a dashed overlay and explicitly show `carried over`. Longer losses show `missing`.
7. Save the overlay and frame-level diagnostics.

Confidence is a weighted heuristic based on supporting pixels, vertical coverage, residual error and temporal consistency. It is **not a calibrated probability**. Bright non-lane objects may still receive high scores.

## Camera assumptions and position

`configs/clips.json` stores source corners as normalised image coordinates, ordered top-left, top-right, bottom-right, bottom-left. These map to a fixed rectangular road plane. This is an approximate visual transform, not camera calibration; hills, camera motion, tight curves and changing road width violate its assumptions.

`vehicle_reference_x` is set to `0.5` for the configured clips, assuming a centred, forward-facing camera. This enables an approximate image-based offset; the physical vehicle centre has not been measured. The overlay calls this an estimated offset; the camera assumption is documented here and in configuration/metrics files. Replace this setting with a measured normalised reference when available, or use null to withhold offsets. `evaluation_y` sets the normalised image row of that reference; it must lie within the transformed road region. The displayed percentage is:

`100 * (vehicle_x - lane_centre_x) / (right_x - left_x)`

All coordinates in this equation are evaluated at the same bird's-eye cross-section. Positive means right, negative left. Offset requires two fresh detections and sufficient confidence; carried fits never produce an offset. Position labels use 8% as the centred threshold and 35% as the near-boundary threshold. These are illustrative thresholds, not validated safety margins. No metre offset or physically calibrated curve radius is claimed.

## Evaluation and limitations

See `metrics/EVALUATION.md` for observed results and the operational design domain. CSV/JSON reports measure detection availability, fit residuals and processing speed, **not accuracy**: no labelled lane boundaries or measured vehicle positions were supplied. To evaluate accuracy, annotate representative frames from each clip (including failures), compare boundary positions at fixed rows, and report pixel error and missed/false detections separately. Hand tuning these same clips is development evaluation, not independent testing.

The provided brief mentions daylight, night and rain footage; only the files actually present in `video_source/` are processed. Add a clip-specific configuration for additional videos and inspect several frames before interpreting its results.

## Rain test clip

Place the additional input at `test/rain_dark.mp4`. It has a separate camera configuration. Run it without replacing the daylight outputs:

```powershell
.\.venv\Scripts\python.exe codes/lka_pipeline.py --video test/rain_dark.mp4 --config configs/rain_dark.json
.\.venv\Scripts\python.exe codes/evaluate_clip.py --video test/rain_dark.mp4
```

The annotated video is `outputs/rain_dark_annotated.mp4`. Review frames and montage also use the `rain_dark_` prefix. Metrics include `rain_dark_frames.csv`, `rain_dark_summary.json`, `rain_dark_validation.json`, source metadata and `rain_dark_EVALUATION.md`. The rain configuration excludes the hood and uses the same detector/tracker as the baseline. All three annotated videos use `Estimated offset`, with the centred-camera assumption described above, plus the top-right diagnostics panel.

## On-video diagnostics

The compact top-right panel shows current candidate support pixels, fit RMSE, vertical coverage, and maximum curve movement relative to the previous smoothed curve. Pixel units refer to the 640 x 480 bird's-eye image. Candidate diagnostics can describe rejected fits; the top-left status states whether a curve was accepted, carried over, or missing. `--` means a measurement is unavailable, including temporal movement before a previous curve exists.

The panel also shows cumulative fresh/carry/missing percentages, mean confidence, offset availability, processing FPS, frame progress, and source resolution/frame rate. Running statistics include the current frame and converge to the clip totals at the end. Processing FPS is offline throughput, including work already completed; it is distinct from playback FPS. Coverage, movement and running processing FPS are also saved in each frame's CSV row. Final encoded-file checks remain in the validation JSON files because they require the completed video to be decoded. No labelled accuracy, precision, recall, F1 or IoU is claimed.
