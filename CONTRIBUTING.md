# 贡献指南 / Contributing

感谢你考虑为 WarcLens 做贡献！本项目坚持**零第三方运行时依赖**，请在贡献时遵守这一原则。

## 开发环境

- Python 3.8+
- 无需安装任何运行时依赖；测试使用标准库 `unittest`。

```bash
git clone https://github.com/gitstq/warclens.git
cd warclens
python3 -m unittest discover -s tests
```

## 提交规范

所有提交遵循 [Angular 提交约定](https://www.conventionalcommits.org/)：

- `feat:` 新功能
- `fix:` 缺陷修复
- `docs:` 文档变更
- `refactor:` 重构（不改变行为）
- `test:` 测试相关
- `chore:` 构建/工具链

示例：`feat(parser): 支持 WARC/1.1 记录版本行`

## 代码要求

1. 新增功能必须附带单元测试，并放在 `tests/` 下；
2. 保持公共 API 有清晰的中文 + 英文 docstring；
3. 不得引入任何会破坏"零依赖"承诺的第三方库；
4. 确保 `build.sh` 全流程通过后再提交 PR。

## 问题与建议

请通过 GitHub Issues 反馈，附上可复现的最小示例（可脱敏的 WARC 片段）。
