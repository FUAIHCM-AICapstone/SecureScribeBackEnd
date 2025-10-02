import logging
import time

from langchain_core.messages import AIMessage, HumanMessage

from app.utils.meeting_agent.agent_schema import MeetingState


class InformativeChecker:
	def __init__(self, llm, token_tracker):
		self.llm = llm
		self.token_tracker = token_tracker
		self.logger = logging.getLogger('InformativeChecker')

	def check(self, state: MeetingState) -> MeetingState:
		self.logger.info('Checking if meeting transcript is informative enough')
		start_time = time.time()
		transcript = state['transcript']

		if not transcript or not transcript.strip():
			self.logger.warning('Transcript is empty or None')
			return {**state, 'is_informative': False, 'messages': state['messages'] + [HumanMessage(content='Kiểm tra nội dung transcript'), AIMessage(content='Transcript trống hoặc không hợp lệ')]}

		if len(transcript.strip()) < 100:
			self.logger.warning(f'Transcript too short: {len(transcript.strip())} chars')
			return {
				**state,
				'is_informative': False,
				'messages': state['messages'] + [HumanMessage(content='Kiểm tra nội dung transcript'), AIMessage(content=f'Transcript quá ngắn ({len(transcript.strip())} ký tự)')],
			}

		self.logger.info('Transcript is informative')
		duration = time.time() - start_time
		self.logger.info(f'Check completed in {duration:.2f} seconds')
		return {**state, 'is_informative': True, 'messages': state['messages'] + [HumanMessage(content='Kiểm tra nội dung transcript'), AIMessage(content='Transcript đủ thông tin để xử lý')]}
