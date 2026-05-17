# QTrade

QTrade 是一个 AI 驱动的国内股票量化交易系统。
当前处于 **O0 阶段**，已建立了稳固的工程基座。

## 阶段目标 (O0)

- [x] 提供统一的项目安装与测试运行机制 (`uv`)
- [x] 建立清晰的项目目录结构
- [x] 定义核心领域模型（Symbol、Bar、Signal、Order 等）
- [x] 提供支持多环境隔离的配置系统
- [x] 基础日志与错误异常类型的划分

## 环境要求

- Python 3.11+
- `uv` 包管理器

## 安装与运行

本工程推荐使用 `uv` 进行依赖管理。

1. **安装依赖**：
   ```bash
   uv sync
   ```
   *注意：开发时所需依赖已在 `pyproject.toml` 中通过 `[dependency-groups]` 设定。*

2. **运行测试**：
   ```bash
   PYTHONPATH=. uv run pytest
   ```

3. **代码检查与格式化**：
   ```bash
   uv run ruff check .
   uv run ruff format .
   ```

## 目录结构说明

- `qtrade/core/`：系统核心抽象层，包含领域类型、配置系统、日志、错误定义。
- `tests/`：单元测试与集成测试，保证系统的正确性和基座可信。
- `configs/`：存放示例配置。
- `docs/`：存放所有的架构设计与 OKR 文档。
