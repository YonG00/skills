import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('batch', Path(__file__).parents[1] / 'scripts/publish_batch.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / 'plan.json'
        plan = {'account': {'blogApp': 'test', 'username': 'test'},
                'collection': {'id': 42, 'title': 'Example'},
                'createEndpoint': 'https://i.cnblogs.com/openapi/v1/posts',
                'joinEndpoint': 'https://i.cnblogs.com/api/collections/42/entries',
                'joinMethod': 'PUT', 'articles': [{'title': 'A', 'body': 'B'}]}
        self.sha = app.digest(plan)
        self.file.write_text(json.dumps({'plan': plan, 'sha256': self.sha}))
        self.client = Mock()

    def test_approval_checked_before_network(self):
        with self.assertRaises(ValueError):
            app.publish(self.file, 'wrong', self.client)
        self.client.request.assert_not_called()

    def test_timeout_is_never_retried(self):
        self.client.request.side_effect = [{'title': 'Example'}, TimeoutError()]
        with self.assertRaises(ValueError):
            app.publish(self.file, self.sha, self.client)
        count = self.client.request.call_count
        with self.assertRaises(ValueError):
            app.publish(self.file, self.sha, self.client)
        self.assertEqual(self.client.request.call_count, count)
        state = json.loads(self.file.with_name('batch_status.json').read_text())
        self.assertEqual(state['state'], 'needs_inspection')
        self.assertEqual(state['posts'][0]['state'], 'creating')

    def test_join_failure_retains_created_id(self):
        self.client.request.side_effect = [{'title': 'Example'},
            {'success': True, 'value': {'postId': 123, 'postUrl': 'https://www.cnblogs.com/test/articles/123'}},
            TimeoutError()]
        with self.assertRaises(ValueError):
            app.publish(self.file, self.sha, self.client)
        state = json.loads(self.file.with_name('batch_status.json').read_text())
        self.assertEqual(state['posts'][0]['post_id'], 123)
        self.assertEqual(state['posts'][0]['state'], 'body_verified')

    def test_membership_is_checked(self):
        self.client.request.side_effect = [{'title': 'Example'},
            {'success': True, 'value': {'postId': 123, 'postUrl': 'https://www.cnblogs.com/test/articles/123'}},
            None, {'items': [{'postId': 123}]}]
        state = app.publish(self.file, self.sha, self.client)
        self.assertEqual(state['state'], 'verified')
        self.client.verify.assert_called_once()


if __name__ == '__main__':
    unittest.main()
