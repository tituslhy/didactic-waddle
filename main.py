import chainlit as cl
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langchain_mcp_adapters.client import MultiServerMCPClient

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@cl.on_chat_start
async def on_start():
    llm = ChatOllama(model="qwen3.5:latest", temperature=0)

    client = MultiServerMCPClient({
        "revenue_chart": {
            "url": "http://localhost:8888/mcp",
            "transport": "http",
        }
    })

    tools = await client.get_tools()
    agent = create_agent(
        model=llm, 
        tools=tools,
        system_prompt="""
        You are a helpful assistant for business analysts. Use the tools at your disposal to answer the user's questions. 
        When solving a task:
        1. FIRST explain briefly what you are going to do before calling any tools.
        2. THEN call the necessary tools.
        3. AFTER the tool calls are complete. Tell the user that you have completed the task and invite the user to ask more questions.

        Always produce BOTH a pre-tool explanation and a post-tool explanation.
        Do not skip either."""
    )

    cl.user_session.set("agent", agent)

@cl.on_message
async def on_message(message: cl.Message):
    logger.info(f"Received message: {message.content}")
    agent = cl.user_session.get("agent")

    response_msg = cl.Message(content="")
    await response_msg.send()

    ui_rendered = False

    current_step = None

    tool_in_progress = False
    pending_ui = None
    post_text_buffer = []

    # Stream tokens
    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": message.content}]},
        stream_mode="updates",
    ):
        for node_output in chunk.values():
            for msg in node_output.get("messages", []):
                
                # Stream text tokens
                content = getattr(msg, "content", "")    
                
                # ---- TOOL CALL DETECTION ----
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    tool_name = tool_calls[0].get("name", "unknown_tool")

                    logger.info(f"Tool call detected: {tool_name}")

                    tool_in_progress = True

                    current_step = cl.Step(name=f"{tool_name} tool")
                    await current_step.send()

                # ---- TOOL RESULT ----
                if msg.__class__.__name__ == "ToolMessage":
                    if current_step:
                        if isinstance(content, list):
                            content = "".join(
                                item.get("text", "") if isinstance(item, dict) else str(item)
                                for item in content
                            )
                        elif not isinstance(content, str):
                            content = str(content)

                        await current_step.stream_token(content)

                        # End of tool execution
                        await current_step.update()
                        current_step = None
                        tool_in_progress = False
                    
                    # DO NOT continue here so artifact parsing still happens

                # ---- NORMAL TEXT STREAMING ----
                if isinstance(content, list):
                    content = "".join(
                        item.get("text", "") if isinstance(item, dict) else str(item)
                        for item in content
                    )
                elif not isinstance(content, str):
                    content = str(content)

                if content.strip() and msg.__class__.__name__ != "ToolMessage":
                    if tool_in_progress:
                        post_text_buffer.append(content)
                    else:
                        await response_msg.stream_token(content)

                # Detect Prefab UI artifact
                # ---- PREFAB UI ARTIFACT DETECTION (FIXED) ----
                artifact = None

                # Try multiple known locations (LangChain/MCP variants)
                if hasattr(msg, "artifact"):
                    artifact = msg.artifact

                if artifact is None and hasattr(msg, "additional_kwargs"):
                    artifact = msg.additional_kwargs.get("artifact")

                if artifact is None:
                    artifact = getattr(msg, "__dict__", {}).get("artifact")

                if isinstance(artifact, dict):
                    structured_content = artifact.get("structured_content")

                    if isinstance(structured_content, dict):
                        prefab = structured_content.get("$prefab")

                        if prefab and "view" in structured_content:
                            logger.info("Buffering Prefab UI artifact")
                            pending_ui = structured_content
    if current_step:
        await current_step.update()

    # Flush any buffered post-tool text FIRST (so narration appears before UI)
    if post_text_buffer:
        for chunk in post_text_buffer:
            await response_msg.stream_token(chunk)

    # Finalize the text message before rendering UI
    if response_msg.id:
        await response_msg.update()

    # Render UI AFTER message is fully finalized
    if pending_ui:
        await cl.CustomElement(
            name="StockDashboard",
            props=pending_ui,
        ).send(for_id=response_msg.id)