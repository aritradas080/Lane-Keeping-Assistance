"""Save contact sheets and metadata without modifying the source videos."""
import json
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def main():
    (ROOT / 'outputs').mkdir(exist_ok=True)
    (ROOT / 'metrics').mkdir(exist_ok=True)
    info = {}
    for path in sorted((ROOT / 'video_source').glob('*.mp4')):
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        tiles = []
        for fraction in (0, .2, .4, .6, .8, .95):
            frame_id = int((count-1)*fraction)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            ok, frame = cap.read()
            if not ok:
                continue
            tile = cv2.resize(frame, (640, 360))
            cv2.putText(tile, f'{path.name} | {frame_id/fps:.1f}s', (15, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 255), 2)
            tiles.append(tile)
        info[path.name] = dict(fps=fps, frames=count, duration_s=count/fps,
                               width=int(cap.get(3)), height=int(cap.get(4)))
        cap.release()
        if len(tiles) == 6:
            cv2.imwrite(str(ROOT/'outputs'/f'{path.stem}_contact_sheet.jpg'),
                        np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:])]))
    (ROOT/'metrics'/'source_metadata.json').write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))

if __name__ == '__main__':
    main()
