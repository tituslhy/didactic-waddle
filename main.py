import json
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
        When rendering charts, state that the chart is rendered and the user is free to explore and ask further questions. 
        Don't need to caveat that you're just an AI and can't see the chart or actually a render a chart - the chart is rendered
        for the user via tool calls that you make that pass the results to the frontend directly. """
    )

    cl.user_session.set("agent", agent)
    await cl.Message(content="Ready! Ask me to show the 2025 revenue chart.").send()


@cl.on_message
async def on_message(message: cl.Message):
    logger.info(f"Received message: {message.content}")
    agent = cl.user_session.get("agent")

    response_msg = cl.Message(content="")
    await response_msg.send()

    ui_rendered = False

    async for chunk in agent.astream(
        {"messages": [{"role": "user", "content": message.content}]},
        stream_mode="updates",
    ):
        for node_output in chunk.values():
            for msg in node_output.get("messages", []):
                # Stream text tokens
                content = getattr(msg, "content", "")
                if isinstance(content, str) and content.strip():
                    if not getattr(msg, "tool_call_id", None):
                        await response_msg.stream_token(content)

                # Detect Prefab UI artifact
                if ui_rendered:
                    continue

                artifact = getattr(msg, "artifact", None)
                if not isinstance(artifact, dict):
                    continue

                structured_content = artifact.get("structured_content")
                if not isinstance(structured_content, dict):
                    continue

                if "$prefab" not in structured_content or "view" not in structured_content:
                    continue

                logger.info("Rendering Prefab UI artifact")
                await response_msg.update()

                # cl.CustomElement props arrive empty — pass data via
                # the `content` field as a JSON string instead, which
                # Chainlit does forward reliably to the JSX component.
                anchor = cl.Message(content="")
                await anchor.send()

                await cl.CustomElement(
                    name="RevenueChart",
                    props = structured_content,
                ).send(for_id=anchor.id)

                ui_rendered = True

    await response_msg.update()