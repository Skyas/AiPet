"""
视觉记忆模块 — 滚动屏幕观察缓冲区

维护最近 N 次屏幕观察，供两个场景使用：

  1. 注入对话 system prompt：让 AI 了解"最近发生了什么"，实现时间连贯性。
     比如 AI 能感知到"五分钟前用户还在主菜单，现在已经在游戏里了"。

  2. ProactiveEngine 的变化检测：通过词袋重叠率判断画面是否发生了显著变化，
     辅助决策"是否有值得说的新内容"（无显著变化时倾向于 SILENT）。

设计原则：
  - 纯内存结构，进程重启后清空。屏幕观察是实时性数据，不需要持久化。
  - 线程安全不是必须的，因为 FastAPI + asyncio 是单线程事件循环，
    所有写操作都在同一线程上发生。
"""
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScreenObservation:
    """单次屏幕观察记录。"""
    timestamp: float                        # Unix 时间戳
    vision_desc: str                        # 视觉模型返回的画面描述
    triggered_by: str = "auto"             # "proactive" | "user_chat" | "manual"
    associated_reply: Optional[str] = None  # 如果这次观察触发了 AI 回复，记录下来

    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    def formatted_age(self) -> str:
        """返回人类可读的时间差，用于 context 注入。"""
        age = self.age_seconds()
        if age < 60:
            return f"{int(age)}秒前"
        if age < 3600:
            return f"{int(age / 60)}分钟前"
        return f"{int(age / 3600)}小时前"


class VisionMemory:
    def __init__(self, max_size: int = 5):
        self._buffer: deque[ScreenObservation] = deque(maxlen=max_size)

    def add(self, vision_desc: str, triggered_by: str = "auto") -> ScreenObservation:
        """添加一次新的屏幕观察记录并返回它，方便调用方设置 associated_reply。"""
        obs = ScreenObservation(
            timestamp=time.time(),
            vision_desc=vision_desc,
            triggered_by=triggered_by,
        )
        self._buffer.append(obs)
        return obs

    def get_latest(self) -> Optional[ScreenObservation]:
        """获取最近一次观察。"""
        return self._buffer[-1] if self._buffer else None

    def get_recent(self, n: int = 3) -> list[ScreenObservation]:
        """获取最近 n 次观察（最旧的在前，最新的在后）。"""
        items = list(self._buffer)
        return items[-n:]

    def get_context_for_prompt(self, n: int = 3) -> str:
        """
        生成可以注入 system prompt 的屏幕变化摘要。

        格式：
            [30秒前] 用户在 CS2 主菜单浏览皮肤
            [10秒前] 用户进入了竞技匹配模式，地图 Mirage 正在加载

        这个摘要让 AI 具备时间感，知道局势是如何演变的，而不仅仅是当前这一帧。
        只包含有 vision_desc 的条目；空字符串不注入。
        """
        recent = self.get_recent(n)
        lines = [
            f"[{obs.formatted_age()}] {obs.vision_desc}"
            for obs in recent
            if obs.vision_desc.strip()
        ]
        return "\n".join(lines)

    def has_significant_change(self, new_desc: str) -> bool:
        """
        用词袋 Jaccard 相似度判断新描述与上次是否有显著差异。

        Jaccard 相似度 = |交集| / |并集|
        低于阈值（0.65）认为变化显著，即有新东西可以说。

        这是一个刻意简单的实现：不需要语义理解，只需快速判断"大致一样还是不一样"。
        误差在可接受范围内——最坏情况是偶尔错过一次真实变化，或偶尔多说一次没必要的话。
        """
        latest = self.get_latest()
        if not latest or not latest.vision_desc:
            return True  # 第一次观察，始终视为"有变化"

        old_words = set(latest.vision_desc.split())
        new_words = set(new_desc.split())
        if not old_words and not new_words:
            return False
        if not old_words or not new_words:
            return True

        jaccard = len(old_words & new_words) / len(old_words | new_words)
        return jaccard < 0.65

    def clear(self):
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)