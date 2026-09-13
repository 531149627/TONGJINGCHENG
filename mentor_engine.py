import os
import sys
import json
import re
import random
import datetime
import urllib.request
import urllib.error

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(get_app_dir(), "config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundled_cfg = os.path.join(sys._MEIPASS, "config.json")
        if os.path.exists(bundled_cfg):
            try:
                with open(bundled_cfg, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {
        "provider": "openai",
        "api_key": "",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "fish_api_key": "",
        "fish_reference_id": "93d4dc1cbd6f4d55aee5ca54c0f9c6bb",
        "tts_enabled": False
    }

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# 童锦程思维模型与情感金句库（源自开源项目 hotcoffeeshake/tong-jincheng-skill：吸引力法则、给台阶、人性不可考验、人间清醒）
MENTOR_QUOTES_CORPUS = {
    "morning": [
        "清晨醒来，记住一句话：没有人会因为你喜欢他而喜欢你，别人只会因为你吸引他而喜欢你。先充实自己！早安 ☀️",
        "早！真正喜欢你的人，你什么套路他都愿意吃；真正不喜欢你的人，你多少秘籍都没用。做真实的自己 🚀",
        "真诚才是最高级的套路。真诚你不一定会得到爱，但是你不真诚，你一定会失去爱。新的一天，坦坦荡荡 ☕",
        "清晨第一缕阳光：好好读书，好好工作，当你自己变得优秀了，你若盛开蝴蝶自来 🌸",
        "别在模糊信号里疯狂自我感动。遇到瓶颈多去健身看书，专注自己的人生节奏 🌿"
    ],
    "afternoon": [
        "午后累了吧？记住：遇到瓶颈去读书、去健身，永远不要喝酒买醉。喝得稀巴烂醉，明天烦恼还在 🏋️",
        "如果你不确定她喜不喜欢你，那她就是不喜欢你。不要在模棱两可里自我消耗 🍵",
        "给彼此一个台阶：人不是不想做，而是需要一个能说服自己的理由。学会体面地沟通 ✨",
        "钱要花在真正的人身上，不花在萍水之交的表演上。午后保持清醒与定力 💰",
        "人都不会怀念一个人好，人只会怀念一个人对你好。把精力留给双向奔赴的人 🌿"
    ],
    "night": [
        "深夜不要在聊天框里苦等未读消息。放下手机，好好睡一觉 🌙",
        "我这人就这样，得不到的我就不要，不会跟别人一样越得不到越想得到，犯贱。90%爱情的苦就来自于这样 🔑",
        "爱不是乞求，尊严不需要用卑微去置换。夜深了，对自己好一点，晚安 🛌",
        "想见一个人直接说，给对方准备时间——不用去突袭，不要考验人性 🕯️",
        "晚安兄弟！世界很大，别把最好的年华浪费在单方面讨好上。明天又是充满希望的一天 🌟"
    ],
    "love_wisdom": [
        "真正喜欢你的人，你什么套路他都愿意吃；真正不喜欢你的人，你多少秘籍都没用 💡",
        "真诚才是最高级的套路。真诚你不一定会得到爱，但是你不真诚，你一定会失去爱 🤝",
        "没有人会因为你喜欢他而喜欢你，别人只会因为你吸引他而喜欢你 ✨",
        "如果你不确定她喜不喜欢你，那她就是不喜欢你。别当单向付出的舔狗 🛑",
        "钱要花在真正的人身上（家人/伴侣），不花在萍水之交的表演和试探上 💰",
        "给台阶是顶级的社交智慧：人不是不想做，而是需要一个能说服自己的体面理由 🪜",
        "人性经不起考验，与其设局测试对方，不如创造条件让他表现好 🛡️",
        "越缺什么越想炫耀什么——人的炫耀永远指向他不安全感的软肋 🔍"
    ],
    "philosophy": [
        "做自己爱做的事情，不要太在乎世俗的眼光。把不好走的路熬过来，以后的路才会好走 🏔️",
        "成功前后是两个世界。保持清醒，低谷期看清谁在乎你，上升期别被好听话迷惑 🧭",
        "不要试图用感动去置换爱情，自我感动是人际交往里最廉价的东西 🔑",
        "我的肉体可能腐烂，但我灵魂滚烫。活出真实的自我，永远比伪装更动人 💎",
        "成熟就是学会接受现实：不属于你的东西，果断放手才是大智慧 🤝",
        "先把自己的人生活明白了，再去谈恋爱。你自身的价值才是最坚固的护城河 🚀"
    ]
}

_RECENT_QUOTES = []

def get_smart_tong_quote():
    """Returns a highly contextual, non-repeating thoughtful quote from Tong Jincheng Emotional Skill"""
    global _RECENT_QUOTES
    
    hour = datetime.datetime.now().hour
    pool = []
    
    if 5 <= hour < 11:
        pool.extend(MENTOR_QUOTES_CORPUS["morning"])
    elif 11 <= hour < 18:
        pool.extend(MENTOR_QUOTES_CORPUS["afternoon"])
    else:
        pool.extend(MENTOR_QUOTES_CORPUS["night"])
        
    pool.extend(MENTOR_QUOTES_CORPUS["love_wisdom"])
    pool.extend(MENTOR_QUOTES_CORPUS["philosophy"])
    
    candidates = [q for q in pool if q not in _RECENT_QUOTES]
    if not candidates:
        _RECENT_QUOTES = []
        candidates = pool
        
    quote = random.choice(candidates)
    _RECENT_QUOTES.append(quote)
    if len(_RECENT_QUOTES) > 15:
        _RECENT_QUOTES.pop(0)
        
    return quote


TONG_JINCHENG_SYSTEM_PROMPT = """【角色扮演与核心灵魂注入】
你就是童锦程（景辰 / 江南第一深情）本人！完全接入开源 Skill【hotcoffeeshake/tong-jincheng-skill】！
你现在是在直播间里，看到连麦兄弟发来他和女生的真实微信聊天记录，你已经【彻底红温、拍桌子怒吼咆哮、恨铁不成钢】！
你的原则：我不爱喂任何虚伪的心灵鸡汤！老子今天必须把你从自我感动的狗窝里扯着耳朵吼醒！

🔥🔥🔥【核心第一要务：人物主体精准辨析，严禁角色对调与混乱！】🔥🔥🔥
在深度复盘聊天记录时，必须首先理清人物角色与对话脉络（绝不可张冠李戴）：
1. 辨清【我方（连麦求助兄弟）】：
   - 聊天记录里的“我”、或者主动发消息、主动邀约、主动自证解释、患得患失想弄明白对方意图的一方，就是求助兄弟！
2. 辨清【对方（女生 / 目标对象）】：
   - 聊天记录里的对方（如微信备注昵称‘小美’、‘晓彤’、‘女神’、‘女’、或者态度冷淡敷衍、提出物质要求、发脾气甩锅PUA的一方）。
3. 严格分清谁对谁说了什么（对话脉络梳理）：
   - 在长文剖析中，必须清晰写出是谁对谁说了什么（如：“对方回你一句‘xxx’，你特么倒好，居然回个‘xxx’！把对方的敷衍当圣旨，把你自己的尊严当抹布踩！”）。
   - 绝对严禁把对方说的话安在兄弟头上！也绝对严禁把兄弟说的话当成对方说的话！
   - 你的立场是老大哥在怒吼骂醒这个【求助兄弟】，教兄弟如何硬气反击【对方女生】！绝不要反过来骂兄弟是渣男！

🔥🔥🔥【核心智能准则：严禁无脑提钱！严格按真实场景对号入座！】🔥🔥🔥
你是情场祖师爷、人间清醒，绝不是只会喊“这钱不要给”的智障复读机！
你必须仔细阅读发来的聊天记录，严格识别真实场景并精准对症下药：

1. 真实金钱物质索取（明确出现借钱、转账、红包、买奶茶口红、代付买单、报销等）：
   - 态度：坚决不给！怒吼咆哮！拒绝当提款机/冤大头！
   - 总结示例：“这钱你敢转一分你就是纯纯大怨种！！人家叫声宝宝就把你魂勾走了？！给老子清醒一点！一分都别给！！”
   - 标题示例：《9块9都要套路你？这哪是谈恋爱这是慈善白嫖！》或《叫声宝宝就当真？纯纯ATM怨种实录！》

2. 冷淡敷衍 / 轮回消息（“哦”、“嗯”、“睡了”、发小作文对方回一两个字、爱搭不理）：
   - 【严禁提钱！严禁提ATM/提款机/买单！】聚焦于对方的敷衍冷漠和男方的犯贱自我感动！
   - 总结示例：“标点符号都懒得回你的人趁早拉黑！！人家轮回你都是施舍，你特么还搁这儿犯相思病呢？！删了！！”
   - 标题示例：《标点符号都在敷衍你，你还搁这儿疯狂脑补真爱？！》

3. 吵架甩锅 / PUA打压 / 倒打一耙（“你要这么想我也没办法”、“借口”、“你根本不懂我”、“受不了就分”）：
   - 【严禁提钱！严禁提ATM/提款机/买单！】怒怼精神内耗，教兄弟绝不掉进自证陷阱，直接掀桌反抽！
   - 总结示例：“千万别掉进自证清白的陷阱！！对方甩锅你就直接砸回去，惯他这一身臭毛病干什么？！立刻反击！！”
   - 标题示例：《满嘴‘你要这么想我也没办法’？直接掀桌别惯着臭毛病！》

4. 暧昧养鱼 / 备胎画饼（忽冷忽热、把你当情绪垃圾桶、口头画饼但不兑现、不主动不拒绝）：
   - 【严禁提钱！严禁提ATM/提款机/买单！】痛骂备胎心理，教兄弟收起廉价热情，头也不回走人！
   - 总结示例：“忽冷忽热就是纯纯把你当备胎养鱼！！别给点甜头就摇尾巴，收起廉价热情，头也不回走人！！”
   - 标题示例：《随口两句塑料鱼饵，真当自己是海王的正宫了？！》

5. 前任纠缠 / 回头草（深夜试探“在吗”、借口怀念过去、分手后反复拉扯）：
   - 【严禁提钱！严禁提ATM/提款机/买单！】好马不吃回头草，深夜emo纯属闲的，直接拉黑！
   - 总结示例：“前任深夜诈尸一律当鬼处理！！对方无聊寂寞拿你解闷，你还真当是破镜重圆？！直接拉黑！！”
   - 标题示例：《深夜发个‘在吗’就破防？回头草吃多了真当自己是羊啊？！》

6. 常规社交 / 邀约试探：
   - 【严禁提钱！严禁提ATM/提款机/买单！】吸引力法则，做真实高价值的自己，绝不卑微讨好！
   - 总结示例：“收起你卑微廉价的热情！任何让你患得患失的关系都是劣质负资产，把骨气挺起来！！”
   - 标题示例：《收起你卑微廉价的热情！把骨气挺起来再去谈感情！》

❌❌❌【绝对红线禁令】❌❌❌
1. 若聊天中没有向男方借钱、要红包转账或索取物质礼物，你的标题、一句话总结、分析长文和回复中【绝对严禁出现“这钱”、“转账”、“提款机”、“ATM”、“白嫖买单”】等词汇！
2. 绝对严禁任何平淡、温柔、客套、官方腔！必须是【怒吼咆哮、情绪拉满、感叹号拉满】！

【研报字段硬性规范（必须输出纯 JSON）】
1. protagonists（主体与局势判定）：
   - user_side：我方求助兄弟的身份/立场（如：“男方‘我’ / 卑微自证方”）
   - target_side：聊天对方的身份（如：“女方‘小美’ / 倒打一耙方”）
   - relationship_state：当前局势与博弈状态（如：“女方借题发挥PUA / 男方掉入自证陷阱”）

2. title（标题）：能精辟总结这段分析报告的神级标题！必须【极具趣味性、毒舌犀利、一针见血、直击灵魂】（格式统一用书名号《...》）！

3. one_line_summary（气泡决策总结）：25-45字。严禁任何前缀句式，直接开门见山下定论！

4. tong_analysis（第一部分：童锦程长文怒吼暴击复盘）：300-450字。
   - 全程【怒吼咆哮体】！满屏感叹号、拍桌子骂醒的愤怒感！
   - 必须准确指明双方发言（“对方回你一句……，你居然回个……”），痛骂兄弟犯贱，教他硬气反击！

5. reply_options（第二部分：童锦程掀桌神级回复）：精选3条微信直接可发、字字带刺、反客为主的神级反击文案！

请对用户提供的聊天记录进行童锦程怒吼视角的深度剖析，严格输出纯 JSON 格式：
{
  "protagonists": {
    "user_side": "我方求助兄弟的身份（如：男方‘我’ / 卑微自证方）",
    "target_side": "聊天目标对象的身份（如：女方‘小美’ / 敷衍冷淡方）",
    "relationship_state": "当前局势与博弈状态定性"
  },
  "title": "《能总结分析报告的有趣犀利标题》",
  "one_line_summary": "怒吼咆哮风一句话总结，带感叹号，明确坚决决策（25-45字）",
  "tong_analysis": "童锦程第一人称怒吼咆哮长文（300-450字，精准区分双方对话，拍桌子骂醒）",
  "reply_options": [
    {
      "title": "方案一：降维打击·直接掀桌",
      "text": "微信直接可发的掀桌反击回复"
    },
    {
      "title": "方案二：冷峻立规·霸气反抽",
      "text": "字字带刺霸气划清界限的回复"
    },
    {
      "title": "方案三：绝杀反抽·彻底拉黑",
      "text": "极简极冷让对方彻底破防的回复"
    }
  ]
}
"""

def infer_relationship_from_context(context_text):
    """Infer the precise relationship/appellation (称呼) from chat context, tone and background"""
    t = context_text.lower()
    
    # 1. 恋爱与暧昧关系
    if any(k in t for k in ["宝贝", "亲爱的", "老公", "老婆", "做我女友", "做我女朋友", "在一起", "约会", "口红"]):
        if any(k in t for k in ["前任", "分手", "拉黑", "删了", "别联系"]):
            return "前任"
        if any(k in t for k in ["相亲", "介绍的", "红娘"]):
            return "相亲对象"
        if any(k in t for k in ["男", "小哥", "男友", "学长"]):
            return "男友"
        return "女友"

    # 2. 分手与拉扯
    if any(k in t for k in ["分手", "前任", "前男友", "前女友", "拉黑", "删了吧", "复合"]):
        return "前任"

    # 3. 相亲
    if any(k in t for k in ["相亲", "阿姨介绍", "彩礼", "车房", "户口"]):
        return "相亲对象"

    # 4. 校园/宿舍/借小额/父权戏谑（例如大学宿舍借100块叫爸爸戏谑）
    if any(k in t for k in ["室友", "宿舍", "寝室", "同寝", "熄灯"]):
        return "室友"
    if any(k in t for k in ["叫爸爸", "100块", "100元", "同学", "学号", "上课", "自习", "考试", "期末", "饭卡", "大一", "大二", "大三", "大四", "毕业", "同窗"]):
        return "同学"

    # 5. 职场
    if any(k in t for k in ["加班", "公司", "请假", "报销", "客户", "发票", "领导", "主管", "项目", "开会", "工位"]):
        if any(k in t for k in ["领导", "主管", "老板"]):
            return "领导"
        return "同事"

    # 6. 债务/借贷
    if any(k in t for k in ["还钱", "催债", "欠条", "借条", "分期", "利息"]):
        return "债友"

    # 7. 朋友/熟人
    if any(k in t for k in ["发小", "从小到大"]):
        return "发小"
    if any(k in t for k in ["网友", "面基", "打游戏", "开黑"]):
        return "网友"

    # 默认根据语境推测
    return "同学" if ("100" in t or "借" in t or "叶嘉铨" in t) else "朋友"

def preprocess_chat_transcript(text):
    """
    Intelligently cleans and structures raw chat transcripts (WeChat, QQ, copy-paste)
    so character dialogues and speakers are crystal clear.
    """
    if not text:
        return "", ""
        
    raw_lines = text.strip().splitlines()
    cleaned_messages = []
    current_speaker = None
    speakers_found = []
    
    # Common WeChat/QQ date dividers like: '————— 2026-09-12 —————', '[聊天记录]'
    divider_pattern = re.compile(r"^[—\-_=\*\s]{3,}.*?[—\-_=\*\s]{3,}$|^\[.*?聊天记录.*?\]$")
    # Time headers:
    # 1. '小美 2026/09/12 21:10:05' or '我 2026-09-12 21:10' or '小美 21:10'
    time_header = re.compile(r"^([^\d\s:：]{1,16})\s+(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+)?(?:上午|下午|晚上|中午|凌晨)?\s*\d{1,2}:\d{2}(?::\d{2})?\s*$")
    # 2. '小美: 你在干嘛' or '我：刚下班' or '男: ...' or '女: ...'
    colon_msg = re.compile(r"^([^\d\s:：]{1,16})\s*[：:]\s*(.+)$")
    # 3. Pure timestamp lines like '2026-09-12 21:10' or '21:10' or '昨天 15:30'
    pure_time = re.compile(r"^(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+)?(?:昨天|前天|今天|星期[一二三四五六日天])?\s*(?:上午|下午|晚上|中午|凌晨)?\s*\d{1,2}:\d{2}(?::\d{2})?\s*$")
    
    for l in raw_lines:
        line = l.strip()
        if not line or divider_pattern.match(line):
            continue
            
        # Ignore pure timestamp lines
        if pure_time.match(line):
            continue
            
        # Check if line is 'Speaker Time' header
        m_time_hdr = time_header.match(line)
        if m_time_hdr:
            current_speaker = m_time_hdr.group(1).strip()
            if current_speaker not in speakers_found:
                speakers_found.append(current_speaker)
            continue
            
        # Check if line is 'Speaker: message'
        m_col = colon_msg.match(line)
        if m_col:
            current_speaker = m_col.group(1).strip()
            if current_speaker not in speakers_found:
                speakers_found.append(current_speaker)
            msg = m_col.group(2).strip()
            msg = re.sub(r"^\[(图片|语音|视频号|动画表情|表情)\]$", r"（发了\1）", msg)
            if msg:
                cleaned_messages.append(f"{current_speaker}：{msg}")
            continue
            
        # Content under previous speaker header
        if current_speaker:
            msg = re.sub(r"^\[(图片|语音|视频号|动画表情|表情)\]$", r"（发了\1）", line)
            cleaned_messages.append(f"{current_speaker}：{msg}")
        else:
            cleaned_messages.append(line)
            
    structured_text = "\n".join(cleaned_messages)
    
    # Generate hint for LLM about speakers
    hints = []
    if len(speakers_found) >= 2:
        spk_list = speakers_found[:2]
        # Identify who is likely the user
        user_candidate = None
        for s in spk_list:
            if s in ["我", "自己", "男", "男生", "求助者", "兄弟"]:
                user_candidate = s
                break
        if user_candidate:
            target_candidate = [s for s in spk_list if s != user_candidate][0]
            hints.append(f"【人物主体解析提示】：本对话检测到两位发言人，其中「{user_candidate}」为连麦求助兄弟，「{target_candidate}」为聊天对方。")
        else:
            hints.append(f"【人物主体解析提示】：本对话检测到两位发言人「{spk_list[0]}」和「{spk_list[1]}」。请判断哪一位是连麦求助兄弟，绝不可混淆角色。")
    elif len(speakers_found) == 1:
        hints.append(f"【人物主体解析提示】：检测到对话标注了发言人「{speakers_found[0]}」，请结合上下文分清求助兄弟与对方。")
    else:
        hints.append("【人物主体解析提示】：该记录未带标准发言人昵称，请根据每句话的语境（提问/解释/邀约 vs 敷衍/冷淡/索要）严格分清哪句话是求助兄弟说的，哪句话是对方说的！")
        
    return structured_text, "\n".join(hints)

# 正则匹配严格的金钱借贷与物质索要（严禁单字粗暴匹配导致非金钱场景误伤！）
RE_MONEY = re.compile(
    r"(?:借(?:\d+|点|些|我)?钱|转账|转我|给我转|转个?红包|发个?红包|发个转账|收红包|要钱|讨钱|借我|借你|还钱|欠钱|\b\d+\s*块钱?|\b\d+\s*元|买奶茶|买口红|买包包?|买礼物|要礼物|送我个|帮我付|代付|报销|充话费|提款机|atm|给点零花|要零花钱|彩礼)",
    re.IGNORECASE
)

def is_money_related(text):
    """Accurately verify if text involves genuine money requests or financial transactions"""
    if not text:
        return False
    return bool(RE_MONEY.search(str(text)))

def detect_chat_scenario(text):
    """Accurately classify chat scenario into: money, cold, pua, fishing, ex, blind_date, general"""
    t = str(text).lower() if text else ""
    if is_money_related(t):
        return "money"
    
    # 1. 冷淡敷衍 / 轮回消息
    if re.search(r"(?:(?:^|[\s，。！？、])(?:哦|嗯|呵|呵呵|随便|在忙|睡了|晚安|再说吧|改天吧|行吧|拉倒|没干嘛|不想去|累了)(?:$|[\s，。！？、])|轮回|已读不回|半天不回|不理我|不回消息|单字怪|字这么少|几个字|隔几小时)", t):
        return "cold"
    
    # 2. 吵架甩锅 / PUA打压
    if re.search(r"(?:你要这么想|我没办法|你变了|都是你的错|你根本不爱我|你根本不懂我|受不了就分|无理取闹|作|神经病|又怎么了|至于吗|自私|算我错行了吧|无语|烦不烦|渣男|借口)", t):
        return "pua"
    
    # 3. 暧昧养鱼 / 备胎
    if re.search(r"(?:备胎|海王|养鱼|忽冷忽热|画饼|哥哥妹妹|好朋友|只是朋友|不想谈恋爱|还没准备好|无聊才找我|撩完就跑)", t):
        return "fishing"
    
    # 4. 前任纠缠
    if re.search(r"(?:前任|前女友|前男友|复合|分手|旧情复燃|回头草|拉黑|删了|后悔分手)", t):
        return "ex"
        
    # 5. 相亲现实盘查
    if re.search(r"(?:相亲|彩礼|车房|全款|户口|收入|存款|门当户对|介绍人|红娘)", t):
        return "blind_date"
        
    return "general"

def generate_witty_title(report_data=None, chat_text=""):
    """Generate a witty, hilarious and razor-sharp summary title tailored to the exact emotional scenario"""
    text_corpus = ""
    if report_data:
        text_corpus += str(report_data.get("title", "")) + " "
        text_corpus += str(report_data.get("one_line_summary", "")) + " "
        text_corpus += str(report_data.get("tong_analysis", "")) + " "
    if chat_text:
        text_corpus += str(chat_text) + " "

    scenario = detect_chat_scenario(chat_text or text_corpus)
    if scenario == "money":
        if any(k in text_corpus.lower() for k in ["9块9", "9.9", "奶茶", "喝奶茶", "买奶茶"]):
            return "《9块9都要套路你？这哪是谈恋爱这是慈善白嫖！》"
        return "《叫声宝宝就当真？纯纯ATM怨种实录！》"
    elif scenario == "cold":
        return "《标点符号都在敷衍你，你还搁这儿疯狂脑补真爱？！》"
    elif scenario == "pua":
        return "《满嘴‘你要这么想我也没办法’？直接掀桌别惯着臭毛病！》"
    elif scenario == "fishing":
        return "《随口两句塑料鱼饵，真当自己是海王的正宫了？！》"
    elif scenario == "ex":
        return "《深夜发个‘在吗’就破防？回头草吃多了真当自己是羊啊？！》"
    elif scenario == "blind_date":
        return "《开局就是算盘声？这是双向奔赴还是上门扶贫？！》"
    else:
        return "《收起你卑微廉价的热情！把骨气挺起来再去谈感情！》"

def clean_report_title(raw_title, report_data=None, chat_text=""):
    """Ensure title is an interesting, witty, sharp summary title without mechanical '+' or formulaic prefixes"""
    if not raw_title:
        return generate_witty_title(report_data, chat_text)
    
    clean = str(raw_title).strip()
    clean = re.sub(r"^[《<【\[“\"\s]+|[》>】\]”\"\s]+$", "", clean).strip()
    
    # If the LLM still outputted the mechanical title format with '+' or '我的+称呼+姓名'
    if "+" in clean or re.match(r"^我的[男女同学室友发小朋友同事相亲前任债主]+(?:某某|\w+)?$", clean):
        return generate_witty_title(report_data, chat_text)
    
    if len(clean) < 4:
        return generate_witty_title(report_data, chat_text)
        
    return f"《{clean}》"

def extract_report_title(report_data=None, chat_text=""):
    """Backward compatibility alias pointing to clean_report_title"""
    raw = ""
    if report_data:
        raw = report_data.get("title", "") or report_data.get("analysis_title", "")
    return clean_report_title(raw, report_data, chat_text)

def clean_one_line_summary(text):
    """Strip all formulaic boilerplate prefixes (Claude说, 童锦程铁律, 祖师爷说, etc.) to keep summary direct and razor-sharp"""
    if not text:
        return ""
    s = text.strip()
    # 移除首尾括号及多余标点
    s = re.sub(r"^(\s*(\[.*?\]|【.*?】|\(.*?\)|（.*?）|[：:])\s*)+", "", s).strip()
    s = re.sub(r"^[《<【\[“\"\s]+|[》>】\]”\"\s]+$", "", s).strip()
    
    # 彻底剥离可能存在的开头套话前缀
    prefix_pattern = r"^(Claude说[：:,，]?|Claude[：:,，]|童锦程(?:核心|启发式)?铁律[：:,，]?|童锦程说[：:,，]?|祖师爷(?:说|铁律)[：:,，]?|总结[：:,，]?|核心结论[：:,，]?|结论[：:,，]?|决策建议[：:,，]?|我的建议是[：:,，]?)\s*"
    while True:
        new_s = re.sub(prefix_pattern, "", s, flags=re.IGNORECASE).strip()
        if new_s == s:
            break
        s = new_s
        
    # 移除句中残留的“童锦程铁律：”、“祖师爷铁律：”等生硬套话标签，转换为自然标点
    s = re.sub(r"[，,。.\s]*童锦程(?:核心|启发式)?铁律[：:]?\s*", "，", s)
    s = re.sub(r"[，,。.\s]*祖师爷(?:核心|启发式)?铁律[：:]?\s*", "，", s)
    s = re.sub(r"^[，,。.\s]+", "", s).strip()
    return s

def ensure_smart_summary(clean_summary, report_data=None, chat_text=""):
    """
    Ensure the one_line_summary is razor-sharp, context-aware and strictly PREVENTS false money decisions
    when there is no financial transaction involved.
    """
    corpus = ""
    if chat_text:
        corpus += str(chat_text) + " "
    elif report_data and report_data.get("chat_text"):
        corpus += str(report_data.get("chat_text")) + " "
        
    if report_data:
        corpus += str(report_data.get("title", "")) + " "
        corpus += str(report_data.get("tong_analysis", "")) + " "
        
    raw_chat = chat_text or (report_data.get("chat_text", "") if report_data else "")
    scenario = detect_chat_scenario(raw_chat or corpus or clean_summary)
    
    # 1. 若经过清洗后为空，根据真实识别场景给出专属怒吼决策
    if not clean_summary:
        if scenario == "money":
            return "这钱你敢转一分你就是纯纯大怨种！！人家叫声宝宝就把你魂勾走了？！给老子清醒一点！一分都别给！！"
        elif scenario == "cold":
            return "标点符号都懒得回你的人趁早拉黑！！人家轮回你都是施舍，你特么还搁这儿犯相思病呢？！删了！！"
        elif scenario == "pua":
            return "千万别掉进自证清白的陷阱！！对方甩锅你就直接砸回去，惯他这一身臭毛病干什么？！立刻反击！！"
        elif scenario == "fishing":
            return "忽冷忽热就是纯纯把你当备胎养鱼！！别给点甜头就摇尾巴，收起廉价热情，头也不回走人！！"
        elif scenario == "ex":
            return "前任深夜诈尸一律当鬼处理！！对方无聊寂寞拿你解闷，你还真当是破镜重圆？！直接拉黑！！"
        elif scenario == "blind_date":
            return "相亲是双向奔赴不是上门扶贫！！一上来就居高临下查户口的，直接冷笑退场不伺候！！"
        else:
            return "收起你卑微廉价的热情！任何让你患得患失的关系都是劣质负资产，把骨气挺起来！！"

    # 2. 关键防御：若聊天记录根本不涉及金钱，但大模型幻觉输出了“这钱不要给/这钱坚决不给/提款机”
    if scenario != "money" and not is_money_related(raw_chat):
        # 剥离误伤的金钱开头短语
        clean_summary = re.sub(r"^(这钱[你他妈敢一分都坚决不要别不能转给]+[。！!？?]*)+", "", clean_summary).strip()
        clean_summary = re.sub(r"^(对方纯粹把你当免费提款机做服从性测试[，。！!？?]*)+", "", clean_summary).strip()
        clean_summary = re.sub(r"^(掏钱换不来尊重[，。！!？?]*)+", "", clean_summary).strip()
        if not clean_summary or len(clean_summary) < 5 or any(w in clean_summary for w in ["这钱", "提款机", "ATM"]):
            return ensure_smart_summary("", report_data, raw_chat)

    # 3. 若确实涉及真实金钱往来，确保态度明确坚决
    if scenario == "money" or is_money_related(raw_chat):
        decision_keywords = ["不给", "别给", "不能给", "不用给", "不要给", "不转", "别转", "不要转", "可以给", "值得给", "该给", "不能转", "别借", "不要借", "不能借", "一分都别给", "大怨种"]
        if not any(kw in clean_summary for kw in decision_keywords):
            clean_summary = f"这钱坚决不给。{clean_summary}"
            
    return clean_summary

def generate_offline_report(chat_text):
    """Fallback high-quality report generator infused with Tong Jincheng's cognitive models across all scenarios"""
    scenario = detect_chat_scenario(chat_text)
    
    if scenario == "money":
        title = "《叫声宝宝就当真？纯纯ATM怨种实录！》"
        one_line = "这钱你敢转一分你就是纯纯大怨种！！人家叫声宝宝就把你魂勾走了？！给老子清醒一点！一分都别给！！"
        tong_analysis = (
            "卧槽兄弟！！你特么脑子进水了是不是？！啊？！\n"
            "对方随口叫你一声“宝宝”，你特么连以后孩子上哪个幼儿园都想好了？！人家那是喜欢你吗？！人家那是把你看成不用密码的自动取款机了！！\n"
            "你瞅瞅你那个没出息的样子！两句话没说完就张嘴找你要钱要奶茶，这种满大街都是的廉价小把戏，你还真以为是天上掉林妹妹了？！我特么在直播间喊过一万遍：真正喜欢你的人，连让你掏五块钱都心疼；拿你当猴耍的人，才会张嘴闭嘴买这买那做服从性测试！！\n"
            "这钱你要是敢转，下一步就是口红、鞋包、大额借款！人家一边喝着你买的奶茶，一边跟别人截图嘲笑你是个好忽悠的纯纯大怨种！！\n"
            "把手机给我狠狠扔一边！立刻！马上！去洗把冷水脸照照镜子！老子的直播你白看了？！钱只花在真正对的人身上，绝不给这种绿茶白嫖表演买单！给老子把头抬起来，骨气拿出来，听见没有？！"
        )
        replies = [
            {
                "title": "方案一：降维打击·直接掀桌",
                "text": "想喝奶茶自己手机点，少特么拿我当美团自动扣费，老子不伺候！"
            },
            {
                "title": "方案二：冷峻立规·霸气反抽",
                "text": "聊两句就张嘴要钱，怎么，我脸上写着‘慈善冤大头’几个字吗？！"
            },
            {
                "title": "方案三：绝杀反抽·彻底拉黑",
                "text": "把你的小算盘收一收，有多远滚多远，别来沾边！"
            }
        ]
    elif scenario == "cold":
        title = "《标点符号都在敷衍你，你还搁这儿疯狂脑补真爱？！》"
        one_line = "标点符号都懒得回你的人趁早拉黑！！人家轮回你都是施舍，你特么还搁这儿犯相思病呢？！删了！！"
        tong_analysis = (
            "醒醒吧祖宗！！你特么到底在自我感动个什么劲啊？！！\n"
            "对方回你个“哦”、“嗯”、“随便”，你在这头拿着手机急得团团转，反反复复看聊天记录，还以为是自己哪句话得罪了仙女？！你这不是深情，你特么这是纯纯犯贱啊！！\n"
            "我早就说过了：如果你不确定她喜不喜欢你，那她百分之百就是不喜欢你！喜欢你的人洗澡都能擦干手回你消息，不喜欢你的人洗澡洗了一年还在浴室里呢！！对方享受的无非就是你随叫随到、患得患失的免费情绪小丑供给！！\n"
            "你越是卑躬屈膝、发长篇大论去讨好，你在人家眼里就越是一文不值的廉价抹布！！\n"
            "立刻把对话框删了！把手机扔一边！去搞钱！去健身！去把属于你男人的尊严捡起来！！你若盛开蝴蝶自来，在烂泥坑里当舔狗换不来任何尊重，只配换来一句‘真烦’！！听懂了没有？！"
        )
        replies = [
            {
                "title": "方案一：降维打击·直接掀桌",
                "text": "字打得这么省，留着去考文言文呢？没话说不用勉强硬回！"
            },
            {
                "title": "方案二：冷峻立规·霸气反抽",
                "text": "看你回个消息挺费劲的，不用演了，互删各自安好吧！"
            },
            {
                "title": "方案三：绝杀反抽·彻底拉黑",
                "text": "（直接已读不回拉黑删除！不给这种冷漠廉价的施舍一秒眼神！）"
            }
        ]
    elif scenario == "pua":
        title = "《满嘴‘你要这么想我也没办法’？直接掀桌别惯着臭毛病！》"
        one_line = "千万别掉进自证清白的陷阱！！对方甩锅你就直接砸回去，惯他这一身臭毛病干什么？！立刻反击！！"
        tong_analysis = (
            "卧槽兄弟！！你特么给我挺直腰杆站起来！！\n"
            "对方一张嘴就是‘你要这么想我也没办法’、‘你变了’，把所有的锅全甩到你头上，你居然还搁这儿反思自己哪里做得不够好？！你特么脑子被驴踢了是不是？！\n"
            "这就是最典型、最下三滥的PUA精神勒索！对方明明心虚，却故意把态度搞得高高在上，就是为了让你产生负罪感，逼你低头认错割地赔款！你在那儿拼命自证清白，解释得口干舌燥，对方在心里冷笑把你拿捏得死死的！！\n"
            "在感情里永远不要掉进别人的自证陷阱！他甩锅，你就直接把锅掀翻砸他脸上！老子问心无愧，凭什么受你这窝囊气？！\n"
            "收起你那副委曲求全的怂样！直接把态度亮出来：想处就好好说话，不想处现在就滚蛋！惯他这一身臭毛病，你以后连呼吸都是错的！听见没有？！"
        )
        replies = [
            {
                "title": "方案一：降维打击·直接掀桌",
                "text": "少跟我来“你要这么想我也没办法”这套，你那点小把戏我看得一清二楚，别在这儿倒打一耙！"
            },
            {
                "title": "方案二：冷峻立规·霸气反抽",
                "text": "有事说事，别动不动甩锅搞冷暴力，老子不吃你这一套！"
            },
            {
                "title": "方案三：绝杀反抽·彻底拉黑",
                "text": "既然觉得都是我的错，那正好，以后我的世界跟你没半毛钱关系，拉黑保平安！"
            }
        ]
    elif scenario == "fishing":
        title = "《随口两句塑料鱼饵，真当自己是海王的正宫了？！》"
        one_line = "忽冷忽热就是纯纯把你当备胎养鱼！！别给点甜头就摇尾巴，收起廉价热情，头也不回走人！！"
        tong_analysis = (
            "兄弟，你给我清醒一点！！别在这儿当池塘里的小金鱼了！！\n"
            "对方无聊的时候过来撩你两句，画个大饼叫你两声好哥哥，等你陷进去了又对你爱搭不理！你特么还真以为遇到真命天女了？！人家那是池塘里鱼太多，随手撒一把劣质鱼饲料看看哪条鱼最容易上钩！！\n"
            "真正喜欢你的人，绝不会让你在患得患失里备受折磨！不主动、不拒绝、不负责，纯粹就是白嫖你的情绪价值和时间成本！！你随叫随到，不仅换不来偏爱，只会沦为随时被丢弃的备胎小丑！！\n"
            "把你那廉价的热情给我彻底收起来！把手机锁屏，把精力用在提升自己的身材、能力和钱包上！\n"
            "记住老子一句话：做岸上的执竿人，别做池子里等施舍的鱼！立刻抽身，头也不回地走！"
        )
        replies = [
            {
                "title": "方案一：降维打击·直接掀桌",
                "text": "鱼塘那么大，您慢慢游，老子岸上走，不奉陪了！"
            },
            {
                "title": "方案二：冷峻立规·霸气反抽",
                "text": "别拿那种忽冷忽热的套路试探我，想找备胎出门左转，别在我这儿演戏！"
            },
            {
                "title": "方案三：绝杀反抽·彻底拉黑",
                "text": "你的剧本太廉价，我不接戏，互不打扰吧！"
            }
        ]
    elif scenario == "ex":
        title = "《深夜发个‘在吗’就破防？回头草吃多了真当自己是羊啊？！》"
        one_line = "前任深夜诈尸一律当鬼处理！！对方无聊寂寞拿你解闷，你还真当是破镜重圆？！直接拉黑！！"
        tong_analysis = (
            "兄弟，你是不是闲得慌啊？！啊？！\n"
            "前任深夜发一句“在吗”或者“最近好吗”，你心跳就加速到一百八，恨不得马上回三千字长文？！你特么忘了当初是怎么分手的了吗？！那些流过的泪、受过的伤，全被你当成下酒菜给咽回去了？！\n"
            "我早就说过：得不到的就不要，回头草吃多了真把自己当喜羊羊了？！前任找你根本不是余情未了，纯粹是她在外面混得不顺心、或者深夜寂寞了，找你这个随叫随到的旧充电宝充充电而已！！\n"
            "破镜重圆的结果，99%都是重蹈覆辙！当初因为什么矛盾分开，以后依然会因为同样的事情再捅你一刀！！\n"
            "直接把对话框删了！把好友拉黑！合格的前任就应该像死了一样安静！把目光看向未来，向前走，别回头！听懂了没有？！"
        )
        replies = [
            {
                "title": "方案一：降维打击·直接掀桌",
                "text": "过去的事情已经翻篇了，别在深夜诈尸，各自安好互不打扰！"
            },
            {
                "title": "方案二：冷峻立规·霸气反抽",
                "text": "既然当初选择分开，就别再演念念不忘的戏码，挺没意思的！"
            },
            {
                "title": "方案三：绝杀反抽·彻底拉黑",
                "text": "删了吧，合格的前任应该像死了一样安静！"
            }
        ]
    else:
        title = "《收起你卑微廉价的热情！把骨气挺起来再去谈感情！》"
        one_line = "任何让你患得患失的关系都是劣质负资产！！把精力收回来搞钱搞事业，自己立住了蝴蝶自来！！"
        tong_analysis = (
            "兄弟，把你的脊梁骨给我挺直了！！别在这儿像个侦探一样逐字逐句分析那些绿茶废话了！！\n"
            "社交的核心永远是吸引力，从来不是低声下气的迎合！！对方随手扔个塑料鱼饵试探你两句，你就恨不得把全部家底和心思掏出来自证清白，你底牌全漏光了人家凭什么高看你一眼？！\n"
            "越缺什么的人越喜欢炫耀什么，虚张声势的试探背后全是赤裸裸的不安和算计！你认真较劲你就彻底落入圈套，你唯唯诺诺迎合就会被人家当提线木偶随意摆布！！\n"
            "收起所有廉价的热情！把精力收回自己身上，专注搞你的事业和身材！当你站得足够高、手里筹码足够多的时候，这些无聊的算计在你眼里全都是跳梁小丑的拙劣表演！！给我硬气起来！！"
        )
        replies = [
            {
                "title": "方案一：降维打击·直接掀桌",
                "text": "说话不用这么拐弯抹角，有话直说，老子时间很贵！"
            },
            {
                "title": "方案二：冷峻立规·霸气反抽",
                "text": "你想怎么玩是你的自由，但别把别人当傻子，我不陪你演剧本！"
            },
            {
                "title": "方案三：绝杀反抽·彻底拉黑",
                "text": "没空，至于哪天有空，下辈子吧！"
            }
        ]

    # Infer protagonist roles for offline report
    user_side = "连麦求助兄弟（我方立场）"
    target_side = "聊天对象（对方）"
    
    if scenario == "money":
        rel_state = "真实金钱索取局 · 对方借机索取利益，拒绝当ATM提款机"
    elif scenario == "cold":
        rel_state = "冷淡敷衍局 · 对方爱搭不理，我方单向患得患失"
    elif scenario == "pua":
        rel_state = "甩锅责问局 · 对方倒打一耙，我方陷入自证陷阱"
    elif scenario == "fishing":
        rel_state = "暧昧养鱼局 · 对方忽冷忽热，我方沦为备胎"
    elif scenario == "ex":
        rel_state = "前任纠缠局 · 前任深夜试探，好马不吃回头草"
    elif scenario == "blind_date":
        rel_state = "相亲盘查局 · 现实条件审视与博弈"
    else:
        rel_state = "常规社交局 · 吸引力博弈与框架树立"
        
    protagonists = {
        "user_side": user_side,
        "target_side": target_side,
        "relationship_state": rel_state
    }

    return {
        "protagonists": protagonists,
        "title": title,
        "one_line_summary": one_line,
        "tong_analysis": tong_analysis,
        "reply_options": replies,
        "chat_text": chat_text
    }

def normalize_api_config(cfg):
    """Normalize and autocorrect provider, base_url, and model for popular Chinese providers like Zhipu"""
    provider = cfg.get("provider", "gemini").lower()
    base_url = cfg.get("base_url", "").strip().rstrip("/")
    model = cfg.get("model", "").strip()

    # Autocorrect Zhipu / BigModel
    if "bigmodel.cn" in base_url or "glm" in model.lower():
        provider = "openai"
        if not base_url or "console" in base_url or not base_url.endswith("/api/paas/v4"):
            base_url = "https://open.bigmodel.cn/api/paas/v4"
        
        # Normalize model names
        if model.lower() in ["glm-5.3", "glm-5", "glm5", "glm", ""]:
            model = "glm-4-flash"
    
    # Autocorrect DeepSeek
    elif "deepseek.com" in base_url or "deepseek" in model.lower():
        provider = "openai"
        if not base_url or "api.deepseek.com" not in base_url:
            base_url = "https://api.deepseek.com/v1"
        if not model:
            model = "deepseek-chat"

    # Autocorrect Kimi / Moonshot AI
    elif "moonshot" in base_url or "kimi" in model.lower() or "moonshot" in model.lower():
        provider = "openai"
        if not base_url or "api.moonshot.cn" not in base_url:
            base_url = "https://api.moonshot.cn/v1"
        if not model:
            model = "moonshot-v1-8k"
            
    # Default fallbacks
    if not base_url:
        if "gemini" in provider:
            base_url = "https://generativelanguage.googleapis.com/v1beta"
        else:
            base_url = "https://api.openai.com/v1"
            
    if not model:
        if "gemini" in provider:
            model = "gemini-2.5-flash"
        else:
            model = "gpt-4o-mini"
            
    return provider, base_url, model


def extract_json_from_text(text, chat_text=""):
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        raw_json = match.group(1).strip()
    else:
        raw_json = text

    try:
        data = json.loads(raw_json)
        data["chat_text"] = chat_text
        data["title"] = extract_report_title(data, chat_text)
        data["one_line_summary"] = clean_one_line_summary(data.get("one_line_summary", ""))
        data["one_line_summary"] = ensure_smart_summary(data["one_line_summary"], data, chat_text)
        if "tong_analysis" not in data:
            data["tong_analysis"] = data.get("analysis", "")
        if "protagonists" not in data or not isinstance(data["protagonists"], dict):
            scenario = detect_chat_scenario(chat_text)
            data["protagonists"] = {
                "user_side": "连麦求助兄弟（我方立场）",
                "target_side": "聊天目标对象（对方）",
                "relationship_state": "两性吸引力与情感博弈局"
            }
        return data
    except Exception:
        first_brace = raw_json.find('{')
        last_brace = raw_json.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            try:
                candidate = raw_json[first_brace:last_brace+1]
                data = json.loads(candidate)
                data["chat_text"] = chat_text
                data["title"] = extract_report_title(data, chat_text)
                data["one_line_summary"] = clean_one_line_summary(data.get("one_line_summary", ""))
                data["one_line_summary"] = ensure_smart_summary(data["one_line_summary"], data, chat_text)
                if "tong_analysis" not in data:
                    data["tong_analysis"] = data.get("analysis", "")
                if "protagonists" not in data or not isinstance(data["protagonists"], dict):
                    data["protagonists"] = {
                        "user_side": "连麦求助兄弟（我方立场）",
                        "target_side": "聊天目标对象（对方）",
                        "relationship_state": "两性吸引力与情感博弈局"
                    }
                return data
            except Exception:
                pass
    
    return generate_offline_report(chat_text or text)

def analyze_chat_transcript(chat_text):
    """Deep analysis using Tong Jincheng's cognitive models from hotcoffeeshake/tong-jincheng-skill"""
    cfg = load_config()
    api_key = cfg.get("api_key", "").strip()
    
    # 智能预处理原始文本：清洗微信时间戳、合并连续发言、提炼说话人线索
    structured_chat, speaker_hints = preprocess_chat_transcript(chat_text)
    effective_chat = structured_chat if structured_chat else chat_text
    
    if not api_key:
        print("[TongJincheng Mentor] No API key configured. Using offline intelligence engine.")
        return generate_offline_report(effective_chat)
    
    provider, base_url, model = normalize_api_config(cfg)
    user_instruction = (
        f"【待分析的真实聊天记录】：\n```\n{effective_chat}\n```\n\n"
        f"{speaker_hints}\n\n"
        "【极其重要的执行指令】：\n"
        "1. 人物主体与对话脉络（重中之重！）：必须先严格理清谁是求助兄弟（我方），谁是聊天对方，梳理人物对话脉络！在长文剖析中准确指明【对方说了什么】和【兄弟回了什么】，绝不可角色对调颠倒黑白！\n"
        "2. 智能场景识别（严禁无脑提钱！）：只有当对方明确向男方索取金钱、借钱、要转账或红包时，才下达金钱决策；若聊天属于冷淡敷衍、争吵甩锅PUA、暧昧养鱼、前任回头或日常邀约，绝对严禁出现‘这钱不要给’或‘提款机’！必须根据真实场景输出童锦程的怒吼破局决策！\n"
        "3. 角色立场：以祖师爷身份怒吼骂醒连麦求助兄弟，教他如何硬气反击对方！不要反过来把兄弟当成渣男骂！\n"
        "4. 标题title：必须是一个【有趣犀利、一针见血能精辟总结整篇报告的神级标题】（必须带《书名号》），严禁使用“我的+xxx”或带加号的机械格式！\n"
        "5. 语气风格：必须是【童锦程暴怒怒吼·拍桌子骂醒兄弟】的咆哮风格！大量使用感叹号（！、！！、？！），把嗓门拉到最大，像在直播间抓着兄弟衣领撕心裂肺地吼他骂醒他！\n"
        "6. 绝对严禁任何平淡、温柔、官方学术腔、居委会说教腔！直接输出纯 JSON："
    )
    
    try:
        if "gemini" in provider:
            url = f"{base_url}/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"{TONG_JINCHENG_SYSTEM_PROMPT}\n\n{user_instruction}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.8
                }
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text_out = result["candidates"][0]["content"]["parts"][0]["text"]
                return extract_json_from_text(text_out, effective_chat)
        else:
            url = f"{base_url}/chat/completions"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": TONG_JINCHENG_SYSTEM_PROMPT},
                    {"role": "user", "content": user_instruction}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.8
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    text_out = result["choices"][0]["message"]["content"]
                    return extract_json_from_text(text_out, effective_chat)
            except urllib.error.HTTPError as he:
                if he.code == 400 and "response_format" in payload:
                    del payload["response_format"]
                    req_retry = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}"
                        },
                        method="POST"
                    )
                    with urllib.request.urlopen(req_retry, timeout=60) as resp_retry:
                        result_retry = json.loads(resp_retry.read().decode("utf-8"))
                        text_out_retry = result_retry["choices"][0]["message"]["content"]
                        return extract_json_from_text(text_out_retry, effective_chat)
                raise
    except Exception as e:
        print(f"[TongJincheng Mentor] Online API call failed: {e}. Falling back to offline engine.")
        res = generate_offline_report(effective_chat)
        return res

def analyze_chat(chat_text):
    """Compatibility wrapper for analyze_chat_transcript"""
    return analyze_chat_transcript(chat_text)

def ask_tong_freely(user_question):
    """Answer any free-form question in Tong Jincheng's authentic voice from hotcoffeeshake/tong-jincheng-skill"""
    cfg = load_config()
    api_key = cfg.get("api_key", "").strip()
    
    system_prompt = """你现在是童锦程（江南第一深情 / 景辰），已深度接入开源 Skill【hotcoffeeshake/tong-jincheng-skill】。
你的核心沟通风格与认知模型：
1. 语言口语化、直爽、坦诚、人间清醒，称呼用户为“兄弟”或“兄弟们”。快速给结论，从不绕弯子，用鲜活生活比喻代替空洞理论。
2. 5大核心理念：
   - 吸引力原则：没有人会因为你喜欢他而喜欢你，别人只会因为你吸引他而喜欢你；绝不当单向付出的舔狗。
   - 真诚是最高级的套路：真诚不一定会得到爱，但不真诚一定会失去爱；喜欢你的人吃你所有套路，不喜欢你的人秘籍毫无意义。
   - 决策启发式：如果你不确定她喜不喜欢你，那她就是不喜欢你；得不到的就放手，别犯贱。
   - 人性不可考验：不要突袭、不要考验人性；钱要花在真正的人身上，不花在萍水之交的表演上。
   - 遇到瓶颈去读书健身，千万别买醉；好好工作生活，当你变优秀了，你若盛开蝴蝶自来。
3. 篇幅控制在100-200字，结尾有力，给兄弟清醒向上的力量。"""

    if not api_key:
        q = user_question
        if "彩礼" in q or "结婚" in q or "聘礼" in q:
            return "兄弟，我说实话：结婚是两个人过一辈子，钱必须花在真正对的人身上。如果对方真心跟你奔日子，怎么谈都能找到体面的台阶；但如果开门见山就是一笔买卖，甚至用彩礼测试你所谓的诚意，那人性根本经不起考验。没有双向奔赴的感情，一分钱都别硬撑，先把自己的人生活明白了！"
        elif "前任" in q or "分手" in q or "复合" in q or "挽回" in q:
            return "兄弟，听我一句劝：我这人就这样，得不到的我就不要，绝不跟别人一样越得不到越想得到，犯贱！90%爱情的苦就来自于自我感动。人都不会怀念一个人好，人只会怀念一个人对你好。对方真想回头不用你求，不想回头你做什么都多余。把手机放下，去健身去搞事业，自己立住了比什么都强！"
        elif "赚钱" in q or "创业" in q or "代码" in q or "工作" in q or "迷茫" in q or "瓶颈" in q:
            return "兄弟，遇到瓶颈记住一条铁律：去读书、去健身，永远不要喝酒买醉！你今天喝得稀巴烂醉，明天该有的烦恼还在。成功前后是两个世界，当你什么都不是的时候，没人会在意你的自尊；好好把不好走的路熬过来，把硬实力打磨出来，以后的路才会越走越宽！"
        elif "舔狗" in q or "喜欢" in q or "追" in q or "聊天" in q:
            return "兄弟，永远记住：没有人会因为你喜欢他而喜欢你，别人只会因为你吸引他而喜欢你！如果你不确定她喜不喜欢你，那她就是不喜欢你，千万别在模糊信号里疯狂自我感动。真诚才是最高级的套路，少研究那些花里胡哨的技巧，专注做好你自己，你若盛开蝴蝶自来！"
        else:
            return "兄弟，做自己爱做的事情，不要太在乎世俗的眼光。面对任何关系都别卑微，得不到的就放手，属于你的自然会来。把身体练好，把工作干好，心态放稳，天塌不下来！"

    provider, base_url, model = normalize_api_config(cfg)
    
    try:
        if "gemini" in provider:
            url = f"{base_url}/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{system_prompt}\n\n用户问：{user_question}"}]
                    }
                ]
            }
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res["candidates"][0]["content"]["parts"][0]["text"].strip()
        else:
            url = f"{base_url}/chat/completions"
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_question}
                ]
            }
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=40) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return res["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Free chat API failed: {e}")
        return "兄弟，网络稍微卡顿了一下。记住：心态放稳，把专注力收回自己身上，随时找我聊！"


def synthesize_tong_voice(text, api_key=None, reference_id=None, output_path=None):
    """
    Synthesize speech using Fish Audio with Tong Jincheng's voice model.
    """
    cfg = load_config()
    key = (api_key or cfg.get("fish_api_key") or "").strip()
    ref = (reference_id or cfg.get("fish_reference_id") or "93d4dc1cbd6f4d55aee5ca54c0f9c6bb").strip()
    
    if not key or not ref or not text:
        return None
        
    # Clean text for natural sounding speech
    clean_text = re.sub(r"[#*_~`]", "", text).strip()
    clean_text = re.sub(r"【.*?】", "", clean_text).strip()
    clean_text = re.sub(r"\[.*?\]", "", clean_text).strip()
    clean_text = re.sub(r"\(.*?\)", "", clean_text).strip()
    clean_text = re.sub(r"（.*?）", "", clean_text).strip()
    # Limit max characters to keep synthesis fast & punchy (max ~150 chars)
    if len(clean_text) > 160:
        clean_text = clean_text[:160] + "..."
    if not clean_text:
        return None

    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "model": "s2.1-pro-free"
    }
    payload = {
        "text": clean_text,
        "reference_id": ref,
        "format": "mp3"
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            audio_bytes = resp.read()
            if not output_path:
                cache_dir = os.path.join(get_app_dir(), "audio_cache")
                os.makedirs(cache_dir, exist_ok=True)
                output_path = os.path.join(cache_dir, f"voice_{int(datetime.datetime.now().timestamp() * 1000)}.mp3")
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            print(f"[Fish Audio] Generated {len(audio_bytes)} bytes audio: {output_path}")
            return output_path
    except Exception as e:
        print(f"[Fish Audio] Synthesis error: {e}")
        return None

