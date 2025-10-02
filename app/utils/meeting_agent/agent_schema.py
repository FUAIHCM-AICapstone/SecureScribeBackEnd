from typing import Annotated, Dict, List, Optional, TypedDict
import unicodedata
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class MeetingState(TypedDict):
	"""Định nghĩa trạng thái cho Meeting Agent workflow"""

	messages: Annotated[List, add_messages]
	transcript: str
	meeting_note: str
	task_items: List[Dict]  # Danh sách các nhiệm vụ được trích xuất riêng
	decision_items: List[Dict]  # Danh sách các quyết định được trích xuất riêng
	question_items: List[Dict]  # Danh sách các câu hỏi được trích xuất riêng
	token_usage: Dict
	is_informative: bool  # Thêm trường để xác định cuộc họp có đủ thông tin không
	meeting_type: str  # Loại cuộc họp: general, project, business, product, report
	custom_prompt: Optional[str]  # Prompt tùy chỉnh từ người dùng


class Task(BaseModel):
	"""Mô hình cho nhiệm vụ được giao trong cuộc họp"""

	description: str = Field(description='Mô tả chi tiết của nhiệm vụ cần thực hiện')
	assignee: str = Field(description='Người được giao nhiệm vụ Xác định rõ tên cho tôi', default='Chưa xác định')
	deadline: str | None = Field(description='Thời hạn hoàn thành nhiệm vụ (định dạng YYYY-MM-DD)', default=None)
	priority: str = Field(description='Mức độ ưu tiên của nhiệm vụ (cao, trung bình, thấp)', default='Trung bình')
	status: str = Field(description='Trạng thái hiện tại của nhiệm vụ (chưa bắt đầu, đang thực hiện, đã hoàn thành)', default='Chưa bắt đầu')
	related_topic: List[str] = Field(description='Các chủ đề liên quan đến nhiệm vụ', default_factory=list)
	notes: str = Field(description='Ghi chú bổ sung về nhiệm vụ', default='Không có ghi chú bổ sung')

	def __init__(self, **data):
		# Ensure assignee has a value
		if 'assignee' not in data or data['assignee'] is None or data['assignee'] == '':
			data['assignee'] = 'Chưa xác định'

		# Ensure deadline has a value
		if 'deadline' not in data or data['deadline'] is None:
			data['deadline'] = 'Cần xác định sau'

		# Ensure priority has a value
		if 'priority' not in data or data['priority'] is None or data['priority'] == '':
			data['priority'] = 'Trung bình'

		# Ensure status has a value
		if 'status' not in data or data['status'] is None or data['status'] == '':
			data['status'] = 'Chưa bắt đầu'

		# Ensure related_topic is a list and normalize if provided
		if 'related_topic' not in data or data['related_topic'] is None:
			data['related_topic'] = []
		elif isinstance(data['related_topic'], list) and data['related_topic']:
			# Process each topic item in the list
			normalized_topics = []
			for topic_item in data['related_topic']:
				# Convert to string if it's not already
				topic_str = str(topic_item).lower().replace('đ', 'd')
				# Normalize Vietnamese characters to their unsign version
				normalized_topic = unicodedata.normalize('NFKD', topic_str)
				normalized_topic = normalized_topic.encode('ASCII', 'ignore').decode('ASCII')
				# Replace spaces with underscores
				normalized_topic = normalized_topic.replace(' ', '_')
				# Remove leading/trailing underscores
				normalized_topic = normalized_topic.strip('_')
				normalized_topics.append(normalized_topic)

			data['related_topic'] = normalized_topics

		# Ensure notes has a value
		if 'notes' not in data or data['notes'] is None:
			data['notes'] = 'Không có ghi chú bổ sung'

		super().__init__(**data)


class Decision(BaseModel):
	"""Mô hình cho quyết định được đưa ra trong cuộc họp"""

	topic: List[str] = Field(description='Chủ đề của quyết định')
	decision: str = Field(description='Nội dung chi tiết của quyết định')
	impact: str = Field(description='Tác động của quyết định (nếu được đề cập)')
	timeline: Optional[str] = Field(description='Thời gian thực hiện (nếu được đề cập)')
	stakeholders: List[str] = Field(description='Những người liên quan đến quyết định')
	next_steps: Optional[List[str]] = Field(description='Identify and list the next steps or action items discussed during the meeting, and provide your response in Vietnamese.')

	def __init__(self, **data):
		if 'topic' in data and isinstance(data['topic'], list) and data['topic']:
			# Process each topic item in the list
			normalized_topics = []
			for topic_item in data['topic']:
				# Convert to string if it's not already
				topic_str = str(topic_item).lower().replace('đ', 'd')
				# Normalize Vietnamese characters to their unsign version
				normalized_topic = unicodedata.normalize('NFKD', topic_str)
				normalized_topic = normalized_topic.encode('ASCII', 'ignore').decode('ASCII')
				# Replace spaces with underscores
				normalized_topic = normalized_topic.replace(' ', '_')
				# Remove leading/trailing underscores
				normalized_topic = normalized_topic.strip('_')
				normalized_topics.append(normalized_topic)

			data['topic'] = normalized_topics
		super().__init__(**data)


class Question(BaseModel):
	"""Mô hình cho câu hỏi được nêu ra trong cuộc họp"""

	question: str = Field(description='Nội dung câu hỏi')
	asker: Optional[str] = Field(description='Người đặt câu hỏi (nếu có thể xác định)')
	answer: Optional[str] = Field(description='Câu trả lời cho câu hỏi (nếu có)')
	answered: bool = Field(description='Câu hỏi đã được trả lời hay chưa')
	topic: List[str] = Field(description='Chủ đề liên quan của câu hỏi')
	follow_up_actions: List[Task] = Field(description='Các hành động cần thực hiện sau khi câu hỏi được nêu ra hoặc trả lời', default_factory=list)
	context: Optional[str] = Field(description='Bối cảnh của câu hỏi, tại sao câu hỏi này được đặt ra', default=None)
	importance: Optional[str] = Field(description='Mức độ quan trọng của câu hỏi (cao, trung bình, thấp)', default=None)

	def __init__(self, **data):
		if 'topic' in data and isinstance(data['topic'], list) and data['topic']:
			# Process each topic item in the list
			normalized_topics = []
			for topic_item in data['topic']:
				# Convert to string if it's not already
				topic_str = str(topic_item).lower().replace('đ', 'd')
				# Normalize Vietnamese characters to their unsign version
				normalized_topic = unicodedata.normalize('NFKD', topic_str)
				normalized_topic = normalized_topic.encode('ASCII', 'ignore').decode('ASCII')
				# Replace spaces with underscores
				normalized_topic = normalized_topic.replace(' ', '_')
				# Remove leading/trailing underscores
				normalized_topic = normalized_topic.strip('_')
				normalized_topics.append(normalized_topic)

			data['topic'] = normalized_topics
		super().__init__(**data)


# Tạo các mô hình riêng biệt cho từng loại trích xuất
class TaskItems(BaseModel):
	"""Mô hình chứa danh sách các nhiệm vụ được trích xuất từ cuộc họp"""

	tasks: List[Task] = Field(description='Danh sách các nhiệm vụ được giao trong cuộc họp, người phụ trách và thời hạn', default_factory=list)


class DecisionItems(BaseModel):
	"""Mô hình chứa danh sách các quyết định được trích xuất từ cuộc họp"""

	decisions: List[Decision] = Field(description='Danh sách các quyết định chính được đưa ra trong cuộc họp, bao gồm chủ đề, nội dung, tác động và các bước tiếp theo', default_factory=list)


class QuestionItems(BaseModel):
	"""Mô hình chứa danh sách các câu hỏi được trích xuất từ cuộc họp"""

	questions: List[Question] = Field(description='Danh sách các câu hỏi được nêu ra trong cuộc họp, bao gồm người hỏi, nội dung câu hỏi và trạng thái đã được trả lời hay chưa', default_factory=list)
