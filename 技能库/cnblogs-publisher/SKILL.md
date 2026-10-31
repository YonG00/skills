---
name: cnblogs-publisher
description: 检查指定文档、整理博客园文章预览，并在用户明确确认当前版本后通过 MetaWeblog 发布及核验。适用于博客园文章发布，不负责其他平台。
---

# 博客园文章发布

默认博客是 `https://www.cnblogs.com/yong2333`，MetaWeblog 登录名 `yong_2333`（含下划线），接口 `https://rpc.cnblogs.com/metaweblog/yong2333`。这两个名称不同；已于 2026-10-26 通过只读认证验证，blog ID 为 `869139`，运行时仍从接口读取。可用脚本参数覆盖。令牌由 `CNBLOGS_TOKEN` 环境变量或交互式隐藏输入提供；不要将它放入仓库、命令参数、日志或作品文件。连接验证只调用读取接口。

## 工作流

1. 读取用户指定的文档。飞书文档使用对应文档技能；无法访问时如实说明，不能把链接页当正文。用户只给文档时，先整理预览，不视为已经允许公开。
2. 检查标题与正文结构、代码块、图片和链接、隐私及密钥、待核实事实。保留原意；实质修改明确列出。核实能力不足时标出问题，不编造核验结果。
3. 在当前工作区的 `资料/YYYY-MM-DD_HHMMSS_博客园_主题/` 存放正文、预览和发布记录，时间使用 Asia/Shanghai。作品不放进技能源码。其他工作区遵循其资料约定。
4. 将审核后的正文保存为 UTF-8 Markdown；正文不要重复写文章主标题。执行 `prepare` 生成 `preview.md` 和 `manifest.json`。脚本只支持文本和已有 HTTPS 远端图片；遇到本地图片、附件、HTML 嵌图，先解决托管并重新生成预览。不得悄悄丢图或引用本机路径。
5. 将最终标题、摘要（如有）、分类、标签、完整正文或可访问的本地预览链接、修改点、公开发布目标及 manifest SHA256 展示给用户。明确询问是否发布这一版本。没有当前版本的明确确认，不得调用 `publish`。修改文章、分类或目标后必须重新准备并确认。确认前不上传图片、不创建远端草稿。
6. 用户确认后，以该 manifest SHA256 调用 `publish`。首次发布前用 `check` 验证认证，并用 `categories` 查询可用分类；不存在的分类与用户核实后重新准备。实际 blog ID 从 `getUsersBlogs` 获取，不能用用户名猜。用户要归入合集时走下面的合集流程，不能把合集名直接当作传统分类。
7. 发布成功后核验文章 ID、标题和正文，并给出正式文章链接。核验失败只能报告已创建但未核验，不能称发布成功。`publishing` / `uncertain` 状态禁止重试；先在后台或只读接口确认是否已经创建。需要核验已有 ID 时使用 `verify`；不要再次新建。

## 命令

脚本仅使用 Python 标准库：`python3 <技能目录>/scripts/cnblogs.py ...`。

```bash
python3 scripts/cnblogs.py check
python3 scripts/cnblogs.py categories
python3 scripts/cnblogs.py prepare --source 正文.md --title '文章标题' --out 发布目录 --category '分类' --tag '标签'
# 仅在用户明确确认上述最终版本后执行；参数为 prepare 输出的完整摘要
python3 scripts/cnblogs.py publish --manifest 发布目录/manifest.json --approved-sha256 SHA256
python3 scripts/cnblogs.py verify --manifest 发布目录/manifest.json --post-id 文章ID
```

认证参数在子命令之前：`--username`、`--endpoint`。`prepare` 不需要认证。发布会在 manifest 所在目录先写 `status.json`，不会自动重试网络写操作，也不提供覆盖或删除文章命令。

## 当前边界

`cnblogs.py` 通过 MetaWeblog 发布普通随笔，使用博客园的 `[Markdown]` 正文格式；文章类型和合集发布使用下述 PAT 批量脚本。真实渲染、图片可访问性及链接检查仍需打开文章确认；API 回读相同不等于页面排版已验证。首次上线需用用户确认的真实文章验证，禁止擅自发布测试文章。文章修订、图片上传、远端草稿和定时发布尚未实现，遇到这些需求先说明并扩展工具。

## 合集与批量文章

2026-10-26 已通过真实的三篇文章验证 PAT 发布、MetaWeblog 标题/正文回读和合集归属。合集是独立功能，传统 `getCategories` 不返回合集，`getRecentPosts` 也不能用于声称全站全部文章数量。公开侧栏的合集篇数不等于后台全部条数；需要完整统计时读取后台并去重、区分草稿与已发布。

读取合集时用 `GET https://i.cnblogs.com/api/collections`，详情和条目分别用 `/api/collections/{id}`、`/api/collections/{id}/entries?pageIndex=1&pageSize=200`。超过一页要分页。请求头为 `Authorization: Bearer <PAT>` 和 `Authorization-Type: pat`。令牌来自环境变量，禁止回显。该后台接口从当前官方前端调用定义核实，可能变动；不能将返回 HTML 的未知路由当成可用 API。

批量脚本 `scripts/publish_batch.py` 使用 [官方博客后台 API](https://www.cnblogs.com/cmt/articles/19246558) 的 `POST /openapi/v1/posts` 发布。合集关联参数来自官方前端合集服务：`PUT /api/collections/{id}/entries`，JSON 为 `{"postIds": [文章ID]}`。只在用户确认整个版本后执行。请求体支持 `postType: "Article"`、`postFormat: "Markdown"`、`isPublished: true`、`categories` 和 `tags`。公开发布和归属必须在预览中说清。

准备 UTF-8 JSON 文件 `{ "sha256": "...", "plan": {...} }`，其中 plan 字段为：

```json
{
  "account": {"blogApp": "yong2333", "username": "yong_2333"},
  "collection": {"id": 44622, "title": "问题集"},
  "createEndpoint": "https://i.cnblogs.com/openapi/v1/posts",
  "joinEndpoint": "https://i.cnblogs.com/api/collections/44622/entries",
  "joinMethod": "PUT",
  "articles": [
    {"title": "确认后的标题", "body": "确认后的完整正文", "postType": "Article", "postFormat": "Markdown", "isPublished": true, "categories": [], "tags": []}
  ]
}
```

通过脚本的 `digest(plan)` 生成 SHA256，覆盖完整正文、全部文章及目标合集。不要直接复用单篇 manifest 的摘要代替批量摘要。向用户展示完整正文预览、文章类型、公开目标与整批摘要；确认前不调用脚本。

```bash
python3 scripts/publish_batch.py --plan 最终发布请求.json --approved-sha256 整批SHA256
```

脚本先写本地 `batch_status.json`，逐篇保存远端 ID、回读核验，再批量加入合集并核验归属。任何已有状态都拒绝自动重跑；网络写入中断时先只读排查，不能删除状态后再次新建。API 创建成功但合集失败时，报告已发布的 ID，只修复关联，不重发正文。用户原稿、计划、预览、发布记录都放在资料目录，不进技能仓库。

## 发布后核验与审核状态

2026-10-28 发布两篇到合集「思索」时确认：`batch_status.json` 达到 `verified` 只代表创建、正文回读和合集归属成功，**不代表公开页已可访问**。其中一篇公开 URL 返回 404，另一篇正常；继续检查审核状态后发现前者为「待审核」。

用 PAT 查询审核状态（`POST`，请求体按 PostId）：

```bash
curl -sS -X POST "https://i.cnblogs.com/openapi/v1/posts/reviewStatus:check" \
  -H "Authorization: Bearer $CNBLOGS_TOKEN" -H "Authorization-Type: pat" \
  -H "Content-Type: application/json" -d '{"PostId": 12345678}'
```

返回 `reviewStatus`：`0` = 待审核，`1` = 审核通过。待审核期间公开页 404 属正常状态，**不要重建或重发**；报告「已创建并加入合集，等待平台审核」，稍后再查。也可用 `{"Url": "..."}` 查询。

公开页检查用 `curl -L` 跟随跳转；`/p/{id}.html` 会 301 到 `/articles/{id}`。合集名称可能被用户改名，发布前必须重新 `GET /api/collections` 取当前标题，不能沿用旧发布记录里的名称。

源码放入技能库不代表已安装到运行时技能目录；未同步不得声称已全局生效。
