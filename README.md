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
python3 music_repl.py                    # 酷狗
python3 music_repl.py --provider spotify # Spotify
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

## Spotify 配置

### 1. 注册 Developer App

1. 登录 [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. 创建 App（名称随意，Redirect URI 填 `http://127.0.0.1:8888/callback`）
3. 复制 **Client ID**

### 2. 写入配置文件

```bash
mkdir -p ~/.config/music-cli
cat > ~/.config/music-cli/config.json << 'EOF'
{
  "spotify": {
    "client_id": "YOUR_CLIENT_ID"
  }
}
EOF
```

或用环境变量：

```bash
export SPOTIFY_CLIENT_ID=YOUR_CLIENT_ID
```

### 3. 授权登录（首次）

```bash
python3 music_cli.py --provider spotify auth
```

浏览器打开 Spotify 授权页，登录并同意后自动完成。Token 存到 `~/.config/music-cli/config.json`，过期后自动刷新，无需重复操作。

### 说明

- **搜索**：走酷狗 API（免费、无需授权），结果用 `spotify:search:` URI 在 Spotify 客户端播放
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
