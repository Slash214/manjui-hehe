from copy import deepcopy
from typing import Any

FIELDS = {"prompt", "negative_prompt", "seed", "width", "height", "first_frame", "frame_count", "fps"}


def validate_mapping(graph: dict[str, Any], mapping: dict[str, Any]) -> None:
    for field, destination in mapping.items():
        if field not in FIELDS and not (field.startswith("ref_image_") and field[10:].isdigit()):
            raise ValueError("未知平台参数")
        if not isinstance(destination, dict) or set(destination) != {"node_id", "input"}:
            raise ValueError("参数映射需要 node_id 和 input")
        node = graph.get(str(destination["node_id"]), {})
        if destination["input"] not in node.get("inputs", {}):
            raise ValueError("映射目标不存在")


def fill_workflow(graph: dict[str, Any], mapping: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    validate_mapping(graph, mapping)
    result = deepcopy(graph)
    for field, value in values.items():
        if field not in mapping:
            raise ValueError(f"工作流不支持参数：{field}")
        target = mapping[field]
        result[str(target["node_id"])]["inputs"][target["input"]] = value
    return result
