#!/usr/bin/env python3
"""
OpenCLI 采集接口封装层。

职责：
1. 检测 opencli 是否安装
2. 动态发现平台适配器命令
3. 对指定平台执行搜索
4. 使用 OpenCLI browser 提取指定 URL
5. 管理 OpenCLI profile 与浏览器桥接状态
6. 标准化返回内容
7. 失败时返回空列表/False/None，由调用方决定是否降级 WebSearch

注意：本脚本不直接暴露给 SKILL.md，对 skill 是黑盒。
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any


class OpenCLIAdapter:
    """OpenCLI 采集接口封装。"""

    # 平台别名映射： skill 中的名称 -> OpenCLI 中可能的适配器名称
    # 只包含 ziliaocaiji 场景中可能有 OpenCLI 适配器的平台
    # 其他平台（百度、36氪、贴吧、豆瓣、BBC、NYT、Medium、arXiv、Google Scholar 等）
    # 直接走 WebSearch/WebFetch 降级，不在此映射中硬编码
    PLATFORM_ALIASES = {
        "知乎": ["zhihu"],
        "微博": ["weibo"],
        "B站": ["bilibili"],
        "哔哩哔哩": ["bilibili"],
        "YouTube": ["youtube"],
        "youtube": ["youtube"],
        "Reddit": ["reddit"],
        "reddit": ["reddit"],
    }

    # 每个平台尝试的 search 命令
    # 空列表表示该平台不适合用 OpenCLI 做关键词搜索，直接降级 WebSearch
    SEARCH_COMMANDS = {
        "zhihu": ["search", "hot"],
        "weibo": ["search", "feed", "hot"],
        "bilibili": ["search", "hot", "feed"],
        "youtube": ["search"],
        "reddit": ["search", "hot"],
    }

    # 不需要关键词参数的命令
    NO_ARG_COMMANDS = {"hot"}

    # 平台默认语言推断（用于与 score_materials.py 对齐）
    PLATFORM_LANGUAGE = {
        "知乎": "zh",
        "微博": "zh",
        "B站": "zh",
        "哔哩哔哩": "zh",
        "YouTube": "en",
        "Reddit": "en",
    }

    # 平台默认类型推断
    PLATFORM_TYPE = {
        "知乎": "知乎",
        "微博": "社交媒体",
        "B站": "视频",
        "哔哩哔哩": "视频",
        "YouTube": "视频",
        "Reddit": "论坛",
    }

    def __init__(self):
        self._manifest: Optional[List[Dict[str, Any]]] = None

    def is_installed(self) -> bool:
        """检查 opencli 是否安装。"""
        return shutil.which("opencli") is not None

    def get_version(self) -> Optional[str]:
        """获取 opencli 版本。"""
        try:
            result = subprocess.run(
                ["opencli", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return result.stdout.strip()
        except Exception:
            return None

    def load_manifest(self) -> List[Dict[str, Any]]:
        """加载 OpenCLI 适配器清单。"""
        if self._manifest is not None:
            return self._manifest

        try:
            result = subprocess.run(
                ["opencli", "list", "-f", "json"],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            self._manifest = json.loads(result.stdout)
        except Exception as e:
            print(f"[OpenCLIAdapter] 加载清单失败: {e}")
            self._manifest = []

        return self._manifest

    def resolve_site(self, platform_name: str) -> Optional[str]:
        """
        将 skill 中的平台名称解析为 OpenCLI 适配器名称。
        """
        aliases = self.PLATFORM_ALIASES.get(platform_name, [platform_name])
        manifest = self.load_manifest()

        available_sites = {entry.get("site", "").lower() for entry in manifest}

        for alias in aliases:
            if alias.lower() in available_sites:
                return alias.lower()

        return None

    def list_commands_for_site(self, site: str) -> List[str]:
        """列出某站点下可用的命令名称。"""
        manifest = self.load_manifest()
        commands = []
        for entry in manifest:
            if entry.get("site", "").lower() == site.lower():
                commands.append(entry.get("name", ""))
        return commands

    def search(self, platform_name: str, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        在指定平台搜索关键词。

        返回标准化内容列表。失败时返回空列表。
        站点适配器命令即使带 --keep-tab false，仍可能留下空白窗口，因此 finally 中统一清理。
        """
        site = self.resolve_site(platform_name)
        if not site:
            print(f"[OpenCLIAdapter] 未找到平台 {platform_name} 的 OpenCLI 适配器")
            return []

        available_commands = self.list_commands_for_site(site)
        candidate_commands = self.SEARCH_COMMANDS.get(site, ["search"])

        # 找到第一个可用的 search 类命令
        command = None
        for cmd in candidate_commands:
            if cmd in available_commands:
                command = cmd
                break

        if not command:
            print(f"[OpenCLIAdapter] 平台 {platform_name}({site}) 没有可用搜索命令")
            return []

        try:
            # 构造命令参数
            # --window background: 避免反复弹出前景浏览器窗口，降低视觉干扰与内存峰值
            # --keep-tab false: 命令执行后释放 tab lease，降低标签堆积（但部分版本仍会留下空白窗口）
            cmd_args = ["opencli", site, command]
            if command not in self.NO_ARG_COMMANDS:
                cmd_args.append(keyword)
            cmd_args.extend(["-f", "json", "--window", "background", "--keep-tab", "false"])

            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                print(f"[OpenCLIAdapter] {site} {command} 失败: {result.stderr}")
                return []

            data = json.loads(result.stdout)
            return self._normalize(data, platform_name, site)

        except Exception as e:
            print(f"[OpenCLIAdapter] {site} {command} 异常: {e}")
            return []
        finally:
            # 站点适配器可能遗留空白窗口，统一清理
            self.cleanup_leaked_windows()

    def _normalize(self, data: Any, platform_name: str, site: str) -> List[Dict[str, Any]]:
        """将 OpenCLI 返回数据标准化为统一结构。

        输出字段与 scripts/score_materials.py 的输入 schema 对齐：
        title, url, platform, language, publish_date, type, authority, verification, stance
        """
        items = []

        if isinstance(data, list):
            raw_items = data
        elif isinstance(data, dict):
            # 尝试常见的 list 键名
            raw_items = data.get("data") or data.get("items") or data.get("list") or []
            if not isinstance(raw_items, list):
                raw_items = []
        else:
            raw_items = []

        default_language = self.PLATFORM_LANGUAGE.get(platform_name, "")
        default_type = self.PLATFORM_TYPE.get(platform_name, "其他")

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            title = self._extract_field(item, ["title", "name", "question", "topic", "text"])
            url = self._extract_field(item, ["url", "link", "href", "share_url"])
            summary = self._extract_field(item, ["summary", "description", "content", "excerpt", "snippet"])
            publish_date = self._extract_field(
                item, ["published_at", "publish_time", "publish_date", "created_at", "time", "date"]
            )

            if not title:
                continue

            items.append({
                "title": title,
                "summary": summary or "",
                "url": url or "",
                "platform": platform_name,
                "language": item.get("language") or default_language,
                "publish_date": publish_date or "",
                "type": item.get("type") or default_type,
                "authority": item.get("authority") or "中",
                "verification": item.get("verification") or "单一来源",
                "stance": item.get("stance") or "中立",
                "source": "opencli",
                "raw": item,
            })

        return items

    def fetch_url(self, url: str, session: str = "ziliaocaiji") -> Optional[Dict[str, Any]]:
        """
        使用 OpenCLI browser 打开并提取指定 URL 的内容。
        适合没有站点适配器或适配器读取失败的页面。
        返回标准化结构，失败时返回 None。

        注意：browser open/extract 不支持 --keep-tab，必须手动解析返回的 page/targetId 并关闭标签。
        """
        if not self.is_installed():
            return None

        page_id: Optional[str] = None
        try:
            # 打开页面（browser open 只支持 --window，不支持 --keep-tab）
            open_result = subprocess.run(
                ["opencli", "browser", session, "open", url, "--window", "background"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if open_result.returncode != 0:
                print(f"[OpenCLIAdapter] browser open 失败: {open_result.stderr}")
                return None

            # 解析返回的 page/targetId
            try:
                open_data = json.loads(open_result.stdout)
                page_id = open_data.get("page")
            except json.JSONDecodeError:
                print(f"[OpenCLIAdapter] browser open 返回非 JSON: {open_result.stdout}")
                return None

            # 提取内容
            extract_result = subprocess.run(
                ["opencli", "browser", session, "extract"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if extract_result.returncode != 0:
                print(f"[OpenCLIAdapter] browser extract 失败: {extract_result.stderr}")
                return None

            return {
                "title": "",
                "summary": extract_result.stdout.strip(),
                "url": url,
                "platform": "browser",
                "language": "",
                "publish_date": "",
                "type": "其他",
                "authority": "中",
                "verification": "单一来源",
                "stance": "中立",
                "source": "opencli",
                "raw": extract_result.stdout,
            }
        except Exception as e:
            print(f"[OpenCLIAdapter] fetch_url 异常: {e}")
            return None
        finally:
            # 显式关闭本次打开的标签，防止标签堆积
            if page_id:
                try:
                    subprocess.run(
                        ["opencli", "browser", session, "tab", "close", page_id],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                except Exception as e:
                    print(f"[OpenCLIAdapter] 关闭标签 {page_id} 失败: {e}")

    def close_session(self, session: str = "ziliaocaiji") -> bool:
        """释放指定的 OpenCLI browser 会话，并关闭该会话所有标签。"""
        if not self.is_installed():
            return False
        try:
            # 先关闭会话所有标签，避免 OpenCLI Browser 标签堆积
            try:
                tab_result = subprocess.run(
                    ["opencli", "browser", session, "tab", "list"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if tab_result.returncode == 0:
                    tabs = json.loads(tab_result.stdout)
                    if isinstance(tabs, list):
                        for tab in tabs:
                            target_id = tab.get("page")
                            if target_id:
                                subprocess.run(
                                    ["opencli", "browser", session, "tab", "close", target_id],
                                    capture_output=True,
                                    text=True,
                                    timeout=15,
                                )
            except Exception as e:
                print(f"[OpenCLIAdapter] 关闭会话标签失败: {e}")

            # 释放会话
            result = subprocess.run(
                ["opencli", "browser", session, "close"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                print(f"[OpenCLIAdapter] close_session 失败: {result.stderr}")
                return False
            return True
        except Exception as e:
            print(f"[OpenCLIAdapter] close_session 异常: {e}")
            return False

    def cleanup_leaked_windows(self) -> bool:
        """
        清理 OpenCLI 残留的空白窗口和标签分组（macOS）。

        清理策略：
        1. 遍历所有窗口，关闭所有标题包含 "OpenCLI Browser" 的标签（无论该窗口是否有其他正常标签）
        2. 关闭所有标签都是 about:blank / chrome://newtab 的空窗口
        不会误关用户的正常标签。

        当前仅实现 macOS；其他平台返回 False 并由调用方决定是否忽略。
        """
        if sys.platform != "darwin":
            print("[OpenCLIAdapter] cleanup_leaked_windows 当前仅支持 macOS")
            return False

        script = r'''
        tell application "Google Chrome"
            set closedWindows to 0
            set closedTabs to 0

            -- 第一阶段：关闭所有标题包含 "OpenCLI Browser" 的标签
            repeat with i from (count of windows) to 1 by -1
                set w to window i
                set tabCount to count of tabs of w
                repeat with j from tabCount to 1 by -1
                    try
                        set t to tab j of w
                        set ttl to title of t
                        if (ttl contains "OpenCLI Browser") then
                            close t
                            set closedTabs to closedTabs + 1
                        end if
                    on error
                        -- 忽略无法读取的标签
                    end try
                end repeat
            end repeat

            -- 第二阶段：关闭只剩 about:blank / chrome://newtab 的空窗口
            repeat with i from (count of windows) to 1 by -1
                set w to window i
                set tabCount to count of tabs of w
                if tabCount = 0 then
                    close w
                    set closedWindows to closedWindows + 1
                else
                    set isLeakedWindow to true
                    repeat with j from tabCount to 1 by -1
                        try
                            set t to tab j of w
                            set u to URL of t
                            if not (u starts with "about:blank" or u starts with "chrome://newtab") then
                                set isLeakedWindow to false
                                exit repeat
                            end if
                        on error
                            -- 忽略无法读取的标签
                        end try
                    end repeat
                    if isLeakedWindow then
                        repeat with j from tabCount to 1 by -1
                            try
                                close tab j of w
                            end try
                        end repeat
                        if (count of tabs of w) = 0 then
                            close w
                            set closedWindows to closedWindows + 1
                        end if
                    end if
                end if
            end repeat

            return "closedTabs:" & closedTabs & ",closedWindows:" & closedWindows
        end tell
        '''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                print(f"[OpenCLIAdapter] 清理残留窗口失败: {result.stderr}")
                return False
            print(f"[OpenCLIAdapter] 清理残留窗口: {result.stdout.strip()}")
            return True
        except Exception as e:
            print(f"[OpenCLIAdapter] cleanup_leaked_windows 异常: {e}")
            return False

    # ------------------------------------------------------------------
    # Profile / Bridge / Chrome 进程管理（步骤 4.5 与步骤 11 使用）
    # ------------------------------------------------------------------

    def profile_use(self, profile_id: str) -> bool:
        """切换 OpenCLI profile。"""
        if not self.is_installed():
            return False
        try:
            subprocess.run(
                ["opencli", "profile", "use", profile_id],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            return True
        except Exception as e:
            print(f"[OpenCLIAdapter] profile_use 失败: {e}")
            return False

    def doctor_check(self) -> bool:
        """检查 OpenCLI 浏览器桥接是否就绪。

        opencli doctor 在扩展未连接时仍可能返回 0，因此需要解析 stdout 中的 [FAIL] 标记。
        """
        status = self.bridge_status()
        return status.get("ok", False)

    def bridge_status(self) -> Dict[str, Any]:
        """获取 OpenCLI 桥接状态。

        注：opencli doctor 目前不支持 -f json，且即使扩展未连接也可能返回 0，
        因此通过返回码和 stdout/stderr 文本共同判断状态。
        """
        if not self.is_installed():
            return {"ok": False, "error": "opencli not installed"}
        try:
            result = subprocess.run(
                ["opencli", "doctor"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            has_fail = "[FAIL]" in output or "Connectivity: failed" in output
            if result.returncode != 0 or has_fail:
                return {
                    "ok": False,
                    "error": result.stderr.strip() or result.stdout.strip(),
                }
            return {
                "ok": True,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def is_chrome_running(self) -> bool:
        """检测 Chrome 浏览器是否正在运行（跨平台简化）。"""
        try:
            if sys.platform == "darwin":
                result = subprocess.run(
                    ["pgrep", "-x", "Google Chrome"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0
            elif sys.platform.startswith("linux"):
                result = subprocess.run(
                    ["pgrep", "-x", "chrome"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.returncode == 0
            elif sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return "chrome.exe" in result.stdout
            else:
                return False
        except Exception as e:
            print(f"[OpenCLIAdapter] is_chrome_running 失败: {e}")
            return False

    def list_chrome_profiles(self) -> List[Dict[str, Any]]:
        """从 Chrome Local State 直接读取本地 profile 列表（无需 extension 连接）。

        返回 [{profile_id, name, email, gaia_name}, ...]。
        读取失败时返回空列表，由调用方决定是否降级。
        """
        import json as _json
        try:
            if sys.platform == "darwin":
                local_state = Path.home() / "Library/Application Support/Google/Chrome/Local State"
            elif sys.platform.startswith("linux"):
                local_state = Path.home() / ".config/google-chrome/Local State"
            elif sys.platform == "win32":
                local_state = Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data/Local State"
            else:
                return []

            if not local_state.exists():
                return []

            data = _json.loads(local_state.read_text("utf-8"))
            info = data.get("profile", {}).get("info_cache", {})
            profiles = []
            for pid, pdata in info.items():
                profiles.append({
                    "profile_id": pid,
                    "name": pdata.get("name", ""),
                    "email": pdata.get("user_name", ""),
                    "gaia_name": pdata.get("gaia_name", ""),
                })
            return profiles
        except Exception as e:
            print(f"[OpenCLIAdapter] list_chrome_profiles 失败: {e}")
            return []

    def launch_chrome(self, profile_dir: Optional[str] = None) -> bool:
        """启动 Chrome 浏览器并确保至少有一个可见窗口（跨平台简化）。

        若指定 profile_dir，则使用 --profile-directory 启动到对应 Chrome profile。
        """
        try:
            if sys.platform == "darwin":
                if profile_dir:
                    # 通过 --profile-directory 指定 Chrome profile 启动。
                    # 注意：
                    # - macOS 下用 open -na 冷启动 Chrome 会打开两个窗口，因此用 open -a。
                    # - 调用本方法前，如果 Chrome 已在运行且 profile 不匹配，会先 quit_chrome()
                    #   退出，所以这里 open -a 实际上是冷启动到目标 profile。
                    args = [
                        "open", "-a", "Google Chrome",
                        "--args", f"--profile-directory={profile_dir}",
                    ]
                    subprocess.run(args, check=True, timeout=15)
                else:
                    # 如果 Chrome 已经在运行，直接 open -a 不会创建新窗口，
                    # 因此用 AppleScript 显式要求一个窗口，确保扩展能连接。
                    script = r'''
                    tell application "Google Chrome"
                        if not running then
                            launch
                            delay 1
                        end if
                        make new window
                        activate
                    end tell
                    '''
                    subprocess.run(
                        ["osascript", "-e", script],
                        check=True,
                        timeout=15,
                    )
            elif sys.platform.startswith("linux"):
                cmd = ["google-chrome", "--new-window", "about:blank"]
                if profile_dir:
                    cmd.insert(1, f"--profile-directory={profile_dir}")
                subprocess.Popen(cmd)
            elif sys.platform == "win32":
                cmd = ["start", "chrome", "--new-window", "about:blank"]
                if profile_dir:
                    cmd.insert(2, f"--profile-directory={profile_dir}")
                subprocess.Popen(cmd, shell=True)
            else:
                print(f"[OpenCLIAdapter] launch_chrome 不支持平台: {sys.platform}")
                return False
            return True
        except Exception as e:
            print(f"[OpenCLIAdapter] launch_chrome 失败: {e}")
            return False

    def quit_chrome(self) -> bool:
        """强制退出 Chrome（跨平台简化）。

        策略 B 需要：当前 profile 不是目标 profile 时，关闭 Chrome 并用目标 profile 重启。
        注意：这会关闭用户所有 Chrome 窗口和标签。
        """
        try:
            if sys.platform == "darwin":
                script = r'''
                tell application "Google Chrome"
                    if running then
                        quit
                    end if
                end tell
                '''
                subprocess.run(
                    ["osascript", "-e", script],
                    check=False,
                    timeout=15,
                )
            elif sys.platform.startswith("linux"):
                subprocess.run(["pkill", "-x", "chrome"], check=False, timeout=10)
            elif sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], check=False, timeout=10)
            else:
                print(f"[OpenCLIAdapter] quit_chrome 不支持平台: {sys.platform}")
                return False
            return True
        except Exception as e:
            print(f"[OpenCLIAdapter] quit_chrome 失败: {e}")
            return False

    def wait_for_chrome_exit(self, max_attempts: int = 20, interval: float = 0.5) -> bool:
        """等待 Chrome 进程完全退出。"""
        for attempt in range(max_attempts):
            if not self.is_chrome_running():
                return True
            print(f"[OpenCLIAdapter] 等待 Chrome 退出... ({attempt + 1}/{max_attempts})")
            time.sleep(interval)
        return False

    def get_connected_opencli_profile(self) -> Optional[str]:
        """获取当前已连接的 OpenCLI profile ID。

        如果 extension 未连接，返回 None。
        """
        if not self.is_installed():
            return None
        try:
            result = subprocess.run(
                ["opencli", "profile", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # 已连接时输出类似：
            # Connected Browser Bridge profiles
            #   g3a5ehu6 — connected v1.0.22
            if result.returncode != 0 or "Connected Browser Bridge profiles" not in result.stdout:
                return None
            for line in result.stdout.splitlines():
                line = line.strip()
                if "— connected" in line or "-- connected" in line:
                    # 取第一个 token 作为 profile id
                    return line.split()[0]
            return None
        except Exception as e:
            print(f"[OpenCLIAdapter] get_connected_opencli_profile 失败: {e}")
            return None

    def ensure_browser_with_profile(
        self,
        opencli_profile_id: str,
        chrome_profile_dir: str,
        max_retry: int = 5,
        retry_interval: float = 2.0,
    ) -> bool:
        """确保 Chrome 已打开并连接到指定的 OpenCLI profile。

        策略 B：
        1. 若目标 profile 已连接，直接返回成功。
        2. 若 Chrome 未运行，用 chrome_profile_dir 启动。
        3. 若 Chrome 已运行但目标 profile 未连接（无论当前是什么 profile），
           强制退出 Chrome，再用 chrome_profile_dir 重启。
        4. 等待 extension 连接成功。

        注意：profile 不匹配时会关闭用户所有 Chrome 窗口。
        """
        # 前置清理：关闭之前运行残留的 OpenCLI Browser 标签分组
        print("[OpenCLIAdapter] 前置清理：关闭已有 OpenCLI Browser 残留标签...")
        self.cleanup_leaked_windows()

        # 1. 先检查目标 profile 是否已连接
        connected = self.get_connected_opencli_profile()
        if connected == opencli_profile_id and self.doctor_check():
            print(f"[OpenCLIAdapter] 目标 profile {opencli_profile_id} 已连接")
            return True

        # 2. Chrome 是否运行
        running = self.is_chrome_running()

        # 3. 如果 Chrome 在运行但目标 profile 没连上，说明当前 profile 不对或扩展未激活，
        #    强制退出后重新启动到目标 profile。
        if running:
            print(f"[OpenCLIAdapter] Chrome 在运行但目标 profile {opencli_profile_id} 未连接，准备重启 Chrome")
            if not self.quit_chrome():
                print("[OpenCLIAdapter] 关闭 Chrome 失败")
                return False
            if not self.wait_for_chrome_exit():
                print("[OpenCLIAdapter] Chrome 未能在预期时间内退出")
                return False

        # 4. 启动 Chrome（如未运行或刚被关闭）
        print(f"[OpenCLIAdapter] 用 profile {chrome_profile_dir} 启动 Chrome")
        if not self.launch_chrome(profile_dir=chrome_profile_dir):
            return False
        if not self.wait_for_chrome():
            print("[OpenCLIAdapter] Chrome 启动后未就绪")
            return False

        # 5. 使用目标 profile
        print(f"[OpenCLIAdapter] 切换 OpenCLI profile: {opencli_profile_id}")
        self.profile_use(opencli_profile_id)

        # 6. 等待 extension 连接
        print("[OpenCLIAdapter] 等待 extension 连接...")
        for attempt in range(max_retry):
            if self.doctor_check():
                connected_now = self.get_connected_opencli_profile()
                if connected_now == opencli_profile_id:
                    print(f"[OpenCLIAdapter] extension 已连接 ({opencli_profile_id})")
                    return True
            print(f"[OpenCLIAdapter] 等待 extension 连接... ({attempt + 1}/{max_retry})")
            time.sleep(retry_interval)

        print("[OpenCLIAdapter] extension 最终未连接")
        return False

    def wait_for_chrome(self, max_attempts: int = 10, interval: float = 1.0) -> bool:
        """等待 Chrome 进程就绪。"""
        for attempt in range(max_attempts):
            if self.is_chrome_running():
                return True
            print(f"[OpenCLIAdapter] 等待 Chrome 启动... ({attempt + 1}/{max_attempts})")
            time.sleep(interval)
        return False

    @staticmethod
    def _extract_field(item: Dict[str, Any], field_names: List[str]) -> Optional[str]:
        """从 item 中提取第一个存在的字段值。"""
        for name in field_names:
            value = item.get(name)
            if value is not None:
                return str(value)
        return None


def main():
    """简单的 CLI 测试入口。"""
    adapter = OpenCLIAdapter()
    print("OpenCLI 安装:", adapter.is_installed())
    print("版本:", adapter.get_version())

    if not adapter.is_installed():
        return

    manifest = adapter.load_manifest()
    print(f"适配器数量: {len(manifest)}")

    # 测试知乎（cookie 策略，需要登录）
    results = adapter.search("知乎", "减脂")
    print(f"知乎搜索结果: {len(results)} 条")
    for r in results[:3]:
        print("-", r["title"], r.get("url", ""))


if __name__ == "__main__":
    main()
