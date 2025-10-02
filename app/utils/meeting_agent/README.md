# Meeting Agent Module

## Overview

The Meeting Agent module is an intelligent meeting analysis system that processes meeting transcripts to extract key information, generate meeting notes, and identify actionable items. It uses AI-powered natural language processing to analyze meeting content and produce structured outputs in Vietnamese.

## Architecture

The module is built using a **LangGraph-based workflow** that orchestrates multiple AI agents to perform specialized tasks:

```
Transcript Input → Meeting Type Detection → Informative Check → [Extraction Phase] → Note Generation → Output
```

## Core Components

### 1. MeetingAnalyzer (Main Interface)
```python
from app.utils.meeting_agent import MeetingAnalyzer

analyzer = MeetingAnalyzer()
result = await analyzer.complete(
    transcript="Meeting transcript text",
    meeting_type="general",  # Optional: general, project, business, product, report
    custom_prompt="Custom analysis instructions"  # Optional
)
```

### 2. MeetingProcessor (Core Engine)
- Orchestrates the entire analysis workflow
- Uses LangGraph for state management and workflow control
- Integrates multiple specialized processors

### 3. Specialized Processors

#### MeetingTypeDetector
- Automatically detects meeting type from transcript content
- Supports: general, project, business, product, report
- Uses AI to analyze transcript patterns and keywords

#### InformativeChecker
- Determines if transcript contains sufficient meaningful content
- Filters out short or empty transcripts
- Minimum threshold: 100 characters

#### SummaryExtractor
- Extracts structured data from meeting transcripts:
  - **Tasks**: Action items with assignees and deadlines
  - **Decisions**: Key decisions made during the meeting
  - **Questions**: Questions raised and their status

#### SimpleMeetingNoteGenerator
- Generates human-readable meeting notes in Vietnamese
- Creates structured markdown format with:
  - Meeting agenda and summary
  - Key points, facts, problems, solutions
  - Risks and next steps
  - Organized decisions and action items

#### OutputGenerator
- Compiles all extracted information into final output
- Calculates token usage and costs
- Returns structured response with all meeting insights

## Data Models

### MeetingState
```python
class MeetingState(TypedDict):
    messages: List[Message]  # Conversation history
    transcript: str          # Original meeting transcript
    meeting_note: str        # Generated meeting notes
    task_items: List[Dict]   # Extracted tasks
    decision_items: List[Dict] # Extracted decisions
    question_items: List[Dict] # Extracted questions
    token_usage: Dict        # Token consumption data
    is_informative: bool     # Whether transcript has enough content
    meeting_type: str        # Detected/assigned meeting type
    custom_prompt: str       # Optional custom instructions
```

### Task Model
```python
class Task(BaseModel):
    description: str       # Task description
    assignee: str         # Person responsible (defaults to "Chưa xác định")
    deadline: str         # Due date (YYYY-MM-DD format)
    priority: str         # Priority level (cao, trung bình, thấp)
    status: str          # Current status
    related_topic: List[str] # Related topics (normalized)
    notes: str           # Additional notes
```

### Decision Model
```python
class Decision(BaseModel):
    topic: List[str]     # Decision topics
    decision: str        # Decision content
    impact: str         # Expected impact
    timeline: str       # Implementation timeline
    stakeholders: List[str] # Involved parties
    next_steps: List[str] # Follow-up actions
```

### Question Model
```python
class Question(BaseModel):
    question: str       # Question content
    asker: str         # Person who asked
    answer: str        # Answer provided
    answered: bool     # Whether answered
    topic: List[str]   # Related topics
    follow_up_actions: List[Task] # Required follow-up tasks
```

## Usage Examples

### Basic Usage
```python
from app.utils.meeting_agent import MeetingAnalyzer

async def analyze_meeting():
    analyzer = MeetingAnalyzer()

    # Simple meeting analysis
    result = await analyzer.complete(
        transcript="Chúng ta cần hoàn thành dự án trước ngày 30/12. Anh A sẽ phụ trách phần frontend, chị B lo phần backend..."
    )

    print(f"Meeting Note: {result['meeting_note']}")
    print(f"Tasks: {result['task_items']}")
    print(f"Cost: ${result['token_usage']['price_usd']}")
```

### Advanced Usage with Custom Prompt
```python
# Custom prompt for specific meeting types
custom_prompt = """
Hãy tập trung vào các vấn đề kỹ thuật và giải pháp được thảo luận.
Ưu tiên các quyết định liên quan đến công nghệ và timeline thực hiện.
"""

result = await analyzer.complete(
    transcript=transcript,
    meeting_type="product",
    custom_prompt=custom_prompt
)
```

### Batch Processing
```python
# Process multiple meetings
meetings = [
    {"transcript": "Meeting 1...", "type": "project"},
    {"transcript": "Meeting 2...", "type": "business"}
]

for meeting in meetings:
    result = await analyzer.complete(
        transcript=meeting["transcript"],
        meeting_type=meeting["type"]
    )
    # Process results...
```

## Configuration

### Required Dependencies
```python
# Core dependencies
langchain-core
langchain-google-genai
langgraph
pydantic
tiktoken

# Utility dependencies
litellm  # For LLM abstraction
```

### API Configuration
```python
# Requires Google API key for Gemini AI
GOOGLE_API_KEY = "your-api-key-here"

# Token pricing (configurable in app.core.config)
INPUT_PRICE_PER_MILLION = 0.075   # USD per million input tokens
OUTPUT_PRICE_PER_MILLION = 0.3    # USD per million output tokens
CONTEXT_PRICE_PER_MILLION = 0.075 # USD per million context tokens
```

## Implementation Guide

### 1. Setup LLM Integration
```python
from langchain_google_genai import ChatGoogleGenerativeAI

def initialize_llm(api_key: str):
    return ChatGoogleGenerativeAI(
        model='gemini-2.0-flash',
        api_key=api_key,
        temperature=0.3,
    )
```

### 2. Create Workflow Graph
```python
from langgraph.graph import StateGraph, START, END

def build_workflow():
    workflow = StateGraph(MeetingState)

    # Add processing nodes
    workflow.add_node("detect_type", MeetingTypeDetector(llm, tracker).detect)
    workflow.add_node("check_content", InformativeChecker(llm, tracker).check)
    workflow.add_node("extract_tasks", SummaryExtractor(llm, tracker).extract_tasks)
    # ... additional nodes

    # Define workflow edges
    workflow.add_edge(START, "detect_type")
    workflow.add_conditional_edges("check_content",
        lambda state: "extract_tasks" if state["is_informative"] else "generate_output"
    )

    return workflow.compile()
```

### 3. Process Meeting Data
```python
async def process_meeting(transcript: str, custom_prompt: str = None):
    # Initialize state
    initial_state = {
        "messages": [SystemMessage(content="Bạn là trợ lý...")],
        "transcript": transcript,
        "meeting_note": "",
        "task_items": [],
        "decision_items": [],
        "question_items": [],
        "token_usage": {},
        "is_informative": False,
        "meeting_type": "general",
        "custom_prompt": custom_prompt,
    }

    # Execute workflow
    result = await workflow.ainvoke(initial_state, config)

    return {
        "meeting_note": result["meeting_note"],
        "task_items": result["task_items"],
        "decision_items": result["decision_items"],
        "question_items": result["question_items"],
        "token_usage": result["token_usage"],
        "is_informative": result["is_informative"],
        "meeting_type": result["meeting_type"],
    }
```

## Token Management & Cost Tracking

### TokenTracker Class
```python
class TokenTracker:
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.context_tokens = 0

    def add_input_tokens(self, tokens: int)
    def add_output_tokens(self, tokens: int)
    def add_context_tokens(self, tokens: int)

    @property
    def total_tokens(self)
```

### Cost Calculation
```python
def calculate_price(input_tokens: int, output_tokens: int, context_tokens: int = 0) -> float:
    """Calculate total cost in USD based on token usage"""
    input_price = (input_tokens / 1_000_000) * INPUT_PRICE_PER_MILLION
    output_price = (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_MILLION
    context_price = (context_tokens / 1_000_000) * CONTEXT_PRICE_PER_MILLION
    return input_price + output_price + context_price
```

## Output Format

The module returns a comprehensive result dictionary:

```python
{
    "meeting_note": "# 📋 Biên bản cuộc họp\n## Tóm tắt\n[Summary content]...",
    "task_items": [
        {
            "description": "Complete frontend development",
            "assignee": "Anh A",
            "deadline": "2024-12-30",
            "priority": "cao",
            "status": "Chưa bắt đầu"
        }
    ],
    "decision_items": [
        {
            "topic": ["development"],
            "decision": "Use React for frontend",
            "impact": "Improved user experience",
            "stakeholders": ["Anh A", "Chị B"]
        }
    ],
    "question_items": [
        {
            "question": "When is the deployment deadline?",
            "asker": "Chị C",
            "answered": True,
            "answer": "End of December"
        }
    ],
    "token_usage": {
        "input_tokens": 1500,
        "output_tokens": 800,
        "context_tokens": 0,
        "total_tokens": 2300,
        "price_usd": 0.000345
    },
    "is_informative": True,
    "meeting_type": "project"
}
```

## Error Handling

The module includes comprehensive error handling:

- **Empty transcripts**: Returns default structure with empty fields
- **Insufficient content**: Skips detailed extraction, generates simple note
- **API failures**: Graceful fallback with token usage tracking
- **JSON parsing errors**: Attempts multiple parsing strategies

## Performance Considerations

- **Token Efficiency**: Uses transcript sampling for meeting type detection
- **Cost Optimization**: Tracks and reports token usage and costs
- **Processing Speed**: Asynchronous processing with workflow optimization
- **Memory Management**: Uses LangGraph's memory saver for state persistence

## Customization Options

### Adding New Meeting Types
1. Update `valid_types` in `MeetingTypeDetector`
2. Add corresponding prompts in `meeting_prompts.py`
3. Define extraction logic for the new type

### Custom Processing Logic
- Extend `SummaryExtractor` for specialized extraction
- Modify prompts in `meeting_prompts.py`
- Add new workflow nodes in `MeetingProcessor`

## Testing

```python
import pytest
from app.utils.meeting_agent import MeetingAnalyzer

async def test_meeting_analysis():
    analyzer = MeetingAnalyzer()

    # Test with sample transcript
    result = await analyzer.complete(
        transcript="Sample meeting transcript...",
        meeting_type="general"
    )

    assert result["meeting_note"]
    assert result["token_usage"]["total_tokens"] > 0
    assert result["is_informative"] == True
```

This module provides a robust foundation for intelligent meeting analysis with room for customization and extension based on specific organizational needs.
