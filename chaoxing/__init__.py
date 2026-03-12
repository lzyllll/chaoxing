# -*- coding: utf-8 -*-
"""
超星学习通自动化项目

包结构：
- core: 核心 API 和基础设施
- services: 外部服务集成（题库、通知）
- processors: 任务处理器
- utils: 工具类
"""

__version__ = "3.1.3"


def formatted_output(_status, _text, _data):
    """格式化输出"""
    return {"status": _status, "msg": _text, "data": _data}