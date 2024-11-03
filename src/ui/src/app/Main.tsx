import { ResearchCanvas } from "@/components/ResearchCanvas";
import { useModelSelectorContext } from "@/lib/model-selector-provider";
import { AgentState } from "@/lib/types";
import { useCoAgent } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import ScoringTable from "./components/monitoring/Scoringtable";

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
			<div className="container mx-auto border max-w-10xl">
				<h1 className="flex h-[60px] bg-[#0E103D] text-white items-center px-10 text-2xl font-medium">
					Veriver - The Misinformation Analysis Platform
				</h1>
				{/* <ScoringTable /> */}
				<ResearchCanvas />
			</div>
		</>
	);
}
