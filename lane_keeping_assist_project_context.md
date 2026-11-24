# Lane Keeping Assist Video Analysis

## Project goal

This is an optional homework project for Intro to Vehicles and Sensors. It covers the perception part of Lane Keeping Assist (LKA). Process continuous, forward-facing road footage offline, identify the boundaries of the vehicle’s current lane, and show the vehicle’s estimated position within that lane. The project scope is video analysis and annotation.

## What the professor expects

- Save an annotated video with the **left and right boundaries of the current lane in distinct colours**. Follow visible solid or dashed markings where possible.
- Show the estimated lane centre and describe the vehicle’s position as centred, shifted left or right, or close to a boundary when the estimate is reliable. An offset relative to lane width is sufficient.
- Indicate uncertainty or missing detections separately for each side. If a fit is reused from an earlier frame, visibly label it **carried over**.
- If feasible, show separate left and right confidence scores based on evidence such as supporting pixels, fit quality, and consistency across frames. Describe each score as a heuristic unless it has been calibrated as a probability.
- Road curvature or curve radius is optional. A physically calibrated radius is unnecessary.
- Briefly discuss the operational design domain (ODD), including the conditions the method handles reliably and the conditions that expose its limits. The professor’s example overlay is a visual reference. The specific processing steps in the brief are suggestions.

## Approach selected in the chat

Use a single classical Python/OpenCV pipeline across the clips. This approach needs no model training or labelled training data. Use the original continuous videos for processing and representative frames for setup or debugging. Short segments of roughly 15–30 seconds are a suggested starting point. If the approach later changes to a neural network, the brief expects substantial original work and an explanation of the model, data, training, pretrained components, and modifications.

## The three clips

These observations are based on one screenshot per clip. Verify the boundaries and conditions in the actual video before setting the configuration.

| Clip | Current lane markings in the screenshot | What to check in the video |
| --- | --- | --- |
| Daylight with shadows | Dashed yellow centreline on the left, solid white edge line on the right. The far-left white line borders the oncoming lane. | Use as the baseline. Check whether both fits follow the right-hand bend and stay aligned through shadows. |
| Night | Dashed white on both sides. The left boundary is beside the silver car. | Check stability between dashes and when a vehicle occludes a marking. Watch for false detections from lights, signs, and adjacent lanes. |
| Rain | Two dashed white lines immediately ahead. A dark pavement seam is visible near the right marking. | Check the effect of windshield droplets, wet-road reflections, and the pavement seam. Watch for false fits and correctly flagged losses. |

The daytime clip already contains shadows, so the current plan uses three clips. Their camera views, road layouts, markings, and traffic differ. Interpret the results as performance across three scenes. These clips alone cannot isolate the effect of weather or lighting.

## Camera setup per clip

- Set a road region of interest (ROI) on a clear representative frame. Store its corners as fractions of frame width and height. Leave room for the lane to curve. Exclude irrelevant areas such as the dashboard, player controls, and overhead lights where applicable.
- If using a bird’s-eye transform, choose the source points for each camera view. Check that the geometry is usable on later frames.
- Establish a vehicle reference at a fixed evaluation row near the bottom of the usable road image, or at a consistent cross-section in bird’s-eye coordinates. For a camera known to be centred and forward-aligned, the image midpoint can serve as an approximation. A frame where the vehicle is independently known to be centred can provide a rough reference for a fixed camera. The screenshots alone do not establish the camera mounting or vehicle centre. If the reference is unknown, show the estimated lane centre when supported and label the vehicle position uncertain.
- Compute the lane centre from the midpoint of the left and right fits at the same cross-section. For an approximate image-based offset, use `100 * (x_vehicle - x_lane_centre) / (x_right - x_left)`. Positive means right and negative means left when x increases to the right. Only report a numeric estimate when both boundaries and the vehicle reference are reliable.

## Suggested pipeline

1. Read the video frame by frame and apply the clip’s road ROI.
2. Highlight candidate white and yellow markings using HLS or HSV colour thresholds, brightness, and Sobel or Canny edges as needed.
3. Find candidates with a Hough transform, or use a bird’s-eye transform and search for lane pixels. Fit lines or curves appropriate to the footage.
4. Select the left and right boundaries of the current lane. Reject implausible fits, including crossings, abrupt changes in width, or jumps to adjacent markings.
5. Smooth the fits across frames. During a brief loss, a recent fit may be shown as carried over. When there is insufficient evidence for a boundary or the current lane becomes ambiguous, show the relevant uncertainty and withhold an unreliable position estimate.
6. Draw and save the annotated video. Review representative working frames and failure cases for each clip, including how the overlay responds when a boundary disappears and reappears.

## Handoff to Codex

The chat contains the assignment brief and three example screenshots. Source video files, code, camera calibration, and measured results are still to be supplied. When code is shared, review the existing pipeline against this brief before proposing changes. Confirm the video paths and clip-specific settings from the actual inputs. Use observed results for the ODD discussion.
