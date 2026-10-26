#!/usr/bin/env python3
"""Prepare reviewed Markdown and publish only an explicitly approved digest."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sys
import xmlrpc.client
from datetime import datetime, timezone
from urllib.parse import urlparse


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path, value, exclusive=False):
    with path.open('x' if exclusive else 'w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def validate_endpoint(endpoint):
    parsed = urlparse(endpoint)
    if (parsed.scheme != 'https' or parsed.hostname != 'rpc.cnblogs.com'
            or parsed.port not in (None, 443) or parsed.username or parsed.password
            or parsed.query or parsed.fragment
            or not re.fullmatch(r'/metaweblog/[A-Za-z0-9_-]+/?', parsed.path)):
        raise ValueError('只允许 HTTPS rpc.cnblogs.com/metaweblog/博客名 接口')


def validate_body(body):
    if not body.strip():
        raise ValueError('正文不能为空')
    if re.search(r'<\s*(?:img|script|iframe)\b', body, re.I):
        raise ValueError('请先审核并转换 HTML 图片或脚本/iframe')
    # Deliberately reject reference images: otherwise a local definition may be missed.
    if re.search(r'!\[[^\]]*\]\s*(?:\[|\n)', body):
        raise ValueError('请将引用式图片转为内联 HTTPS 图片')
    images = re.findall(r'!\[[^\]]*\]\(([^\n]*)\)', body)
    if body.count('![') != len(images):
        raise ValueError('图片语法需人工转换为内联 HTTPS 格式')
    for image in images:
        url = image.strip().split()[0].strip('<>') if image.strip() else ''
        if urlparse(url).scheme != 'https' or not urlparse(url).hostname:
            raise ValueError('图片必须已托管为 HTTPS 地址；当前不自动上传图片')
    if re.search(r'(?:file://|(?:/Users/|[A-Za-z]:\\))', body):
        raise ValueError('正文包含本机文件路径，请先检查')


def prepare(args):
    validate_endpoint(args.endpoint)
    body = Path(args.source).read_text(encoding='utf-8')
    validate_body(body)
    if not args.title.strip():
        raise ValueError('标题不能为空')
    payload = {'schema': 1, 'endpoint': args.endpoint, 'username': args.username,
               'title': args.title.strip(), 'body': body,
               'categories': args.category, 'tags': args.tag, 'publish': True}
    sha = digest(payload)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'status.json').exists():
        raise ValueError('此目录已有发布记录，请为新版本使用新目录')
    write_json(out / 'manifest.json', {'sha256': sha, 'payload': payload})
    preview = (f"# {payload['title']}\n\n目标：{args.endpoint}\n\n"
               f"分类：{', '.join(args.category) or '未设置'}\n\n"
               f"标签：{', '.join(args.tag) or '未设置'}\n\n"
               f"SHA256：`{sha}`\n\n---\n\n{body}")
    (out / 'preview.md').write_text(preview, encoding='utf-8')
    return {'ok': True, 'sha256': sha, 'preview': str(out / 'preview.md')}


def load_manifest(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    payload = data['payload']
    if digest(payload) != data['sha256']:
        raise ValueError('manifest 已修改，请重新生成并确认')
    if payload.get('schema') != 1 or payload.get('publish') is not True:
        raise ValueError('不支持的 manifest')
    validate_endpoint(payload['endpoint'])
    validate_body(payload['body'])
    return data


def connect(endpoint, username):
    validate_endpoint(endpoint)
    token = os.environ.get('CNBLOGS_TOKEN')
    if not token:
        if not sys.stdin.isatty():
            raise ValueError('请通过 CNBLOGS_TOKEN 环境变量或交互式隐藏输入提供令牌')
        token = getpass.getpass('博客园 MetaWeblog 访问令牌：')
    if not token or token != token.strip():
        raise ValueError('令牌为空或含首尾空白')
    proxy = xmlrpc.client.ServerProxy(endpoint, allow_none=True)
    blogs = proxy.blogger.getUsersBlogs('', username, token)
    slug = urlparse(endpoint).path.rstrip('/').split('/')[-1]
    matches = [b for b in blogs if urlparse(b.get('url', '')).path.strip('/').casefold() == slug.casefold()]
    if len(matches) != 1:
        raise ValueError('返回的博客与目标不唯一匹配，停止操作')
    return proxy, token, matches[0]


def post_content(payload):
    return {'title': payload['title'], 'description': '[Markdown]\n' + payload['body'],
            'categories': payload['categories'], 'mt_keywords': ','.join(payload['tags'])}


def verify(proxy, token, payload, post_id):
    post = proxy.metaWeblog.getPost(str(post_id), payload['username'], token)
    if post.get('title') != payload['title'] or post.get('description', '').strip() != post_content(payload)['description'].strip():
        raise ValueError('文章已创建，但 API 回读标题或正文不匹配；请人工核验，勿重发')
    slug = urlparse(payload['endpoint']).path.rstrip('/').split('/')[-1]
    return {'ok': True, 'state': 'verified', 'post_id': str(post_id),
            'url': f'https://www.cnblogs.com/{slug}/p/{post_id}.html',
            'verification': 'API title/body only; visual review still required'}


def run(args):
    if args.command == 'prepare':
        return prepare(args)
    if args.command in ('check', 'categories'):
        proxy, token, blog = connect(args.endpoint, args.username)
        if args.command == 'categories':
            return {'ok': True, 'categories': proxy.metaWeblog.getCategories(str(blog['blogid']), args.username, token)}
        return {'ok': True, 'blog': blog}
    manifest = load_manifest(args.manifest)
    payload = manifest['payload']
    status = Path(args.manifest).parent / 'status.json'
    if args.command == 'publish':
        if args.approved_sha256 != manifest['sha256']:
            raise ValueError('批准的 SHA256 与当前版本不符，禁止发布')
        if status.exists():
            raise ValueError('已有发布记录；禁止重复新建，请先核查 status.json')
    proxy, token, blog = connect(payload['endpoint'], payload['username'])
    if args.command == 'verify':
        if not re.fullmatch(r'\d+', args.post_id):
            raise ValueError('文章 ID 必须为数字')
        result = verify(proxy, token, payload, args.post_id)
        # Read-only verification never overwrites a publishing record.
        return result
    available = proxy.metaWeblog.getCategories(str(blog['blogid']), payload['username'], token)
    names = {item.get('title', item.get('description', '')) for item in available}
    if set(payload['categories']) - names:
        raise ValueError('分类不存在，请先查询 categories 并重新准备')
    record = {'state': 'publishing', 'sha256': manifest['sha256'],
              'started_at': datetime.now(timezone.utc).isoformat()}
    write_json(status, record, exclusive=True)  # Cross-process duplicate guard, before network write.
    try:
        post_id = proxy.metaWeblog.newPost(str(blog['blogid']), payload['username'], token, post_content(payload), True)
        record.update(state='created', post_id=str(post_id))
        write_json(status, record)
        result = verify(proxy, token, payload, post_id)
        record.update(result)
        write_json(status, record)
        return result
    except Exception:
        record['state'] = 'created_unverified' if 'post_id' in record else 'uncertain'
        write_json(status, record)
        raise ValueError('发布或核验未完成，请查 status.json 与后台；禁止自动重试新建') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', default='yong_2333')
    parser.add_argument('--endpoint', default='https://rpc.cnblogs.com/metaweblog/yong2333')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('check')
    commands.add_parser('categories')
    prep = commands.add_parser('prepare')
    for name in ('source', 'title', 'out'):
        prep.add_argument('--' + name, required=True)
    prep.add_argument('--category', action='append', default=[])
    prep.add_argument('--tag', action='append', default=[])
    pub = commands.add_parser('publish')
    pub.add_argument('--manifest', required=True)
    pub.add_argument('--approved-sha256', required=True)
    check = commands.add_parser('verify')
    check.add_argument('--manifest', required=True)
    check.add_argument('--post-id', required=True)
    args = parser.parse_args()
    socket.setdefaulttimeout(30)
    try:
        result = run(args)
    except xmlrpc.client.Fault as error:
        # Never echo a remote error body: it may contain credentials or article text.
        result = {'ok': False, 'error': '博客园拒绝请求', 'fault_code': error.faultCode}
    except (ValueError, OSError, KeyError, TypeError, xmlrpc.client.Error) as error:
        result = {'ok': False, 'error_type': type(error).__name__}
        if isinstance(error, ValueError):
            result['error'] = str(error)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
