# syserroranl - IT系统故障影响分析应用

## 项目简介

syserroranl 是一个 IT 系统故障分析基础数据库应用。通过录入 IT 系统的节点数据和依赖关系，建立故障传播分析的基础数据库。

---

## 项目文件结构

```
syserroranl/
├── app.py                        # FastAPI 主应用入口
├── database.py                   # 数据库配置（SQLAlchemy + SQLite）
├── models.py                     # SQLAlchemy ORM 模型（System 模型）
├── schemas.py                    # Pydantic 请求/响应模型
├── main_entry.py                 # 备用启动入口
├── requirements.txt               # Python 依赖列表
├── start.bat                     # Windows 启动脚本
├── syserroranl.db                # SQLite 数据库文件（运行时生成）
│
├── routers/                      # API 路由模块
│   ├── __init__.py
│   ├── systems.py                # 系统管理 API
│   ├── nodes.py                  # 节点管理 API（含批量导入）
│   ├── edges.py                  # 边管理 API（含自动初始化）
│   └── server_query.py           # IP 查询 API（SHA256 哈希匹配）
│
├── static/                       # 前端静态资源
│   ├── index.html                # 单页应用主文件（Vue 3 + Tailwind）
│   ├── vue.global.prod.js        # Vue 3 生产版本
│   ├── tailwind.min.css          # Tailwind CSS 样式
│   ├── axios.min.js               # HTTP 客户端
│   ├── d3.v7.min.js               # D3.js 图谱可视化
│   └── xlsx.full.min.js          # SheetJS Excel 处理（离线）
│
├── output/                       # 打包输出目录
│   ├── 启动应用.bat
│   └── syserroranl/
│       └── syserroranl.exe       # 打包后的可执行文件
│
├── add_test_data.py              # 测试数据生成脚本
├── migrate_add_insertID.py       # 数据库迁移脚本（添加 insertID 字段）
├── temp_check*.py                # 临时调试脚本
├── test_api.py                   # API 测试脚本
├── syserroranl.spec              # PyInstaller 打包配置
├── PROJECT_REPORT.md             # 项目报告
└── README.md                    # 项目说明文档
```

---

## 核心数据模型

### 节点类型（8种）

| 类型 | 说明 | 层级 | 录入方式 |
|------|------|------|----------|
| 服务系统 | 依赖系统功能完成某项业务 | L1 | 资源录入 |
| 系统功能 | 系统对外部提供的功能（API/页面） | L2 | 资源录入 |
| 系统 | 完成一组系统功能的IT系统 | L3 | 添加系统 |
| 支撑系统 | 为本系统提供底层支撑的外部系统 | L3 | 资源录入 |
| 节点 | 系统内共同完成一组功能的集群 | L4 | 资源录入 |
| 集群 | 节点内完成某项业务功能的一组服务器 | L5 | 资源录入 |
| 服务器 | 为组件提供运行环境的物理机/虚拟机 | L6 | 资源录入 |
| 组件 | 实现某项功能的软件（可运行多个） | L7 | 资源录入 |

### 节点名称唯一性规则

- **唯一类型**：服务系统、支撑系统、系统功能、节点 → 同类型下名称不可重复
- **可重复类型**：集群、服务器、组件 → 同类型下名称可重复
- **系统**：只能通过「添加系统」功能创建

### 边（Edge）

点与点之间的依赖关系：
- **源节点**: 依赖方
- **目标节点**: 被依赖方
- **故障权重**: 1-10，数字越大影响越严重

### insertID 字段

用于批量导入时的去重标识：
- **insertID 相同**：更新已有节点（保留系统 id，按新数据更新字段）
- **insertID 不同或无 insertID**：新增节点
- insertID 不作为系统内唯一键，系统按 id 字段管理数据

### cluster 字段

用于自动初始化边关系，存储上级节点的 insertID：
- 服务器的 cluster = 所属集群的 insertID
- 组件的 cluster = 所属服务器的 insertID
- 节点的 cluster = 所属系统的 insertID
- 后续手动创建/修改边时不参考此字段

---

## 依赖层级关系

```
服务系统 → 系统功能 → 系统/支撑系统 → 节点 → 集群 → 服务器 → 组件
```

### 自动初始化边规则

| 边类型 | 权重 | 判断方式 |
|--------|------|----------|
| 节点 → 系统 | 8 | 节点的 cluster = 上级系统的 insertID |
| 集群 → 节点 | 8 | 集群的 cluster = 上级节点的 insertID |
| 服务器 → 集群 | 5 | 服务器的 cluster = 上级集群的 insertID |
| 组件 → 服务器 | 10 | 组件的 cluster = 上级服务器的 insertID |

---

## 快速启动

### 方式一：使用启动脚本

```bash
cd D:\project\syserroranlbuil
start.bat
```

### 方式二：命令行启动

```bash
cd D:\project\syserroranlbuil
pip install -r requirements.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

访问地址：**http://localhost:8000**

---

## 功能页面

### 1. 数据概览
- 总节点数/总边数统计
- 节点类型分布
- 故障权重分布
- **启动时自动加载**：访问页面时自动加载数据库中第一个系统的数据

### 2. 资源录入
- **录入节点**: 添加节点、集群、服务器、组件、服务系统、支撑系统、系统功能
- **建立依赖**: 创建节点间的边关系

### 3. 依赖维护
- 查看所有依赖关系
- 按类型筛选
- 编辑/删除边

### 4. 节点管理
- 节点列表（支持搜索/筛选）
- 编辑/删除节点

### 5. 系统图谱
- D3.js 可视化拓扑图
- **贝塞尔曲线边**：同对节点多边自动平行偏移绑扎
- **四叉树碰撞检测**：`forceCollide` 按节点类型动态半径，防止标签叠加
- **集群 Hull 凸包**：同集群服务器节点自动圈起分组
- **路径高亮**：点击节点高亮上下游依赖路径（橙线上游/蓝线下游）
- **缩放指示器**：实时显示当前缩放比例
- **节点类型力参数**：按层级调整斥力大小，顶层更强
- 支持拖拽布局
- 边权重编辑

### 6. 导入导出
- **导出**：按样表格式导出为 Excel（服务器名称、IP、组件名称、组件描述、服务器所属集群、集群所属节点）
- **导入**：3步骤向导流程（上传 Excel → 加密设置 → 确认导入），支持 insertID 去重
- 自动初始化边

---

## API 接口

### 系统管理 `/api/systems`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 获取所有系统 |
| POST | / | 创建系统 |
| GET | /{system_id} | 获取单个系统 |
| PUT | /{system_id} | 更新系统 |
| DELETE | /{system_id} | 删除系统 |

### 节点管理 `/api/systems/{system_id}/nodes`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 获取所有节点 |
| GET | /{node_id} | 获取单个节点 |
| POST | / | 创建节点 |
| PUT | /{node_id} | 更新节点 |
| DELETE | /{node_id} | 删除节点 |
| POST | /batch | 批量导入节点 |

### 边管理 `/api/systems/{system_id}/edges`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 获取所有边 |
| GET | /{edge_id} | 获取单个边 |
| POST | / | 创建边 |
| PUT | /{edge_id} | 更新边 |
| DELETE | /{edge_id} | 删除边 |
| DELETE | /all | 删除所有边 |
| POST | /auto-init | 自动初始化边 |
| GET | /from/{node_id} | 获取从某节点出发的边 |
| GET | /to/{node_id} | 获取指向某节点的边 |
| POST | /batch | 批量创建边 |

### 服务器查询 `/api/server-query`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /{system_id} | 查询系统内所有服务器（返回 IP 哈希列表） |
| GET | /{system_id}/match | IP 哈希匹配查询（支持模糊匹配） |

### 统计 `/api/systems/{system_id}/stats`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 获取统计数据 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python FastAPI |
| 数据库 | SQLite + SQLAlchemy |
| 前端框架 | Vue 3 (CDN) |
| 样式 | Tailwind CSS |
| 可视化 | D3.js v7 |
| HTTP 客户端 | Axios |
| Excel 处理 | SheetJS (xlsx.js) |
| 打包工具 | PyInstaller |

---

## 数据库结构

### systems 表（主表）
```sql
CREATE TABLE systems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(20) DEFAULT '#6366f1',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### nodes_system_{id} 表（每个系统独立）
```sql
CREATE TABLE nodes_system_{id} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    description TEXT,
    cluster VARCHAR(100),        -- 上级节点的 insertID（用于初始化边）
    insertID VARCHAR(255),      -- 导入唯一标识（不显示不修改）
    properties JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### edges_system_{id} 表（每个系统独立）
```sql
CREATE TABLE edges_system_{id} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    weight INTEGER DEFAULT 5,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, target_id)
);
```

---

## 常用命令

### 生成测试数据
```bash
python add_test_data.py
```

### 数据库迁移（添加 insertID 字段）
```bash
python migrate_add_insertID.py
```

### 打包为可执行文件
```bash
pyinstaller syserroranl.spec
```

---

## 端口配置

- 默认端口：**8000**
- 修改位置：`app.py` 中的 `uvicorn` 启动参数

---

## 注意事项

1. **数据安全**：删除系统时会级联删除该系统的所有节点和边数据
2. **批量导入**：使用 insertID 实现去重功能
3. **边初始化**：手动创建的边不受 cluster 字段影响
4. **名称重复**：集群/服务器/组件类型允许同名，其他类型不允许
5. **离线运行**：所有依赖已打包到本地，无需网络连接
6. **路径无关**：使用绝对路径，可部署到任意目录
