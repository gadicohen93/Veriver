I'm building an agent that monitors specific Telegram channels for disinformation, flagging potentially false or misleading posts, images, and videos for further review.
Required to use CopilotKit, Langgraph, and use Gemini for video/image analysis, etc. (maybe for example for location identification, etc., specifically to help detect misinformation?)

I am attaching:
* example React components that hook into an example backend CopilotKit agent
* example CopilotKit agent in Python
* example integration with Telegram

Can you write a full PRD with core user flows and a technical outline of the architecture/implementation?

import { ResearchCanvas } from "@/components/ResearchCanvas";
import { useModelSelectorContext } from "@/lib/model-selector-provider";
import { AgentState } from "@/lib/types";
import { useCoAgent } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";

export default function Main() {
  const { model } = useModelSelectorContext();
  const { state, setState } = useCoAgent<AgentState>({
    name: "research_agent",
    initialState: {
      model,
      research_question: "",
      resources: [],
      report: "",
      logs: [],
    },
  });

  return (
    <>
      <h1 className="flex h-[60px] bg-[#0E103D] text-white items-center px-10 text-2xl font-medium">
        Research Helper
      </h1>

      <div
        className="flex flex-1 border"
        style={{ height: "calc(100vh - 60px)" }}
      >
        <div className="flex-1 overflow-hidden">
          <ResearchCanvas />
        </div>
        <div
          className="w-[500px] h-full flex-shrink-0"
          style={
            {
              "--copilot-kit-background-color": "#E0E9FD",
              "--copilot-kit-secondary-color": "#6766FC",
              "--copilot-kit-secondary-contrast-color": "#FFFFFF",
              "--copilot-kit-primary-color": "#FFFFFF",
              "--copilot-kit-contrast-color": "#000000",
            } as any
          }
        >
          <CopilotChat
            className="h-full"
            onSubmitMessage={async (message) => {
              // clear the logs before starting the new research
              setState({ ...state, logs: [] });
              await new Promise((resolve) => setTimeout(resolve, 30));
            }}
            labels={{
              initial: "Hi! How can I assist you with your research today?",
            }}
          />
        </div>
      </div>
    </>
  );
}

"""
This is the main entry point for the AI.
It defines the workflow graph and the entry point for the agent.
"""
# pylint: disable=line-too-long, unused-import
import json
from typing import cast

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from research_canvas.state import AgentState
from research_canvas.download import download_node
from research_canvas.chat import chat_node
from research_canvas.search import search_node
from research_canvas.delete import delete_node, perform_delete_node

# Define a new graph
workflow = StateGraph(AgentState)
workflow.add_node("download", download_node)
workflow.add_node("chat_node", chat_node)
workflow.add_node("search_node", search_node)
workflow.add_node("delete_node", delete_node)
workflow.add_node("perform_delete_node", perform_delete_node)

def route(state):
    """Route after the chat node."""

    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage):
        ai_message = cast(AIMessage, messages[-1])

        if ai_message.tool_calls and ai_message.tool_calls[0]["name"] == "Search":
            return "search_node"
        if ai_message.tool_calls and ai_message.tool_calls[0]["name"] == "DeleteResources":
            return "delete_node"
    if messages and isinstance(messages[-1], ToolMessage):
        return "chat_node"

    return END

memory = MemorySaver()
workflow.set_entry_point("download")
workflow.add_edge("download", "chat_node")
workflow.add_conditional_edges("chat_node", route, ["search_node", "chat_node", "delete_node", END])
workflow.add_edge("delete_node", "perform_delete_node")
workflow.add_edge("perform_delete_node", "chat_node")
workflow.add_edge("search_node", "download")
graph = workflow.compile(checkpointer=memory, interrupt_after=["delete_node"])

"""Demo"""

import os
from dotenv import load_dotenv

load_dotenv()

# pylint: disable=wrong-import-position
from fastapi import FastAPI
import uvicorn
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitSDK, LangGraphAgent
from research_canvas.agent import graph

app = FastAPI()
sdk = CopilotKitSDK(
    agents=[
        LangGraphAgent(
            name="research_agent",
            description="Research agent.",
            agent=graph,
        )
    ],
)

add_fastapi_endpoint(app, sdk, "/copilotkit")

# add new route for health check
@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok"}

def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("research_canvas.demo:app", host="0.0.0.0", port=port, reload=True)





---# Telegram Disinformation Monitor
Product Requirements Document

## Overview
A real-time monitoring system that uses AI to detect and flag potential disinformation in Telegram channels, with a focus on multi-modal analysis (text, images, video) and automated reporting.

### Problem Statement
Disinformation on Telegram spreads rapidly and is difficult to track manually. Current solutions lack:
- Real-time monitoring capabilities
- Multi-modal analysis (text, image, video)
- Automated classification and triage
- Systematic tracking and reporting
- Integration with existing workflows

### Goals
1. Reduce time to detect potential disinformation
2. Increase accuracy of classification
3. Provide clear audit trails
4. Enable rapid response
5. Scale monitoring across multiple channels
6. Generate actionable reports

## User Flows

### 1. Channel Configuration
1. User logs into dashboard
2. Adds new Telegram channels to monitor
3. Sets monitoring parameters:
   - Update frequency
   - Types of content to analyze
   - Alert thresholds
   - Custom keywords/topics

### 2. Real-time Monitoring
1. System continuously monitors configured channels
2. For each new post:
   - Analyzes text content
   - Processes images and videos
   - Checks for manipulation markers
   - Cross-references with known patterns
3. Flags suspicious content for review
4. Generates real-time alerts for high-confidence cases

### 3. Content Review
1. Reviewer opens flagged content queue
2. Views AI analysis results:
   - Confidence scores
   - Detection criteria met
   - Similar past cases
3. Makes determination:
   - Confirm as disinformation
   - Mark as false positive
   - Request additional analysis
4. Adds notes and classification

### 4. Reporting
1. User selects reporting period
2. System generates comprehensive report:
   - Detection statistics
   - Channel analysis
   - Content patterns
   - Response metrics
3. Exports in multiple formats
4. Maintains audit trail

## Technical Architecture

### Frontend Components
```
/components
  /Dashboard
    - ChannelConfig.tsx
    - MonitoringView.tsx
    - ReviewQueue.tsx
    - ReportGenerator.tsx
  /Analysis
    - ContentViewer.tsx
    - AIInsights.tsx
    - ClassificationForm.tsx
  /Common
    - AlertComponent.tsx
    - LoadingStates.tsx
```

### Backend Services

#### 1. Telegram Integration Service
- Handles channel monitoring
- Message extraction
- Media downloading
- Rate limiting
- Authentication

#### 2. Analysis Pipeline
```python
class AnalysisPipeline:
    def __init__(self):
        self.text_analyzer = TextAnalyzer()
        self.image_analyzer = ImageAnalyzer()
        self.video_analyzer = VideoAnalyzer()
        self.cross_referencer = CrossReferencer()

    async def process_content(self, content):
        results = await asyncio.gather(
            self.text_analyzer.analyze(content.text),
            self.image_analyzer.analyze(content.images),
            self.video_analyzer.analyze(content.videos),
            self.cross_referencer.find_patterns(content)
        )
        return self.aggregate_results(results)
```

#### 3. LangGraph Agent Structure
```python
workflow = StateGraph(AgentState)

# Core Nodes
workflow.add_node("monitor", monitor_node)
workflow.add_node("analyze", analysis_node)
workflow.add_node("alert", alert_node)
workflow.add_node("report", report_node)

# Helper Nodes
workflow.add_node("content_download", download_node)
workflow.add_node("classification", classify_node)
workflow.add_node("pattern_matching", pattern_node)

# Conditional Routing
def route_content(state):
    if state.requires_immediate_attention():
        return "alert"
    if state.needs_human_review():
        return "classify"
    return "pattern"

workflow.add_conditional_edges(
    "analyze",
    route_content,
    ["alert", "classify", "pattern"]
)
```

#### 4. CopilotKit Integration
```typescript
interface AgentState {
  channels: Channel[];
  activeAlerts: Alert[];
  reviewQueue: Content[];
  analysisResults: Analysis[];
}

const MonitoringAgent = () => {
  const { state, setState } = useCoAgent<AgentState>({
    name: "monitoring_agent",
    initialState: {
      channels: [],
      activeAlerts: [],
      reviewQueue: [],
      analysisResults: []
    }
  });

  // Agent logic
}
```

### AI Models Integration

#### 1. Text Analysis
- GPT-4 for content analysis
- Custom-trained classifiers for known patterns
- Sentiment and stance detection

#### 2. Image Analysis (Gemini)
```python
async def analyze_image(image):
    results = await gemini.analyze_image(
        image,
        tasks=[
            "manipulation_detection",
            "location_verification",
            "object_recognition",
            "text_extraction"
        ]
    )
    return ImageAnalysisResult(
        manipulation_score=results.manipulation_confidence,
        location_match=results.location_verification,
        detected_objects=results.objects,
        extracted_text=results.text
    )
```

#### 3. Video Analysis
- Frame extraction and analysis
- Audio transcription
- Metadata verification
- Deepfake detection

## Performance Requirements
- Real-time monitoring with <5 minute delay
- Analysis pipeline completion <30 seconds per item
- 99.9% system uptime
- Support for 1000+ concurrent channels
- <1% false positive rate for high-confidence alerts

## Security Requirements
- End-to-end encryption
- Role-based access control
- Audit logging
- Data retention policies
- API authentication
- Secure storage of sensitive data

## Monitoring and Metrics
- System health metrics
- Detection accuracy metrics
- Response time tracking
- Resource utilization
- User engagement metrics
- Alert response times

## Future Enhancements
1. API for external integrations
2. Mobile app for alerts
3. Advanced pattern recognition
4. Automated response capabilities
5. Cross-platform monitoring
6. Community contribution features