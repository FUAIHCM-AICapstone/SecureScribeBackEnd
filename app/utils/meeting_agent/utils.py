import json
import re
from typing import Dict

import tiktoken

from app.core.config import (
	CONTEXT_PRICE_PER_MILLION,
	INPUT_PRICE_PER_MILLION,
	OUTPUT_PRICE_PER_MILLION,
)
from app.utils.meeting_agent.agent_schema import MeetingState


def calculate_price(input_tokens: int, output_tokens: int, context_tokens: int = 0) -> float:
	"""Calculate total price based on token usage.

	Args:
	    input_tokens (int): Number of input tokens
	    output_tokens (int): Number of output tokens
	    context_tokens (int): Number of context tokens

	Returns:
	    float: Total price in USD
	"""
	input_price = (input_tokens / 1_000_000) * INPUT_PRICE_PER_MILLION
	output_price = (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_MILLION
	context_price = (context_tokens / 1_000_000) * CONTEXT_PRICE_PER_MILLION
	return input_price + output_price + context_price


def parse_json_from_response(response: str) -> Dict:
	"""_summary_

	Args:
	    response (str): _description_

	Returns:
	    Dict: _description_
	"""

	try:
		parsed_response = json.loads(response)
	except json.JSONDecodeError:
		try:
			new_response = response.split('```')[1][5:]
			parsed_response = json.loads(new_response)
		except json.JSONDecodeError:
			pattern = r'(json)\s*({.*})'
			match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)

			if match:
				parsed_response = json.loads(match.group(2))
			else:
				parsed_response = {}
	return parsed_response


def count_tokens(text: str, model: str = 'gpt-4') -> int:
	"""Count the number of tokens in a text string.

	Args:
	    text (str): The text to count tokens for
	    model (str): The model to use for counting tokens

	Returns:
	    int: Number of tokens
	"""
	if not text:
		return 0

	# Handle Gemini models
	if 'gemini' in model.lower():
		# Gemini approximates tokens as ~4 characters per token
		return len(text) // 4

	# Handle Google/Vertex AI models through LiteLLM
	elif model.lower().startswith(('google/', 'vertex_ai/')):
		# Use same approximation for Google models
		return len(text) // 4

	# Handle OpenAI models with tiktoken
	else:
		try:
			encoding = tiktoken.encoding_for_model(model)
			return len(encoding.encode(text))
		except (KeyError, ValueError, ImportError):
			# Fallback for unknown models
			# Average English text is ~4 chars per token
			return len(text) // 4


def generate_meeting_note(meeting_state: MeetingState) -> str:
	"""Generate a Markdown formatted meeting note from the provided meeting state.

	Args:
	    meeting_state (MeetingState): Processed meeting data containing:
	        - chunk_summaries: List of ChunkSummary objects.
	        - meeting_items: List of MeetingItems objects (each with decisions, action_items, and questions).

	Returns:
	    str: Markdown formatted meeting note.
	"""
	result = []

	result.append('# 📋 Biên bản cuộc họp\n')

	chunk_summaries = meeting_state.get('chunk_summaries', [])

	best_chunk = None
	max_info_count = -1

	for chunk in chunk_summaries:
		if not hasattr(chunk, 'summary') or not chunk.summary or chunk.summary == 'Không đủ thông tin có ý nghĩa để tóm tắt':
			continue

		info_count = (
			len(getattr(chunk, 'key_points', []))
			+ len(getattr(chunk, 'facts', []))
			+ len(getattr(chunk, 'problems', []))
			+ len(getattr(chunk, 'solutions', []))
			+ len(getattr(chunk, 'risks', []))
			+ len(getattr(chunk, 'next_steps', []))
		)

		if info_count > max_info_count:
			max_info_count = info_count
			best_chunk = chunk

	if best_chunk is None and chunk_summaries:
		best_chunk = chunk_summaries[0]

	all_key_points = []
	all_facts = []
	all_problems = []
	all_solutions = []
	all_risks = []
	all_next_steps = []

	for chunk in chunk_summaries:
		all_key_points.extend(getattr(chunk, 'key_points', []))
		all_facts.extend(getattr(chunk, 'facts', []))
		all_problems.extend(getattr(chunk, 'problems', []))
		all_solutions.extend(getattr(chunk, 'solutions', []))
		all_risks.extend(getattr(chunk, 'risks', []))
		all_next_steps.extend(getattr(chunk, 'next_steps', []))

	all_key_points = list(dict.fromkeys(all_key_points))
	all_facts = list(dict.fromkeys(all_facts))
	all_problems = list(dict.fromkeys(all_problems))
	all_solutions = list(dict.fromkeys(all_solutions))
	all_risks = list(dict.fromkeys(all_risks))
	all_next_steps = list(dict.fromkeys(all_next_steps))

	if best_chunk and hasattr(best_chunk, 'agenda') and best_chunk.agenda and best_chunk.agenda != 'Không đủ thông tin để xác định chương trình nghị sự':
		result.append('## 🧭 Chương trình nghị sự')
		result.append(f'- {best_chunk.agenda}\n')

	if best_chunk and hasattr(best_chunk, 'summary') and best_chunk.summary and best_chunk.summary != 'Không đủ thông tin có ý nghĩa để tóm tắt':
		result.append('## 📝 Tóm tắt')
		result.append(f'{best_chunk.summary}\n')

	def add_bullet_section(title: str, items: list):
		if items:
			result.append(f'## {title}')
			for item in items:
				result.append(f'- {item}')
			result.append('')

	add_bullet_section('🔑 Điểm chính', all_key_points)
	add_bullet_section('📌 Thông tin quan trọng', all_facts)
	add_bullet_section('⚠️ Vấn đề', all_problems)
	add_bullet_section('💡 Giải pháp', all_solutions)
	add_bullet_section('🚧 Rủi ro', all_risks)
	add_bullet_section('📍 Bước tiếp theo', all_next_steps)

	decisions = []
	action_items = []
	questions = []

	for item in meeting_state.get('meeting_items', []):
		if hasattr(item, 'decisions') and item.decisions:
			decisions.extend(item.decisions)
		if hasattr(item, 'action_items') and item.action_items:
			action_items.extend(item.action_items)
		if hasattr(item, 'questions') and item.questions:
			questions.extend(item.questions)

	if decisions:
		result.append('## ✅ Quyết định')
		for idx, d in enumerate(decisions, 1):
			topics = ' / '.join(d.topic) if d.topic else f'Quyết định {idx}'
			result.append(f'### {idx}. {topics}')
			result.append(f'- **Nội dung quyết định**: {d.decision}')
			if d.impact:
				result.append(f'- **Tác động**: {d.impact}')
			if d.timeline:
				result.append(f'- **Thời gian**: {d.timeline}')
			if d.stakeholders:
				result.append(f'- **Người liên quan**: {", ".join(d.stakeholders)}')
			if d.next_steps:
				result.append(f'- **Bước tiếp theo**: ' + '; '.join(d.next_steps))
			result.append('')

	if action_items:
		result.append('## 📌 Nhiệm vụ')
		for idx, a in enumerate(action_items, 1):
			topics = ', '.join(a.topic) if a.topic else f'Nhiệm vụ {idx}'
			result.append(f'### {idx}. {topics}')
			result.append(f'- **Người thực hiện**: {a.assignee}')
			result.append(f'- **Nhiệm vụ**: {a.task}')
			if a.deadline:
				result.append(f'- **Hạn chót**: {a.deadline}')
			result.append('')

	if questions:
		result.append('## ❓ Câu hỏi')
		for idx, q in enumerate(questions, 1):
			result.append(f'### {idx}. {q.question}')
			if q.asker:
				result.append(f'- **Người hỏi**: {q.asker}')
			result.append(f'- **Đã trả lời**: {"✅ Có" if q.answered else "❌ Chưa"}')
			if q.answer:
				result.append(f'- **Câu trả lời**: {q.answer}')
			if q.topic:
				result.append(f'- **Chủ đề**: {", ".join(q.topic)}')
			result.append('')

	if len(result) <= 2:  # Chỉ có tiêu đề và xuống dòng
		result.append('## ℹ️ Thông báo')
		result.append('Không tìm thấy đủ thông tin có ý nghĩa để tạo ghi chú cuộc họp chi tiết.')
		result.append('Vui lòng cung cấp transcript hoàn chỉnh hơn để có kết quả tốt hơn.')

	return '\n'.join(result)


class TokenTracker:
	def __init__(self):
		self.input_tokens = 0
		self.output_tokens = 0
		self.context_tokens = 0

	@property
	def total_tokens(self):
		return self.input_tokens + self.output_tokens + self.context_tokens

	def add_input_tokens(self, tokens: int):
		self.input_tokens += tokens

	def add_output_tokens(self, tokens: int):
		self.output_tokens += tokens

	def add_context_tokens(self, tokens: int):
		self.context_tokens += tokens
