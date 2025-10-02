from app.core.config import GOOGLE_API_KEY
from .meeting_processor import MeetingProcessor

import logging

# Initialize LiteLLM settings
try:
	import litellm

	# Force LiteLLM to drop unsupported parameters
	litellm.drop_params = True
	litellm.set_verbose = True
except ImportError:
	pass


class MeetingAnalyzer:
	def __init__(self):
		self.logger = logging.getLogger('MeetingAnalyzer')
		self.meeting_processor = MeetingProcessor(api_key=GOOGLE_API_KEY)

	async def complete(
		self,
		transcript: str,
		meeting_type: str = None,
		custom_prompt: str = None,
	):
		try:
			self.logger.info(f'Processing meeting transcript with length: {len(transcript or "")}')

			# Create a new processor instance with the specified meeting type if provided
			if meeting_type:
				self.logger.info(f'Using specified meeting type: {meeting_type}')
				processor = MeetingProcessor(api_key=GOOGLE_API_KEY, meeting_type=meeting_type)
			else:
				self.logger.info('No meeting type specified, using default or auto-detection')
				processor = self.meeting_processor

			# Log custom prompt if provided
			if custom_prompt:
				self.logger.info('Using custom prompt for meeting analysis')

			result = await processor.process_meeting(transcript, custom_prompt=custom_prompt)
			# if email:
			#     self.SendEmail.send_meeting_note_to_email(email=email, note=result['meeting_note'])
			return result
		except Exception as e:
			self.logger.error(f'Error in complete: {str(e)}')
			return {
				'meeting_note': '',  # Include empty meeting note on error
				'task_items': [],
				'decision_items': [],
				'question_items': [],
				'token_usage': {
					'input_tokens': 0,
					'output_tokens': 0,
					'context_tokens': 0,
					'total_tokens': 0,
					'price_usd': 0,
				},
				'is_informative': False,
				'meeting_type': meeting_type or 'general',
			}
