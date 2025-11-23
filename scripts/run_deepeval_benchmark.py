#!/usr/bin/env python3
"""Run DeepEval metrics by driving the SecureScribe chat API with meeting mentions."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple, cast

import requests
from deepeval.metrics import AnswerRelevancyMetric, ContextualPrecisionMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = os.environ.get("SECURESCRIBE_API_BASE_URL", "https://securescribe.wc504.io.vn/be")
API_VERSION = os.environ.get("SECURESCRIBE_API_VERSION", "v1")
DEFAULT_DATASET = "resources/benchmarks/sop_kickoff_qas.json"
DEFAULT_CONVERSATION_TITLE = "DeepEval Benchmark"
REPORT_DIR = Path("reports/deepeval")


def load_dataset(path: Path) -> List[Dict[str, Any]]:
    with path.open() as f:
        return cast(List[Dict[str, Any]], json.load(f))


def create_conversation(*, base_url: str, token: str, title: str) -> str:
    url = f"{base_url}/api/{API_VERSION}/conversations"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {"title": title}
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json().get("data") or {}
    conversation_id = data.get("id")
    if not conversation_id:
        raise RuntimeError("Conversation creation response missing 'id'")
    return str(conversation_id)


def ensure_conversation_id(*, base_url: str, token: str, conversation_id: str | None, conversation_title: str) -> str:
    if conversation_id:
        return conversation_id
    return create_conversation(base_url=base_url, token=token, title=conversation_title)


def build_chat_payload(dataset_row: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    prompt = dataset_row["input"]
    meeting_id = dataset_row["meeting_id"]
    mention_marker = f"[meeting:{meeting_id}]"
    if prompt.endswith("\n"):
        content = f"{prompt}{mention_marker}"
    else:
        content = f"{prompt}\n{mention_marker}"
    offset_start = len(content) - len(mention_marker)
    offset_end = len(content)
    mentions: List[Dict[str, Any]] = [
        {
            "entity_type": "meeting",
            "entity_id": meeting_id,
            "offset_start": offset_start,
            "offset_end": offset_end,
        }
    ]
    return content, mentions


def send_chat_message(
    *,
    base_url: str,
    token: str,
    conversation_id: str,
    content: str,
    mentions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    url = f"{base_url}/api/{API_VERSION}/conversations/{conversation_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {"content": content, "mentions": mentions}
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json().get("data") or {}
    user_message = data.get("user_message")
    if not user_message:
        raise RuntimeError("Chat API response missing 'user_message'")
    return cast(Dict[str, Any], user_message)


def poll_for_ai_message(
    *,
    base_url: str,
    token: str,
    conversation_id: str,
    user_message_id: str,
    history_limit: int,
    poll_interval: float,
    poll_timeout: float,
) -> Dict[str, Any]:
    url = f"{base_url}/api/{API_VERSION}/conversations/{conversation_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    deadline = time.time() + poll_timeout

    while time.time() < deadline:
        response = requests.get(url, headers=headers, params={"limit": history_limit}, timeout=30)
        response.raise_for_status()
        messages = (response.json().get("data") or {}).get("messages") or []

        found_user = False
        for message in messages:
            message_id = str(message.get("id"))
            if message_id == str(user_message_id):
                found_user = True
                continue

            message_type = message.get("message_type") or message.get("role")
            if found_user and message_type == "assistant":
                return cast(Dict[str, Any], message)

        time.sleep(poll_interval)

    raise TimeoutError(f"No assistant response within {poll_timeout} seconds for conversation {conversation_id}")


def call_chat_api(
    *,
    base_url: str,
    token: str,
    conversation_id: str,
    content: str,
    mentions: List[Dict[str, Any]],
    history_limit: int,
    poll_interval: float,
    poll_timeout: float,
) -> Dict[str, Any]:
    user_message = send_chat_message(
        base_url=base_url,
        token=token,
        conversation_id=conversation_id,
        content=content,
        mentions=mentions,
    )
    assistant_message = poll_for_ai_message(
        base_url=base_url,
        token=token,
        conversation_id=conversation_id,
        user_message_id=str(user_message.get("id")),
        history_limit=history_limit,
        poll_interval=poll_interval,
        poll_timeout=poll_timeout,
    )
    return {"data": {"answer": assistant_message.get("content", ""), "contexts": []}}


def build_test_case(dataset_row: Dict[str, Any], api_response: Dict[str, Any]) -> LLMTestCase:
    data = api_response.get("data") or {}
    contexts = data.get("contexts") or []
    answer = data.get("answer", "")
    return LLMTestCase(
        input=dataset_row["input"],
        actual_output=answer,
        expected_output=dataset_row["expected_output"],
        context=contexts if contexts else dataset_row.get("context", []),
    )


def evaluate_cases(test_cases: List[LLMTestCase]) -> Dict[str, Any]:
    metrics = [
        AnswerRelevancyMetric(minimum_score=0.7),
        FaithfulnessMetric(minimum_score=0.7),
        ContextualPrecisionMetric(minimum_score=0.7),
    ]
    report_rows: List[Dict[str, Any]] = []
    summary: Dict[str, List[Any]] = {metric.__class__.__name__: [] for metric in metrics}

    for case in test_cases:
        row: Dict[str, Any] = {"input": case.input, "expected_output": case.expected_output, "actual_output": case.actual_output, "metrics": {}}
        for metric in metrics:
            result = metric.measure(case)
            metric_name = metric.__class__.__name__
            row["metrics"][metric_name] = {
                "score": getattr(result, "score", None),
                "passed": getattr(result, "passed", None),
                "reason": getattr(result, "reason", ""),
            }
            summary[metric_name].append(result)
        report_rows.append(row)

    summary_stats: Dict[str, Dict[str, Any]] = {}
    for metric in metrics:
        metric_name = metric.__class__.__name__
        metric_results = summary[metric_name]
        scores = [getattr(res, "score", 0) or 0 for res in metric_results]
        passes = [bool(getattr(res, "passed", False)) for res in metric_results]
        summary_stats[metric_name] = {
            "average_score": sum(scores) / len(scores) if scores else 0.0,
            "pass_rate": sum(passes) / len(passes) if passes else 0.0,
        }

    return {"cases": report_rows, "summary": summary_stats}


def write_reports(report: Dict[str, Any], label: str) -> Dict[str, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base_name = f"{label}_{timestamp}"
    json_path = REPORT_DIR / f"{base_name}.json"
    md_path = REPORT_DIR / f"{base_name}.md"

    with json_path.open("w") as jf:
        json.dump(report, jf, indent=2)

    with md_path.open("w") as mf:
        mf.write(f"# DeepEval Benchmark: {label}\n\n")
        mf.write("## Summary\n")
        for metric, stats in report["summary"].items():
            mf.write(f"- {metric}: avg={stats['average_score']:.2f}, pass_rate={stats['pass_rate']:.0%}\n")
        mf.write("\n## Cases\n")
        for idx, case in enumerate(report["cases"], start=1):
            mf.write(f"### Case {idx}\n")
            mf.write(f"- **Prompt:** {case['input']}\n")
            mf.write(f"- **Expected:** {case['expected_output']}\n")
            mf.write(f"- **Actual:** {case['actual_output']}\n")
            for metric, details in case["metrics"].items():
                score = details.get("score")
                mf.write(f"  - {metric}: score={score}, passed={details.get('passed')}\n")
            mf.write("\n")

    return {"json": json_path, "markdown": md_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Execute DeepEval metrics via the SecureScribe chat API")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Path to the DeepEval dataset JSON")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="SecureScribe API base URL")
    parser.add_argument("--api-token", default=os.environ.get("SECURESCRIBE_API_TOKEN"), help="Bearer token for the SecureScribe API")
    parser.add_argument("--label", default="sop_kickoff", help="Label prefix for output reports")
    parser.add_argument("--conversation-id", default=None, help="Existing conversation UUID to reuse")
    parser.add_argument("--conversation-title", default=DEFAULT_CONVERSATION_TITLE, help="Title to use when auto-creating a conversation")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Seconds between polls for the assistant response")
    parser.add_argument("--poll-timeout", type=float, default=90.0, help="Maximum seconds to wait for the assistant response")
    parser.add_argument("--history-limit", type=int, default=50, help="Number of recent messages to inspect while polling")
    parser.add_argument("--log-level", default="INFO", help="Logging level (e.g., INFO, DEBUG)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    log_level_name = (args.log_level or "INFO").upper()
    log_level = getattr(logging, log_level_name, None)
    if not isinstance(log_level, int):
        print(f"Invalid log level '{args.log_level}', defaulting to INFO", file=sys.stderr)
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s")

    if not args.api_token:
        raise SystemExit("SECURESCRIBE_API_TOKEN is required (env var or --api-token)")

    logger.info(
        "Starting DeepEval benchmark label=%s dataset=%s base_url=%s conversation_id=%s conversation_title=%s",
        args.label,
        args.dataset,
        args.base_url,
        args.conversation_id,
        args.conversation_title,
    )

    dataset = load_dataset(Path(args.dataset))
    logger.info("Loaded dataset with %d entries", len(dataset))
    test_cases: List[LLMTestCase] = []
    base_url = args.base_url.rstrip("/")
    if args.conversation_id:
        logger.info("Reusing existing conversation %s", args.conversation_id)
    else:
        logger.info("Creating new conversation titled '%s'", args.conversation_title)
    conversation_id = ensure_conversation_id(
        base_url=base_url,
        token=args.api_token,
        conversation_id=args.conversation_id,
        conversation_title=args.conversation_title,
    )
    logger.info("Using conversation %s", conversation_id)

    total_cases = len(dataset)
    for idx, row in enumerate(dataset, start=1):
        meeting_id = row.get("meeting_id")
        prompt_preview = row.get("input", "")[:60].replace("\n", " ")
        logger.info("Processing case %d/%d meeting=%s prompt='%s...'", idx, total_cases, meeting_id, prompt_preview)
        content, mentions = build_chat_payload(row)
        start_time = time.perf_counter()
        try:
            api_payload = call_chat_api(
                base_url=base_url,
                token=args.api_token,
                conversation_id=conversation_id,
                content=content,
                mentions=mentions,
                history_limit=args.history_limit,
                poll_interval=args.poll_interval,
                poll_timeout=args.poll_timeout,
            )
        except Exception:
            logger.exception("Case %d/%d failed for meeting_id=%s", idx, total_cases, meeting_id)
            raise
        duration = time.perf_counter() - start_time
        logger.debug("Case %d/%d completed in %.2fs", idx, total_cases, duration)
        test_cases.append(build_test_case(row, api_payload))

    logger.info("Evaluating %d test cases", len(test_cases))
    report = evaluate_cases(test_cases)
    outputs = write_reports(report, args.label)
    logger.info("Wrote reports: json=%s markdown=%s", outputs["json"], outputs["markdown"])
    print(json.dumps({"report": {k: str(v) for k, v in outputs.items()}, "conversation_id": conversation_id}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
