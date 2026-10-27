import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('narrate', Path(__file__).parents[1] / 'scripts/narrate.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class NarrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'ref.wav').write_bytes(b'reference')
        (self.root/'ref.txt').write_text('This is the reference transcript.')
        for name in ['tts', 'asr', 'denoiser']:
            (self.root/name).mkdir()
        self.profile = self.root/'profile.json'
        self.profile.write_text(json.dumps({'id': 'test', 'reference_audio': 'ref.wav',
            'reference_text': 'ref.txt', 'reference_sha256': app.sha(b'reference'),
            'tts_model': 'tts', 'asr_model': 'asr', 'denoiser_model': 'denoiser'}))
        self.text = self.root/'speech.txt'
        self.text.write_text('一个完整的句子。\n\n后来我改变了想法。')
        self.prepared = app.prepare(self.text, self.profile, self.root/'out', 280)
        self.plan = self.root/'out/plan.json'

    def test_segmentation_preserves_words_and_order(self):
        text = ('先解释一个问题，再说另一件事情。\n\n' * 60).strip()
        parts = app.split_text(text, 120)
        self.assertEqual(''.join(parts), text)
        self.assertTrue(all(len(x) <= 120 for x in parts))

    def test_long_unpunctuated_input_is_not_lost(self):
        text = '很长的一段没有句号的素材' * 40
        self.assertEqual(''.join(app.split_text(text, 100)), text)

    def test_formula_is_not_silently_read(self):
        with self.assertRaises(ValueError):
            app.split_text('文字\n$$x=y$$\n更多文字')

    def test_approval_digest_checked(self):
        with self.assertRaises(ValueError):
            app.validate_plan(self.plan, 'not-approved')
        app.validate_plan(self.plan, self.prepared['sha256'])

    def test_source_change_requires_new_approval(self):
        self.text.write_text('改过的正文。')
        with self.assertRaises(ValueError):
            app.validate_plan(self.plan, self.prepared['sha256'])

    def test_reference_change_requires_new_approval(self):
        (self.root/'ref.wav').write_bytes(b'a different speaker')
        with self.assertRaises(ValueError):
            app.validate_plan(self.plan, self.prepared['sha256'])

    def test_reference_transcript_change_requires_new_approval(self):
        (self.root/'ref.txt').write_text('Changed transcript')
        with self.assertRaises(ValueError):
            app.validate_plan(self.plan, self.prepared['sha256'])

    def test_number_reading_does_not_change_values(self):
        self.assertEqual(app.spoken('2,500条，9,680步，1.08，20%'), '两千五百条，九千六百八十步，一点零八，二十%'.replace('两千', '二千'))


if __name__ == '__main__':
    unittest.main()
