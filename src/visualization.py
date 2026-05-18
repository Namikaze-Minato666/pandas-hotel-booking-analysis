"""
可视化模块：
- 统一 Matplotlib + Seaborn 绘图风格
- 封装常用分析图表
- 自动保存到 outputs/figures/
- save_figure() 在保存前自动修复中文显示
"""

import os
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.font_manager as fm
from matplotlib.text import Text
import seaborn as sns
import numpy as np
from src.config import FIGURE_DIR

# Windows 中文字体文件路径（按优先级）
_WIN_CJK_FONT_PATHS = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
]

_cjk_font_path = None
_cjk_font_name = None


def _detect_cjk_font_path():
    """检测第一个可用的 Windows 中文字体文件路径并注册到 matplotlib。"""
    global _cjk_font_path, _cjk_font_name

    if _cjk_font_path is not None or _cjk_font_name is not None:
        return _cjk_font_path

    for font_path in _WIN_CJK_FONT_PATHS:
        if os.path.exists(font_path):
            try:
                fm.fontManager.addfont(font_path)
                fp = fm.FontProperties(fname=font_path)
                _cjk_font_name = fp.get_name()
                _cjk_font_path = font_path
                print(f"[字体配置] 已加载中文字体: {_cjk_font_name} ({font_path})")
                return _cjk_font_path
            except Exception as e:
                print(f"[字体配置] 加载失败 {font_path}: {e}")

    # 回退方案：通过名称在系统字体列表中查找
    cjk_candidates = [
        "Microsoft YaHei", "SimHei", "SimSun",
        "Noto Sans CJK SC", "WenQuanYi Micro Hei",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in cjk_candidates:
        if font in available:
            _cjk_font_name = font
            print(f"[字体配置] 已启用中文字体（系统检测）: {font}")
            return None

    print("[字体配置] 未检测到中文字体，中文可能显示为方块。")
    return None


def _get_cjk_fp(size=None, weight=None):
    """
    获取中文字体 FontProperties 对象，用于显式传入绘图函数。
    若已通过文件路径加载，优先使用 fname 参数确保渲染准确。
    """
    path = _detect_cjk_font_path()
    if path is None and _cjk_font_name is None:
        return None

    kwargs = {}
    if path:
        kwargs["fname"] = path
    else:
        kwargs["family"] = _cjk_font_name
    if size:
        kwargs["size"] = size
    if weight:
        kwargs["weight"] = weight
    return fm.FontProperties(**kwargs)


def set_plot_style():
    """统一设置 Matplotlib / Seaborn 全局绘图风格与中文字体。"""
    # 1. 先加载中文字体文件到 matplotlib 字体管理器
    _detect_cjk_font_path()

    # 2. 应用 seaborn 风格（必须在设置中文字体之前）
    sns.set_style("whitegrid")
    sns.set_palette("Set2")

    # 3. 在 seaborn 之后覆盖中文字体设置——避免被 seaborn 的默认字体覆盖
    if _cjk_font_name:
        matplotlib.rcParams["font.family"] = "sans-serif"
        matplotlib.rcParams["font.sans-serif"] = [_cjk_font_name, "DejaVu Sans"]
        matplotlib.rcParams["axes.unicode_minus"] = False
        print(f"[字体配置] rcParams 已设置为: {_cjk_font_name}")

    matplotlib.rcParams["figure.dpi"] = 150
    matplotlib.rcParams["savefig.dpi"] = 150
    matplotlib.rcParams["savefig.bbox"] = "tight"


def _apply_font_to_element(elem, cjk_path, cjk_name):
    """对单个文本元素应用中文字体，同时保留其原有的 size / weight / style 等属性。"""
    if elem is None:
        return

    fp = elem.get_fontproperties()
    if cjk_path:
        fp.set_file(cjk_path)
    elif cjk_name:
        fp.set_family(cjk_name)
    elem.set_fontproperties(fp)


def apply_chinese_font(fig=None):
    """
    遍历 figure 中所有 axes，对全部文本元素显式设置中文字体，保留原有样式。

    参数:
        fig: matplotlib Figure 对象，若为 None 则使用 plt.gcf()
    返回:
        fig 对象
    """
    if fig is None:
        fig = plt.gcf()

    cjk_path = _detect_cjk_font_path()
    if cjk_path is None and _cjk_font_name is None:
        return fig

    # 统一处理 figure 中所有 Text 对象，包括标题、坐标轴标签、刻度、
    # 图例、suptitle、annotate、colorbar 和 twinx 轴上的文字。
    for text in fig.findobj(match=Text):
        _apply_font_to_element(text, cjk_path, _cjk_font_name)

    return fig


def save_figure(fig, filename):
    """将 figure 保存到 outputs/figures/ 目录，保存前自动修复中文显示。"""
    apply_chinese_font(fig)
    os.makedirs(FIGURE_DIR, exist_ok=True)
    filepath = os.path.join(FIGURE_DIR, filename)
    fig.savefig(filepath)
    print(f"图表已保存: {filepath}")
    plt.close(fig)


def plot_missing_values(missing_df):
    """
    绘制缺失值柱状图。

    参数:
        missing_df: get_missing_summary() 返回的缺失值统计 DataFrame
    """
    if missing_df.empty:
        print("无缺失值，跳过绘图。")
        return None

    title_fp = _get_cjk_fp(size=14, weight="bold")
    label_fp = _get_cjk_fp(size=12)
    tick_fp = _get_cjk_fp(size=9)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(missing_df["列名"], missing_df["缺失数量"],
                  color=sns.color_palette("Set2")[2])
    ax.set_title("各列缺失值数量", fontproperties=title_fp)
    ax.set_xlabel("列名", fontproperties=label_fp)
    ax.set_ylabel("缺失数量", fontproperties=label_fp)
    ax.tick_params(axis="x", rotation=45)

    for bar, pct in zip(bars, missing_df["缺失比例(%)"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 500,
                f"{pct}%", ha="center", fontproperties=tick_fp)

    fig.tight_layout()
    return fig


def plot_cancel_rate_by_group(df, group_col):
    """
    按分组列绘制取消率对比柱状图。

    参数:
        df      : DataFrame
        group_col: 用于分组的列名（如 'hotel'）
    """
    title_fp = _get_cjk_fp(size=14, weight="bold")
    label_fp = _get_cjk_fp(size=12)
    tick_fp = _get_cjk_fp(size=10)

    cancel_rate = df.groupby(group_col)["is_canceled"].mean().sort_values()
    colors = sns.color_palette("Set2", len(cancel_rate))

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(cancel_rate.index.astype(str), cancel_rate.values,
                  color=colors)
    ax.set_title(f"按 {group_col} 分组的取消率", fontproperties=title_fp)
    ax.set_xlabel(group_col, fontproperties=label_fp)
    ax.set_ylabel("取消率", fontproperties=label_fp)
    ax.set_ylim(0, 1)

    for bar, val in zip(bars, cancel_rate.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f"{val:.1%}", ha="center", fontproperties=tick_fp)

    fig.tight_layout()
    return fig
