#!/usr/bin/env python3
"""Publish a reviewed batch using PAT and attach its posts to a collection.

Plan: {sha256, plan: {account, collection, createEndpoint, joinEndpoint,
joinMethod, articles}}. Hash uses sorted compact UTF-8 JSON, including all body
text and destination settings. Approval must be obtained before invoking this.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import urllib.request
import xmlrpc.client


def digest(plan):
    return hashlib.sha256(json.dumps(plan, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def save(path, state, exclusive=False):
    if exclusive:
        with path.open('x', encoding='utf-8') as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
    else:
        temporary = path.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(path)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Client:
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, method, path, data=None):
        req = urllib.request.Request('https://i.cnblogs.com' + path,
            data=json.dumps(data, ensure_ascii=False).encode() if data is not None else None,
            headers={'Authorization': 'Bearer ' + self.token, 'Authorization-Type': 'pat',
                     'Content-Type': 'application/json'}, method=method)
        with self.opener.open(req, timeout=30) as response:
            raw = response.read()
            if not raw:
                return None
            if 'json' not in response.headers.get('Content-Type', ''):
                raise ValueError('Expected JSON; do not retry a write')
            return json.loads(raw)

    def verify(self, account, article, post_id):
        rpc = xmlrpc.client.ServerProxy('https://rpc.cnblogs.com/metaweblog/' + account['blogApp'])
        result = rpc.metaWeblog.getPost(str(post_id), account['username'], self.token)
        body = result.get('description', '').strip()
        if body.startswith('[Markdown]'):
            body = body[len('[Markdown]'):].strip()
        if result.get('title') != article['title'] or body != article['body'].strip():
            raise ValueError('Post exists but title/body verification failed; do not recreate')


def publish(path, approved, client):
    source = Path(path)
    document = json.loads(source.read_text(encoding='utf-8'))
    plan = document['plan']
    sha = digest(plan)
    if sha != document['sha256'] or sha != approved:
        raise ValueError('Approval digest mismatch')
    account = plan['account']
    collection_id = plan['collection']['id']
    if (not isinstance(collection_id, int) or collection_id <= 0
            or plan['createEndpoint'] != 'https://i.cnblogs.com/openapi/v1/posts'
            or plan['joinEndpoint'] != f'https://i.cnblogs.com/api/collections/{collection_id}/entries'
            or plan['joinMethod'] != 'PUT'
            or not plan['articles']):
        raise ValueError('Unsupported plan')
    state_path = source.with_name('batch_status.json')
    if state_path.exists():
        raise ValueError('Batch already attempted: inspect records; no automatic write retries')
    collection = client.request('GET', f'/api/collections/{collection_id}')
    if collection.get('title') != plan['collection']['title']:
        raise ValueError('Collection mismatch')
    state = {'sha256': sha, 'state': 'started', 'collection_id': collection_id, 'posts': []}
    save(state_path, state, exclusive=True)
    try:
        for article in plan['articles']:
            record = {'title': article['title'], 'state': 'creating'}
            state['posts'].append(record)
            save(state_path, state)
            reply = client.request('POST', '/openapi/v1/posts', article)
            if not reply or reply.get('success') is not True:
                raise ValueError('Create did not report success; inspect before retry')
            result = reply['value']
            post_id = int(result['postId'])
            record.update(post_id=post_id, url=result['postUrl'], state='created')
            save(state_path, state)
            client.verify(account, article, post_id)
            record['state'] = 'body_verified'
            save(state_path, state)
            print(json.dumps(record, ensure_ascii=False), flush=True)
        state['state'] = 'joining_collection'
        save(state_path, state)
        ids = [post['post_id'] for post in state['posts']]
        client.request('PUT', f'/api/collections/{collection_id}/entries', {'postIds': ids})
        entries = client.request('GET', f'/api/collections/{collection_id}/entries?pageIndex=1&pageSize=200')
        present = {int(entry['postId']) for entry in entries['items']}
        if not set(ids).issubset(present):
            raise ValueError('Collection verification failed; do not recreate posts')
        state['state'] = 'verified'
        save(state_path, state)
        return state
    except Exception as error:
        state['state'] = 'needs_inspection'
        state['error_type'] = type(error).__name__
        save(state_path, state)
        raise ValueError('Write or verification interrupted. Inspect batch_status.json; do not retry blindly') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--approved-sha256', required=True)
    args = parser.parse_args()
    socket.setdefaulttimeout(30)
    token = os.environ.get('CNBLOGS_TOKEN')
    if not token:
        parser.error('Set CNBLOGS_TOKEN securely; never pass it as a command argument')
    try:
        result = publish(args.plan, args.approved_sha256, Client(token))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({'ok': False, 'error_type': type(error).__name__,
                          'error': str(error) if isinstance(error, ValueError) else 'Inspect local status record'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
