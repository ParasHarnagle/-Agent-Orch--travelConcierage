async def classify_adk_event(event):
    # TEXT DELTA
    if event and hasattr(event, "content") and event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, "text") and part.text:
                yield {"type": "text", "value": part.text}

    # TOOL CALL (function_call)
    if event and hasattr(event, "actions") and event.actions:
        for action in event.actions:
            if hasattr(action, "function_call") and action.function_call:
                yield {
                    "type": "tool_call",
                    "name": action.function_call.name,
                    "arguments": action.function_call.args,
                }

    # TOOL RESULT (function_response)
    if event and hasattr(event, "actions") and event.actions:
        for action in event.actions:
            if hasattr(action, "function_response") and action.function_response:
                yield {
                    "type": "tool_result",
                    "id": action.function_response.id,
                    "response": action.function_response.response,
                }

    # # INPUT TRANSCRIPTION (Audio → Text)
    # if event and hasattr(event, "input_transcription") and event.input_transcription:
    #     for part in event.input_transcription.parts:
    #         if hasattr(part, "text") and part.text:
    #             yield {"type": "input_transcription", "value": part.text}

    # # OUTPUT TRANSCRIPTION (Text → Audio transcript)
    # if event and hasattr(event, "output_transcription") and event.output_transcription:
    #     for part in event.output_transcription.parts:
    #         if hasattr(part, "text") and part.text:
    #             yield {"type": "output_transcription", "value": part.text}


    # GROUNDING METADATA
    if event and hasattr(event, "grounding_metadata") and event.grounding_metadata:
        yield {"type": "grounding", "value": event.grounding_metadata}

    # BRANCHING
    if event and hasattr(event, "branch") and event.branch:
        yield {"type": "branch", "value": event.branch}

    # COMPLETION / FINALIZATION
    if event and hasattr(event, "finish_reason") and event.finish_reason:
        yield {"type": "finish", "reason": event.finish_reason}

    if event and hasattr(event, "is_final_response") and event.is_final_response:
        yield {"type": "final"}

    # INTERRUPTED
    if event and hasattr(event, "interrupted") and event.interrupted:
        yield {"type": "interrupted"}

    # ERROR
    if event and hasattr(event, "error_code") and event.error_code:
        yield {
            "type": "error",
            "error_code": event.error_code,
            "error_message": event.error_message,
        }

    # CUSTOM METADATA (Your MCP logs, routing logs, etc.)
    if event and hasattr(event, "custom_metadata") and event.custom_metadata:
        yield {"type": "custom", "value": event.custom_metadata}
