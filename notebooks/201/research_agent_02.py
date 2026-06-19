import operator


def override_reducer(current_value, new_value):
    """允许覆盖（override）state 中已有值的 reducer 函数"""
    if isinstance(new_value, dict) and new_value.get("type") == "override":
        return new_value.get("value", new_value)
    else:
        return operator.add(current_value, new_value)
