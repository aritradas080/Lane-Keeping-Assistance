# Evaluation: rain_dark.mp4

Processed all 1123 frames (37.43 seconds) at 30.00 fps, 1908 x 1080. Encoded video frame count, resolution and frame rate passed validation.

Wet forest road, low light, solid yellow centre and white edge; speed humps, wipers, reflections and embedded player controls. Hood excluded.

| Boundary | Fresh detection | Carried over | Missing | Mean heuristic confidence |
| --- | ---: | ---: | ---: | ---: |
| left | 40.1% | 9.0% | 50.9% | 0.396 |
| right | 13.8% | 9.9% | 76.3% | 0.152 |

Offset availability: 11.2%. Processing speed: 1.42 fps (offline).

Offsets use the image midpoint as an assumed vehicle reference. Positive means right of lane centre; negative means left. Units are percent of lane width, not metres. Physical camera alignment and vehicle centre are unmeasured. Numeric offsets are withheld during carry-over or missing detections.

This is an unlabelled test scene with clip-specific ROI setup, not a calibrated accuracy benchmark. Detection availability, pixel support, fit residuals and confidence are diagnostics; high confidence does not prove correct lane tracking. Inspect the review montage and full video for false fits.

The review montage samples nine times across the clip, the weakest combined-confidence frame, and the first carried/missing event per side when present. Individual full-resolution review frames are also saved.

Rain, windshield droplets, wiper occlusions, wet-road reflections, transverse speed-hump markings and dark paint challenge this colour/curve method. A reflection or hump stripe can be mistaken for a lane boundary; missing detections and false fits must both be considered. The hood is excluded by the configured ROI. Titles and player controls embedded in the source remain in the annotated output.

No ground-truth labels were supplied. For accuracy evaluation, manually label boundary points in representative working and failure frames and compare at common image rows. This clip cannot isolate rain effects from road geometry, camera placement and lighting differences.
