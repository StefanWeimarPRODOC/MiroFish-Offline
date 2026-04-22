"""
Pipeline Benchmark Collector (MIR-17)
Collects timing data across pipeline stages and evaluates content quality.
Outputs: timing.json + content_evaluation.json per simulation run.
"""

import os
import re
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('mirofish.benchmark')


class BenchmarkCollector:
    """Collects pipeline timing data and writes timing.json"""

    def __init__(self, sim_dir: str):
        self.sim_dir = sim_dir
        self._timestamps: Dict[str, str] = {}
        self._metrics: Dict[str, Any] = {}
        self._file_path = os.path.join(sim_dir, "timing.json")

        # Load existing timing data if present (for multi-stage accumulation)
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                self._timestamps = existing.get("timestamps", {})
                self._metrics = existing.get("metrics", {})
            except (json.JSONDecodeError, IOError):
                pass

    def start_phase(self, name: str):
        self._timestamps[f"{name}_start"] = datetime.now().isoformat()

    def end_phase(self, name: str):
        self._timestamps[f"{name}_end"] = datetime.now().isoformat()

    def set_timestamp(self, phase: str, kind: str, value: str):
        """Set a timestamp directly (for backfilling from external sources).
        kind must be 'start' or 'end'."""
        self._timestamps[f"{phase}_{kind}"] = value

    def set_metric(self, key: str, value: Any):
        self._metrics[key] = value

    def get_durations(self) -> Dict[str, float]:
        """Public accessor for computed phase durations."""
        return self._calc_durations()

    def _calc_durations(self) -> Dict[str, float]:
        durations = {}
        phases = set()
        for key in self._timestamps:
            phase = key.rsplit("_", 1)[0]  # strip _start / _end
            phases.add(phase)

        total = 0.0
        for phase in sorted(phases):
            start_key = f"{phase}_start"
            end_key = f"{phase}_end"
            if start_key in self._timestamps and end_key in self._timestamps:
                try:
                    start = datetime.fromisoformat(self._timestamps[start_key])
                    end = datetime.fromisoformat(self._timestamps[end_key])
                    secs = (end - start).total_seconds()
                    durations[phase] = round(secs, 1)
                    total += secs
                except (ValueError, TypeError):
                    pass

        if total > 0:
            durations["total_pipeline"] = round(total, 1)
        return durations

    def save(self):
        data = {
            "model": Config.LLM_MODEL_NAME,
            "ner_model": Config.NER_MODEL_NAME or Config.LLM_MODEL_NAME,
            "embedding_model": Config.EMBEDDING_MODEL,
            "output_language": Config.OUTPUT_LANGUAGE,
            "timestamps": self._timestamps,
            "durations_seconds": self._calc_durations(),
            "metrics": self._metrics,
        }
        with open(self._file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Timing data saved to {self._file_path}")


# ========== Content Quality Evaluation ==========

# Regex for Unicode emoji detection (broad range)
_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"    # symbols & pictographs
    "\U0001F680-\U0001F6FF"    # transport & map
    "\U0001F1E0-\U0001F1FF"    # flags
    "\U00002702-\U000027B0"    # dingbats
    "\U0001F900-\U0001F9FF"    # supplemental symbols
    "\U0001FA00-\U0001FA6F"    # chess symbols
    "\U0001FA70-\U0001FAFF"    # symbols extended-A
    "\U00002600-\U000026FF"    # misc symbols
    "]", flags=re.UNICODE
)

_HASHTAG_RE = re.compile(r'#\w+')
_MARKDOWN_RE = re.compile(r'(\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\)|^#{1,6}\s)', re.MULTILINE)
_CJK_THAI_RE = re.compile(
    '[\u4e00-\u9fff'    # CJK Unified Ideographs
    '\u3400-\u4dbf'     # CJK Extension A
    '\u0e00-\u0e7f'     # Thai
    '\u3040-\u309f'     # Hiragana
    '\u30a0-\u30ff'     # Katakana
    ']+'
)


def _eval_platform(db_path: str, platform: str) -> Optional[Dict[str, Any]]:
    """Evaluate content quality for one platform's SQLite database."""
    if not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch all posts
        cursor.execute("SELECT content, original_post_id, num_likes, num_dislikes, num_shares FROM post")
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return {"total_posts": 0}

        contents = []
        original_count = 0
        repost_count = 0
        total_likes = 0
        total_dislikes = 0
        total_shares = 0

        for content, orig_id, likes, dislikes, shares in rows:
            contents.append(content or "")
            if orig_id is None:
                original_count += 1
            else:
                repost_count += 1
            total_likes += likes or 0
            total_dislikes += dislikes or 0
            total_shares += shares or 0

        total_posts = len(contents)

        # Word/char lengths
        word_counts = [len(c.split()) for c in contents if c]
        char_counts = [len(c) for c in contents if c]

        # Emoji counts
        emoji_counts = [len(_EMOJI_RE.findall(c)) for c in contents]

        # Hashtag counts
        hashtag_counts = [len(_HASHTAG_RE.findall(c)) for c in contents]

        # Markdown detection
        markdown_posts = sum(1 for c in contents if _MARKDOWN_RE.search(c))

        # Duplicate detection (exact)
        content_hashes = [hashlib.md5(c.encode()).hexdigest() for c in contents if c]
        unique_hashes = set(content_hashes)
        exact_dupes = len(content_hashes) - len(unique_hashes)

        # Near-duplicates (first 50 chars match, excluding already-exact-duplicates)
        exact_dupe_hashes = set()
        hash_seen = set()
        for h in content_hashes:
            if h in hash_seen:
                exact_dupe_hashes.add(h)
            hash_seen.add(h)

        prefixes = [c[:50] for c in contents
                     if len(c) >= 50 and hashlib.md5(c.encode()).hexdigest() not in exact_dupe_hashes]
        near_dupes = len(prefixes) - len(set(prefixes))

        # Non-target language detection (CJK/Thai characters)
        non_target_count = sum(1 for c in contents if _CJK_THAI_RE.search(c))

        # Comments (Reddit)
        total_comments = 0
        try:
            cursor.execute("SELECT COUNT(*) FROM comment")
            total_comments = cursor.fetchone()[0] or 0
        except sqlite3.OperationalError:
            pass  # table might not exist

        conn.close()

        avg_words = round(sum(word_counts) / len(word_counts), 1) if word_counts else 0
        avg_chars = round(sum(char_counts) / len(char_counts), 1) if char_counts else 0

        return {
            "total_posts": total_posts,
            "original_posts": original_count,
            "reposts": repost_count,
            "avg_length_chars": avg_chars,
            "avg_length_words": avg_words,
            "min_length_words": min(word_counts) if word_counts else 0,
            "max_length_words": max(word_counts) if word_counts else 0,
            "emoji_total": sum(emoji_counts),
            "avg_emojis_per_post": round(sum(emoji_counts) / total_posts, 2),
            "posts_with_hashtags_pct": round(sum(1 for c in hashtag_counts if c > 0) / total_posts * 100, 1),
            "avg_hashtags_per_post": round(sum(hashtag_counts) / total_posts, 2),
            "posts_with_markdown_pct": round(markdown_posts / total_posts * 100, 1),
            "exact_duplicates": exact_dupes,
            "near_duplicates": near_dupes,
            "avg_likes": round(total_likes / total_posts, 1),
            "avg_dislikes": round(total_dislikes / total_posts, 1),
            "avg_shares": round(total_shares / total_posts, 1),
            "total_comments": total_comments,
            "non_target_language_pct": round(non_target_count / total_posts * 100, 1),
        }

    except Exception as e:
        logger.error(f"Failed to evaluate {platform} content: {e}")
        return None


def _calc_quality_score(stats: Dict[str, Any]) -> float:
    """
    Simple weighted quality score (0-100).
    - No duplicates: +30
    - Target language 100%: +25
    - Avg word length 15-50: +20
    - Emoji usage 0.1-0.5/post: +15
    - Hashtag usage 0.2-1.0/post: +10
    """
    score = 0.0
    total = stats.get("total_posts", 0)
    if total == 0:
        return 0.0

    # Duplicates (30 pts)
    dupe_ratio = (stats.get("exact_duplicates", 0) + stats.get("near_duplicates", 0)) / total
    score += max(0, 30 * (1 - dupe_ratio * 5))  # 20% dupes = 0 pts

    # Target language (25 pts)
    non_target = stats.get("non_target_language_pct", 0) / 100
    score += max(0, 25 * (1 - non_target * 4))  # 25% non-target = 0 pts

    # Avg word length (20 pts) — sweet spot 15-50
    avg_words = stats.get("avg_length_words", 0)
    if 15 <= avg_words <= 50:
        score += 20
    elif 5 <= avg_words < 15:
        score += 20 * (avg_words - 5) / 10
    elif 50 < avg_words <= 80:
        score += 20 * (80 - avg_words) / 30
    # else: 0

    # Emoji usage (15 pts) — sweet spot 0.1-0.5 per post
    avg_emoji = stats.get("avg_emojis_per_post", 0)
    if 0.1 <= avg_emoji <= 0.5:
        score += 15
    elif 0 <= avg_emoji < 0.1:
        score += 15 * avg_emoji / 0.1
    elif 0.5 < avg_emoji <= 2.0:
        score += max(0, 15 * (2.0 - avg_emoji) / 1.5)

    # Hashtag usage (10 pts) — sweet spot 0.2-1.0 per post
    avg_hash = stats.get("avg_hashtags_per_post", 0)
    if 0.2 <= avg_hash <= 1.0:
        score += 10
    elif 0 <= avg_hash < 0.2:
        score += 10 * avg_hash / 0.2
    elif 1.0 < avg_hash <= 3.0:
        score += max(0, 10 * (3.0 - avg_hash) / 2.0)

    return round(min(100, score), 1)


def evaluate_content(sim_dir: str) -> Optional[str]:
    """
    Evaluate content quality for a completed simulation.
    Reads SQLite DBs, computes metrics, writes content_evaluation.json.

    Returns path to the evaluation file, or None if no data found.
    """
    twitter_db = os.path.join(sim_dir, "twitter_simulation.db")
    reddit_db = os.path.join(sim_dir, "reddit_simulation.db")

    platforms = {}
    twitter_stats = _eval_platform(twitter_db, "twitter")
    if twitter_stats:
        platforms["twitter"] = twitter_stats

    reddit_stats = _eval_platform(reddit_db, "reddit")
    if reddit_stats:
        platforms["reddit"] = reddit_stats

    if not platforms:
        logger.warning(f"No simulation databases found in {sim_dir}")
        return None

    # Combined metrics
    all_posts = sum(p.get("total_posts", 0) for p in platforms.values())
    combined_stats = {}
    if all_posts > 0:
        # Weighted average across platforms
        for key in ["avg_length_words", "avg_emojis_per_post", "avg_hashtags_per_post",
                     "posts_with_markdown_pct", "non_target_language_pct"]:
            weighted = sum(
                p.get(key, 0) * p.get("total_posts", 0)
                for p in platforms.values()
            )
            combined_stats[key] = round(weighted / all_posts, 2)

        combined_stats["total_posts"] = all_posts
        combined_stats["exact_duplicates"] = sum(p.get("exact_duplicates", 0) for p in platforms.values())
        combined_stats["near_duplicates"] = sum(p.get("near_duplicates", 0) for p in platforms.values())

    # Quality score based on combined stats
    quality_score = _calc_quality_score(combined_stats) if combined_stats else 0.0

    evaluation = {
        "evaluated_at": datetime.now().isoformat(),
        "platforms": platforms,
        "combined": {
            "total_posts": all_posts,
            "quality_score": quality_score,
        },
    }

    eval_path = os.path.join(sim_dir, "content_evaluation.json")
    with open(eval_path, 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, ensure_ascii=False, indent=2)

    logger.info(f"Content evaluation saved to {eval_path} (quality_score={quality_score})")
    return eval_path
