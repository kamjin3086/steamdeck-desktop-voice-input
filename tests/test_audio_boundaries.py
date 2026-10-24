"""The release cue must not be included in the recognition session."""
import unittest
from unittest.mock import MagicMock, patch
from voice_input import main


class AudioBoundaryTest(unittest.TestCase):
    def test_release_finishes_audio_before_stop_tone(self):
        events = []
        source = MagicMock()
        source.__enter__.return_value = source
        source.poll.side_effect = [['press'], ['release'], KeyboardInterrupt]
        stream = MagicMock()
        stream.__enter__.return_value = stream
        stream.position.return_value = 0
        stream.preroll = 0
        stream.read_since.return_value = (b'', 0)
        beep = MagicMock()
        beep.stop.side_effect = lambda: events.append('tone')
        beep.start.side_effect = lambda: events.append('start-tone')
        stream.position.side_effect = lambda: events.append('capture-boundary') or 60000
        cursors = []
        stream.read_since.side_effect = lambda cursor: (cursors.append(cursor) or b'', cursor)
        cfg = {'trigger': {'source': 'hidraw', 'byte': 9, 'bit': 7}, 'asr': {},
               'auto_stop': {'enabled': False, 'silence_ms': 600, 'threshold': .02}}
        args = main.build_parser().parse_args([])
        def finish(*args, **kwargs):
            events.append('finish')
            return None, ''
        with patch.multiple(main, effective_config=MagicMock(return_value=cfg),
                            create_backend=MagicMock(), AudioStream=MagicMock(return_value=stream),
                            make_source=MagicMock(return_value=source), Injector=MagicMock(),
                            Beep=MagicMock(return_value=beep), RecorderHUD=MagicMock(),
                            say=MagicMock(), finish_session=finish):
            main.cmd_run(args)
        self.assertLess(events.index('finish'), events.index('tone'))
        self.assertLess(events.index('start-tone'), events.index('capture-boundary'))
        self.assertEqual(cursors[0], 60000, 'do not include pre-activation audio')

    def test_tones_default_to_disabled(self):
        self.assertFalse(main.build_parser().parse_args([]).beep)


if __name__ == '__main__':
    unittest.main()
