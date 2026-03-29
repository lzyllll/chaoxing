# :computer: 超星学习通自动化完成任务点(命令行版)

<p align="center">
    <a href="https://github.com/Samueli924/chaoxing" target="_blank" style="margin-right: 20px; font-style: normal; text-decoration: none;">
        <img src="https://img.shields.io/github/stars/Samueli924/chaoxing" alt="Github Stars" />
    </a>
    <a href="https://github.com/Samueli924/chaoxing" target="_blank" style="margin-right: 20px; font-style: normal; text-decoration: none;">
        <img src="https://img.shields.io/github/forks/Samueli924/chaoxing" alt="Github Forks" />
    </a>
    <a href="https://github.com/Samueli924/chaoxing" target="_blank" style="margin-right: 20px; font-style: normal; text-decoration: none;">
        <img src="https://img.shields.io/github/languages/code-size/Samueli924/chaoxing" alt="Code-size" />
    </a>
    <a href="https://github.com/Samueli924/chaoxing" target="_blank" style="margin-right: 20px; font-style: normal; text-decoration: none;">
        <img src="https://img.shields.io/github/v/release/Samueli924/chaoxing?display_name=tag&sort=semver" alt="version" />
    </a>
</p>
:muscle: 本项目的最终目的是通过开源消灭所谓的付费刷课平台，希望有能力的朋友都可以为这个项目提交代码，支持本项目的良性发展

:star: 觉得有帮助的朋友可以给个Star

## :point_up: 更新通知
20241021更新通知： 感谢[sz134055](https://github.com/sz134055)提交代码[PR #360](https://github.com/Samueli924/chaoxing/pull/360)，**添加了对题库答题的支持**  

## :books: 使用方法

### 源码运行（Python 3.13+）

1. clone 项目至本地

```bash
git clone --depth=1 https://github.com/Samueli924/chaoxing 
cd chaoxing
```

2. 安装依赖

```bash
uv sync
```
使用 `uv run` 运行命令即可自动使用项目环境。

3. (可选直接运行)

```bash
python main.py
```

4. (可选配置文件运行)

> 复制config_template.ini文件为config.ini文件，修改文件内的账号密码内容

```bash
python main.py -c config.ini
```

5. (可选命令行运行)

```bash
python main.py -u 手机号 -p 密码 -l 课程ID1,课程ID2,课程ID3...(可选) -a [retry|ask|continue](可选)
```

> Tips:  
> 如果已安装低版本 Python 推荐使用 `uv` 运行：

```bash
uv run --python 3.13 main.py
```

使用配置文件运行 ：
```bash
uv run --python 3.13 main.py -c config.ini
```

### 打包文件运行
1. 从最新[Releases](https://github.com/Samueli924/chaoxing/releases)中下载exe文件
2. (可选直接运行) 双击运行即可
3. (可选配置文件运行) 下载config_template.ini文件保存为config.ini文件，修改文件内的账号密码内容, 执行 `./chaoxing.exe -c config.ini`
4. (可选命令行运行)`./chaoxing.exe -u "手机号" -p "密码" -l 课程ID1,课程ID2,课程ID3...(可选) -a [retry|ask|continue](可选)`

### Docker运行（Web 控制台）
当前 Docker 部署已调整为 `frontend` 和 `backend` 两个服务：

1. 准备 Compose 环境变量（端口和百度地图 AK）

```bash
copy docker-compose.env.example .env
```

2. 准备后端配置（管理员登录账号密码）

```bash
copy config.example.yaml config.yaml
```

在 `./config.yaml` 里填写 `admin.username` 和 `admin.password`。

> 注意：Docker Compose 会把项目根目录 `config.yaml` 挂载到容器内 `/config/config.yaml`，修改 `./config.yaml` 后重启 `backend` 即可生效。

3. 构建并启动服务

```bash
docker compose up --build -d
```

4. 打开浏览器访问

```text
http://127.0.0.1:5173
```

5. 说明
    - `backend` 使用根目录 `Dockerfile` 构建，并通过 Compose 将 `./config.yaml` 挂载到容器内 `/config/config.yaml`
   - `frontend` 使用 `frontend/Dockerfile` 构建，负责静态页面和 `/api`、`/ws` 反向代理
    - Docker 运行数据（SQLite、cookies 等）默认持久化到根目录 `./.docker-data/runtime`
    - 修改 `./config.yaml` 后，执行 `docker compose restart backend` 即可让后端加载新配置
   - 百度地图 AK 通过根目录 `.env` 中的 `VITE_BAIDU_MAP_AK` 注入到前端镜像构建阶段
   - 如果需要改端口，可在根目录 `.env` 里修改 `BACKEND_PORT_BIND` 和 `FRONTEND_PORT_BIND`

### Web 控制台（FastAPI + Vue3 + SQLModel）

后端使用 `FastAPI + SQLModel + SQLite` 保存账号、课程快照和任务记录，前端使用 `Vue3 + Vite` 提供多账号、多课程选择界面。

1. 准备各自配置文件

```bash
copy config.example.yaml config.yaml
copy frontend\.env.example frontend\.env
```

如需在签到页使用地图选点，请在 `frontend\.env` 中配置百度地图浏览器端 AK：`VITE_BAIDU_MAP_AK`。

2. 安装后端依赖

```bash
uv sync
```

3. 启动后端 API

```bash
uvicorn chaoxing.web.app:app --host 127.0.0.1 --port 8000 --reload
```

或使用 `uv`：

```bash
uv run -m uvicorn chaoxing.web.app:app --host 127.0.0.1 --port 8000 --reload
```

4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

5. 打开浏览器访问

```text
http://127.0.0.1:5173
```

说明：
- 后端配置文件为 `config.yaml`，默认模板为 `config.example.yaml`
- 前端配置文件为 `frontend/.env`，默认模板为 `frontend/.env.example`
- 后端监听地址、CORS、SQLite 路径、cookies 存储目录都由 `config.yaml` 控制
- 如果希望启用 Web 管理员登录，请在 `config.yaml` 的 `admin` 段填写 `username` 和 `password`
- 前端 dev host、dev port、API 基地址、WS 基地址和代理目标都由 `frontend/.env` 控制
- 也可以直接运行 `.\run-web.ps1`，脚本会分别启动前后端并提示配置文件位置

### 题库配置说明

命令行版与 Web 版现在各自使用独立配置：

- 命令行版 `main.py` 继续使用根目录 `config.ini`
- Web 后端默认从 `config.yaml` 的 `tiku` 段读取默认题库配置

在对应配置文件中找到 `tiku` 段，按照注释填写想要使用的题库名（即 `provider`，大小写要一致），并填写必要信息，如 token。

对于 Web 控制台，账号页面中的 `Answer Provider` 和 `Provider 附加配置(JSON)` 会覆盖 `config.yaml` 里的默认 `tiku` 配置；如果留空，则沿用 `config.yaml` 中的默认值。

对于那些有章节检测且任务点需要解锁的课程，必须配置题库。

**提交模式与答题**
不配置题库（命令行版没有 `config.ini`，或 Web 版没有在 `config.yaml` / 账号配置中填写题库）视为不使用题库，对于章节检测等需要答题的任务会自动跳过。
题库覆盖率：搜到的题目占总题目的比例
提交模式`submit`值为

- `true`：会答完题，达到题库题目覆盖率提交，没达到只保存，**正确率不做保证**。
- `false`：会答题，但是不会提交，仅保存搜到答案的，随后你可以自行前往学习通查看、修改、提交。**任何填写不正确的`submit`值会被视为`false`**

> 题库名即`answer.py`模块中根据`Tiku`类实现的具体题库类，例如`TikuYanxi`（言溪题库），在填写时，请务必保持大小写一致。

### 已关闭任务点处理配置说明

在配置文件的 `[common]` 部分，可以通过 `notopen_action` 选项配置遇到已关闭任务点时的处理方式:

- `retry` (默认): 遇到关闭的任务点时尝试重新完成上一个任务点，如果连续重试 3 次仍然失败 (或未配置题库及自动提交) 则停止
- `ask`: 遇到关闭的任务点时询问用户是否继续。选择继续后会自动跳过连续的关闭任务点，直到遇到开放的任务点
- `continue`: 自动跳过所有关闭的任务点，继续检查和完成后续任务点

也可以通过命令行参数 `-a` 或 `--notopen-action` 指定处理方式，例如：

```bash
python main.py -a ask  # 使用询问模式
```

**外部通知配置说明**

这功能会在所有课程学习任务结束后，或是程序出现错误时，使用外部通知服务推送消息告知你（~~有用但不多~~）

与题库配置类似，不填写视为不使用，按照注释填写想要使用的外部通知服务（也是`provider`，大小写要一致），并填写必要的`url`

## :heart: CONTRIBUTORS

![Alt](https://repobeats.axiom.co/api/embed/d3931e84b4b2f17cbe60cafedb38114bdf9931cb.svg "Repobeats analytics image")  

<a style="margin-top: 15px" href="https://github.com/Samueli924/chaoxing/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Samueli924/chaoxing" />
</a>

## :warning: 免责声明
- 本代码遵循 [GPL-3.0 License](https://github.com/Samueli924/chaoxing/blob/main/LICENSE) 协议，允许**开源/免费使用和引用/修改/衍生代码的开源/免费使用**，不允许**修改和衍生的代码作为闭源的商业软件发布和销售**，禁止**使用本代码盈利**，以此代码为基础的程序**必须**同样遵守 [GPL-3.0 License](https://github.com/Samueli924/chaoxing/blob/main/LICENSE) 协议
- 本代码仅用于**学习讨论**，禁止**用于盈利**
- 他人或组织使用本代码进行的任何**违法行为**与本人无关
