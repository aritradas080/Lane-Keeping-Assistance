# Evaluation and operational design domain

These are development results on the two supplied daylight videos. No ground-truth labels or camera calibration were provided. Detection availability is not accuracy, and confidence is not a probability.

| Clip | Frames | Left fresh | Right fresh | Left carried | Right carried | Processing fps |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| l1.mp4 | 628 | 100.0% | 100.0% | 0.0% | 0.0% | 5.8 |
| l2.mp4 | 726 | 100.0% | 100.0% | 0.0% | 0.0% | 1.5 |

## Interpretation

Both full outputs were decoded to verify frame count, resolution and frame rate against the source files. Review sheets include six positions across each clip and the frame with the weakest combined confidence. Per-frame CSVs record status, confidence, supporting-pixel count and residual error for each side. Residual error measures agreement with selected image pixels, not distance from a labelled true lane boundary.

The overlay covers the near-field road below 70% of image height. Restricting the region avoids unsupported extrapolation towards the horizon on these curved and hilly roads. Visual review of the temporal contact sheets showed both near-field boundaries following the paint through the sampled bends and shadows. This sparse review does not establish every-frame accuracy. The double yellow marking is treated as one boundary band; the fitted curve can lie between its two strokes. The source clips contain a cursor and watermarks, and the final l2 frame contains a desktop bar; these source artifacts are retained in the output.

Initial development exposed missed shaded paint under a high absolute brightness threshold, and a false right fit on the roadside when colour thresholds were too loose. Local contrast, a lower brightness threshold and a stricter low-saturation white mask improved those reviewed cases. The right boundary uses white candidates for these clips; other marking conventions require changes. Remaining high confidence fits can still be wrong.

## Operational design domain

- Supported evidence: these two continuous daylight rural-road scenes, visible yellow/white paint, moderate bends, and some shadows. The camera view is stable enough for a fixed per-clip transform.
- Limits: steep changes in grade, tighter curves, worn paint, vehicles covering markings, merges, intersections, adjacent lanes, glare and pavement seams can break the fixed geometry or introduce false candidates. Tracking assumes gradual motion and can lag rapid lane changes.
- Not tested here: night, rain, snow, dense traffic and dashed-marking continuity. The brief described additional conditions but those videos were not present. Two views from similar footage cannot establish general robustness or isolate a weather effect.
- Missing/carry-over behaviour is additionally checked using a synthetic disappearance test. A carried boundary is dashed and labelled, expires after 0.35 seconds, and suppresses offset reporting.
- Numeric offsets assume that the image midpoint represents the vehicle centre, with a centred, forward-facing camera. They are labelled as estimated percentages of lane width. The camera assumption is documented in README and configuration files. The physical reference remains unmeasured; this does not constitute calibration.

## Further evaluation

Annotate lane points at several fixed image rows on frames sampled throughout each scene, including shadows, bends and detection losses. Report per-side pixel errors, false detections, misses, temporal jitter and recovery time. Use independent footage after tuning. A measured centre reference and camera calibration are needed for physical offset validation.
