import runpy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'framework/tools'))
import study_retry as retry


class StudyRetry(unittest.TestCase):
    def test_stop_overrides_everything_before_any_external_action(self):
        main=runpy.run_path(str(retry.CASE/'valve_3d_cfd.py'))['main']
        with patch('tempfile.mkdtemp',side_effect=AssertionError('started a job')), patch('subprocess.run',side_effect=AssertionError('external action')):
            with self.assertRaisesRegex(RuntimeError,'暂停'):main()

    def test_release_of_pause_alone_does_not_restart_exhausted_route(self):
        self.assertEqual(retry.archived_outcomes(),[False]*4)
        with patch.object(retry,'OPERATOR_PAUSED',False):
            with self.assertRaisesRegex(RuntimeError,'change_method'):retry.require_fixed_study_run()

    def test_two_failures_review_three_switch(self):
        self.assertEqual(retry.decision([False,False],paused=False),'review_before_retry')
        self.assertEqual(retry.decision([False]*3,paused=False),'change_method')
        self.assertEqual(retry.decision([False,False,True],paused=False),'no_retry_hold')
        self.assertEqual(retry.decision([True],paused=True),'paused')
        with self.assertRaises(ValueError):retry.decision(['COMPLETE'],paused=False)
