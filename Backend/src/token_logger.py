import json
import os
from datetime import datetime
from pathlib import Path


class TokenLogger:
    def __init__(self, log_file_path="logs/token_usage.json"):
        self.log_file_path = Path(log_file_path)
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_log_file_exists()

    def _ensure_log_file_exists(self):
        if not self.log_file_path.exists():
            self.log_file_path.write_text("[]")

    def log_usage(self, feature: str, input_tokens: int, output_tokens: int):
        timestamp = datetime.now().isoformat()
        total_tokens = input_tokens + output_tokens

        usage_entry = {
            "timestamp": timestamp,
            "feature": feature,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total": total_tokens
        }

        logs = self.load_usage_log()
        logs.append(usage_entry)
        self.save_usage_log(logs)

        return total_tokens

    def get_total_usage(self) -> dict:
        logs = self.load_usage_log()

        if not logs:
            return {
                "total_calls": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0
            }

        total_input = sum(log["input_tokens"] for log in logs)
        total_output = sum(log["output_tokens"] for log in logs)

        return {
            "total_calls": len(logs),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output
        }

    def save_usage_log(self, logs: list):
        with open(self.log_file_path, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

    def load_usage_log(self) -> list:
        try:
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def get_feature_usage(self, feature: str) -> dict:
        logs = self.load_usage_log()
        feature_logs = [log for log in logs if log["feature"] == feature]

        if not feature_logs:
            return {
                "feature": feature,
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0
            }

        total_input = sum(log["input_tokens"] for log in feature_logs)
        total_output = sum(log["output_tokens"] for log in feature_logs)

        return {
            "feature": feature,
            "calls": len(feature_logs),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output
        }


def log_usage(feature: str, input_tokens: int, output_tokens: int):
    logger = TokenLogger()
    return logger.log_usage(feature, input_tokens, output_tokens)


def get_total_usage() -> dict:
    logger = TokenLogger()
    return logger.get_total_usage()


def get_feature_usage(feature: str) -> dict:
    logger = TokenLogger()
    return logger.get_feature_usage(feature)
