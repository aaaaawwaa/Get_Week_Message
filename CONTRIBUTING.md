# 贡献指南

感谢你对每周热点聚合的关注！

## 如何贡献

### 报告 Bug
- 使用 [Bug Report](https://github.com/yourname/weekly-hot/issues/new?template=bug_report.md) 模板
- 描述复现步骤、预期行为和实际行为
- 附上 Python 版本和操作系统信息

### 功能提议
- 使用 [Feature Request](https://github.com/yourname/weekly-hot/issues/new?template=feature_request.md) 模板
- 描述你想要的功能和使用场景

### Pull Request
1. Fork 本仓库
2. 创建你的功能分支：`git checkout -b feature/amazing-feature`
3. 提交你的修改：`git commit -m 'Add amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

### 开发环境
```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\Activate.ps1  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行
python -m app.run_weekly
uvicorn app.main:app --reload
```

### 代码风格
- 遵循 PEP 8
- 函数和类添加文档字符串
- 提交信息使用清晰的中文描述
