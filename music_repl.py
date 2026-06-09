#!/usr/bin/env python3
"""music-repl — 交互式音乐控制终端。"""
import sys
import os
import argparse
import threading
import time
import urllib.parse
import readline  # noqa: F401 — 方向键 / 历史记录

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music_cli
from providers import get_provider, MR_CMD_NEXT, MR_CMD_PREV, MR_CMD_TOGGLE

_provider = get_provider("kugou")

# ── ANSI ──────────────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
RED    = "\033[31m"

def _c(text, *codes): return "".join(codes) + text + RESET


# ── 搜索状态（翻页）──────────────────────────────────────────────────────────
class _SearchState:
    def __init__(self):
        self.keyword     = ""
        self.page        = 0
        self.all_results = []
        self.page_results = []

    def reset(self, keyword: str):
        self.keyword      = keyword
        self.page         = 0
        self.all_results  = []
        self.page_results = []

    def load_next(self, provider) -> list:
        self.page += 1
        results = provider.search(self.keyword, page_size=10, page=self.page)
        self.page_results = results
        self.all_results.extend(results)
        return results


_search = _SearchState()


# ── 状态栏 ────────────────────────────────────────────────────────────────────
_status_cache = None
_status_lock  = threading.Lock()


def _refresh_status():
    global _status_cache
    info = music_cli.detect_status(_provider)
    with _status_lock:
        _status_cache = info


def _status_line() -> str:
    with _status_lock:
        info = _status_cache
    if not info:
        return _c("  ♪  没有检测到正在播放的音乐", DIM)
    playing = info.get("playing")
    icon   = _c("▶", GREEN) if playing else (_c("⏸", YELLOW) if playing is False else _c("♪", CYAN))
    title  = _c(info.get("title", ""), BOLD)
    artist = _c(info.get("artist", ""), DIM)
    return f"  {icon}  {title}{_c(' — ', DIM)}{artist}"


def _print_status():
    print(_status_line())
    print()


# ── 帮助 ──────────────────────────────────────────────────────────────────────
HELP = f"""
{_c('命令', BOLD, CYAN)}
  {_c('n / next', BOLD)}            下一首（队列激活时跳队列下一首）
  {_c('p / prev', BOLD)}            上一首（同时清空队列）
  {_c('space / pause', BOLD)}       播放 / 暂停
  {_c('s <关键词>', BOLD)}           搜索（序号 / 多选 / a 全部 / m 更多）
  {_c('play <歌名>', BOLD)}          直接播放（Spotify 走 search URI）
  {_c('r <mood>', BOLD)}             心情推荐  focused/relaxed/hyped/sad/debug
  {_c('stop / clear', BOLD)}         清空播放队列
  {_c('status', BOLD)}               刷新当前播放状态
  {_c('help', BOLD)}                 显示帮助
  {_c('q / quit / Ctrl-C', BOLD)}   退出
"""


# ── 播放队列 ──────────────────────────────────────────────────────────────────
class _Queue:
    def __init__(self):
        self._songs  = []
        self._idx    = 0
        self._stop   = threading.Event()
        self._skip   = threading.Event()
        self._thread = None

    def start(self, songs: list):
        self.stop()
        self._songs  = songs
        self._idx    = 0
        self._stop   = threading.Event()
        self._skip   = threading.Event()
        print(_c("  加入队列：" + "、".join(s["title"] for s in songs), CYAN))
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def skip_next(self) -> bool:
        if not self.active():
            return False
        if self._idx + 1 >= len(self._songs):
            self.stop()
            return False
        self._skip.set()
        return True

    def stop(self):
        self._stop.set()
        self._skip.set()

    def active(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop.is_set())

    def _run(self):
        while self._idx < len(self._songs):
            if self._stop.is_set():
                return
            song = self._songs[self._idx]
            _play_song(song)
            if self._idx == len(self._songs) - 1:
                return
            self._skip.clear()
            self._wait_for_end(song)
            if self._stop.is_set():
                return
            self._idx += 1
        _refresh_status()

    def _wait_for_end(self, song: dict):
        """等待当前歌曲播完，Spotify 用实时进度轮询，其他用时长计时。"""
        if _provider.name == "spotify":
            self._wait_spotify_end(song)
        else:
            # 酷狗：按 duration 计时
            deadline = time.time() + song.get("duration", 0) + 2
            while time.time() < deadline:
                if self._stop.is_set() or self._skip.is_set():
                    return
                time.sleep(1)

    def _wait_spotify_end(self, song: dict):
        """轮询 Spotify player position，剩余 < 2s 时触发下一首。"""
        import subprocess as _sp
        # 先等 2 秒让 Spotify 加载完开始播
        for _ in range(4):
            if self._stop.is_set() or self._skip.is_set():
                return
            time.sleep(0.5)

        consecutive_errors = 0
        while True:
            if self._stop.is_set() or self._skip.is_set():
                return
            r = _sp.run(
                ["osascript",
                 "-e", 'tell application "Spotify"',
                 "-e", "return (player position as string) & \"|\" & (duration of current track as string)",
                 "-e", "end tell"],
                capture_output=True, text=True,
            )
            if r.returncode != 0 or not r.stdout.strip():
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    return  # Spotify 挂了，放弃等待
                time.sleep(2)
                continue
            consecutive_errors = 0
            try:
                pos_s, dur_ms = r.stdout.strip().split("|")
                pos = float(pos_s)
                dur = float(dur_ms) / 1000  # 毫秒转秒
                remaining = dur - pos
                if remaining < 2:
                    return  # 即将结束，播下一首
                # 剩余较多时多睡一会，减少 AppleScript 调用频率
                sleep_time = max(0.5, min(remaining - 2, 5))
                for _ in range(int(sleep_time / 0.5)):
                    if self._stop.is_set() or self._skip.is_set():
                        return
                    time.sleep(0.5)
            except (ValueError, IndexError):
                time.sleep(2)


_queue = _Queue()


# ── 结果展示 + 选择 ───────────────────────────────────────────────────────────
def _fmt_dur(secs: int) -> str:
    return f"{secs // 60}:{secs % 60:02d}" if secs else ""


def _show_results(results: list) -> None:
    if not results:
        print(_c("  无搜索结果", DIM))
        return
    print()
    if _search.page > 1:
        print(_c(f"  —— 第 {_search.page} 页 ——", DIM))
    offset = len(_search.all_results) - len(results)
    for i, s in enumerate(results, offset + 1):
        dur = _c(f"  {_fmt_dur(s['duration'])}", DIM) if s.get("duration") else ""
        alb = _c(f"  [{s['album']}]", DIM) if s.get("album") else ""
        print(f"{_c(f'  {i:2}.', DIM)} {_c(s['title'], BOLD)} — {_c(s['artist'], DIM)}{alb}{dur}")
    print()


def _pick_and_play(results: list):
    _show_results(results)
    if not results:
        return
    try:
        raw = input(_c("  序号 / 多选 / a 全部 / m 更多（回车跳过）: ", DIM)).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    if not raw:
        return
    if raw.lower() in ("m", "more"):
        _load_more()
        return
    if raw.lower() in ("a", "all"):
        selected = list(_search.all_results)
    else:
        selected = []
        for tok in raw.split():
            try:
                idx = int(tok) - 1
                if 0 <= idx < len(_search.all_results):
                    selected.append(_search.all_results[idx])
                else:
                    print(_c(f"  序号 {tok} 超出范围，跳过", DIM))
            except ValueError:
                print(_c(f"  {tok} 不是数字，跳过", DIM))
    if not selected:
        return
    if len(selected) == 1:
        _queue.stop()
        _play_song(selected[0])
    else:
        _queue.start(selected)


def _load_more():
    print(_c("  加载更多…", DIM))
    results = _search.load_next(_provider)
    if not results:
        print(_c("  没有更多结果了", DIM))
        return
    _pick_and_play(results)


def _play_song(song: dict):
    song_id = song.get("id", "")
    if not song_id and _provider.name == "spotify":
        q = f"{song.get('title', '')} {song.get('artist', '')}".strip()
        song_id = f"spotify:search:{urllib.parse.quote(q)}"
    if not song_id:
        print(_c("  无法播放（缺少 id）", RED))
        return
    ok, _ = _provider.play_song(song_id)
    if ok:
        print(_c(f"  ▶ 正在播放：{song['title']} — {song['artist']}", GREEN))
        threading.Timer(2.0, _refresh_status).start()
    else:
        print(_c(f"  打开失败，请确认 {_provider.name} 已安装并运行", RED))


# ── 命令处理 ──────────────────────────────────────────────────────────────────
def _handle(line: str) -> bool:
    parts = line.strip().split(None, 1)
    if not parts:
        return True
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if _provider.name == "spotify" and hasattr(_provider, "capture_focus"):
        _provider.capture_focus()

    if cmd in ("q", "quit", "exit"):
        return False

    elif cmd in ("n", "next"):
        if _queue.skip_next():
            threading.Timer(1.5, _refresh_status).start()
        else:
            ok = _provider.control(MR_CMD_NEXT)
            print(_c("  ⏭  下一首", GREEN) if ok else _c("  控制失败", RED))
            threading.Timer(1.5, _refresh_status).start()

    elif cmd in ("p", "prev"):
        _queue.stop()
        ok = _provider.control(MR_CMD_PREV)
        print(_c("  ⏮  上一首", GREEN) if ok else _c("  控制失败", RED))
        threading.Timer(1.5, _refresh_status).start()

    elif cmd in ("stop", "clear"):
        _queue.stop()
        print(_c("  ✕  队列已清空", DIM))

    elif cmd in ("space", "pause", "toggle"):
        ok = _provider.control(MR_CMD_TOGGLE)
        print(_c("  ⏯  播放/暂停", GREEN) if ok else _c("  控制失败", RED))
        threading.Timer(1.0, _refresh_status).start()

    elif cmd == "status":
        _refresh_status()
        _print_status()

    elif cmd in ("s", "search"):
        if not arg:
            print(_c("  用法: s <关键词>", DIM))
        else:
            print(_c(f"  搜索中：{arg} …", DIM))
            _search.reset(arg)
            _pick_and_play(_search.load_next(_provider))

    elif cmd in ("play", "open"):
        if not arg:
            print(_c("  用法: play <歌名>", DIM))
        elif _provider.name == "spotify":
            uri = f"spotify:search:{urllib.parse.quote(arg)}"
            ok, _ = _provider.play_song(uri)
            if ok:
                print(_c(f"  ▶ 正在播放：{arg}", GREEN))
                threading.Timer(2.0, _refresh_status).start()
            else:
                print(_c("  播放失败，请确认 Spotify 已启动并登录", RED))
        else:
            print(_c(f"  搜索中：{arg} …", DIM))
            results = _provider.search(arg, page_size=5)
            if not results:
                print(_c(f"  未找到：{arg}", RED))
            else:
                _play_song(results[0])

    elif cmd in ("r", "recommend"):
        mood = arg.strip().lower() or "relaxed"
        if mood not in music_cli.MOOD_MAP:
            print(_c(f"  mood 可选：{' / '.join(music_cli.MOOD_MAP)}", DIM))
        else:
            print(_c(f"  心情：{mood}", CYAN))
            results = []
            for kw in music_cli.MOOD_MAP[mood]:
                results = _provider.search(kw, page_size=8)
                if results:
                    break
            _search.reset(mood)
            _search.all_results = results
            _search.page_results = results
            _search.page = 1
            _pick_and_play(results)

    elif cmd in ("help", "h", "?"):
        print(HELP)

    else:
        print(_c(f"  未知命令：{cmd}（输入 help 查看帮助）", DIM))

    return True


# ── 后台定时刷新 ──────────────────────────────────────────────────────────────
def _start_bg_refresh(interval: float = 5.0):
    def loop():
        while True:
            time.sleep(interval)
            _refresh_status()
    threading.Thread(target=loop, daemon=True).start()


# ── 主循环 ────────────────────────────────────────────────────────────────────
def main():
    global _provider
    parser = argparse.ArgumentParser(prog="music-repl")
    parser.add_argument(
        "--provider", choices=["kugou", "spotify"],
        default=os.environ.get("MUSIC_PROVIDER", "spotify"),
    )
    _provider = get_provider(parser.parse_args().provider)

    _refresh_status()
    _start_bg_refresh()

    print()
    print(_c("  music-cli", BOLD, CYAN)
          + _c(f"  [{_provider.name}]", YELLOW)
          + _c("  输入 help 查看命令", DIM))
    _print_status()

    while True:
        try:
            line = input(_c("❯ ", CYAN))
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not _handle(line):
            break

    print(_c("  bye", DIM))


if __name__ == "__main__":
    main()
