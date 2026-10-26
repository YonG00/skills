import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cnblogs', Path(__file__).parents[1] / 'scripts/cnblogs.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class PublishingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / 'article.md'
        source.write_text('Hello world\n', encoding='utf-8')
        self.args = SimpleNamespace(source=str(source), title='Title', out=str(self.root / 'release'),
                                    endpoint='https://rpc.cnblogs.com/metaweblog/yong2333',
                                    username='yong2333', category=[], tag=[])
        self.prepared = app.prepare(self.args)
        self.pub = SimpleNamespace(command='publish', manifest=str(self.root / 'release/manifest.json'),
                                   approved_sha256=self.prepared['sha256'])

    def test_approval_mismatch_never_connects(self):
        self.pub.approved_sha256 = 'wrong'
        with patch.object(app, 'connect') as connection:
            with self.assertRaises(ValueError):
                app.run(self.pub)
            connection.assert_not_called()

    def test_edited_body_invalidates_manifest(self):
        path = Path(self.pub.manifest)
        path.write_text(path.read_text().replace('Hello world', 'Changed body'))
        with self.assertRaises(ValueError):
            app.load_manifest(path)

    def test_uncertain_write_blocks_retry(self):
        from unittest.mock import Mock
        proxy = Mock()
        proxy.metaWeblog.getCategories.return_value = []
        proxy.metaWeblog.newPost.side_effect = TimeoutError('simulated lost reply')
        with patch.object(app, 'connect', return_value=(proxy, 'fake-secret', {'blogid': '123'})):
            with self.assertRaises(ValueError):
                app.run(self.pub)
            with self.assertRaises(ValueError):
                app.run(self.pub)
        self.assertEqual(proxy.metaWeblog.newPost.call_count, 1)
        self.assertIn('uncertain', (self.root / 'release/status.json').read_text())

    def test_success_is_read_back_and_duplicate_blocked(self):
        from unittest.mock import Mock
        proxy = Mock()
        proxy.metaWeblog.getCategories.return_value = []
        proxy.metaWeblog.newPost.return_value = '999'
        proxy.metaWeblog.getPost.return_value = {'title': 'Title', 'description': '[Markdown]\nHello world\n'}
        with patch.object(app, 'connect', return_value=(proxy, 'fake-secret', {'blogid': '123'})):
            result = app.run(self.pub)
            self.assertEqual(result['state'], 'verified')
            with self.assertRaises(ValueError):
                app.run(self.pub)
        self.assertNotIn('fake-secret', (self.root / 'release/status.json').read_text())

    def test_local_images_and_wrong_host_rejected(self):
        with self.assertRaises(ValueError):
            app.validate_body('![image](./secret.png)')
        with self.assertRaises(ValueError):
            app.validate_endpoint('https://example.com/metaweblog/yong2333')


if __name__ == '__main__':
    unittest.main()
