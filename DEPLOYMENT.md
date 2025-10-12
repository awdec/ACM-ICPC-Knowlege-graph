# 部署指南

## 生产环境部署

### 1. 环境准备

#### 系统要求
- Ubuntu 20.04+ / CentOS 7+ / Windows Server 2019+
- Python 3.8+
- Neo4j 5.x
- 至少 4GB RAM
- 10GB+ 磁盘空间

#### Neo4j数据库部署

1. **安装Neo4j**
   ```bash
   # Ubuntu/Debian
   wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
   echo 'deb https://debian.neo4j.com stable 4.4' | sudo tee -a /etc/apt/sources.list.d/neo4j.list
   sudo apt update
   sudo apt install neo4j=1:5.9.0
   
   # 或使用Docker
   docker run --name neo4j \
     -p7474:7474 -p7687:7687 \
     -d \
     -v $HOME/neo4j/data:/data \
     -v $HOME/neo4j/logs:/logs \
     -v $HOME/neo4j/import:/var/lib/neo4j/import \
     -v $HOME/neo4j/plugins:/plugins \
     --env NEO4J_AUTH=neo4j/your_password \
     neo4j:5.9.0
   ```

2. **配置Neo4j**
   ```bash
   # 编辑配置文件
   sudo nano /etc/neo4j/neo4j.conf
   
   # 关键配置项
   dbms.default_listen_address=0.0.0.0
   dbms.connector.bolt.listen_address=:7687
   dbms.connector.http.listen_address=:7474
   dbms.memory.heap.initial_size=1G
   dbms.memory.heap.max_size=2G
   dbms.memory.pagecache.size=1G
   ```

3. **启动服务**
   ```bash
   sudo systemctl enable neo4j
   sudo systemctl start neo4j
   sudo systemctl status neo4j
   ```

### 2. 应用部署

#### 使用Docker部署

1. **创建Dockerfile**
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY src/ ./src/
   COPY . .
   
   EXPOSE 8501
   
   HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
   
   CMD ["streamlit", "run", "src/app.py", "--server.address=0.0.0.0"]
   ```

2. **构建和运行**
   ```bash
   docker build -t acm-kg-qa .
   docker run -d \
     --name acm-kg-qa \
     -p 8501:8501 \
     -e NEO_URI=bolt://neo4j:7687 \
     -e NEO_USER=neo4j \
     -e NEO_PWD=your_password \
     --link neo4j:neo4j \
     acm-kg-qa
   ```

#### Docker Compose部署

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.9.0
    container_name: neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - ./neo4j_import_csvs:/var/lib/neo4j/import
    environment:
      NEO4J_AUTH: neo4j/luogu20201208
      NEO4J_PLUGINS: ["apoc"]
    restart: unless-stopped

  app:
    build: .
    container_name: acm-kg-qa
    ports:
      - "8501:8501"
    environment:
      NEO_URI: bolt://neo4j:7687
      NEO_USER: neo4j
      NEO_PWD: luogu20201208
    depends_on:
      - neo4j
    restart: unless-stopped

volumes:
  neo4j_data:
  neo4j_logs:
```

#### 传统部署

1. **克隆代码**
   ```bash
   git clone <repository-url>
   cd ACM-ICPC-Knowlege-graph
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或 venv\Scripts\activate  # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量**
   ```bash
   export NEO_URI="bolt://localhost:7687"
   export NEO_USER="neo4j"
   export NEO_PWD="luogu20201208"
   ```

5. **启动应用**
   ```bash
   streamlit run src/app.py --server.port 8501 --server.address 0.0.0.0
   ```

### 3. 数据导入

#### 准备CSV文件
确保以下CSV文件在 `neo4j_import_csvs/` 目录中：
- `problems.csv` - 题目信息
- `contest.csv` - 竞赛信息
- `solution.csv` - 题解信息
- 其他相关数据文件

#### 导入数据
```cypher
// 导入题目数据
LOAD CSV WITH HEADERS FROM 'file:///problems.csv' AS row
CREATE (p:Problem {
  name: row.name,
  rating: toInteger(row.rating)
});

// 导入竞赛数据
LOAD CSV WITH HEADERS FROM 'file:///contest.csv' AS row
CREATE (c:Contest {
  name: row.name,
  year: toInteger(row.year)
});

// 创建索引
CREATE INDEX FOR (p:Problem) ON (p.name);
CREATE INDEX FOR (c:Contest) ON (c.name);
CREATE INDEX FOR (t:Tag) ON (t.name);
```

### 4. 反向代理配置

#### Nginx配置
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

### 5. 监控和日志

#### 应用监控
```python
# 在app.py中添加监控
import logging
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/acm-kg-qa.log'),
        logging.StreamHandler()
    ]
)
```

#### 系统监控
```bash
# 使用systemd管理服务
sudo tee /etc/systemd/system/acm-kg-qa.service > /dev/null <<EOF
[Unit]
Description=ACM KG QA System
After=network.target

[Service]
Type=simple
User=app
WorkingDirectory=/opt/acm-kg-qa
Environment=NEO_URI=bolt://localhost:7687
Environment=NEO_USER=neo4j
Environment=NEO_PWD=luogu20201208
ExecStart=/opt/acm-kg-qa/venv/bin/streamlit run src/app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable acm-kg-qa
sudo systemctl start acm-kg-qa
```

## 安全配置

### 1. Neo4j安全
```bash
# 修改默认密码
cypher-shell -u neo4j -p neo4j
CALL dbms.security.changePassword('strong_password');

# 配置SSL（可选）
dbms.connector.bolt.tls_level=REQUIRED
dbms.ssl.policy.bolt.enabled=true
```

### 2. 网络安全
- 使用防火墙限制端口访问
- 配置HTTPS
- 使用VPN或专网访问

### 3. 应用安全
- 设置Streamlit密码保护
- 限制文件上传
- 输入验证和清理

## 性能优化

### 1. Neo4j优化
```cypher
// 创建必要的索引
CREATE INDEX FOR (p:Problem) ON (p.name);
CREATE INDEX FOR (p:Problem) ON (p.rating);
CREATE INDEX FOR (t:Tag) ON (t.name);
CREATE INDEX FOR (c:Contest) ON (c.name, c.year);

// 查询优化示例
PROFILE MATCH (p:Problem) WHERE p.name CONTAINS $name RETURN p;
```

### 2. 应用优化
- 启用Streamlit缓存
- 实现查询结果缓存
- 使用连接池
- 添加查询超时

### 3. 系统优化
- 增加内存配置
- 使用SSD存储
- 配置负载均衡
- 启用压缩传输

## 备份和恢复

### 1. Neo4j备份
```bash
# 创建备份
neo4j-admin database dump --database=neo4j --to-path=/backup

# 恢复备份
neo4j-admin database load --from-path=/backup --database=neo4j --overwrite-destination
```

### 2. 应用备份
- 备份配置文件
- 备份自定义代码
- 备份日志文件

## 故障排除

### 常见问题
1. **端口冲突** - 修改端口配置
2. **内存不足** - 增加系统内存或调整配置
3. **连接超时** - 检查网络和防火墙设置
4. **数据不一致** - 重新导入数据或修复索引

### 日志分析
```bash
# 查看应用日志
tail -f /var/log/acm-kg-qa.log

# 查看Neo4j日志
tail -f /var/log/neo4j/neo4j.log

# 查看系统资源
htop
iostat -x 1
```