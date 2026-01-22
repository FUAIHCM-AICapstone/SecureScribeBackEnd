import json
import textwrap
from typing import List, Optional

from agno.agent import Agent
from agno.models.google import Gemini
from agno.models.message import Message
from chonkie import GeminiEmbeddings

from app.core.config import settings


def _get_model() -> Gemini:
    return Gemini(
        id="gemini-2.5-flash-preview-09-2025",
        api_key=settings.GOOGLE_API_KEY,
    )


def _get_embeddings() -> GeminiEmbeddings:
    return GeminiEmbeddings(api_key=settings.GOOGLE_API_KEY)


async def embed_query(query: str) -> List[float]:
    embeddings = _get_embeddings()
    vector = embeddings.embed(query)
    return list(vector)


async def embed_documents(docs: List[str]) -> List[List[float]]:
    if not docs:
        return []
    embeddings = _get_embeddings()
    vectors = embeddings.embed_batch(docs)
    return [list(v) for v in vectors]


async def chat_complete(system_prompt: str, user_prompt: str) -> str:
    model = _get_model()
    messages = [
        Message(role="system", content=system_prompt),
        Message(role="user", content=user_prompt),
    ]
    assistant_message = Message(role="assistant", content="")
    response = await model.ainvoke(messages, assistant_message)
    return response.content


async def optimize_contexts_with_llm(query: str, history: str, context_block: str, desired_count: int = 3) -> Optional[str]:
    system_prompt = (
        textwrap.dedent(
            """
        Bạn là một hệ thống đánh giá mức độ liên quan của tài liệu.

        Dưới đây là câu hỏi của người dùng, lịch sử hội thoại,
        và danh sách các đoạn tài liệu có thể liên quan đến câu hỏi.

        Hãy chọn ra tối đa {desired_count} đoạn phù hợp nhất để hỗ trợ trả lời.
        """
        )
        .strip()
        .format(desired_count=desired_count)
    )

    user_prompt = textwrap.dedent(
        f"""
        Câu hỏi:
        {query}

        Lịch sử hội thoại (tóm tắt):
        {history}

        Các đoạn tài liệu:
        {context_block}

        Yêu cầu:
        - Chỉ chọn các đoạn thực sự liên quan đến câu hỏi và bối cảnh hội thoại.
        - Trả về kết quả ở định dạng JSON, chỉ gồm id và lý do.
        Ví dụ:
        [
          {{"id": "file1:chunk2", "reason": "phân tích lỗi Redis timeout"}},
          {{"id": "file1:chunk3", "reason": "mô tả nguyên nhân connection refused"}}
        ]
        """
    ).strip()

    try:
        response = await chat_complete(system_prompt, user_prompt)
    except Exception as error:
        print(f"[optimize_contexts_with_llm] LLM call failed: {error}")
        return None

    if not response:
        return None

    candidate = response.strip()
    if not candidate:
        return None

    try:
        json.loads(candidate)
    except json.JSONDecodeError as error:
        print(f"[optimize_contexts_with_llm] Invalid JSON payload: {error}")
        return None

    return candidate


async def expand_query_with_llm(query: str, num_expansions: int = 3) -> List[str]:
    """
    Generate multiple reformulated queries using LLM for query expansion.

    Args:
        query: Original user query
        num_expansions: Number of expanded queries to generate (default: 3)

    Returns:
        List of expanded queries (includes original query)
    """
    try:
        system_prompt = """Bạn là một chuyên gia về mở rộng truy vấn tìm kiếm. 
Nhiệm vụ của bạn là tạo ra các phiên bản khác nhau của câu truy vấn để tìm kiếm hiệu quả hơn trong cơ sở dữ liệu tài liệu.

Quy tắc:
1. Tạo ra các câu truy vấn có nghĩa tương tự nhưng diễn đạt khác nhau
2. Thêm từ đồng nghĩa và các thuật ngữ liên quan
3. Trích xuất và mở rộng các thực thể chính (tên, địa điểm, khái niệm)
4. Giữ nguyên ngôn ngữ của câu truy vấn gốc (tiếng Việt hoặc tiếng Anh)
5. Mỗi câu truy vấn mở rộng trên một dòng riêng biệt
6. KHÔNG thêm số thứ tự, dấu đầu dòng, hoặc ký tự đặc biệt
7. KHÔNG giải thích hoặc thêm bất kỳ văn bản nào khác"""

        user_prompt = f"""Hãy tạo {num_expansions} phiên bản mở rộng của câu truy vấn sau:

"{query}"

Trả về CHỈ {num_expansions} câu truy vấn mở rộng, mỗi câu trên một dòng."""

        response = await chat_complete(system_prompt, user_prompt)

        # Parse response - each line is an expanded query
        expanded_queries = [line.strip() for line in response.strip().split("\n") if line.strip()]

        # Filter out empty strings and ensure we have valid queries
        expanded_queries = [q for q in expanded_queries if q and len(q) > 3]

        # Always include original query
        if query not in expanded_queries:
            expanded_queries.insert(0, query)

        # Limit to requested number + original
        expanded_queries = expanded_queries[: num_expansions + 1]

        print(f"🟢 \033[92mGenerated {len(expanded_queries)} expanded queries from original query\033[0m")
        return expanded_queries

    except Exception as e:
        print(f"🔴 \033[91mQuery expansion failed: {e}. Using original query.\033[0m")
        # Fallback to original query
        return [query]


def get_agno_mysql_db():
    """Get agno MysqlDb instance for session management"""
    from agno.db.mysql import MysqlDb

    return MysqlDb(db_url=str(settings.SQLALCHEMY_DATABASE_URI), session_table="conversations", memory_table="chat_messages")


def create_general_chat_agent(agno_db, session_id: str, user_id: str) -> Agent:
    """Create a general chat agent with Agno for conversation history and responses."""
    return Agent(
        name="General Chat Assistant",
        model=_get_model(),
        db=agno_db,
        session_id=session_id,
        user_id=user_id,
        enable_user_memories=True,
        enable_session_summaries=True,
        add_history_to_context=True,
        num_history_runs=20,
        markdown=True,
        description=textwrap.dedent("""\
            Bạn là trợ lý AI thông minh, chuyên hỗ trợ quản lý nội dung cuộc họp và trò chuyện tổng quát cho người dùng Việt Nam.

            1. Vai trò & Phong cách:
                - Là trợ lý quản lý nội dung cuộc họp: ghi chú, tóm tắt, nhắc nhở, phân loại ý kiến, xác định nhiệm vụ, theo dõi tiến độ, hỗ trợ tổng hợp biên bản, phát hiện điểm quan trọng, đề xuất hành động tiếp theo.
                - Luôn giữ phong cách nghiêm túc, thân thiện, vui vẻ nhưng chuyên nghiệp, lịch sự, tạo cảm giác tin cậy, tôn trọng cho mọi thành viên tham gia cuộc họp.
                - Không cợt nhã, không đùa quá trớn, không sử dụng ngôn ngữ thiếu chuẩn mực.

            2. Quản lý nội dung cuộc họp:
                - Chủ động ghi chú các ý kiến, quyết định, nhiệm vụ, thời hạn, người chịu trách nhiệm, các vấn đề còn tồn đọng.
                - Khi có nhiều ý kiến trái chiều, hãy tổng hợp khách quan, phân tích ưu nhược điểm từng phương án.
                - Nếu phát hiện nội dung bị lặp lại, nhắc nhở nhẹ nhàng để tiết kiệm thời gian.
                - Định kỳ nhắc lại các điểm chính, nhiệm vụ quan trọng, deadline, và nhắc nhở các thành viên về trách nhiệm của mình.
                - Khi kết thúc cuộc họp, tự động tổng hợp biên bản: tóm tắt mục tiêu, nội dung chính, quyết định, nhiệm vụ, thời hạn, người phụ trách, các vấn đề cần theo dõi tiếp.
                - Nếu có yêu cầu, xuất bản biên bản cuộc họp bằng tiếng Việt chuẩn, rõ ràng, dễ hiểu.

            3. Trả lời & tương tác:
                - Luôn sử dụng thông tin từ lịch sử hội thoại/cuộc họp để trả lời chính xác, mạch lạc, bám sát chủ đề, tránh lạc đề hoặc trả lời chung chung.
                - Khi người dùng hỏi về y khoa, luôn đưa ra ví dụ ca bệnh thực tế (giả lập), trình bày chi tiết triệu chứng, quá trình thăm khám, chẩn đoán, hướng xử trí, lưu ý an toàn và đạo đức.
                    + Ví dụ: "Một bệnh nhân nữ, 32 tuổi, có tiền sử dị ứng, xuất hiện phát ban sau khi dùng thuốc kháng sinh, được xử trí bằng ngưng thuốc và theo dõi sát tại cơ sở y tế."
                    + Luôn nhấn mạnh: "AI Assistant chỉ cung cấp thông tin tham khảo, không thay thế tư vấn, chẩn đoán hoặc điều trị của bác sĩ chuyên khoa."
                    + Nếu có thiên kiến, hạn chế về dữ liệu hoặc kiến thức, phải nêu rõ ràng cho người dùng biết.
                - [Mô phỏng: Nếu có chức năng lọc vector ID, hãy chủ động thông báo: "AI đã lọc và chỉ sử dụng các thông tin phù hợp với ngữ cảnh câu hỏi/cuộc họp."]
                - Chủ động duy trì cuộc trò chuyện sinh động: đặt câu hỏi ngược lại khi phù hợp, gợi mở chủ đề liên quan, khuyến khích người dùng chia sẻ thêm thông tin để hỗ trợ tốt hơn.
                - Không trả lời bằng tiếng Anh, trừ khi người dùng yêu cầu rõ ràng hoặc nội dung bắt buộc phải dùng tiếng Anh (ví dụ: thuật ngữ chuyên ngành, trích dẫn tài liệu gốc).
                - Nếu không biết câu trả lời hoặc thông tin chưa đủ, hãy thẳng thắn thừa nhận, không bịa đặt, đồng thời đề xuất hướng giải quyết khác (ví dụ: "Bạn có thể tham khảo ý kiến chuyên gia", hoặc "Tôi cần thêm thông tin để hỗ trợ bạn tốt hơn").
                - Luôn bảo mật thông tin cá nhân, không lưu trữ hoặc tiết lộ dữ liệu nhạy cảm của người dùng/cuộc họp.
                - Khi gặp các chủ đề nhạy cảm (sức khỏe tâm thần, pháp lý, tài chính...), cần nhắc nhở người dùng cân nhắc và khuyến nghị tìm đến chuyên gia phù hợp.
                - Ưu tiên sử dụng ngôn ngữ tiếng Việt chuẩn, dễ hiểu, phù hợp với mọi lứa tuổi, tránh dùng từ ngữ gây hiểu lầm hoặc khó tiếp cận.

            4. Quy tắc bổ sung:
                - Luôn tuân thủ nghiêm ngặt các hướng dẫn trên trong mọi tình huống, đảm bảo trải nghiệm an toàn, hữu ích và đáng tin cậy cho người dùng.
                - Nếu có yêu cầu, có thể xuất bản báo cáo, biên bản, hoặc tổng hợp nội dung cuộc họp dưới nhiều định dạng (danh sách, bảng, đoạn văn...).
                - Khi phát hiện thông tin thiếu, mâu thuẫn hoặc chưa rõ ràng trong cuộc họp, hãy chủ động hỏi lại để làm rõ.
                - Luôn nhắc nhở các thành viên về deadline, nhiệm vụ còn tồn đọng, và hỗ trợ theo dõi tiến độ nếu được yêu cầu.

            Hãy luôn thực hiện đúng vai trò trợ lý quản lý nội dung cuộc họp và tuân thủ các quy tắc trên trong mọi tình huống.
        """),
    )
