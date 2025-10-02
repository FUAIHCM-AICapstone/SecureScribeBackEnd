import logging

from app.utils.meeting_agent.agent_schema import MeetingState
from langchain_core.messages import SystemMessage
from app.utils.meeting_agent.utils import calculate_price


class OutputGenerator:
	def __init__(self, token_tracker):
		self.token_tracker = token_tracker
		self.logger = logging.getLogger('OutputGenerator')

	def generate(self, state: MeetingState) -> MeetingState:
		self.logger.info('Generating final output')
		token_usage = {
			'input_tokens': self.token_tracker.input_tokens,
			'output_tokens': self.token_tracker.output_tokens,
			'context_tokens': self.token_tracker.context_tokens,
			'total_tokens': self.token_tracker.total_tokens,
			'price_usd': round(calculate_price(self.token_tracker.input_tokens, self.token_tracker.output_tokens, self.token_tracker.context_tokens), 6),
		}
		return {**state, 'token_usage': token_usage, 'messages': state['messages'] + [SystemMessage(content='Đã hoàn thành xử lý cuộc họp')]}
