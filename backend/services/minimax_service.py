import requests
import json
import re

MINIMAX_API_BASE = "https://api.minimax.chat/v1"
THINK_START_TAG = "<think>"
THINK_END_TAG = "</think>"
TOOL_CALLS_TAG = "<｜tool▁calls｜>"


def ensure_no_think_instruction(system_prompt: str) -> str:
    guard = "禁止输出任何思考过程、<think>标签、工具调用标签，不要展示深度思考过程。"
    if guard in system_prompt:
        return system_prompt
    return f"{system_prompt} {guard}"

def call_minimax(prompt, system_prompt="你是一个专业的创意写作助手，擅长撰写各类灵感报告和文章。", model="MiniMax-M2", api_key=None):
    """调用MiniMax Coding Plan API生成内容"""
    url = f"{MINIMAX_API_BASE}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    safe_system_prompt = ensure_no_think_instruction(system_prompt)
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": safe_system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        print(f"API响应状态码: {response.status_code}")
        
        result = response.json()
        print(f"API响应内容: {json.dumps(result, ensure_ascii=False)[:500]}")
        
        if "choices" in result and result["choices"]:
            content = result["choices"][0].get("message", {}).get("content")
            if content:
                content = strip_think_content(content)
                return content
        
        if "error" in result:
            print(f"API错误: {result['error']}")
        
        return None
    except Exception as e:
        print(f"MiniMax API调用失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def call_minimax_stream(prompt, system_prompt="你是一个专业的创意写作助手，擅长撰写各类灵感报告和文章。", model="MiniMax-M2", api_key=None):
    """调用MiniMax Coding Plan API流式生成内容"""
    url = f"{MINIMAX_API_BASE}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    safe_system_prompt = ensure_no_think_instruction(system_prompt)
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": safe_system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "stream": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=120, stream=True)
        response.raise_for_status()
        
        stream_state = {"buffer": "", "in_think": False, "stopped": False}

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str.strip() == '[DONE]':
                        break
                    try:
                        data_json = json.loads(data_str)
                        if "choices" in data_json and data_json["choices"]:
                            delta = data_json["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                cleaned = clean_stream_content_chunk(content, stream_state)
                                if cleaned:
                                    yield cleaned
                    except json.JSONDecodeError:
                        continue

        tail = flush_stream_content(stream_state)
        if tail:
            yield tail
    except Exception as e:
        print(f"MiniMax API流式调用失败: {e}")
        import traceback
        traceback.print_exc()

def strip_think_content(content: str) -> str:
    """移除AI思考过程内容，只保留最终回复"""
    content = re.sub(r"<\s*think\b[^>]*>.*?<\s*/\s*think\s*>", "", content, flags=re.S | re.I)
    content = re.sub(r"<\s*think\b[^>]*>.*$", "", content, flags=re.S | re.I)
    content = re.sub(r"```(?:thinking|think)[\s\S]*?```", "", content, flags=re.I)
    if TOOL_CALLS_TAG in content:
        content = content.split(TOOL_CALLS_TAG, 1)[0]
    content = content.replace(THINK_START_TAG, "").replace(THINK_END_TAG, "")
    return content.strip("\r\n")


def clean_stream_content_chunk(chunk: str, state: dict) -> str:
    """Stateful filtering for streamed content; strips think/tool segments even across chunk boundaries."""
    if state.get("stopped"):
        return ""

    state["buffer"] = state.get("buffer", "") + chunk
    out = []
    tail_keep = max(len(THINK_START_TAG), len(TOOL_CALLS_TAG)) - 1

    while True:
        if state.get("in_think"):
            end_idx = state["buffer"].find(THINK_END_TAG)
            if end_idx == -1:
                if len(state["buffer"]) > len(THINK_END_TAG):
                    state["buffer"] = state["buffer"][-(len(THINK_END_TAG) - 1):]
                return "".join(out)
            state["buffer"] = state["buffer"][end_idx + len(THINK_END_TAG):]
            state["in_think"] = False
            continue

        tool_idx = state["buffer"].find(TOOL_CALLS_TAG)
        think_idx = state["buffer"].find(THINK_START_TAG)
        markers = [idx for idx in (tool_idx, think_idx) if idx != -1]

        if not markers:
            if len(state["buffer"]) > tail_keep:
                out.append(state["buffer"][:-tail_keep])
                state["buffer"] = state["buffer"][-tail_keep:]
            return "".join(out)

        next_marker = min(markers)
        if next_marker > 0:
            out.append(state["buffer"][:next_marker])
            state["buffer"] = state["buffer"][next_marker:]

        if state["buffer"].startswith(TOOL_CALLS_TAG):
            state["stopped"] = True
            state["buffer"] = ""
            return "".join(out)

        if state["buffer"].startswith(THINK_START_TAG):
            state["in_think"] = True
            state["buffer"] = state["buffer"][len(THINK_START_TAG):]
            continue


def flush_stream_content(state: dict) -> str:
    if state.get("stopped") or state.get("in_think"):
        return ""
    buffer = state.get("buffer", "")
    state["buffer"] = ""
    return strip_think_content(buffer)

def generate_outline_with_minimax(title: str, paper_type: str, direction: str, major: str, keywords: list, word_count: int = 10000, custom_prompt: str = "", api_key=None) -> list:
    """使用MiniMax生成文稿大纲"""
    
    paper_type_text = {
        "graduation": "毕业报告",
        "course": "课程报告", 
        "proposal": "开题报告",
        "review": "文献综述"
    }.get(paper_type, "文稿")
    
    direction_templates = {
        "finance": {
            "name": "财务管理",
            "chapters": [
                {
                    "id": "ch1",
                    "title": "第1章 绪论",
                    "sections": [
                        {"id": "ch1-1", "title": "1.1 研究背景", "content": "", "word_count": 0},
                        {"id": "ch1-2", "title": "1.2 研究目的与意义", "content": "", "word_count": 0},
                        {"id": "ch1-3", "title": "1.3 研究问题与假设", "content": "", "word_count": 0},
                        {"id": "ch1-4", "title": "1.4 研究框架与方法", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch2",
                    "title": "第2章 文献综述",
                    "sections": [
                        {"id": "ch2-1", "title": "2.1 财务管理相关理论回顾", "content": "", "word_count": 0},
                        {"id": "ch2-2", "title": "2.2 财务分析方法的演变", "content": "", "word_count": 0},
                        {"id": "ch2-3", "title": "2.3 国内外研究现状与不足", "content": "", "word_count": 0},
                        {"id": "ch2-4", "title": "2.4 研究空白及本文贡献", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch3",
                    "title": "第3章 研究方法",
                    "sections": [
                        {"id": "ch3-1", "title": "3.1 研究设计与数据来源", "content": "", "word_count": 0},
                        {"id": "ch3-2", "title": "3.2 财务数据的采集与分析方法", "content": "", "word_count": 0},
                        {"id": "ch3-3", "title": "3.3 实证分析模型的建立", "content": "", "word_count": 0},
                        {"id": "ch3-4", "title": "3.4 研究假设的验证", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch4",
                    "title": "第4章 财务分析与企业绩效",
                    "sections": [
                        {"id": "ch4-1", "title": "4.1 财务比率分析与财务状况评估", "content": "", "word_count": 0},
                        {"id": "ch4-2", "title": "4.2 盈利能力分析", "content": "", "word_count": 0},
                        {"id": "ch4-3", "title": "4.3 偿债能力与流动性分析", "content": "", "word_count": 0},
                        {"id": "ch4-4", "title": "4.4 企业绩效与财务指标的关系", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch5",
                    "title": "第5章 资本结构与盈利能力分析",
                    "sections": [
                        {"id": "ch5-1", "title": "5.1 资本结构的理论与应用", "content": "", "word_count": 0},
                        {"id": "ch5-2", "title": "5.2 资本结构与盈利能力的实证分析", "content": "", "word_count": 0},
                        {"id": "ch5-3", "title": "5.3 财务杠杆效应的分析", "content": "", "word_count": 0},
                        {"id": "ch5-4", "title": "5.4 不同资本结构对公司盈利的影响", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch6",
                    "title": "第6章 财务风险管理",
                    "sections": [
                        {"id": "ch6-1", "title": "6.1 财务风险的类型与特征", "content": "", "word_count": 0},
                        {"id": "ch6-2", "title": "6.2 风险管理理论与模型", "content": "", "word_count": 0},
                        {"id": "ch6-3", "title": "6.3 企业财务风险识别与评估", "content": "", "word_count": 0},
                        {"id": "ch6-4", "title": "6.4 财务风险控制措施", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch7",
                    "title": "第7章 实证研究：案例分析",
                    "sections": [
                        {"id": "ch7-1", "title": "7.1 研究对象与案例选择", "content": "", "word_count": 0},
                        {"id": "ch7-2", "title": "7.2 数据收集与处理", "content": "", "word_count": 0},
                        {"id": "ch7-3", "title": "7.3 实证结果分析", "content": "", "word_count": 0},
                        {"id": "ch7-4", "title": "7.4 案例分析结果的讨论", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch8",
                    "title": "第8章 结论与建议",
                    "sections": [
                        {"id": "ch8-1", "title": "8.1 研究主要结论", "content": "", "word_count": 0},
                        {"id": "ch8-2", "title": "8.2 研究的理论与实践意义", "content": "", "word_count": 0},
                        {"id": "ch8-3", "title": "8.3 对财务管理的建议", "content": "", "word_count": 0},
                        {"id": "ch8-4", "title": "8.4 研究局限性与未来研究方向", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch9",
                    "title": "参考文献",
                    "sections": []
                },
                {
                    "id": "ch10",
                    "title": "附录",
                    "sections": [
                        {"id": "ch10-1", "title": "附录A 调查问卷", "content": "", "word_count": 0},
                        {"id": "ch10-2", "title": "附录B 相关数据表", "content": "", "word_count": 0}
                    ]
                }
            ]
        },
        "business": {
            "name": "工商管理",
            "chapters": [
                {
                    "id": "ch1",
                    "title": "第1章 绪论",
                    "sections": [
                        {"id": "ch1-1", "title": "1.1 研究背景与动机", "content": "", "word_count": 0},
                        {"id": "ch1-2", "title": "1.2 研究问题与目标", "content": "", "word_count": 0},
                        {"id": "ch1-3", "title": "1.3 研究的创新点与意义", "content": "", "word_count": 0},
                        {"id": "ch1-4", "title": "1.4 文稿结构安排", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch2",
                    "title": "第2章 文献综述",
                    "sections": [
                        {"id": "ch2-1", "title": "2.1 战略管理的理论与模型", "content": "", "word_count": 0},
                        {"id": "ch2-2", "title": "2.2 市场竞争与竞争战略", "content": "", "word_count": 0},
                        {"id": "ch2-3", "title": "2.3 组织行为与领导力研究", "content": "", "word_count": 0},
                        {"id": "ch2-4", "title": "2.4 研究空白与本文贡献", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch3",
                    "title": "第3章 研究方法",
                    "sections": [
                        {"id": "ch3-1", "title": "3.1 定性与定量研究方法", "content": "", "word_count": 0},
                        {"id": "ch3-2", "title": "3.2 数据来源与分析工具", "content": "", "word_count": 0},
                        {"id": "ch3-3", "title": "3.3 研究假设与模型构建", "content": "", "word_count": 0},
                        {"id": "ch3-4", "title": "3.4 研究样本与调查问卷设计", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch4",
                    "title": "第4章 企业战略与市场竞争分析",
                    "sections": [
                        {"id": "ch4-1", "title": "4.1 企业战略概述与发展趋势", "content": "", "word_count": 0},
                        {"id": "ch4-2", "title": "4.2 市场竞争理论与实证分析", "content": "", "word_count": 0},
                        {"id": "ch4-3", "title": "4.3 竞争战略选择与实施", "content": "", "word_count": 0},
                        {"id": "ch4-4", "title": "4.4 案例分析：成功企业的竞争战略", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch5",
                    "title": "第5章 组织行为与领导力",
                    "sections": [
                        {"id": "ch5-1", "title": "5.1 组织行为学理论与应用", "content": "", "word_count": 0},
                        {"id": "ch5-2", "title": "5.2 领导力模型与实践", "content": "", "word_count": 0},
                        {"id": "ch5-3", "title": "5.3 领导风格对组织效能的影响", "content": "", "word_count": 0},
                        {"id": "ch5-4", "title": "5.4 企业组织行为案例分析", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch6",
                    "title": "第6章 企业创新与可持续发展",
                    "sections": [
                        {"id": "ch6-1", "title": "6.1 企业创新的类型与模式", "content": "", "word_count": 0},
                        {"id": "ch6-2", "title": "6.2 创新对企业竞争力的影响", "content": "", "word_count": 0},
                        {"id": "ch6-3", "title": "6.3 可持续发展与企业战略的结合", "content": "", "word_count": 0},
                        {"id": "ch6-4", "title": "6.4 实证分析：创新型企业的可持续发展", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch7",
                    "title": "第7章 实证研究",
                    "sections": [
                        {"id": "ch7-1", "title": "7.1 研究设计与数据来源", "content": "", "word_count": 0},
                        {"id": "ch7-2", "title": "7.2 样本特征与描述性统计", "content": "", "word_count": 0},
                        {"id": "ch7-3", "title": "7.3 实证结果与分析", "content": "", "word_count": 0},
                        {"id": "ch7-4", "title": "7.4 研究发现与讨论", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch8",
                    "title": "第8章 结论与建议",
                    "sections": [
                        {"id": "ch8-1", "title": "8.1 主要研究发现", "content": "", "word_count": 0},
                        {"id": "ch8-2", "title": "8.2 理论与实践意义", "content": "", "word_count": 0},
                        {"id": "ch8-3", "title": "8.3 对企业管理的建议", "content": "", "word_count": 0},
                        {"id": "ch8-4", "title": "8.4 研究的局限性与展望", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch9",
                    "title": "参考文献",
                    "sections": []
                },
                {
                    "id": "ch10",
                    "title": "附录",
                    "sections": [
                        {"id": "ch10-1", "title": "附录A 调查问卷", "content": "", "word_count": 0},
                        {"id": "ch10-2", "title": "附录B 访谈记录", "content": "", "word_count": 0}
                    ]
                }
            ]
        },
        "hr": {
            "name": "人力资源管理",
            "chapters": [
                {
                    "id": "ch1",
                    "title": "第1章 绪论",
                    "sections": [
                        {"id": "ch1-1", "title": "1.1 研究背景与意义", "content": "", "word_count": 0},
                        {"id": "ch1-2", "title": "1.2 研究问题与目标", "content": "", "word_count": 0},
                        {"id": "ch1-3", "title": "1.3 研究方法与框架", "content": "", "word_count": 0},
                        {"id": "ch1-4", "title": "1.4 文稿结构", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch2",
                    "title": "第2章 文献综述",
                    "sections": [
                        {"id": "ch2-1", "title": "2.1 人力资源管理的理论发展", "content": "", "word_count": 0},
                        {"id": "ch2-2", "title": "2.2 招聘与选拔的研究现状", "content": "", "word_count": 0},
                        {"id": "ch2-3", "title": "2.3 员工激励机制的理论", "content": "", "word_count": 0},
                        {"id": "ch2-4", "title": "2.4 绩效管理与考核方法", "content": "", "word_count": 0},
                        {"id": "ch2-5", "title": "2.5 研究空白与本文贡献", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch3",
                    "title": "第3章 研究方法",
                    "sections": [
                        {"id": "ch3-1", "title": "3.1 定性研究与定量研究方法", "content": "", "word_count": 0},
                        {"id": "ch3-2", "title": "3.2 数据收集与分析方法", "content": "", "word_count": 0},
                        {"id": "ch3-3", "title": "3.3 样本选择与问卷设计", "content": "", "word_count": 0},
                        {"id": "ch3-4", "title": "3.4 研究假设与模型构建", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch4",
                    "title": "第4章 人才招聘与选拔",
                    "sections": [
                        {"id": "ch4-1", "title": "4.1 招聘渠道与选拔流程", "content": "", "word_count": 0},
                        {"id": "ch4-2", "title": "4.2 选拔工具与技术的运用", "content": "", "word_count": 0},
                        {"id": "ch4-3", "title": "4.3 招聘效果的评估", "content": "", "word_count": 0},
                        {"id": "ch4-4", "title": "4.4 案例分析：招聘策略与选拔方法", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch5",
                    "title": "第5章 员工激励机制",
                    "sections": [
                        {"id": "ch5-1", "title": "5.1 激励理论与应用", "content": "", "word_count": 0},
                        {"id": "ch5-2", "title": "5.2 物质激励与非物质激励", "content": "", "word_count": 0},
                        {"id": "ch5-3", "title": "5.3 激励策略的设计与实施", "content": "", "word_count": 0},
                        {"id": "ch5-4", "title": "5.4 激励效果的评估与优化", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch6",
                    "title": "第6章 绩效管理与考核",
                    "sections": [
                        {"id": "ch6-1", "title": "6.1 绩效管理体系与理论", "content": "", "word_count": 0},
                        {"id": "ch6-2", "title": "6.2 绩效评估工具与方法", "content": "", "word_count": 0},
                        {"id": "ch6-3", "title": "6.3 绩效反馈与员工发展", "content": "", "word_count": 0},
                        {"id": "ch6-4", "title": "6.4 案例分析：企业绩效管理最佳实践", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch7",
                    "title": "第7章 实证研究",
                    "sections": [
                        {"id": "ch7-1", "title": "7.1 研究设计与数据来源", "content": "", "word_count": 0},
                        {"id": "ch7-2", "title": "7.2 样本特征分析", "content": "", "word_count": 0},
                        {"id": "ch7-3", "title": "7.3 实证结果与分析", "content": "", "word_count": 0},
                        {"id": "ch7-4", "title": "7.4 研究讨论与启示", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch8",
                    "title": "第8章 结论与建议",
                    "sections": [
                        {"id": "ch8-1", "title": "8.1 主要研究结论", "content": "", "word_count": 0},
                        {"id": "ch8-2", "title": "8.2 对人力资源管理的建议", "content": "", "word_count": 0},
                        {"id": "ch8-3", "title": "8.3 研究的局限性与未来研究方向", "content": "", "word_count": 0}
                    ]
                },
                {
                    "id": "ch9",
                    "title": "参考文献",
                    "sections": []
                },
                {
                    "id": "ch10",
                    "title": "附录",
                    "sections": [
                        {"id": "ch10-1", "title": "附录A 调查问卷", "content": "", "word_count": 0},
                        {"id": "ch10-2", "title": "附录B 访谈提纲", "content": "", "word_count": 0}
                    ]
                }
            ]
        }
    }
    
    template = direction_templates.get(direction, direction_templates["finance"])
    direction_name = template["name"]
    
    custom_prompt_section = f"\n\n【自定义引导词】\n{custom_prompt}" if custom_prompt else ""
    
    prompt = f"""请为以下{paper_type_text}生成一个{direction_name}方向的详细大纲结构。

【文稿基本信息】
- 文稿标题：{title}
- 所属专业：{major}
- 文稿方向：{direction_name}
- 关键词：{', '.join(keywords)}
- 文稿字数要求：约{word_count}字{custom_prompt_section}

请直接返回以下JSON格式的大纲（只需返回JSON，不要其他内容）：
```json
{json.dumps(template["chapters"], ensure_ascii=False, indent=2)}
```

请根据文稿标题和关键词适当调整章节标题，使其更贴合具体研究主题。其他章节结构保持不变。

【字数分配建议】
- 绪论：约{word_count//10}字
- 文献综述：约{word_count//10}字  
- 研究方法：约{word_count//12}字
- 主体章节（分析/实证）：约{word_count//3}字
- 结论与建议：约{word_count//10}字

请生成符合创意规范、结构清晰、内容完整的大纲。"""

    system_prompt = f"你是一个资深的{direction_name}领域创意写作专家，擅长设计灵感文章框架和大纲。请严格按照要求的JSON格式返回内容，确保每个章节的小节标题专业、规范、有层次。"

    result = call_minimax(prompt, system_prompt, api_key=api_key)
    
    if result:
        try:
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                outline = json.loads(json_match.group())
                return outline
            else:
                print("未找到JSON格式的大纲")
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
    
    return get_default_outline()

def get_default_outline():
    """返回默认大纲模板"""
    return [
        {
            "id": "ch1",
            "title": "引言",
            "sections": [
                {"id": "ch1-1", "title": "研究背景", "content": "", "word_count": 0},
                {"id": "ch1-2", "title": "研究意义", "content": "", "word_count": 0},
                {"id": "ch1-3", "title": "研究方法与创新点", "content": "", "word_count": 0}
            ]
        },
        {
            "id": "ch2",
            "title": "文献综述",
            "sections": [
                {"id": "ch2-1", "title": "国外研究现状", "content": "", "word_count": 0},
                {"id": "ch2-2", "title": "国内研究现状", "content": "", "word_count": 0},
                {"id": "ch2-3", "title": "文献评述", "content": "", "word_count": 0}
            ]
        },
        {
            "id": "ch3",
            "title": "理论基础与概念界定",
            "sections": [
                {"id": "ch3-1", "title": "相关理论概述", "content": "", "word_count": 0},
                {"id": "ch3-2", "title": "核心概念界定", "content": "", "word_count": 0}
            ]
        },
        {
            "id": "ch4",
            "title": "研究分析与设计",
            "sections": [
                {"id": "ch4-1", "title": "研究假设", "content": "", "word_count": 0},
                {"id": "ch4-2", "title": "研究模型构建", "content": "", "word_count": 0},
                {"id": "ch4-3", "title": "变量设计与测量", "content": "", "word_count": 0}
            ]
        },
        {
            "id": "ch5",
            "title": "实证分析与结果",
            "sections": [
                {"id": "ch5-1", "title": "数据来源与描述性统计", "content": "", "word_count": 0},
                {"id": "ch5-2", "title": "信度与效度检验", "content": "", "word_count": 0},
                {"id": "ch5-3", "title": "假设检验与结果分析", "content": "", "word_count": 0}
            ]
        },
        {
            "id": "ch6",
            "title": "结论与建议",
            "sections": [
                {"id": "ch6-1", "title": "研究结论", "content": "", "word_count": 0},
                {"id": "ch6-2", "title": "对策建议", "content": "", "word_count": 0},
                {"id": "ch6-3", "title": "研究局限与展望", "content": "", "word_count": 0}
            ]
        },
        {
            "id": "ch7",
            "title": "参考文献",
            "sections": []
        }
    ]

def generate_section_content(paper_title: str, chapter_title: str, section_title: str, 
                            context_before: str = "", keywords: list = [], word_count: int = 800,
                            direction: str = "finance", custom_prompt: str = "", api_key=None) -> str:
    """使用MiniMax生成文稿段落内容"""
    
    direction_names = {
        "finance": "财务管理",
        "business": "工商管理", 
        "hr": "人力资源管理"
    }
    direction_name = direction_names.get(direction, "财务管理")
    
    estimated_length = max(int(word_count), 250)
    length_min = max(220, int(estimated_length * 0.85))
    length_max = max(length_min + 60, int(estimated_length * 1.15))
    custom_prompt_section = f"\n\n【自定义引导词】\n{custom_prompt}" if custom_prompt else ""
    
    prompt = f"""请为以下{direction_name}方向的灵感文章节撰写专业、流畅的内容。

文稿标题：{paper_title}
当前章节：{chapter_title}
当前小节：{section_title}
{custom_prompt_section}

{'前面已写内容：' + context_before[:500] + '...' if context_before else ''}
关键词：{', '.join(keywords)}

请撰写约{estimated_length}字的内容，要求：
1. 流畅自然的表达，规范的书面语言
2. 逻辑清晰，论证充分
3. 层次分明，段落衔接自然
4. {direction_name}领域的专业术语和理论
5. 如有必要可包含数据或案例支撑
6. 必须输出2-4段，总字数严格控制在{length_min}-{length_max}字
7. 每一段开头必须空两格（使用两个全角空格“　　”）
8. 不要输出标题、序号、项目符号或解释性前后缀，只输出正文段落"""

    system_prompt = (
        f"你是一个资深的{direction_name}领域创意写作专家，擅长撰写专业内容。"
        f"必须严格遵守格式：2-4段、总字数{length_min}-{length_max}字、每段开头两个全角空格。"
        "请直接输出正文，不要添加标题。"
    )

    result = call_minimax(prompt, system_prompt, api_key=api_key)
    
    if result:
        result = result.strip()
        return result
    
    return (
        f"　　这是{section_title}部分的初稿内容，围绕{chapter_title}展开核心问题分析，"
        f"结合{direction_name}领域常见理论框架进行说明。当前为回退文本，请稍后重试生成接口以获得完整出稿内容。\n\n"
        f"　　在后续完善中可补充数据、案例和方法细节，确保论述逻辑连贯、论据充分，"
        f"并与文稿主题《{paper_title}》保持一致。当前生成服务暂不可用（MiniMax API调用失败）。"
    )

def generate_section_content_stream(paper_title: str, chapter_title: str, section_title: str, 
                            context_before: str = "", keywords: list = [], word_count: int = 800,
                            direction: str = "finance", custom_prompt: str = "", api_key=None):
    """使用MiniMax流式生成文稿段落内容"""
    
    direction_names = {
        "finance": "财务管理",
        "business": "工商管理", 
        "hr": "人力资源管理"
    }
    direction_name = direction_names.get(direction, "财务管理")
    
    estimated_length = max(int(word_count), 250)
    length_min = max(220, int(estimated_length * 0.85))
    length_max = max(length_min + 60, int(estimated_length * 1.15))
    custom_prompt_section = f"\n\n【自定义引导词】\n{custom_prompt}" if custom_prompt else ""
    
    prompt = f"""请为以下{direction_name}方向的灵感文章节撰写专业、流畅的内容。

文稿标题：{paper_title}
当前章节：{chapter_title}
当前小节：{section_title}
{custom_prompt_section}

{'前面已写内容：' + context_before[:500] + '...' if context_before else ''}
关键词：{', '.join(keywords)}

请撰写约{estimated_length}字的内容，要求：
1. 流畅自然的表达，规范的书面语言
2. 逻辑清晰，论证充分
3. 层次分明，段落衔接自然
4. {direction_name}领域的专业术语和理论
5. 如有必要可包含数据或案例支撑
6. 必须输出2-4段，总字数严格控制在{length_min}-{length_max}字
7. 每一段开头必须空两格（使用两个全角空格“　　”）
8. 不要输出标题、序号、项目符号或解释性前后缀，只输出正文段落"""

    system_prompt = (
        f"你是一个资深的{direction_name}领域创意写作专家，擅长撰写专业内容。"
        f"必须严格遵守格式：2-4段、总字数{length_min}-{length_max}字、每段开头两个全角空格。"
        "请直接输出正文，不要添加标题。"
    )

    for content in call_minimax_stream(prompt, system_prompt, api_key=api_key):
        yield content

def refine_content_with_minimax(content: str, instruction: str, paper_title: str, api_key=None) -> str:
    """使用MiniMax微调文稿内容"""
    
    prompt = f"""请根据以下要求对文稿内容进行修改。

原文：
{content}

修改要求：{instruction}

文稿标题：{paper_title}

请直接输出修改后的内容，保持创意化的写作风格。"""

    system_prompt = "你是一个专业的创意写作助手，擅长根据用户要求修改内容。请直接输出修改后的内容。"

    result = call_minimax(prompt, system_prompt, api_key=api_key)
    
    if result:
        return result.strip()
    
    return f"""根据您的要求"{instruction}"，已对内容进行修改。

{content}

（注意：MiniMax API调用失败）"""
