import json
import logging
import time
from typing import List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.utils.meeting_agent.agent_schema import DecisionItems, MeetingState, QuestionItems, Task, TaskItems
from app.utils.meeting_agent.meeting_prompts import get_decision_extraction_prompt, get_question_extraction_prompt, get_task_extraction_prompt
from app.utils.meeting_agent.utils import TokenTracker, count_tokens


class SummaryExtractor:
	def __init__(self, llm, token_tracker):
		self.llm = llm
		self.token_tracker: TokenTracker = token_tracker
		self.logger = logging.getLogger('SummaryExtractor')

	def _invoke_llm(self, prompt):
		return self.llm.invoke(prompt)

	def _invoke_with_messages_and_rate_limit(self, chain, messages):
		"""Helper method to invoke LLM with messages and rate limit handling"""
		result = chain.invoke(messages)
		# Return result as list to match expected structure
		return [result] if result is not None else []

	def _extract_items_from_transcript(self, transcript: str, schema: type, item_type: str, system_prompt: str = '', prompt_prefix: str = '') -> List:
		"""
		General method to extract items from transcript using a specific schema.

		Args:
		    transcript: The meeting transcript
		    schema: The Pydantic model to use for structured output
		    item_type: Type of items being extracted ("tasks", "decisions", or "questions")
		    system_prompt: Custom system prompt to use
		    prompt_prefix: Additional prefix to add to the prompt for more specific instructions

		Returns:
		    List of extracted items
		"""
		self.logger.info(f'Starting {item_type} extraction process')
		start_time = time.time()

		if transcript is None or not transcript.strip():
			self.logger.warning(f'Transcript is empty or None, skipping {item_type} extraction')
			return []

		if not system_prompt:
			meeting_type = getattr(self, 'meeting_type', 'general')
			self.logger.info(f'Using {meeting_type} meeting prompt for {item_type} extraction')

			# Load appropriate prompt based on item type
			if item_type == 'tasks':
				system_prompt = get_task_extraction_prompt(meeting_type)
			elif item_type == 'decisions':
				system_prompt = get_decision_extraction_prompt(meeting_type)
			elif item_type == 'questions':
				system_prompt = get_question_extraction_prompt(meeting_type)

		# Add specific instruction based on item type
		if prompt_prefix:
			system_prompt = prompt_prefix + '\n\n' + system_prompt

		self.logger.info(f'Processing full transcript with length: {len(transcript)} characters')

		input_tokens = count_tokens(transcript, 'gemini')
		self.token_tracker.add_input_tokens(input_tokens)

		extract_chain = self.llm.with_structured_output(schema)

		try:
			if system_prompt:
				messages = [SystemMessage(content=system_prompt), HumanMessage(content=f'Đây là transcript đầy đủ của cuộc họp. Hãy trích xuất {item_type} từ cuộc họp này: {transcript}')]
				result = self._invoke_with_messages_and_rate_limit(extract_chain, messages)
			else:
				result = self._invoke_llm(extract_chain, transcript)

			items = []
			if isinstance(result, list):
				items = [item for item in result if item is not None]
			elif result is not None:
				items = [result]

			# Process the items to fill in any null fields with default values
			# The specific processing depends on the item type
			if item_type == 'tasks':
				items = self._process_task_items(items)
			elif item_type == 'decisions':
				items = self._process_decision_items(items)
			elif item_type == 'questions':
				items = self._process_question_items(items)

			# Track output tokens
			try:
				output_str = json.dumps([item.dict() for item in items if hasattr(item, 'dict')])
				output_tokens = count_tokens(output_str, 'gemini')
				self.token_tracker.add_output_tokens(output_tokens)
				self.logger.info(f'Output tokens: {output_tokens}')
			except Exception as e:
				self.logger.error(f'Error calculating output tokens: {str(e)}')

		except Exception as e:
			self.logger.error(f'Error processing transcript for {item_type}: {str(e)}')
			items = []

		duration = time.time() - start_time
		self.logger.info(f'{item_type.capitalize()} extraction completed in {duration:.2f} seconds, found {len(items)} items')
		return items

	def _process_task_items(self, items):
		"""Process task items to ensure all fields have values"""
		processed_items = []
		for item in items:
			if hasattr(item, 'tasks'):
				# For each task in the list, ensure all fields have values
				processed_tasks = []
				for task in item.tasks:
					# Create a new Task with all fields properly filled
					task_dict = task.dict() if hasattr(task, 'dict') else task
					processed_task = Task(
						description=task_dict.get('description', 'Nhiệm vụ chưa được mô tả chi tiết'),
						assignee=task_dict.get('assignee') or 'Chưa xác định',
						deadline=task_dict.get('deadline') or 'Cần xác định sau',
						priority=task_dict.get('priority') or 'Trung bình',
						status=task_dict.get('status') or 'Chưa bắt đầu',
						related_topic=task_dict.get('related_topic') or [],
						notes=task_dict.get('notes') or 'Không có ghi chú bổ sung',
					)
					processed_tasks.append(processed_task)
				item.tasks = processed_tasks
			processed_items.append(item)
		return processed_items

	def _process_decision_items(self, items):
		"""Process decision items to ensure all fields have values"""
		processed_items = []
		for item in items:
			if hasattr(item, 'decisions'):
				for decision in item.decisions:
					# Process tasks in decisions
					if hasattr(decision, 'tasks'):
						processed_tasks = []
						for task in decision.tasks:
							task_dict = task.dict() if hasattr(task, 'dict') else task
							processed_task = Task(
								description=task_dict.get('description', 'Nhiệm vụ chưa được mô tả chi tiết'),
								assignee=task_dict.get('assignee') or 'Chưa xác định',
								deadline=task_dict.get('deadline') or 'Cần xác định sau',
								priority=task_dict.get('priority') or 'Trung bình',
								status=task_dict.get('status') or 'Chưa bắt đầu',
								related_topic=task_dict.get('related_topic') or [],
								notes=task_dict.get('notes') or 'Không có ghi chú bổ sung',
							)
							processed_tasks.append(processed_task)
						decision.tasks = processed_tasks
			processed_items.append(item)
		return processed_items

	def _process_question_items(self, items):
		"""Process question items to ensure all fields have values"""
		processed_items = []
		for item in items:
			if hasattr(item, 'questions'):
				for question in item.questions:
					# Process follow-up actions in questions
					if hasattr(question, 'follow_up_actions'):
						processed_actions = []
						for action in question.follow_up_actions:
							action_dict = action.dict() if hasattr(action, 'dict') else action
							processed_action = Task(
								description=action_dict.get('description', 'Hành động cần thực hiện chưa được mô tả chi tiết'),
								assignee=action_dict.get('assignee') or 'Chưa xác định',
								deadline=action_dict.get('deadline') or 'Cần xác định sau',
								priority=action_dict.get('priority') or 'Trung bình',
								status=action_dict.get('status') or 'Chưa bắt đầu',
								related_topic=action_dict.get('related_topic') or [],
								notes=action_dict.get('notes') or 'Không có ghi chú bổ sung',
							)
							processed_actions.append(processed_action)
						question.follow_up_actions = processed_actions
			processed_items.append(item)
		return processed_items

	def extract_tasks(self, state: MeetingState) -> MeetingState:
		"""Extract tasks from the transcript"""
		self.meeting_type = state.get('meeting_type', 'general')
		self.logger.info(f'Extracting tasks from transcript using meeting type: {self.meeting_type}')

		# Use default task prompt prefix
		system_prompt = get_task_extraction_prompt(self.meeting_type)
		task_prompt_prefix = """
        Nhiệm vụ của bạn là phân tích cẩn thận transcript cuộc họp và chỉ trích xuất ra các NHIỆM VỤ được giao cho các thành viên.
        Cố gắng xác định tên người nói dựa vào nội dung cuộc họp không nên dựa vào SPEAKER ID
        Hãy tập trung vào việc xác định:
        - Nhiệm vụ cụ thể cần thực hiện
        - Người được giao nhiệm vụ
        - Thời hạn hoàn thành (nếu được nhắc đến)
        - Mức độ ưu tiên (nếu được nhắc đến)
        - Trạng thái hiện tại của nhiệm vụ
        - Quan hệ phụ thuộc giữa các nhiệm vụ (nếu có)
        - Các chủ đề liên quan đến nhiệm vụ
        
        ĐỪNG trích xuất các quyết định hoặc câu hỏi, chỉ tập trung vào các NHIỆM VỤ.
        """

		# Extract tasks from transcript
		extracted_tasks = self._extract_items_from_transcript(state['transcript'], TaskItems, 'tasks', system_prompt=system_prompt, prompt_prefix=task_prompt_prefix)

		# Update state
		updated_state = {
			**state,
			'task_items': extracted_tasks,
			'messages': state['messages']
			+ [HumanMessage(content=f'Trích xuất các nhiệm vụ từ cuộc họp'), AIMessage(content=f'Đã tìm thấy {sum(len(item.tasks) for item in extracted_tasks if hasattr(item, "tasks"))} nhiệm vụ')],
		}

		return updated_state

	def extract_decisions(self, state: MeetingState) -> MeetingState:
		"""Extract decisions from the transcript"""
		self.meeting_type = state.get('meeting_type', 'general')
		self.logger.info(f'Extracting decisions from transcript using meeting type: {self.meeting_type}')

		system_prompt = get_decision_extraction_prompt(self.meeting_type)
		prompt_prefix = """
        Nhiệm vụ của bạn là phân tích cẩn thận transcript cuộc họp và chỉ trích xuất ra các QUYẾT ĐỊNH được đưa ra.
        Cố gắng xác định tên người nói dựa vào nội dung cuộc họp không nên dựa vào SPEAKER ID
        Hãy tập trung vào việc xác định:
        - Nội dung chi tiết của quyết định
        - Chủ đề liên quan
        - Tác động của quyết định
        - Thời gian thực hiện (nếu được nhắc đến)
        - Những người liên quan đến quyết định
        - Các bước tiếp theo sau quyết định
        - Bối cảnh đưa ra quyết định
        - Các phương án thay thế đã được cân nhắc
        
        Hãy cũng xác định các nhiệm vụ cụ thể cần thực hiện liên quan đến mỗi quyết định.
        
        ĐỪNG trích xuất các nhiệm vụ riêng lẻ hoặc câu hỏi, chỉ tập trung vào các QUYẾT ĐỊNH.
        """

		# Extract decisions from transcript
		extracted_decisions = self._extract_items_from_transcript(state['transcript'], DecisionItems, 'decisions', system_prompt=system_prompt, prompt_prefix=prompt_prefix)

		# Update state
		updated_state = {
			**state,
			'decision_items': extracted_decisions,
			'messages': state['messages']
			+ [
				HumanMessage(content=f'Trích xuất các quyết định từ cuộc họp'),
				AIMessage(content=f'Đã tìm thấy {sum(len(item.decisions) for item in extracted_decisions if hasattr(item, "decisions"))} quyết định'),
			],
		}

		return updated_state

	def extract_questions(self, state: MeetingState) -> MeetingState:
		"""Extract questions from the transcript"""
		self.meeting_type = state.get('meeting_type', 'general')
		self.logger.info(f'Extracting questions from transcript using meeting type: {self.meeting_type}')

		# Use default question prompt prefix
		system_prompt = get_question_extraction_prompt(self.meeting_type)
		prompt_prefix = """
        Nhiệm vụ của bạn là phân tích cẩn thận transcript cuộc họp và chỉ trích xuất ra các CÂU HỎI được nêu ra.
        Cố gắng xác định tên người nói dựa vào nội dung cuộc họp không nên dựa vào SPEAKER ID
        Hãy tập trung vào việc xác định:
        - Nội dung chi tiết của câu hỏi
        - Người đặt câu hỏi (nếu có thể xác định)
        - Câu trả lời (nếu có)
        - Trạng thái đã được trả lời hay chưa
        - Chủ đề liên quan của câu hỏi
        - Bối cảnh của câu hỏi
        - Mức độ quan trọng của câu hỏi
        
        Hãy cũng xác định các hành động cần thực hiện sau khi câu hỏi được nêu ra.
        
        ĐỪNG trích xuất các quyết định hoặc nhiệm vụ riêng lẻ, chỉ tập trung vào các CÂU HỎI.
        """

		# Extract questions from transcript
		extracted_questions = self._extract_items_from_transcript(state['transcript'], QuestionItems, 'questions', system_prompt=system_prompt, prompt_prefix=prompt_prefix)

		# Update state
		updated_state = {
			**state,
			'question_items': extracted_questions,
			'messages': state['messages']
			+ [
				HumanMessage(content=f'Trích xuất các câu hỏi từ cuộc họp'),
				AIMessage(content=f'Đã tìm thấy {sum(len(item.questions) for item in extracted_questions if hasattr(item, "questions"))} câu hỏi'),
			],
		}

		return updated_state
