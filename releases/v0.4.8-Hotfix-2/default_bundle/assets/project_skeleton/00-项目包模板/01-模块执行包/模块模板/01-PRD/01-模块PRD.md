# 模块PRD

## 0. 文档信息

| 字段 | 填写内容 |
|------|------|
| 文档标题 | |
| 文档状态 | `draft` / `approved` |
| 当前模块 | |

#### 12. 下游文档列表

| 字段 | 填写内容 |
|------|------|
| required supporting docs | 1. `01-模块执行包/<模块名>/01-PRD/02-模块流程图与人类确认.md`（模块流程图与人类确认）<br>2. |
| optional candidate docs | 1. <br>2. |
| canonical backlink | `01-模块执行包/<模块名>/01-PRD/01-模块PRD.md` |
| linked_prd_source | 下游正式文件回链到的模块真源路径 |
| retired-truth marker | `active` / `historical` / `retired -> <replacement>` |

- 下游文档列表必须只链接真实存在的正式文件
- `canonical backlink` 固定回到当前模块 `PRD` 真源
- `linked_prd_source` 不得指向 `80-完整提交包/` 展示层
- `required supporting docs` 必须登记 `01-模块执行包/<模块名>/01-PRD/02-模块流程图与人类确认.md`；该文件承接页面流转、点击流、人类确认和原型前总控准入
- `02-模块流程图与人类确认.md` 只做规则卡核对与真源回链，不重写模块 `PRD` 正文
- 若旧真源保留，必须补显式 `retired-truth marker`
