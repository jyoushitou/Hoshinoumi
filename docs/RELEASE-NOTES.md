# v16.0.2 发布说明

- 发布时间：2026-11-10 09:28
- 上一个版本：v15.0
- 提交数：18

## 本次变更

- 4853ef9 feat: 增加 HTML 与 OCR 合并功能，优化小说抓取逻辑
- 74687d6 feat: 更新 v17 文档，明确仅支持 B 站与抖音，放弃起点章节页
- 9e6d8fa feat: 增强登录态注入功能，支持多路径和多格式的 cookie 文件读取
- 9bfdae6 feat: 重构配置管理，敏感信息不再硬编码，支持环境变量和配置文件加载
- 6b8fb00 feat: 增加 OCR 支持，优化章节抓取逻辑，新增分发前检查脚本
- 429795f feat: 新增 OCR 版番茄正文解密脚本，支持浏览器截图和 tesseract OCR 处理
- f2fe78f feat: 新增一键打包脚本，支持多种打包方式及环境变量配置；更新发布检查清单
- f839a93 feat: 更新项目结构，新增 Docker 支持及环境变量配置，优化打包和发布流程
- 012a633 feat: 新增番茄字体解密脚本，支持自动查找参考字体和章节内容解密
- c218523 feat: 新增起点/番茄抓取实测脚本，支持持久化浏览器上下文和挑战处理
- af50f15 feat: 实现空闲时自动读书功能，支持章节摘要和分享；新增相关单元测试
- 1a08ca3 feat: 添加阅读信息到提示文本，支持展示用户最近在看的书籍；新增相关单元测试
- 2d9c754 feat: 添加点名看书功能，支持即时回应并记录书籍链接；新增相关单元测试
- 4336a6f feat: 添加章节摘要功能，支持模型生成摘要和兜底处理；新增相关单元测试
- d88268e feat: 添加从热榜挑书功能，支持已在追书籍的判断和排除已看书籍
- 54e36fe feat: 添加书籍挑选功能，支持自定义书单和从热榜解析书籍
- 6bc3719 feat: Implement novel reading feature (v16) and video watching feature (v17)
- 8711252 chore: 更新发布说明，修改版本号和发布时间，调整升级步骤和回滚命令

## 升级步骤

```bash
git pull ./nao-v16.0.2.bundle main
python3 scripts/preflight.py
python3 -m unittest discover -s tests
# 重启进程
```

## 回滚

```bash
git reset --hard v15.0
```
