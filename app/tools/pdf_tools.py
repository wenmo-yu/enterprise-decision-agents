"""
Markdown 转 PDF 工具

供主智能体把已经生成的 Markdown 文档转换为 PDF。Tool 层只负责解析当前
会话目录中的输入/输出路径，真正的版式转换交给 app.utils.word_converter。
"""

import logging
from pathlib import Path

try:
    from typing import Annotated, Optional
except ImportError:
    from typing_extensions import Annotated, Optional

from langchain_core.tools import tool

from app.api.context import get_session_context
from app.api.monitor import monitor
from app.utils.path_utils import resolve_path
from app.utils.word_converter import convert_md_to_pdf as convert_md_to_pdf_via_word


@tool
def convert_md_to_pdf(
    md_filename: Annotated[str, "要转换的Markdown文档路径（包含.md后缀）"],
    pdf_filename: Annotated[
        Optional[str], "输出的PDF文件路径（可选，默认与源文件同名）"
    ] = None,
) -> str:
    """
    将当前会话目录中的 Markdown 文档转换为 PDF

    :param md_filename: Markdown 文件名或相对路径，缺少后缀时会自动补为 .md
    :param pdf_filename: 可选 PDF 输出文件名；不传时与 Markdown 同名
    :return: 转换结果说明
    """
    monitor.report_tool("Markdown转PDF工具")

    try:
        # 输入路径必须先落到当前会话目录，避免模型传入任意系统路径
        session_dir = get_session_context()
        md_path = Path(md_filename).with_suffix(".md")
        md_abs_path = Path(resolve_path(str(md_path), session_dir))

        if not md_abs_path.exists():
            return f"错误：文件不存在 {md_abs_path}"

        # 未指定 PDF 文件名时，默认与源 Markdown 同目录同名
        if pdf_filename:
            pdf_path = Path(pdf_filename).with_suffix(".pdf")
            pdf_abs_path = Path(resolve_path(str(pdf_path), session_dir))
        else:
            pdf_abs_path = md_abs_path.with_suffix(".pdf")

        # PDF 版式、中文字体和 Markdown 解析细节都封装在底层转换模块中
        return convert_md_to_pdf_via_word(md_abs_path, pdf_abs_path)

    except Exception as e:
        logging.error(f"转换失败: {e}", exc_info=True)
        return f"转换失败: {str(e)}"


if __name__ == "__main__":
    # 本地调试入口：直接运行本文件可验证 Markdown 转 PDF 链路
    get_session_context = lambda: "./examples/test_docs"

    test_dir = Path("./examples/test_docs/sub_dir")
    test_dir.mkdir(parents=True, exist_ok=True)
    test_md_path = test_dir / "企业经营分析报告.md"
    test_md_path.write_text(
        """# 企业经营分析报告

## 一、核心结论

企业经营决策需要同时关注收入增长、客户价值、成本效率和风险控制。
制定年度业务策略时，应优先分析区域差异、客户需求变化和组织能力约束。

## 二、重点观察

- 经营增长不能只看新增客户，也要关注留存、利润与交付效率。
- 服务流程和价格策略会共同影响客户转化与长期价值。
- 业务创新需要同步关注合规、风险控制与客户体验。

## 三、示例数据

| 指标 | 观察结果 | 建议动作 |
| --- | --- | --- |
| 客户转化 | 高价值客户的决策周期更长 | 优化服务触点与跟进节奏 |
| 客户留存 | 服务体验影响长期价值 | 建立分层运营与反馈闭环 |
| 风险控制 | 异常信号需要及时处理 | 强化监测和处置流程 |

## 四、行动建议

围绕“增长、转化、风控、合规”四个关键词设计分析框架，并将公开信息、经营数据和内部知识库材料统一整理成可交付报告。
""",
        encoding="utf-8",
    )

    print(convert_md_to_pdf.invoke({"md_filename": "sub_dir/企业经营分析报告.md"}))
