from __future__ import annotations


SUMMARY_PROMPT = """你是「人工智能应用」赛道的竞赛教练 Agent。
请根据【文件内容】回答用户问题。要求：
1) 必须严格依据文件内容，不要编造文件中不存在的条款或限制；
2) 若文件信息不足，请明确标注「文件未提供」并给出你需要补充哪些信息；
3) 使用简体中文输出，条理清晰，便于直接放进答辩材料。

【用户问题】
{question}

【文件内容（可引用片段）】
{context}

【输出格式（固定）】
一、需求解析（输入/输出/评分类/限制条件）
二、可行方案总览（模块化设计 + 工作流）
三、风险与对策（至少 3 点）
四、建议 Demo 剧本（至少 5 个步骤，带有操作顺序）
"""


PPT_PROMPT = """你是「人工智能应用」赛道的竞赛教练 Agent。
根据【文件内容】与【方案摘要】，输出答辩 PPT 大纲。要求：
1) 每一页要点要能从文件内容间接支持；
2) 直接列出页标题 + 该页要讲的 3-5 个重点；
3) 若文件信息不足，请在对应页标注「待补充」。

【文件内容（可引用片段）】
{context}

【方案摘要（你先前已生成）】
{solution_summary}

【输出格式（固定）】
P1: ...
  - ...
P2: ...
  - ...
（最多 10 页）
"""


QUESTIONS_PROMPT = """你是「人工智能应用」赛道的竞赛教练 Agent。
根据【文件内容】设计一套「Demo 可验证」的测试/评测指标与小测方案。要求：
1) 至少 4 个可量化指标（例如准确率/完成率/延迟/引用命中率等，请说明怎么量）；
2) 给出测试案例类型（至少 6 个案例）与每个案例的期望输出特征；
3) 若文件未要求特定评测，仍要提出合理替代方案并说明理由。

【文件内容（可引用片段）】
{context}

【用户补充指令】
{user_instruction}

【输出格式（固定）】
一、评测指标（4-8 项）
二、测试案例（至少 6 个）
三、成功判准（用可观察描述）
"""


from langchain_core.prompts import PromptTemplate


SUMMARY_TEMPLATE = PromptTemplate.from_template(SUMMARY_PROMPT)
PPT_TEMPLATE = PromptTemplate.from_template(PPT_PROMPT)
QUESTIONS_TEMPLATE = PromptTemplate.from_template(QUESTIONS_PROMPT)

