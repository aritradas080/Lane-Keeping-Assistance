"""Validate and review a full-length clip processed by lka_pipeline.py."""
import argparse
import csv
import json
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, required=True)
    args = parser.parse_args()
    stem = args.video.stem
    summary = json.loads((ROOT/'metrics'/f'{stem}_summary.json').read_text())
    with (ROOT/'metrics'/f'{stem}_frames.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    source = cv2.VideoCapture(str(args.video))
    if not source.isOpened():
        raise RuntimeError(f'Cannot open {args.video}')
    metadata = dict(frames=int(source.get(7)), fps=source.get(5),
                    width=int(source.get(3)), height=int(source.get(4)))
    metadata['duration_s'] = metadata['frames']/metadata['fps']
    source.release()
    (ROOT/'metrics'/f'{stem}_source_metadata.json').write_text(json.dumps(metadata,indent=2))
    weakest = min(range(len(rows)), key=lambda i: float(rows[i]['left_confidence'])+float(rows[i]['right_confidence']))
    indices = {round((len(rows)-1)*f) for f in np.linspace(0,1,9)}
    indices.add(weakest)
    for side in ('left','right'):
        for status in ('carried over','missing'):
            index = next((i for i,r in enumerate(rows) if r[f'{side}_status']==status),None)
            if index is not None:
                indices.add(index)
    cap = cv2.VideoCapture(str(ROOT/'outputs'/f'{stem}_annotated.mp4'))
    fps = cap.get(5)
    sizes = set()
    count = 0
    tiles = []
    while True:
        ok,frame = cap.read()
        if not ok:
            break
        sizes.add((frame.shape[1],frame.shape[0]))
        if count in indices:
            tile = cv2.resize(frame,(640,360))
            cv2.putText(tile,f"{rows[count]['time_s']}s",(480,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,255,255),2)
            tiles.append(tile)
            cv2.imwrite(str(ROOT/'outputs'/f'{stem}_review_{count:06d}.jpg'),frame)
        count += 1
    cap.release()
    offsets = [float(row['offset_percent']) for row in rows if row['offset_percent']]
    checks = dict(decoded_frames=count, csv_rows=len(rows), source_frames=metadata['frames'],
                  frame_count_ok=count==len(rows)==metadata['frames'],
                  resolution_ok=sizes=={(metadata['width'],metadata['height'])},
                  fps_ok=abs(fps-metadata['fps'])<.01,
                  offsets_finite=all(np.isfinite(offsets)),
                  offset_requires_fresh_boundaries=all(not row['offset_percent'] or
                      (row['left_status']=='detected' and row['right_status']=='detected') for row in rows))
    (ROOT/'metrics'/f'{stem}_validation.json').write_text(json.dumps(checks,indent=2))
    if not all(v for k,v in checks.items() if k.endswith('_ok') or k in ('offsets_finite','offset_requires_fresh_boundaries')):
        raise RuntimeError(f'Validation failed: {checks}')
    while len(tiles)%3:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(str(ROOT/'outputs'/f'{stem}_review.jpg'),
                np.vstack([np.hstack(tiles[i:i+3]) for i in range(0,len(tiles),3)]))
    lines = [f'# Evaluation: {args.video.name}', '',
             f"Processed all {count} frames ({metadata['duration_s']:.2f} seconds) at {metadata['fps']:.2f} fps, {metadata['width']} x {metadata['height']}. Encoded video frame count, resolution and frame rate passed validation.", '',
             summary['config'].get('description',''), '',
             '| Boundary | Fresh detection | Carried over | Missing | Mean heuristic confidence |',
             '| --- | ---: | ---: | ---: | ---: |']
    for side in ('left','right'):
        values = summary[side]
        lines.append(f"| {side} | {values['detected']:.1%} | {values['carried over']:.1%} | {values['missing']:.1%} | {values['mean_confidence']:.3f} |")
    lines += ['',f"Offset availability: {summary['offset_available_fraction']:.1%}. Processing speed: {summary['processing_fps']:.2f} fps (offline).", '',
              'Offsets use the image midpoint as an assumed vehicle reference. Positive means right of lane centre; negative means left. Units are percent of lane width, not metres. Physical camera alignment and vehicle centre are unmeasured. Numeric offsets are withheld during carry-over or missing detections.', '',
              'This is an unlabelled test scene with clip-specific ROI setup, not a calibrated accuracy benchmark. Detection availability, pixel support, fit residuals and confidence are diagnostics; high confidence does not prove correct lane tracking. Inspect the review montage and full video for false fits.', '',
              'The review montage samples nine times across the clip, the weakest combined-confidence frame, and the first carried/missing event per side when present. Individual full-resolution review frames are also saved.', '',
              'Rain, windshield droplets, wiper occlusions, wet-road reflections, transverse speed-hump markings and dark paint challenge this colour/curve method. A reflection or hump stripe can be mistaken for a lane boundary; missing detections and false fits must both be considered. The hood is excluded by the configured ROI. Titles and player controls embedded in the source remain in the annotated output.', '',
              'No ground-truth labels were supplied. For accuracy evaluation, manually label boundary points in representative working and failure frames and compare at common image rows. This clip cannot isolate rain effects from road geometry, camera placement and lighting differences.', '']
    (ROOT/'metrics'/f'{stem}_EVALUATION.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(checks,indent=2))


if __name__ == '__main__':
    main()
