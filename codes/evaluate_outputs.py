"""Validate encoded outputs and produce an honest, reproducible diagnostics report."""
import csv
import json
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    metadata = json.loads((ROOT/'metrics'/'source_metadata.json').read_text())
    report = ['# Evaluation and operational design domain', '',
              'These are development results on the two supplied daylight videos. No ground-truth labels or camera calibration were provided. Detection availability is not accuracy, and confidence is not a probability.', '',
              '| Clip | Frames | Left fresh | Right fresh | Left carried | Right carried | Processing fps |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    checks = {}
    for name, source in metadata.items():
        stem = Path(name).stem
        summary = json.loads((ROOT/'metrics'/f'{stem}_summary.json').read_text())
        with (ROOT/'metrics'/f'{stem}_frames.csv').open(newline='') as handle:
            rows = list(csv.DictReader(handle))
        cap = cv2.VideoCapture(str(ROOT/'outputs'/f'{stem}_annotated.mp4'))
        encoded_fps = cap.get(cv2.CAP_PROP_FPS)
        count = 0
        sizes = set()
        # Review a temporal spread plus the frame with weakest combined confidence.
        worst = min(range(len(rows)), key=lambda i: float(rows[i]['left_confidence'])+float(rows[i]['right_confidence']))
        indices = sorted(set([0,len(rows)//5,2*len(rows)//5,3*len(rows)//5,4*len(rows)//5,len(rows)-1,worst]))
        tiles = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            sizes.add((frame.shape[1],frame.shape[0]))
            if count in indices:
                tile = cv2.resize(frame,(640,360))
                cv2.putText(tile,f"{stem}: {rows[count]['time_s']}s",(440,25),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,255,255),2)
                tiles.append(tile)
            count += 1
        cap.release()
        check = dict(decoded_frames=count, csv_rows=len(rows), source_frames=source['frames'],
                     resolution_ok=sizes=={(source['width'],source['height'])},
                     fps_ok=abs(encoded_fps-source['fps']) < .01,
                     frame_count_ok=count==len(rows)==source['frames'])
        checks[name] = check
        if not all(check[k] for k in ('resolution_ok','fps_ok','frame_count_ok')):
            raise RuntimeError(f'Output validation failed: {name}: {check}')
        while len(tiles)%3:
            tiles.append(np.zeros_like(tiles[0]))
        sheet = np.vstack([np.hstack(tiles[i:i+3]) for i in range(0,len(tiles),3)])
        cv2.imwrite(str(ROOT/'outputs'/f'{stem}_review.jpg'),sheet)
        l,r=summary['left'],summary['right']
        report.append(f"| {name} | {count} | {l['detected']:.1%} | {r['detected']:.1%} | {l['carried over']:.1%} | {r['carried over']:.1%} | {summary['processing_fps']:.1f} |")
    report += ['', '## Interpretation', '',
               'Both full outputs were decoded to verify frame count, resolution and frame rate against the source files. Review sheets include six positions across each clip and the frame with the weakest combined confidence. Per-frame CSVs record status, confidence, supporting-pixel count and residual error for each side. Residual error measures agreement with selected image pixels, not distance from a labelled true lane boundary.', '',
               'The overlay covers the near-field road below 70% of image height. Restricting the region avoids unsupported extrapolation towards the horizon on these curved and hilly roads. Visual review of the temporal contact sheets showed both near-field boundaries following the paint through the sampled bends and shadows. This sparse review does not establish every-frame accuracy. The double yellow marking is treated as one boundary band; the fitted curve can lie between its two strokes. The source clips contain a cursor and watermarks, and the final l2 frame contains a desktop bar; these source artifacts are retained in the output.', '',
               'Initial development exposed missed shaded paint under a high absolute brightness threshold, and a false right fit on the roadside when colour thresholds were too loose. Local contrast, a lower brightness threshold and a stricter low-saturation white mask improved those reviewed cases. The right boundary uses white candidates for these clips; other marking conventions require changes. Remaining high confidence fits can still be wrong.', '',
               '## Operational design domain', '',
               '- Supported evidence: these two continuous daylight rural-road scenes, visible yellow/white paint, moderate bends, and some shadows. The camera view is stable enough for a fixed per-clip transform.',
               '- Limits: steep changes in grade, tighter curves, worn paint, vehicles covering markings, merges, intersections, adjacent lanes, glare and pavement seams can break the fixed geometry or introduce false candidates. Tracking assumes gradual motion and can lag rapid lane changes.',
               '- Not tested here: night, rain, snow, dense traffic and dashed-marking continuity. The brief described additional conditions but those videos were not present. Two views from similar footage cannot establish general robustness or isolate a weather effect.',
               '- Missing/carry-over behaviour is additionally checked using a synthetic disappearance test. A carried boundary is dashed and labelled, expires after 0.35 seconds, and suppresses offset reporting.',
               '- Numeric offsets assume that the image midpoint represents the vehicle centre, with a centred, forward-facing camera. They are labelled as estimated percentages of lane width. The camera assumption is documented in README and configuration files. The physical reference remains unmeasured; this does not constitute calibration.', '',
               '## Further evaluation', '',
               'Annotate lane points at several fixed image rows on frames sampled throughout each scene, including shadows, bends and detection losses. Report per-side pixel errors, false detections, misses, temporal jitter and recovery time. Use independent footage after tuning. A measured centre reference and camera calibration are needed for physical offset validation.', '']
    (ROOT/'metrics'/'validation.json').write_text(json.dumps(checks,indent=2))
    (ROOT/'metrics'/'EVALUATION.md').write_text('\n'.join(report),encoding='utf-8')
    print(json.dumps(checks,indent=2))


if __name__ == '__main__':
    main()
