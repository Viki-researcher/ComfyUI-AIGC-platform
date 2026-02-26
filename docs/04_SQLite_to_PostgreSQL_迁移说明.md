## SQLite 到 PostgreSQL 数据库迁移说明

### 1. 为什么迁移到 PostgreSQL？

| 对比维度 | SQLite | PostgreSQL |
|---|---|---|
| **并发** | 单写锁，多用户场景性能瓶颈 | MVCC 多版本并发控制，高并发无阻塞 |
| **数据完整性** | 弱类型，外键默认关闭 | 强类型系统，严格约束 |
| **可扩展性** | 单文件，无法水平扩展 | 支持流复制、读写分离、分区表 |
| **全文搜索** | 不支持 | 内置 tsvector 全文搜索 |
| **JSON 支持** | 基础 | 原生 JSONB，支持索引和查询 |
| **备份与恢复** | 文件复制 | pg_dump/pg_restore，支持增量备份 |
| **生产适用** | 仅适合开发/嵌入式 | 企业级生产环境首选 |

### 2. 潜在不利之处

- **运维成本增加**：需要安装、配置和维护 PostgreSQL 服务，包括备份策略、监控和调优
- **部署复杂度**：多了一个外部依赖服务，Docker 部署需增加 PostgreSQL 容器
- **开发环境门槛**：开发者本机需要安装 PostgreSQL（可用 Docker 替代）
- **资源占用**：PostgreSQL 常驻进程占用额外内存（约 50-200MB 基础开销）
- **迁移风险**：已有 SQLite 数据需要导出/导入，过程中可能出现数据类型不兼容

### 3. 迁移步骤

#### 3.1 安装 PostgreSQL

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

#### 3.2 创建数据库和用户

```bash
sudo -u postgres psql <<EOF
ALTER USER postgres PASSWORD 'postgres';
CREATE DATABASE data_generation;
EOF
```

#### 3.3 修改环境变量

编辑 `docs/.env.platform`：

```bash
DB_DEFAULT_CONNECTION="postgres"
POSTGRES_HOST="127.0.0.1"
POSTGRES_PORT="5432"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"
POSTGRES_DB="data_generation"
```

#### 3.4 重启后端

后端启动时会自动运行 Aerich 迁移，在 PostgreSQL 中创建所有表结构并初始化种子数据（管理员账号、菜单、角色等）。

```bash
cd docs && ./scripts/start_all.sh
```

#### 3.5 数据迁移（可选）

如果需要将已有 SQLite 数据迁移至 PostgreSQL，可使用以下脚本思路：

```python
# 1. 从 SQLite 读取所有表数据
# 2. 按表名逐行写入 PostgreSQL
# 3. 注意处理自增ID和时间格式差异
```

### 4. 回退方案

如需回退到 SQLite（例如开发环境），只需修改：

```bash
DB_DEFAULT_CONNECTION="sqlite"
```

后端会自动使用 `db.sqlite3` 文件作为数据库。
