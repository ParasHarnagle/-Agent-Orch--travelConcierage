import asyncio
import os
import anyio
from dotenv import load_dotenv
load_dotenv()
 
from google.adk.agents.llm_agent import Agent
from google.adk.runners import InMemoryRunner
from google.adk.models.lite_llm import LiteLlm
from stream_adk import classify_adk_event
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.genai import types
from prompts import PROMPT_1
# ---------------------------------------------------------
#  LLM MODEL (LiteLLM backend)
# ---------------------------------------------------------
 
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
LITELLM_API_BASE = os.getenv("LITELLM_API_BASE", "https://openrouter.ai/api/v1")
 
model_1 = "openrouter/deepseek/deepseek-chat-v3-0324:free"
model_2 = "openrouter/minimax/minimax-m2:free"

model = LiteLlm(
    model=model_2,
    api_key=LITELLM_API_KEY,
    api_base=LITELLM_API_BASE,
)
 
 
# ---------------------------------------------------------
#  MCP TOOLSET — Connect to Roadtrip MCP Server
# ---------------------------------------------------------
 
MCP_SERVER_URL = "http://localhost:3001"
 
# RoadTripToolset = McpToolset(
#   connection_params=StdioConnectionParams(
#                 server_params = StdioServerParameters(
#                     command="python3", args=["mcp_server/server.py"]
#                     )
#                 )
#     )
RoadTripToolset =  McpToolset(  #conectiunea cu serverul FastMCP prin HTTP (usor de de dockerizat ulterior)
            connection_params=StreamableHTTPConnectionParams(
                url="http://127.0.0.1:5003/mcp",
                terminate_on_close=False
            ),
        ) 
 
# ---------------------------------------------------------
#  Root RoadTrip Agent
# ---------------------------------------------------------
 
root_agent = Agent(
    model=model,
    name="sentient_roadtrip_copilot",
    description="Emotion-aware, cinematic road-trip planning agent using MCP tools.",
    instruction=PROMPT_1,
    tools=[RoadTripToolset],
)
 
# ---------------------------------------------------------
#  Runner & Session Manager
# ---------------------------------------------------------
 
runner = InMemoryRunner(agent=root_agent, app_name="roadtrip_app")
APP_NAME = "roadtrip_app"
 
 
async def initialize_session(user_id: str):
    try:
        return await runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id
        )
    except:
        # Fallback if session already exists
        return await runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id
        )
 
async def safe_stream_runner(runner, user_id, session_id, content):
    """
    Wraps ADK streaming so it:
     streams text tokens
     absorbs GeneratorExit safely
     avoids AnyIO cancel-scope mismatch
    """
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            if event and hasattr(event, "content") and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        yield part.text

    except GeneratorExit:
        #  avoid cancel scope crashes
        return
    except Exception as e:
        print("[stream error]", e)
        return
    
# ---------------------------------------------------------
#  Main agent execution with retry
# ---------------------------------------------------------

import anyio

async def safe_close(gen):
    try:
        async with anyio.create_task_group() as tg:
            async with anyio.CancelScope(shield=True):
                tg.start_soon(gen.aclose)
    except Exception:
        pass

async def safe_stream(gen):
    try:
        async for event in gen:
            yield event
    except Exception as e:
        print("Stream error:", e)
    finally:
        await safe_close(gen)

async def run_roadtrip_prompt(prompt: str, user_id: str):
    """
    Runs the Roadtrip MCP-powered ADK agent.
    Includes:
    - Session creation
    - Streaming
    - Auto retry on failure
    - Strict JSON output
    """
 
    session = await initialize_session(user_id)
    print("Session:", session)
 
    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt)]
    )
 
    response_text = ""
    try:
        async for event in safe_stream(
            runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content
            )
        ): 

            if event.partial and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        print(part.text, end="", flush=True)
                        response_text += part.text
            elif not event.partial and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        print(part.text, end="", flush=True)
                        response_text += part.text

            # if event and hasattr(event, "content") and event.content.parts:
            #     part = event.content.parts[0]
            #     if hasattr(part, "text") and part.text:
            #         response_text += part.text

    except Exception as e:
        print("Roadtrip Session error, retrying:", e)
        raise e
        
    await RoadTripToolset.close()  
    return response_text.strip()
 
# async def run_roadtrip_prompt(prompt: str, user_id: str):

#     # --------------------------------------------------
#     #  ✅ Create or load session 
#     # --------------------------------------------------
#     session = await initialize_session(user_id)
#     print(f"🔵 Session started: {session.id}")

#     # Wrap content
#     content = types.Content(
#         role="user",
#         parts=[types.Part.from_text(text=prompt)]
#     )

#     # This will accumulate final answer
#     final_output = ""

#     # ==================================================
#     #  ✅ Main execution (with retry)
#     # ==================================================
#     async def execute_once():

#         nonlocal final_output

#         print("🚗 Running agent with streaming enabled...")

#         # TaskGroup wrapper is MANDATORY for MCP streaming
#         async with anyio.create_task_group() as tg:

#             async for event in runner.run_async(
#                 user_id=user_id,
#                 session_id=session.id,
#                 new_message=content,
#             ):

#                 # --------------------------------------------------
#                 # ✅ STREAMED TEXT TOKENS
#                 # --------------------------------------------------
#                 if hasattr(event, "content") and event.content.parts:
#                     part = event.content.parts[0]
                    
#                     if hasattr(part, "text") and part.text:
#                         print(f"📝 Streaming token: {part.text}", end="", flush=True)
#                         final_output += part.text

#                 # --------------------------------------------------
#                 # ✅ TOOL INVOCATIONS (MCP tools)
#                 # --------------------------------------------------
#                 if hasattr(event, "tool_request"):
#                     tr = event.tool_request
#                     print(f"\n🔧 TOOL REQUEST → {tr.name}")
#                     print(f"   Args: {tr.arguments}")

#                 if hasattr(event, "tool_response"):
#                     ts = event.tool_response
#                     print(f"\n✅ TOOL RESPONSE → {ts.name}")
#                     print(f"   Output: {ts.content}")

#     # EXECUTE MAIN BLOCK
#     try:
#         await execute_once()
#     except Exception as e:
#         pass

#     try:
#         await runner.session_service.close_session(session.id)
#         print(f"\n🟢 Session closed: {session.id}")
#     except:
#         print("⚠️ Warning: Failed to close session gracefully.")

#     # DO NOT close McpToolset manually (ADK handles internally)
#     # DO NOT terminate MCP HTTP connection (we use terminate_on_close=False)

#     return final_output.strip()

async def main():
    out = await run_roadtrip_prompt(
        "Plan a 2-day healing scenic road trip from Bangalore to Coorg. Mood = heartbreak.",
        user_id="demo_user"
    )
    print(out)
 
 
if __name__ == "__main__":
    asyncio.run(main())