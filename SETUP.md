# 期货日报系统

## 快速开始

### 1. Fork 本项目到您的 GitHub 账号

### 2. 配置 QQ 邮箱授权码

1. 登录 QQ 邮箱网页版
2. 设置 → 账户 → 开启 POP3/SMTP 服务
3. 获取 16 位授权码（不是登录密码）
4. 在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加：
   - Name: `EMAIL_PASSWORD`
   - Value: 您的 16 位授权码

### 3. 手动测试

进入 Actions 页面，点击 "期货日报" workflow，选择 "Run workflow" 手动触发。

### 4. 自动运行

每天北京时间 07:00 自动运行。

## 自定义配置

编辑 `main.py` 中的以下变量：

- `RECIPIENT_EMAIL`: 收件邮箱
- `FUTURES_CONFIG`: 期货品种配置
- `HISTORICAL_LOW`: 历史最低价数据
- 各分析函数中的行业数据

## 数据来源

- 实时行情：东方财富/AKShare
- 行业分析：基于公开研报整理（需定期更新）

## 注意事项

1. 行业分析数据需要定期手动更新
2. 如 AKShare 接口变化，可能需要更新代码
3. 建议每周检查一次运行日志
