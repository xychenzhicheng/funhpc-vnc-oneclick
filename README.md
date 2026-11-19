# 一键部署 VNC 网页桌面

`install-vnc.sh` 自动安装 XFCE + TigerVNC + noVNC + websockify，启动后验证网页、WebSocket 和 VNC 协议连接。用户最后只需要在云平台开放脚本打印的**网页端口**。

## 1. 使用方法

适用：使用 apt 的 Ubuntu / Debian、root 或 sudo 权限。针对 Ubuntu 22.04 云容器设计；不是 Windows、CentOS 或所有 Linux 发行版通用脚本。需要能够访问软件源。

将 `install-vnc.sh` 上传到服务器，在脚本所在目录运行：

```bash
sudo bash install-vnc.sh
```

已经是 root（提示符为 `root@...`）时：

```bash
bash install-vnc.sh
```

首次运行输入并确认 VNC 密码。输入时不会显示字符。这不是 SSH 密码，请另设密码。传统 VNC 认证只使用最多 8 个字符，本脚本明确限制为 **6～8 个可打印 ASCII 字符**，防止长密码被静默截断。

运行结束看到 `READY` 后，在平台开放 `Expose only this browser port` 对应端口。默认优先使用 `6080`，首次部署遇到占用会自动寻找 `6081`～`6099`。

浏览器打开：

```text
http://平台生成的主机名和外部端口/vnc.html
```

如果平台生成 `example.com:23456`，地址应为 `http://example.com:23456/vnc.html`，不要再加 `:6080`。若提供 HTTPS 地址，保留 HTTPS。平台的 HTTP/HTTPS 代理必须支持 WebSocket。

点击连接，输入 VNC 密码即可。

首次安装通常约 3～10 分钟，取决于软件源速度。源不可达时会报错退出。

## 2. 可选配置

指定网页端口和分辨率：

```bash
bash install-vnc.sh --port 6082 --geometry 1920x1080
```

指定 X 显示编号（一般不需要）：

```bash
bash install-vnc.sh --display 3
```

非交互部署可使用私有密码文件，避免把密码写进命令行或 shell 历史：

```bash
chmod 600 /secure/vnc-password.txt
bash install-vnc.sh --password-file /secure/vnc-password.txt
```

密码文件只放一行密码，不要存入代码仓库。脚本不包含任何服务器地址、SSH 凭据或默认密码。

修改密码：

```bash
bash install-vnc.sh --reset-password
```

重复运行会保留已保存的端口、分辨率、显示编号和密码，除非指定覆盖选项；**会重启本脚本创建的桌面，请先保存桌面里未保存的工作**。不会关闭原先手动启动的 VNC/noVNC。旧的手动桌面不会被迁移；脚本创建的是一个独立的新桌面。

## 3. 运行与重启

### 有 systemd 的服务器

自动注册服务并启用开机启动：

```bash
systemctl status easy-novnc
systemctl restart easy-novnc
systemctl stop easy-novnc
```

组件异常退出时，systemd 会尝试重启整套桌面，连续失败达到限制后停止重试。

### 无 systemd 的容器（常见于算力平台）

脚本使用后台进程运行，SSH 断开后继续工作。**容器重启、重建后不能承诺自动恢复**：需要平台启动钩子，且安装目录必须保留。镜像重置后只保留 `/data` 的平台，需要把安装脚本保存在 `/data`，重建后重新部署。

检查状态：

```bash
bash /opt/easy-novnc/run.sh status
```

停止：

```bash
bash /opt/easy-novnc/run.sh stop
```

启动：

```bash
nohup /bin/bash /opt/easy-novnc/run.sh start \
  >>/var/log/easy-novnc/service.log 2>&1 </dev/null &
```

若平台支持容器启动脚本，把上面的后台启动命令**追加**到已有启动流程，不要替换镜像原有的 SSH 等服务启动命令。容器模式下组件退出会停止整套托管桌面，不自动循环重试；查清日志后手动启动。

## 4. 安全与排障

- 只开放最终网页端口。后端 VNC 仅监听本机，X11 TCP 被禁用；不要额外开放 5901、5902、6001 等端口。
- 默认网页服务为 HTTP，没有 TLS。公网优先使用 HTTPS + WebSocket 反向代理和额外访问认证，或使用 SSH 隧道。VNC 密码不能替代传输加密。
- 这是供独占的 root 算力容器使用的管理员桌面，不是多用户隔离方案。能连接该桌面的人拥有 root 桌面权限。
- 脚本不自动修改平台端口映射、安全组、UFW 或其他防火墙；裸机若有额外防火墙，需要单独允许网页端口。
- `READY` 表示服务器本机的 HTTP、WebSocket 和 VNC 握手检查通过，不代表公网端口已经映射，也不代表浏览器已完成密码认证、桌面画面测试。

日志目录：

```bash
tail -n 80 /var/log/easy-novnc/service.log
tail -n 80 /var/log/easy-novnc/vnc.log
tail -n 80 /var/log/easy-novnc/desktop.log
tail -n 80 /var/log/easy-novnc/web.log
```

文件位置：配置 `/etc/easy-novnc/config`，密码及 X 认证 `/var/lib/easy-novnc/`，进程管理脚本 `/opt/easy-novnc/run.sh`。日志采用追加方式，长期运行时请按需配置日志轮转。

## 5. 验证范围

本地自动检查：安装脚本与生成的运行脚本 Bash 语法、内嵌 Python 语法、帮助输出、合法/非法参数、密码限制。

```bash
python3 -I test_installer.py
```

测试不会安装软件或更改服务器。当前已通过这些离线测试；尚未在全新 Ubuntu/Debian 系统上完整执行此安装脚本，也未实测 systemd 开机恢复。现有服务器原来的 noVNC 服务未被此脚本替换。
