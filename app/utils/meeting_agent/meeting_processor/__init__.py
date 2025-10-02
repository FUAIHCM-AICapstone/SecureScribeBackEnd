import logging
import uuid

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.utils.meeting_agent.agent_schema import MeetingState
from app.utils.meeting_agent.llm_setup import initialize_llm
from app.utils.meeting_agent.meeting_processor.informative_checker import InformativeChecker
from app.utils.meeting_agent.meeting_processor.output_generator import OutputGenerator
from app.utils.meeting_agent.meeting_processor.simple_note_generator import SimpleMeetingNoteGenerator
from app.utils.meeting_agent.meeting_processor.summary_extractor import SummaryExtractor
from app.utils.meeting_agent.meeting_prompts import get_meeting_type_detector_prompt
from app.utils.meeting_agent.utils import TokenTracker, calculate_price


class MeetingTypeDetector:
	"""Detects meeting type from transcript content."""

	def __init__(self, llm, token_tracker):
		self.llm = llm
		self.token_tracker = token_tracker
		self.logger = logging.getLogger('MeetingTypeDetector')

	def detect(self, state: MeetingState) -> MeetingState:
		"""Detects the meeting type based on transcript content if not already provided."""
		self.logger.info('Detecting meeting type from transcript')
		# If meeting type is already set and not 'general', use that
		if state.get('meeting_type') and state.get('meeting_type') != 'general':
			self.logger.info(f'Using provided meeting type: {state.get("meeting_type")}')
			return state

		# If transcript is empty or too short, return general
		transcript = state.get('transcript', '')
		if not transcript or len(transcript) < 50:
			self.logger.warning('Transcript too short for reliable meeting type detection')
			return {**state, 'meeting_type': 'general'}

		# Prepare sample of transcript to analyze (first 2000 chars to save tokens)
		transcript_sample = transcript[:2000]

		try:
			# Get detector prompt
			detector_prompt = get_meeting_type_detector_prompt()

			# Call LLM to detect meeting type
			response = self.llm.invoke(detector_prompt + f'\n\nTranscript:\n{transcript_sample}')
			detected_type = response.content.strip().lower()

			# Validate detected type
			valid_types = ['general', 'project', 'business', 'product', 'report']
			if detected_type not in valid_types:
				self.logger.warning(f"Invalid meeting type detected: {detected_type}. Using 'general' instead.")
				detected_type = 'general'

			self.logger.info(f'Detected meeting type: {detected_type}')

			# Return updated state with detected meeting type
			return {
				**state,
				'meeting_type': detected_type,
				'messages': state['messages'] + [HumanMessage(content='Phân tích loại cuộc họp'), AIMessage(content=f'Đã xác định đây là cuộc họp loại: {detected_type}')],
			}

		except Exception as e:
			self.logger.error(f'Error detecting meeting type: {str(e)}')
			return {**state, 'meeting_type': 'general'}


class MeetingProcessor:
	def __init__(self, api_key: str, meeting_type: str = 'general'):
		self.logger = logging.getLogger('MeetingProcessor')
		self.llm = initialize_llm(api_key)
		self.memory = MemorySaver()
		self.token_tracker = TokenTracker()
		self.meeting_type = meeting_type.lower() if meeting_type else 'general'
		self.meeting_type_detector = MeetingTypeDetector(self.llm, self.token_tracker)
		self.informative_checker = InformativeChecker(self.llm, self.token_tracker)
		self.summary_extractor = SummaryExtractor(self.llm, self.token_tracker)
		self.simple_note_generator = SimpleMeetingNoteGenerator(self.llm, self.token_tracker)
		self.output_generator = OutputGenerator(self.token_tracker)
		self.workflow = self._build_workflow()

	def _build_workflow(self):
		self.logger.info('Building workflow')
		workflow = StateGraph(MeetingState)

		# Add all nodes
		workflow.add_node('detect_meeting_type', self.meeting_type_detector.detect)
		workflow.add_node('check_informative', self.informative_checker.check)

		# Add nodes for the three-phase extraction
		workflow.add_node('extract_tasks', self.summary_extractor.extract_tasks)
		workflow.add_node('extract_decisions', self.summary_extractor.extract_decisions)
		workflow.add_node('extract_questions', self.summary_extractor.extract_questions)

		workflow.add_node('generate_simple_note', self.simple_note_generator.generate)
		workflow.add_node('generate_output', self.output_generator.generate)

		# Start with meeting type detection
		workflow.add_edge(START, 'detect_meeting_type')
		workflow.add_edge('detect_meeting_type', 'check_informative')

		# Check if transcript is informative
		workflow.add_conditional_edges(
			'check_informative', lambda state: 'extract_tasks' if state['is_informative'] else 'generate_output', {'extract_tasks': 'extract_tasks', 'generate_output': 'generate_output'}
		)

		# Three-phase extraction workflow
		workflow.add_edge('extract_tasks', 'extract_decisions')
		workflow.add_edge('extract_decisions', 'extract_questions')
		workflow.add_edge('extract_questions', 'generate_simple_note')

		workflow.add_edge('generate_simple_note', 'generate_output')

		# End workflow
		workflow.add_edge('generate_output', END)

		return workflow.compile(checkpointer=self.memory)

	async def process_meeting(self, transcript: str, custom_prompt: str = None):
		self.logger.info('Starting meeting processing')
		thread_id = str(uuid.uuid4())
		config = {'configurable': {'thread_id': thread_id}}
		transcript = transcript or ''
		initial_state = {
			'messages': [SystemMessage(content='Bạn là trợ lý thông minh chuyên ghi chú cuộc họp...')],
			'transcript': transcript,
			'meeting_note': '',
			'task_items': [],  # Initialize task_items
			'decision_items': [],  # Initialize decision_items
			'question_items': [],  # Initialize question_items
			'token_usage': {},
			'is_informative': False,
			'meeting_type': self.meeting_type,
			'custom_prompt': custom_prompt,  # Add custom_prompt to the state
		}
		try:
			result = await self.workflow.ainvoke(initial_state, config)
			return {
				'meeting_note': result['meeting_note'],
				'task_items': result.get('task_items', []),
				'decision_items': result.get('decision_items', []),
				'question_items': result.get('question_items', []),
				'token_usage': result['token_usage'],
				'is_informative': result['is_informative'],
				'meeting_type': result['meeting_type'],
				# Include separate extraction results in the output
			}
		except Exception as e:
			self.logger.error(f'Error processing meeting: {str(e)}')
			return {
				'meeting_note': '',
				'task_items': [],
				'decision_items': [],
				'question_items': [],
				'token_usage': {
					'input_tokens': self.token_tracker.input_tokens,
					'output_tokens': self.token_tracker.output_tokens,
					'context_tokens': self.token_tracker.context_tokens,
					'total_tokens': self.token_tracker.total_tokens,
					'price_usd': round(calculate_price(self.token_tracker.input_tokens, self.token_tracker.output_tokens, self.token_tracker.context_tokens), 6),
				},
				'is_informative': False,
				'meeting_type': self.meeting_type,
			}
