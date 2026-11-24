"""Focused checks for loss handling, geometry and offset sign."""
import unittest
import cv2
import numpy as np
from lka_pipeline import BH, BW, Tracker, RunningMetrics, draw


class PipelineTests(unittest.TestCase):
    def test_running_metrics_include_zero_offset_and_missing_frames(self):
        metrics = RunningMetrics()
        metrics.update([dict(status='detected', confidence=.8),
                        dict(status='detected', confidence=.9)], 0.)
        metrics.update([dict(status='carried over', confidence=.7),
                        dict(status='missing', confidence=0.)], None)
        self.assertEqual(metrics.frames, 2)
        self.assertEqual(metrics.offset_frames, 1)
        self.assertEqual(metrics.counts[0], {'detected':1,'carried over':1,'missing':0})
        self.assertEqual(metrics.counts[1], {'detected':1,'carried over':0,'missing':1})
        self.assertAlmostEqual(metrics.confidence_sum[0]/metrics.frames, .75)

    def test_detection_carry_and_expiry(self):
        mask = np.zeros((BH, BW), np.uint8)
        cv2.line(mask, (160,0), (160,BH-1), 255, 7)
        cv2.line(mask, (480,0), (480,BH-1), 255, 7)
        tracker = Tracker(30)
        states = tracker.update(mask)
        self.assertEqual([s['status'] for s in states], ['detected','detected'])
        states = tracker.update(np.zeros_like(mask))
        self.assertEqual([s['status'] for s in states], ['carried over','carried over'])
        for _ in range(tracker.max_age):
            states = tracker.update(np.zeros_like(mask))
        self.assertEqual([s['status'] for s in states], ['missing','missing'])
        self.assertEqual(tracker.fits, [None, None])

    def test_reference_and_offset_sign(self):
        tracker = Tracker(30)
        tracker.fits = [np.array([0.,0.,160.]), np.array([0.,0.,480.])]
        states = [dict(status='detected',confidence=.9) for _ in range(2)]
        frame = np.zeros((BH,BW,3), np.uint8)
        config = dict(vehicle_reference_x=None, evaluation_y=.9)
        self.assertIsNone(draw(frame.copy(),tracker,states,np.eye(3),config)[1])
        config['vehicle_reference_x'] = .6
        self.assertAlmostEqual(draw(frame.copy(),tracker,states,np.eye(3),config)[1],20.)
        config['vehicle_reference_x'] = .4
        self.assertAlmostEqual(draw(frame.copy(),tracker,states,np.eye(3),config)[1],-20.)
        states[0]['status'] = 'carried over'
        self.assertIsNone(draw(frame.copy(),tracker,states,np.eye(3),config)[1])


if __name__ == '__main__':
    unittest.main()
