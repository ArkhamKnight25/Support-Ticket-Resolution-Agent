from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from botocore.exceptions import ClientError

from app.schemas.chat_schema import ChatRequest, ChatResponse, SourceMetadata
from app.services.bedrock_service import BedrockService
from app.services.rag_service import RAGService
from app.services.guardrail_service import GuardrailService
from app.services.session_service import SessionService
from app.dependencies import (
    get_bedrock_service,
    get_rag_service,
    get_guardrail_service,
    get_session_service,
    require_api_key,
)

router = APIRouter()


def _to_source_metadata(docs: list) -> list[SourceMetadata]:
    return [
        SourceMetadata(
            source_file=d.metadata.get("source_file"),
            document_type=d.metadata.get("document_type"),
            chunk_id=d.metadata.get("chunk_id"),
        )
        for d in docs
    ]


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    bedrock: BedrockService = Depends(get_bedrock_service),
    rag: RAGService = Depends(get_rag_service),
    guardrail: GuardrailService = Depends(get_guardrail_service),
    session_service: SessionService = Depends(get_session_service),
    _: None = Depends(require_api_key),
):
    # Guardrail — input check
    blocked = await guardrail.check_input(request.message)
    if blocked:
        raise HTTPException(status_code=400, detail="Message blocked by content policy.")

    # Retrieve relevant documents
    context_docs = await rag.retrieve(request.message, top_k=5)

    history = request.history
    if not history and request.session_id:
        session = session_service.get_session(request.session_id) or {}
        history = []
        for turn in session.get("chat_history", [])[-10:]:
            history.append({"role": "user", "content": turn.get("user", "")})
            history.append({"role": "assistant", "content": turn.get("assistant", "")})

    # Call Bedrock LLM
    try:
        response = await bedrock.chat(
            message=request.message,
            context_docs=context_docs,
            history=history,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "ThrottlingException":
            raise HTTPException(
                status_code=429,
                detail="Bedrock rate limit reached. Please wait and retry.",
            )
        raise HTTPException(status_code=502, detail=f"Bedrock error: {code}")

    masked_reply = guardrail.mask_pii(response.content)
    confidence = "high" if len(context_docs) >= 3 else "medium" if context_docs else "low"
    output_flagged = await guardrail.check_output(masked_reply, context_docs)
    warnings = guardrail.build_warnings(
        context_docs=context_docs,
        confidence=confidence,
        requires_human_approval=False,
        output_flagged=output_flagged,
    )

    if request.session_id:
        session_service.append_chat_turn(
            request.session_id,
            user_message=request.message,
            assistant_reply=masked_reply,
            sources=[source.model_dump() for source in _to_source_metadata(context_docs)],
            warnings=warnings,
            confidence=confidence,
        )

    return ChatResponse(
        reply=masked_reply,
        sources=_to_source_metadata(context_docs),
        model=response.model,
        session_id=request.session_id,
        confidence=confidence,
        warnings=warnings,
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    bedrock: BedrockService = Depends(get_bedrock_service),
    rag: RAGService = Depends(get_rag_service),
    _: None = Depends(require_api_key),
):
    context_docs = await rag.retrieve(request.message, top_k=5)

    async def event_stream():
        try:
            async for chunk in bedrock.stream_chat(
                request.message, context_docs, request.history
            ):
                yield f"data: {chunk}\n\n"
        except (RuntimeError, ClientError) as e:
            yield f"data: [ERROR] {e}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
