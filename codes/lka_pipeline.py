"""Classical lane perception: colour masks, perspective warp and robust curves."""
import argparse
import csv
import json
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BW, BH = 640, 480


def marking_mask(frame, allow_yellow=True):
    hls = cv2.cvtColor(cv2.GaussianBlur(frame, (5, 5), 0), cv2.COLOR_BGR2HLS)
    h, light, sat = cv2.split(hls)
    # Bright local contrast suppresses flat asphalt and broad reflections.
    local = cv2.GaussianBlur(light, (0, 0), 9)
    contrast = light.astype(np.int16) - local.astype(np.int16)
    white = (light > 70) & (sat < 65) & (contrast > 12)
    yellow = (h > 12) & (h < 40) & (sat > 95) & (light > 30) & (contrast > 5)
    return ((white | yellow if allow_yellow else white).astype(np.uint8) * 255)


def fit_boundary(mask, low, high, previous):
    """Search in bottom-up windows; fit x as a quadratic function of y."""
    histogram = (mask[BH//2:] > 0).sum(axis=0).astype(float)
    histogram = np.convolve(histogram, np.ones(19)/19, mode='same')
    base = low + int(np.argmax(histogram[low:high]))
    if histogram[base] < 2:
        return None, 0., 0, None, None, None
    yy, xx = np.nonzero(mask)
    selected = []
    centre = float(base)
    for bottom in range(BH, 0, -40):
        middle = bottom - 20
        if previous is not None:
            predicted = np.polyval(previous, middle / BH)
            centre = .65 * predicted + .35 * centre
        indices = np.flatnonzero((yy >= bottom-40) & (yy < bottom) &
                                 (np.abs(xx-centre) < 42))
        selected.extend(indices.tolist())
        if len(indices) > 12:
            centre = float(np.median(xx[indices]))
    if len(selected) < 100:
        return None, 0., len(selected), None, None, None
    x, y = xx[selected].astype(float), yy[selected]/BH
    keep = np.ones(len(x), dtype=bool)
    for _ in range(3):
        if keep.sum() < 80:
            return None, 0., int(keep.sum()), None, None, None
        fit = np.polyfit(y[keep], x[keep], 2)
        residual = np.abs(x-np.polyval(fit, y))
        keep = residual < max(7., min(22., 2.5*np.median(residual[keep])))
    coverage = len(np.unique((y[keep]*12).astype(int))) / 12
    error = float(np.sqrt(np.mean((x[keep]-np.polyval(fit, y[keep]))**2)))
    movement = 0 if previous is None else float(np.max(np.abs(
        np.polyval(fit, [.3, .65, 1.])-np.polyval(previous, [.3, .65, 1.]))))
    confidence = float(.30*min(1, keep.sum()/900) + .35*coverage +
                       .20*np.exp(-error/12) + .15*np.exp(-movement/50))
    if coverage < .42 or confidence < .48 or movement > 95:
        return None, confidence, int(keep.sum()), error, coverage, movement if previous is not None else None
    return fit, confidence, int(keep.sum()), error, coverage, movement if previous is not None else None


class Tracker:
    def __init__(self, fps):
        self.fits = [None, None]
        self.age = [0, 0]
        self.conf = [0., 0.]
        self.max_age = max(1, int(.35*fps))

    def update(self, mask, right_mask=None):
        results = [fit_boundary(mask, 35, 310, self.fits[0]),
                   fit_boundary(mask if right_mask is None else right_mask, 330, 605, self.fits[1])]
        proposed = [r[0] for r in results]
        # Validate the pair at several cross-sections before smoothing.
        if all(f is not None for f in proposed):
            widths = np.polyval(proposed[1], [.25,.5,.75,1])-np.polyval(proposed[0], [.25,.5,.75,1])
            if np.min(widths) < 160 or np.max(widths) > 500 or np.ptp(widths) > 160:
                proposed = [None, None]
        states = []
        for side in range(2):
            fit, score, support, error, coverage, movement = results[side]
            if proposed[side] is not None:
                self.fits[side] = fit if self.fits[side] is None else .3*fit+.7*self.fits[side]
                self.age[side] = 0
                self.conf[side] = score
                status = 'detected'
            else:
                self.age[side] += 1
                self.conf[side] *= .88
                status = 'carried over' if self.fits[side] is not None and self.age[side] <= self.max_age else 'missing'
                if status == 'missing':
                    self.fits[side] = None
            states.append(dict(status=status, confidence=round(self.conf[side], 4),
                               support_pixels=support, fit_rmse_px=error,
                               vertical_coverage=coverage, temporal_movement_px=movement))
        return states


def draw(frame, tracker, states, inverse, config):
    height, width = frame.shape[:2]
    layer = np.zeros((BH, BW, 3), np.uint8)
    y = np.arange(0, BH, dtype=float)
    curves = [None if f is None else np.column_stack((np.polyval(f, y/BH), y)).astype(np.int32)
              for f in tracker.fits]
    both = all(c is not None for c in curves)
    fresh = all(s['status'] == 'detected' for s in states)
    offset = None
    label = 'Vehicle position uncertain'
    if both:
        cv2.fillPoly(layer, [np.vstack((curves[0], curves[1][::-1]))], (0, 0, 255))
        centre = ((curves[0]+curves[1])/2).astype(np.int32)
        cv2.polylines(layer, [centre], False, (255,255,255), 2)
        if fresh and min(s['confidence'] for s in states) >= .55 and config.get('vehicle_reference_x') is not None:
            ref = np.array([[[config['vehicle_reference_x']*width, config['evaluation_y']*height]]], np.float32)
            vehicle, eval_y = cv2.perspectiveTransform(ref, np.linalg.inv(inverse))[0,0]
            lane_l, lane_r = [float(np.polyval(f, eval_y/BH)) for f in tracker.fits]
            if 0 <= eval_y < BH and lane_r-lane_l > 160:
                offset = float(100*(vehicle-(lane_l+lane_r)/2)/(lane_r-lane_l))
            if offset is not None:
                label = 'Centred' if abs(offset) < 8 else ('Shifted right' if offset > 0 else 'Shifted left')
                if abs(offset) > 35:
                    label = 'Close to right boundary' if offset > 0 else 'Close to left boundary'
    for side, colour in enumerate(((0,255,255), (255,190,0))):
        if curves[side] is not None:
            if states[side]['status'] == 'carried over':
                for start in range(0, BH, 30):
                    cv2.polylines(layer, [curves[side][start:start+17]], False, colour, 5)
            else:
                cv2.polylines(layer, [curves[side]], False, colour, 5)
    overlay = cv2.warpPerspective(layer, inverse, (width,height))
    active = np.any(overlay > 0, axis=2)
    frame[active] = cv2.addWeighted(frame, .55, overlay, .45, 0)[active]
    scale = max(.45, width/1600)
    panel_w = min(width, int(660*scale))
    cv2.rectangle(frame, (12,12), (panel_w, int(205*scale)+12), (15,15,15), -1)
    lines = [('LANE CONFIDENCE (heuristic)', (255,255,255))]
    for side, colour in enumerate(((0,255,255),(255,190,0))):
        s = states[side]
        lines.append((f"{'LEFT' if side == 0 else 'RIGHT'} {s['confidence']:.2f} | {s['status']}", colour))
    lines.append((label, (255,255,255)))
    unavailable = ('Offset unavailable | reference unknown' if config.get('vehicle_reference_x') is None
                   else 'Offset unavailable | unreliable lane estimate')
    lines.append((f'Estimated offset: {offset:+.1f}% lane width' if offset is not None else
                  unavailable, (220,220,220)))
    for i,(text, colour) in enumerate(lines):
        cv2.putText(frame, text, (22, int(38*scale+i*35*scale)), cv2.FONT_HERSHEY_SIMPLEX, .65*scale, colour, 1, cv2.LINE_AA)
    return frame, offset, label


class RunningMetrics:
    """Cumulative statistics through the current frame, not whole-clip claims."""
    def __init__(self):
        self.frames = 0
        self.offset_frames = 0
        self.counts = [{s: 0 for s in ('detected', 'carried over', 'missing')} for _ in range(2)]
        self.confidence_sum = [0., 0.]

    def update(self, states, offset):
        self.frames += 1
        self.offset_frames += int(offset is not None)
        for side, state in enumerate(states):
            self.counts[side][state['status']] += 1
            self.confidence_sum[side] += state['confidence']


def draw_metrics_panel(frame, states, running, processing_fps, total_frames, video_fps):
    """Small top-right panel. Candidate errors also describe rejected candidates."""
    height, width = frame.shape[:2]
    scale = min(width/1920., height/1080.)
    font = .53 * scale
    line_height = max(10, round(22*scale))
    margin = max(6, round(12*scale))
    padding = max(6, round(12*scale))
    def pair(key, percent=False):
        values = []
        for state in states:
            value = state.get(key)
            values.append('--' if value is None else
                          f'{100*value:.1f}%' if percent else
                          str(value) if key == 'support_pixels' else f'{value:.1f}')
        return f'{values[0]} / {values[1]}'
    def rates(status):
        return ' / '.join(f'{100*c[status]/running.frames:.1f}%' for c in running.counts)
    lines = [
        ('TRACKING METRICS | LEFT / RIGHT', (255,255,255)),
        ('CURRENT CANDIDATES (bird\'s-eye pixels)', (190,190,190)),
        ('Support pixels: ' + pair('support_pixels'), (235,235,235)),
        ('Fit RMSE (px): ' + pair('fit_rmse_px'), (235,235,235)),
        ('Vertical coverage: ' + pair('vertical_coverage', True), (235,235,235)),
        ('Temporal movement (px): ' + pair('temporal_movement_px'), (235,235,235)),
        ('RUNNING STATISTICS (through this frame)', (190,190,190)),
        ('Fresh detection: ' + rates('detected'), (235,235,235)),
        ('Carried over: ' + rates('carried over'), (235,235,235)),
        ('Missing: ' + rates('missing'), (235,235,235)),
        ('Mean confidence: ' + ' / '.join(f'{c/running.frames:.3f}' for c in running.confidence_sum), (235,235,235)),
        (f'Offset availability: {100*running.offset_frames/running.frames:.1f}%', (235,235,235)),
        (f'Processing: {processing_fps:.1f} fps | Frame {running.frames}/{total_frames}', (235,235,235)),
        (f'Video: {width}x{height} @ {video_fps:g} fps', (190,190,190)),
    ]
    text_width = max(cv2.getTextSize(text,cv2.FONT_HERSHEY_SIMPLEX,font,1)[0][0] for text,_ in lines)
    panel_width = max(round(555*scale), text_width+2*padding)
    panel_height = len(lines)*line_height+2*padding
    x0, y0 = width-margin-panel_width, margin
    region = frame[y0:y0+panel_height, x0:x0+panel_width]
    region[:] = cv2.addWeighted(region,.20,np.full_like(region,15),.80,0)
    for index,(text,colour) in enumerate(lines):
        cv2.putText(frame,text,(x0+padding,y0+padding+(index+1)*line_height-5),
                    cv2.FONT_HERSHEY_SIMPLEX,font,colour,1,cv2.LINE_AA)
    return frame


def process(path, config, seconds=None, start=0):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f'Cannot open {path}')
    fps = cap.get(cv2.CAP_PROP_FPS)
    width, height = int(cap.get(3)), int(cap.get(4))
    if fps <= 0:
        raise RuntimeError('Video has no valid frame rate')
    src = np.float32(config['source']) * [width,height]
    dst = np.float32([[160,0],[480,0],[480,BH],[160,BH]])
    transform = cv2.getPerspectiveTransform(src.astype(np.float32), dst)
    inverse = np.linalg.inv(transform)
    tracker = Tracker(fps)
    running = RunningMetrics()
    available_frames = max(0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT))-round(start*fps))
    total_frames = available_frames if seconds is None else min(available_frames, round(seconds*fps))
    output = ROOT/'outputs'/f'{path.stem}_annotated.mp4'
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width,height))
    if not writer.isOpened():
        raise RuntimeError(f'Cannot create {output}')
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(start*fps))
    rows = []
    began = time.perf_counter()
    n = 0
    try:
        while seconds is None or n < round(seconds*fps):
            ok, frame = cap.read()
            if not ok:
                break
            mask = marking_mask(frame)
            warped = cv2.warpPerspective(mask, transform, (BW,BH), flags=cv2.INTER_NEAREST)
            right_mask = cv2.warpPerspective(marking_mask(frame, allow_yellow=False), transform,
                                             (BW,BH), flags=cv2.INTER_NEAREST)
            states = tracker.update(warped, right_mask)
            annotated, offset, position = draw(frame, tracker, states, inverse, config)
            running.update(states, offset)
            processing_fps = running.frames/max(time.perf_counter()-began, 1e-6)
            annotated = draw_metrics_panel(annotated, states, running, processing_fps, total_frames, fps)
            writer.write(annotated)
            row = dict(frame=round(start*fps)+n, time_s=round(start+n/fps,4), offset_percent=offset,
                       position=position, running_processing_fps=processing_fps)
            for side,s in zip(('left','right'), states):
                row.update({f'{side}_{k}':v for k,v in s.items()})
            rows.append(row)
            if n in (0, round(5*fps), round(15*fps)):
                cv2.imwrite(str(ROOT/'outputs'/f'{path.stem}_frame_{n:06d}.jpg'), annotated)
                cv2.imwrite(str(ROOT/'outputs'/f'{path.stem}_mask_{n:06d}.png'), warped)
            n += 1
            if n % 300 == 0:
                print(f'{path.name}: {n} frames', flush=True)
    finally:
        cap.release()
        writer.release()
    if not rows:
        raise RuntimeError('No frames processed; check start time')
    with (ROOT/'metrics'/f'{path.stem}_frames.csv').open('w', newline='') as handle:
        writer_csv = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer_csv.writeheader()
        writer_csv.writerows(rows)
    try:
        source_label = path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        source_label = path.name
    summary = dict(source=source_label, frames=n, duration_s=n/fps, processing_fps=n/(time.perf_counter()-began),
                   config=config, note='Detection availability and fit diagnostics, not labelled accuracy. Confidence is heuristic.')
    for side in ('left','right'):
        summary[side] = {status:sum(r[f'{side}_status']==status for r in rows)/n
                         for status in ('detected','carried over','missing')}
        summary[side]['mean_confidence'] = float(np.mean([r[f'{side}_confidence'] for r in rows]))
    summary['offset_available_fraction'] = sum(r['offset_percent'] is not None for r in rows)/n
    (ROOT/'metrics'/f'{path.stem}_summary.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', type=Path, help='Default: process all configured source videos')
    parser.add_argument('--config', type=Path, default=ROOT/'configs'/'clips.json')
    parser.add_argument('--seconds', type=float)
    parser.add_argument('--start', type=float, default=0)
    args = parser.parse_args()
    if args.seconds is not None and args.seconds <= 0 or args.start < 0:
        parser.error('seconds must be positive and start non-negative')
    configs = json.loads(args.config.read_text())
    for folder in ('outputs','metrics'):
        (ROOT/folder).mkdir(exist_ok=True)
    paths = [args.video] if args.video else [ROOT/'video_source'/name for name in configs]
    for path in paths:
        if path.name not in configs:
            parser.error(f'Add camera settings for {path.name} to {args.config}')
        process(path, configs[path.name], args.seconds, args.start)


if __name__ == '__main__':
    main()
