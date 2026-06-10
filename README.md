# music-cli

macOS 音乐控制 CLI，支持**酷狗**和 **Spotify** 桌面客户端。

> 暂时支持Spotify

## 功能

- 搜索歌曲、播放、切歌、播放/暂停
- 搜索结果翻页，多选序号或一键播全部
- 播放队列：选多首后自动顺序播放，`n` 跳队列下一首
- 心情推荐（focused / relaxed / hyped / sad / debug）
- 交互式 REPL 和单次命令两种模式

## 要求

- macOS
- Python 3.10+
- 酷狗 Music 或 Spotify 桌面客户端

无第三方依赖，纯 Python 标准库。

## 安装

```bash
git clone https://github.com/ni-shiliu/music-cli.git
cd music-cli

# 设置快捷命令（可选）
echo 'alias music="python3 $(pwd)/music_cli.py"' >> ~/.zshrc
echo 'alias musici="python3 $(pwd)/music_repl.py"' >> ~/.zshrc
source ~/.zshrc
```

## 快速开始

### 交互模式（推荐）

```bash
python3 music_repl.py                    # Spotify
python3 music_repl.py --provider kugou # kugou
```

进入后可用以下命令：

| 命令 | 说明 |
|------|------|
| `s <关键词>` | 搜索歌曲 |
| `1 3 5` | 选序号加入队列播放 |
| `a` | 播放全部搜索结果 |
| `m` | 加载下一页 |
| `play <歌名>` | 直接播放 |
| `n` / `p` | 下一首 / 上一首 |
| `space` | 播放 / 暂停 |
| `stop` | 清空播放队列 |
| `r <mood>` | 心情推荐 |
| `status` | 刷新当前播放状态 |
| `q` | 退出 |

### 单次命令

```bash
python3 music_cli.py [--provider kugou|spotify] <command>
```

```bash
python3 music_cli.py status                      # 当前播放信息（JSON）
python3 music_cli.py search 周杰伦               # 搜索
python3 music_cli.py play-by 晴天 周杰伦         # 搜索并播放
python3 music_cli.py next                        # 下一首
python3 music_cli.py play                        # 播放 / 暂停
python3 music_cli.py recommend focused           # 心情推荐
```

切换 Spotify：

```bash
python3 music_cli.py --provider spotify play-by 晴天 周杰伦
# 或设置默认
export MUSIC_PROVIDER=spotify
```

## Spotify 说明

- 无需注册账号、无需配置，开箱即用
- **搜索**：走 Spotify Web Player 匿名 API，零配置
- **播放控制 / 状态检测**：本地 AppleScript，无需 Premium
- Spotify 免费账号可用，播放时会有广告插播（平台限制）
- 播放切歌时 Spotify 窗口会短暂闪烁，这是 macOS 的限制

## 心情模式

| mood | 场景 |
|------|------|
| `focused` | 深夜专注编码 |
| `relaxed` | 需要放松 |
| `hyped` | 功能跑通了！ |
| `sad` | 需要治愈 |
| `debug` | 找 bug 找到崩溃 |

## License

MIT
