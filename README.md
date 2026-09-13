# 🤵 祖师爷桌宠 (Master Desktop Pet)

> 基于 **PyQt6 + 大语言模型 + 语音克隆** 构建的高颜值沉浸式桌面宠物！
> 接入江南第一深情·童锦程两性情感认知模型（基于开源 Skill `hotcoffeeshake/tong-jincheng-skill`），为您提供深度聊天记录复盘、两性博弈洞察、反击神级文案与人间清醒的语音陪伴。

---

## ✨ 核心特色

1. **🎭 灵动生动的桌面角色**：
   - 包含【待机】、【开始打字】、【持续工作打字】、【结束打字】、【说话互动】、【趣味剪指甲】等 6 种动作序列帧。
   - 支持自由拖拽、无缝吸附、置顶显示、缩放比例调节（25% ~ 75%）。
   - 闲置时自动触发自言自语或趣味打字动画。

2. **🧠 微信/QQ 聊天记录智能深度研报**：
   - **杂质过滤**：自动清洗复制粘贴的微信时间戳、日期分割线、系统标签。
   - **主体辨析**：精准对齐双方身份（我方求助兄弟 vs 对方女生/相亲对象），梳理对话脉络，拒绝颠倒是非。
   - **智能场景洞察**：精准区分真实借贷、冷淡敷衍、争吵甩锅PUA、暧昧养鱼、前任回头、相亲盘查等场景，拒绝无脑提钱。
   - **暴怒怒吼长文**：第一人称拍桌子骂醒兄弟的卑微，彻底粉碎自证陷阱。
   - **可复制神级文案**：提供【直接掀桌】、【冷峻立规】、【绝杀拉黑】三套直接可复制的高情商反击方案。

3. **🤖 多大模型生态全面支持**：
   - 🥇 **Kimi (Moonshot AI)**：长上下文与中文网络聊天记录理解。
   - 🥈 **DeepSeek (深度求索)**：逻辑推理与深层心理动机洞察（推荐 `deepseek-chat` 或 `deepseek-reasoner`）。
   - 🥉 **智谱 AI (GLM)**：国内极速响应（支持 `glm-4-flash` / `glm-4-plus`）。
   - 🌐 亦支持 Google Gemini、OpenAI 官方以及任何兼容 OpenAI 协议的第三方中继。

4. **🎙️ 童锦程原声语音克隆 (Fish Audio)**：
   - 给出分析报告总结时，可选调用 Fish Audio 原声音色朗读决策金句！

---

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/your-username/desktop-pet-mentor.git
cd desktop-pet-mentor
```

### 2. 环境安装 (推荐使用 uv 或 pip)
本项目基于 Python 3.10+ 与 PyQt6：

```bash
# 使用 uv (推荐极速方式)
uv venv
uv pip install pyqt6

# 或使用标准 pip
pip install PyQt6
```

### 3. 配置 API Key
复制配置模板文件：
```bash
copy config.example.json config.json
```
打开 `config.json`，按需填入您的模型 API Key（也可以直接启动程序后，右键桌宠点击 **“🔑 配置大模型 API”** 进行图形化可视化配置）：
```json
{
  "provider": "openai",
  "api_key": "YOUR_MOONSHOT_OR_DEEPSEEK_OR_ZHIPU_API_KEY",
  "base_url": "https://api.moonshot.cn/v1",
  "model": "moonshot-v1-8k",
  "fish_api_key": "",
  "fish_reference_id": "93d4dc1cbd6f4d55aee5ca54c0f9c6bb",
  "tts_enabled": false
}
```

### 4. 运行桌宠
```bash
# 直接运行主脚本
python main.py

# 或双击脚本：
双击启动桌宠.bat
```

---

## 🎮 交互指南

| 操作 | 行为 |
| :--- | :--- |
| **左键拖拽** | 自由移动桌宠在屏幕上的任意位置 |
| **单击桌宠** | 弹出气泡名言并触发说话动效 |
| **双击桌宠** | 触发剪指甲趣味动作（打字时双击为结束收工） |
| **右键菜单** | 切换动作、调整尺寸/帧率、置顶/锁定、投喂聊天记录、API 配置 |
| **投喂对话** | 复制聊天记录粘贴到输入框，一键生成情感深度剖析研报 |

---

## 🔒 隐私与开源安全提示

- 本仓库不包含任何私钥、真实 API Key 或个人敏感信息。
- `.gitignore` 已默认忽略 `config.json` 与 `audio_cache/`，确保您的个人调用凭据和本地音频缓存不会被提交上传。

---

## 📄 License
MIT License
