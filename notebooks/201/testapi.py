"""批量测试中转站（api.zetaapi.ai）模型可用性的脚本。

流程：
1. 调用 /v1/models 接口获取所有模型 id；
2. 对每个模型并发发送一条测试对话请求；
3. 汇总并打印可用与不可用的模型列表。
"""

import json
from concurrent import futures

import requests

# API 密钥统一放在文件顶部，便于维护（请替换为真实密钥，勿提交到仓库）
API_KEY = ""

BASE_URL = "https://api.zetaapi.ai/v1"
MODELS_URL = f"{BASE_URL}/models"
CHAT_URL = f"{BASE_URL}/chat/completions"

# 测试用的问题，内容不重要，只要模型能正常回复即视为可用
TEST_QUESTION = "今天北京的天气怎么样"

# 单个请求的超时时间（秒），部分模型响应较慢，适当放宽
REQUEST_TIMEOUT = 60

# 并发测试的线程数
MAX_WORKERS = 8

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def get_models() -> dict[str, str]:
    """从 /v1/models 接口获取所有模型的 id 及其归属方。

    Returns:
        模型 id 到 owned_by 的映射，如 {"gpt-5.5": "openai", ...}；
        接口返回结构为 {"data": [{"id": ..., "owned_by": ...}, ...]}。

    Raises:
        requests.RequestException: 请求发送失败（网络错误、超时等）。
        ValueError: 响应不是合法 JSON 或结构不符合预期。
    """
    response = requests.get(MODELS_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    data = response.json().get("data")
    if not isinstance(data, list):
        raise ValueError(f"模型列表接口返回结构异常: {response.text[:200]}")

    return {
        item["id"]: item.get("owned_by", "unknown")
        for item in data
        if item.get("id")
    }


def check_model(model_id: str) -> tuple[str, bool, str]:
    """测试单个模型是否可用。

    向 /v1/chat/completions 发送一条测试消息，能正常返回回复内容则视为可用。

    Args:
        model_id: 要测试的模型 id，取自 /v1/models 接口。

    Returns:
        三元组 (model_id, 是否可用, 说明信息)；
        可用时说明信息为回复内容摘要，不可用时为失败原因。
    """
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": TEST_QUESTION}],
    }

    try:
        response = requests.post(
            CHAT_URL, headers=HEADERS, json=payload, timeout=REQUEST_TIMEOUT
        )
    except requests.Timeout:
        return model_id, False, f"请求超时（>{REQUEST_TIMEOUT}s）"
    except requests.RequestException as exc:
        return model_id, False, f"请求异常: {exc}"

    if response.status_code != 200:
        return model_id, False, f"HTTP {response.status_code}: {response.text[:120]}"

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return model_id, False, f"响应结构异常: {response.text[:120]}"

    if not content:
        return model_id, False, "回复内容为空"

    # 只保留回复开头一小段，用于人工确认模型确实正常输出
    summary = content.replace("\n", " ")[:40]
    return model_id, True, summary


def main() -> None:
    """获取全部模型并批量测试，打印可用与不可用的模型汇总。"""
    print(f"正在获取模型列表: {MODELS_URL}")
    try:
        models = get_models()
    except (requests.RequestException, ValueError) as exc:
        print(f"获取模型列表失败: {exc}")
        return

    model_ids = list(models)
    if not model_ids:
        print("模型列表为空，无需测试")
        return

    total = len(model_ids)
    print(f"共获取到 {total} 个模型，开始并发测试（{MAX_WORKERS} 线程）...\n")

    available: list[str] = []
    unavailable: list[tuple[str, str]] = []

    with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        tasks = {executor.submit(check_model, mid): mid for mid in model_ids}
        for index, task in enumerate(futures.as_completed(tasks), start=1):
            model_id, ok, detail = task.result()
            status = "✅ 可用" if ok else "❌ 不可用"
            print(f"[{index}/{total}] {status}  {model_id}  | {detail}")
            if ok:
                available.append(model_id)
            else:
                unavailable.append((model_id, detail))

    print("\n" + "=" * 60)
    print(f"测试完成：可用 {len(available)} 个，不可用 {len(unavailable)} 个")

    # 模型名与 owned_by 一对一打印，宽度对齐便于阅读
    name_width = max(len(model_id) for model_id in model_ids)

    print(f"\n---- 可用模型（{len(available)}）----")
    for model_id in sorted(available):
        print(f"  {model_id:<{name_width}}  | owned_by: {models[model_id]}")

    print(f"\n---- 不可用模型（{len(unavailable)}）----")
    for model_id, reason in sorted(unavailable):
        print(f"  {model_id:<{name_width}}  | owned_by: {models[model_id]}  | {reason}")

    # 同时输出 JSON 结果，便于其他脚本直接消费
    result = {
        "available": [
            {"model": model_id, "owned_by": models[model_id]}
            for model_id in sorted(available)
        ],
        "unavailable": [
            {"model": model_id, "owned_by": models[model_id], "reason": reason}
            for model_id, reason in sorted(unavailable)
        ],
    }
    print("\n---- JSON 结果 ----")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
