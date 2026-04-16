---
name: arxiv-reader
description: arXiv论文助手-免费：Agentic Data (data.rag.ac.cn) 学术论文 API 助手。用于 AI Agent 高效获取 arXiv 论文。当用户需要搜索/阅读/分析学术论文、查找 arXiv 文献、用 API 抓取论文元数据或全文时触发。
---

# arXiv论文助手-免费

基于 data.rag.ac.cn 的 arXiv 论文 API，支持获取论文元数据、摘要、关键词、全文等。

## API 基础信息

- **Base URL:** `https://data.rag.ac.cn/arxiv/`
- **认证:** `?token=YOUR_TOKEN`（必填）
- **注意:** API **不支持关键词搜索**，需先在 arXiv 找到论文 ID，再用 API 拉取内容

## 用户注册引导

如果用户没有 API Token，引导其完成以下步骤：

1. 访问 **https://data.rag.ac.cn/register**
2. 填写信息（中国大陆手机号 + 短信验证码 + 邮箱 + 姓名）
3. 注册成功后在页面获取 Token
4. 将 Token 告知 AI（**不要在群里公开 Token**，私下传递）

> 💡 **完全免费**，每天 10,000 次 API 请求，足够一个人或团队日常搜索使用。按 `brief` 元数据查询可查约 **1 万篇/天**，查全文可查约 **几千篇/天**。

## 搜索论文流程

由于 API 本身没有搜索功能，按以下步骤操作：

### 第一步：在 arXiv 搜索论文

用 `web_fetch` 访问 arXiv 搜索页，提取论文标题和 ID：

```
https://arxiv.org/search/?searchtype=all&query=<关键词>&start=0&order=-announced_date_first
```

页面会返回论文列表，每篇论文的 ID 格式如 `2604.05843`。

### 第二步：用 API 拉取论文详情

拿到 arXiv ID 后，调用 API：

**元数据（brief）- 推荐先用这个：**
```
GET https://data.rag.ac.cn/arxiv/?type=brief&arxiv_id=<ID>&token=<TOKEN>
```

返回字段：`arxiv_id`, `title`, `tldr`（AI摘要）, `keywords`, `publish_at`, `citations`, `src_url`, `github_url`

**完整论文（raw）：**
```
GET https://data.rag.ac.cn/arxiv/?type=raw&arxiv_id=<ID>&token=<TOKEN>
```

返回完整 Markdown 格式论文内容。

**仅摘要（head）：**
```
GET https://data.rag.ac.cn/arxiv/?type=head&arxiv_id=<ID>&token=<TOKEN>
```

返回：`title`, `abstract`, `authors`, `sections`, `categories`, `publish_at`

**指定章节：**
```
GET https://data.rag.ac.cn/arxiv/?type=section&arxiv_id=<ID>&section=<章节名>&token=<TOKEN>
```

## 使用脚本

提供了 `scripts/arxiv_client.py` 方便调用：

```bash
# 获取论文元数据
python scripts/arxiv_client.py --token YOUR_TOKEN --id 2604.05843 --type brief

# 获取完整论文
python scripts/arxiv_client.py --token YOUR_TOKEN --id 2604.05843 --type raw

# 获取摘要
python scripts/arxiv_client.py --token YOUR_TOKEN --id 2604.05843 --type head

# 获取特定章节
python scripts/arxiv_client.py --token YOUR_TOKEN --id 2604.05843 --type section --section "Introduction"

# 从环境变量读取 token
export ARXIV_API_TOKEN="your-token"
python scripts/arxiv_client.py --id 2604.05843 --type brief
```

Python 调用：
```python
from scripts.arxiv_client import ArxivClient

client = ArxivClient(token="your-token")

# 获取元数据
meta = client.get_brief("2604.05843")
print(meta["title"])
print(meta["tldr"])

# 获取完整论文
paper = client.get_raw("2604.05843")
print(paper["content"])

# 获取摘要
head = client.get_head("2604.05843")
print(head["abstract"])
```

## 示例查询

**搜索 "brain-computer interface" 最新论文：**

1. 搜索：`https://arxiv.org/search/?searchtype=all&query=brain-computer+interface&start=0&order=-announced_date_first`
2. 从页面提取论文 ID（如 `2604.05843`）
3. API：`https://data.rag.ac.cn/arxiv/?type=brief&arxiv_id=2604.05843&token=<TOKEN>`

## 响应字段说明

| 字段 | 含义 |
|------|------|
| `title` | 论文标题 |
| `tldr` | AI 生成的简短摘要（可能为 null） |
| `keywords` | 关键词列表（可能为 null） |
| `publish_at` | 发表日期 |
| `citations` | 引用数（可能为 null） |
| `src_url` | PDF 直链 |
| `github_url` | GitHub 链接（如果有） |

## 注意事项

- Token 属于用户个人资产，**不要在群聊等公开场合提及或存储**
- 免费用户每天 10,000 次请求，注意不要浪费在无效调用上
- 某些新论文可能没有 `tldr` 和 `keywords`（为 null）
- API 响应时间约 50ms，性能很好
