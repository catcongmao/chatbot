import streamlit as st
from openai import OpenAI
import datetime

# -----------------------------------------------------------------------------
# 1. 配置与初始化
# -----------------------------------------------------------------------------

# 配置 DeepSeek 客户端
client = OpenAI(
    api_key="sk-3617dbb2d49745c68b88130ce5a6d8b5",  # ⚠️⚠️⚠️ 请在此处填入你的 API Key
    base_url="https://api.deepseek.com"
)

st.set_page_config(page_title="DeepSeek 随心游", page_icon="✈️", layout="wide")

# 初始化 Session State
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "itinerary_generated" not in st.session_state:
    st.session_state["itinerary_generated"] = False


# -----------------------------------------------------------------------------
# 2. 核心逻辑函数
# -----------------------------------------------------------------------------

def generate_response(messages):
    """调用 DeepSeek API 生成回复"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.5,
            stream=True
        )
        return response
    except Exception as e:
        st.error(f"API 调用出错: {e}")
        return None


# -----------------------------------------------------------------------------
# 3. 界面逻辑
# -----------------------------------------------------------------------------

st.title("✈️ 你专属的智能旅行策划师 （璐璐推荐）")

# --- 场景 A: 尚未生成行程，显示信息收集表单 ---
if not st.session_state["itinerary_generated"]:
    st.markdown("### 👋 欢迎！请先告诉我您的旅行计划")

    with st.form("travel_form"):
        col1, col2 = st.columns(2)

        with col1:
            destination = st.text_input("📍 目的地", placeholder="例如：日本京都、云南大理")
            start_date = st.date_input("📅 出发日期", min_value=datetime.date.today())
            days = st.number_input("🕒 旅行天数", min_value=1, max_value=30, value=3)

        with col2:
            budget = st.selectbox("💰 预算等级", ["经济穷游", "舒适标准", "豪华奢享"])
            relationship = st.selectbox("👥 同行关系",
                                        ["单人独行", "情侣/夫妻", "亲子游 (带小孩)", "朋友结伴", "带父母"])
            interests = st.multiselect(
                "❤️ 兴趣偏好 (多选)",
                ["美食探店", "历史古迹", "自然风光", "网红打卡", "极限运动", "博物馆/艺术", "休养度假", "购物血拼"]
            )

        # 补充需求
        extra_req = st.text_area("📝 其他特殊需求 (选填)",
                                 placeholder="例如：如果不吃辣、需要无障碍设施、想要安排一次温泉...")

        submitted = st.form_submit_button("🚀 生成行程方案")

    if submitted:
        if not destination:
            st.warning("请至少填写目的地！")
        else:
            # --- 构造初始 Prompt ---
            system_prompt = "你是一位资深的定制旅行策划师。请根据用户的要求生成一份详细的旅行计划。注重逻辑性、路线顺路程度和个性化体验。"

            user_prompt = f"""
            请为我设计一份旅行计划：
            1. **目的地**：{destination}
            2. **时间**：{start_date} 出发，共 {days} 天
            3. **预算**：{budget}
            4. **同行人**：{relationship}
            5. **兴趣**：{", ".join(interests)}
            6. **特殊需求**：{extra_req}

            【输出要求】
            请以Markdown格式输出，必须包含以下模块：
            - **行前指南**：根据目的地和季节给出穿衣建议、必备物品。
            - **每日安排**：每天分【上午/下午/晚上】，注明景点、推荐餐厅（特色菜）、交通方式（如何从上一站到达）。
            - **避坑/贴士**：针对该类人群（如{relationship}）的特别注意事项。
            """

            # 存入历史记录
            st.session_state["messages"] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # 标记状态改变，触发重绘进入场景 B
            st.session_state["itinerary_generated"] = True
            st.rerun()

# --- 场景 B: 已生成行程，显示结果并允许调整 ---
else:
    # 侧边栏：重置按钮
    with st.sidebar:
        st.success("✅ 行程已创建")
        if st.button("🗑️ 重新开始规划"):
            st.session_state.clear()
            st.rerun()

    # 显示对话历史 (行程展示区)
    chat_container = st.container()

    with chat_container:
        # 1. 先把现有的历史记录画出来
        for msg in st.session_state["messages"]:
            if msg["role"] != "system":
                avatar = "👤" if msg["role"] == "user" else "🤖"
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"])

        # 2. 【关键修改点】自动触发回复
        # 如果最后一条消息是 user 发的，说明 AI 还没回复，现在立马回复！
        if st.session_state["messages"] and st.session_state["messages"][-1]["role"] == "user":
            with st.chat_message("assistant", avatar="🤖"):
                response_placeholder = st.empty()
                full_response = ""

                # 调用 API
                stream = generate_response(st.session_state["messages"])

                if stream:
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_response += content
                            response_placeholder.markdown(full_response + "▌")

                    # 移除光标，显示最终结果
                    response_placeholder.markdown(full_response)

                # 将 AI 的回复存入历史，防止页面刷新后丢失或重复生成
                st.session_state["messages"].append({"role": "assistant", "content": full_response})

    # 3. 底部输入框：用于后续的交互调整
    if prompt := st.chat_input("对行程不满意？输入修改意见（例如：第二天太累了，换轻松点）..."):
        # 用户输入后，只负责存入历史并刷新页面
        # 页面刷新后，会重新从上往下执行，自然会走到上面的 "关键修改点" 触发 AI 回复
        st.session_state["messages"].append({"role": "user", "content": prompt})
        st.rerun()
