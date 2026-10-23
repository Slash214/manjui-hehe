from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

ERRORS = {
    "COMFY_UNREACHABLE": "无法连接 ComfyUI，请检查服务地址和运行状态。",
    "COMFY_VALIDATION": "工作流校验失败，请检查节点、模型和参数映射后重试。",
    "COMFY_EXECUTION": "生成执行失败，请检查工作流和模型配置。",
    "TIMEOUT": "生成超时，请检查执行服务后手动重试。",
    "OUTPUT_MISSING": "任务结束但未找到输出文件，请检查工作流输出节点。",
    "STORAGE_ERROR": "生成结果保存失败，请检查文件存储服务。",
    "WORKER_LOST": "执行进程中断，未能确认生成结果，请检查后手动重试。",
}


class GenerationError(Exception):
    def __init__(self, code: str):
        self.code = code if code in ERRORS else "COMFY_EXECUTION"
        super().__init__(ERRORS[self.code] + " 重试会消耗额外算力。")


class Canceled(Exception):
    pass


@dataclass
class Output:
    data: bytes
    mime: str
    width: int
    height: int
    duration_ms: int | None


Pulse = Callable[[str | None, float | None], None]
ReadFile = Callable[[str], bytes]


class GenerationProvider(Protocol):
    def generate(self, snapshot: dict[str, Any], pulse: Pulse, read: ReadFile) -> Output: ...
    def recover(self, snapshot: dict[str, Any], prompt_id: str | None, read: ReadFile) -> Output | None: ...
