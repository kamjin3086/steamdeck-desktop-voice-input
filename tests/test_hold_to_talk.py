"""Exercise the actual recording loop without audio/controller hardware."""
import unittest
from unittest.mock import MagicMock, patch

from voice_input import main


class HoldToTalkTest(unittest.TestCase):
    def exercise(self, auto, timestamps):
        backend = MagicMock()
        backend.open_session.return_value.finish.return_value = '\u4f60\u597d'
        source = MagicMock()
        source.__enter__.return_value = source
        source.poll.side_effect = [['press'], [], [], ['release'], KeyboardInterrupt]
        stream = MagicMock()
        stream.__enter__.return_value = stream
        stream.position.return_value = 0
        stream.preroll = 0
        stream.read_since.side_effect = lambda cursor: (b'\x00\x10' * 1600, cursor + 3200)
        cfg = {'trigger': {'source': 'hidraw', 'byte': 9, 'bit': 7},
               'asr': {}, 'auto_stop': {'enabled': auto, 'silence_ms': 600, 'threshold': .02}}
        args = main.build_parser().parse_args(['--no-beep'])
        # Each iteration's clock advances, independent of recognition duration.
        clock = iter(timestamps)
        with patch.multiple(main, effective_config=MagicMock(return_value=cfg),
                            create_backend=MagicMock(return_value=backend),
                            AudioStream=MagicMock(return_value=stream),
                            make_source=MagicMock(return_value=source),
                            Injector=MagicMock(), Beep=MagicMock(), RecorderHUD=MagicMock(),
                            SilenceStopper=MagicMock(), say=MagicMock()), \
             patch.object(main.time, 'monotonic', side_effect=lambda: next(clock)), \
             patch.object(main, 'finish_session', return_value=(None, '\u4f60\u597d')) as finish:
            main.cmd_run(args)
        return backend.open_session.call_count, finish.call_count

    def test_silence_segments_continue_until_release(self):
        opened, finished = self.exercise(True, [0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5] * 4)
        self.assertGreater(opened, 1)
        self.assertEqual(finished, opened, 'release must finish the last active segment')

    def test_sixty_second_limit_rotates_instead_of_disarming(self):
        opened, finished = self.exercise(False, list(range(0, 1000, 61)))
        self.assertGreater(opened, 1)
        self.assertEqual(finished, opened)


if __name__ == '__main__':
    unittest.main()
